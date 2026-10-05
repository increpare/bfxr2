"""Actual two-source Mixr coverage probe on four frozen external development references."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.composition import CompositionRenderer
from multisynth.coverage import verify_archived_audio,copy_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture_eval import write_wave,read_wave
from neural_invert.data import file_hash,_json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth')
ROOT=BASE/'runs/mixr-transfer-v1'
GALLERY=BASE/'runs/mixr-transfer-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-off-model-transfer-v1-quick-02'
PRIOR=BASE/'runs/off-model-transfer-v1/results.json'
METRIC=BASE/'models/preference-neural-v2.json'
PLAN=Path('docs/superpowers/plans/2026-10-06-mixr-transfer-probe.md')
NAMES=['hit/FOLYClth_SinglePats04_InMotionAudio_FoleyT-Shirt.wav','door/doorClose_3.ogg','laser/laser1.ogg','clothes/cloth4.ogg']


def freeze():
    if ROOT.exists():raise FileExistsError('Preserve prior probe')
    m=json.loads((ARCHIVE/'manifest.json').read_text())
    prior=json.loads(PRIOR.read_text()); assert prior['complete']
    candidates={c['id']:c for c in m['candidates']}
    targets=[]
    for name in NAMES:
        target=next(t for t in m['targets'] if t['source']['name']==name)
        row=next(r for r in prior['rows'] if r['target']['source']['name']==name)
        verify_archived_audio(ARCHIVE,target['referenceAudio'])
        choice=target['choice']
        if choice['kind']=='best': cid=choice['preferredCandidateIds'][0]
        else:
            assert choice['kind']=='none'
            cid=next(c['id'] for c in target['candidates'] if c['role']=='soft')
        retained=candidates[cid];verify_archived_audio(ARCHIVE,retained['audio'])
        targets.append(dict(target=target,retained=retained,priorRow=row))
    with CompositionRenderer() as renderer: inventory=renderer.inventory
    ROOT.mkdir()
    protocol=dict(complete=True,targets=targets,inventory=inventory,archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),
        priorReportSha256=file_hash(PRIOR),metricSha256=file_hash(METRIC),scriptSha256=file_hash(__file__),
        planSha256=file_hash(PLAN),poolSize=12,maxPerSynth=2,balances=[.2,.35,.5,.65,.8],
        selection='Alternating soft/preference ranks, unique PCM and maximum2 per synth. Test every pair and five balances; soft winner enters listening alongside soft-best single and exact prior candidate.',
        seedPolicy='Map saved uint32 render seed to float seed/4294967295, then canonicalize and re-render with native Mixr source semantics. Do not claim source PCM unchanged.',
        scope='Four repeated external development sources, not held-out validation. No inverse retraining. Original Bfxr source controls may reflect old real-audio fitting. Footsteppr excluded from this bridge.')
    _json_write(ROOT/'protocol.json',protocol)
    # Compact tracked protocol retains target/source identities, not the large raw pool.
    _json_write(BASE/'evaluations/mixr-transfer-v1-protocol.json',{k:v for k,v in protocol.items() if k!='targets'}|
        dict(targets=[dict(source=t['target']['source'],referenceAudio=t['target']['referenceAudio'],
            retainedCandidateId=t['retained']['id'],priorFolder=t['priorRow'].get('folder')) for t in targets],
            protocolSha256=file_hash(ROOT/'protocol.json')))
    print(json.dumps(dict(frozen=NAMES,sourceHash=inventory['sourceHash'])),flush=True)


def run():
    p=json.loads((ROOT/'protocol.json').read_text())
    assert p['scriptSha256']==file_hash(__file__) and p['planSha256']==file_hash(PLAN)
    assert p['archiveManifestSha256']==file_hash(ARCHIVE/'manifest.json')
    assert p['priorReportSha256']==file_hash(PRIOR) and p['metricSha256']==file_hash(METRIC)
    assert not (ROOT/'results.json').exists()
    torch.set_num_threads(1);metric=PreferenceMetric.load(METRIC);rows=[]
    with CompositionRenderer() as renderer:
        assert renderer.inventory==p['inventory']
        for index,entry in enumerate(p['targets']):
            folder=ROOT/f'{index+1:03d}'
            if folder.exists():raise FileExistsError('Inspect interrupted experiment before retry')
            folder.mkdir();started=time.monotonic()
            target=entry['target'];verify_archived_audio(ARCHIVE,target['referenceAudio'])
            ref,sr=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert sr==44100
            copy_archived_audio(ARCHIVE/target['referenceAudio']['file'],folder/'target.wav')
            soft=SoftPeriodicityObjective(ref);legacy=MatchObjective(ref);desc=describe(ref)
            def scores(wave):
                heard=audition_pcm(wave)
                return dict(soft=float(soft.score(heard)),preference=float(metric.distances(desc,describe(heard))[0]),
                    legacy=float(legacy.score(heard)),auditionHash=audio_hash(heard))
            def save(params,wave,filename,extra):
                saved,actual=renderer.render(params,uncached=True)
                assert saved==params and np.array_equal(wave,actual)
                return dict(params=params,**write_wave(folder/filename,wave),**scores(wave),**extra)
            raw=entry['priorRow']['raw']+entry['priorRow']['refined']+[entry['priorRow']['original']]
            singles=[];excluded=[];seen=set()
            for i,c in enumerate(raw):
                if c['synth'] not in renderer.inventory['sources']:
                    excluded.append(dict(index=i,synth=c['synth'],reason='unsupported source'));continue
                # Verify source snapshot before using its controls. Its waveform is not mixed directly.
                read_wave(c)
                source=dict(synth=c['synth'],name=c['synth'],params=c['params'],renderSeed=int(c['seed'])/4294967295)
                requested=dict(sources=json.dumps([source,None]),masterVolume=.5,balance=.5,seed=.5)
                params,wave=renderer.render(requested)
                if np.max(np.abs(wave))<1e-6:excluded.append(dict(index=i,synth=c['synth'],reason='silent'));continue
                stamp=scores(wave)
                if stamp['auditionHash'] in seen:continue
                seen.add(stamp['auditionHash'])
                canonical_source=json.loads(params['sources'])[0]
                singles.append(save(params,wave,f'single-{i:03d}.wav',dict(index=i,source=canonical_source,
                    parentOrigin=c['origin'],parentAudioHash=c['audioHash'],parentRenderSeed=c['seed'])))
            assert len(singles)>=12
            ranked=[sorted(range(len(singles)),key=lambda i:singles[i][key]) for key in ('soft','preference')]
            pool=[];synth_counts={}
            for rank in range(len(singles)):
                for order in ranked:
                    i=order[rank];name=singles[i]['source']['synth']
                    if i in pool or synth_counts.get(name,0)>=p['maxPerSynth']:continue
                    pool.append(i);synth_counts[name]=synth_counts.get(name,0)+1
                    if len(pool)==p['poolSize']:break
                if len(pool)==p['poolSize']:break
            assert len(pool)==12
            print(json.dumps(dict(target=index+1,phase='pairs',pool=[singles[i]['source']['synth'] for i in pool])),flush=True)
            mixed=[]
            for a,b in combinations(pool,2):
                for balance in p['balances']:
                    requested=dict(sources=json.dumps([singles[a]['source'],singles[b]['source']]),
                        balance=balance,masterVolume=.5,seed=.5)
                    params,wave=renderer.render(requested)
                    # Cached actual DSP output is retained; uncached replay is mandatory for finalists.
                    mixed.append(dict(params=params,sourceIndices=[a,b],balance=balance,**scores(wave),
                        **write_wave(folder/f'mix-{len(mixed):03d}.wav',wave)))
            assert len(mixed)==330
            best=min(mixed,key=lambda c:c['soft']);single=min(singles,key=lambda c:c['soft'])
            for c in (best,single):
                params,wave=renderer.render(c['params'],uncached=True)
                assert params==c['params'] and np.array_equal(wave,read_wave(c))
                assert scores(wave)=={k:c[k] for k in ('soft','preference','legacy','auditionHash')}
            row=dict(complete=True,target=target,retained=entry['retained'],singles=singles,mixed=mixed,pool=pool,
                selectedMix=best,selectedSingle=single,preferenceMix=min(mixed,key=lambda c:c['preference']),excluded=excluded,
                seconds=time.monotonic()-started,protocolSha256=file_hash(ROOT/'protocol.json'),sourceHash=p['inventory']['sourceHash'])
            _json_write(folder/'result.json',row);rows.append(row)
            print(json.dumps(dict(done=index+1,single=single['soft'],mix=best['soft'],seconds=round(row['seconds'],1))),flush=True)
    result=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),scriptSha256=file_hash(__file__),rows=rows)
    _json_write(ROOT/'results.json',result)
    _json_write(BASE/'evaluations/mixr-transfer-v1-evaluation.json',dict(complete=True,
        reportSha256=file_hash(ROOT/'results.json'),protocolSha256=file_hash(ROOT/'protocol.json'),scriptSha256=file_hash(__file__),
        rows=[dict(name=r['target']['source']['name'],singles=len(r['singles']),mixes=len(r['mixed']),excluded=r['excluded'],
            singleSoft=r['selectedSingle']['soft'],mixSoft=r['selectedMix']['soft'],
            singlePreference=r['selectedSingle']['preference'],mixPreference=r['selectedMix']['preference'],
            sourceSynths=[s['synth'] for s in json.loads(r['selectedMix']['params']['sources'])],balance=r['selectedMix']['balance']) for r in rows],
        scope=p['scope']))


def gallery():
    torch.set_num_threads(1)
    if GALLERY.exists():raise FileExistsError('Preserve published listening page')
    p=json.loads((ROOT/'protocol.json').read_text());report=json.loads((ROOT/'results.json').read_text())
    assert report['complete'] and len(report['rows'])==4 and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert p['scriptSha256']==file_hash(__file__) and p['archiveManifestSha256']==file_hash(ARCHIVE/'manifest.json')
    GALLERY.mkdir();records=[]
    with CompositionRenderer() as renderer:
        assert renderer.inventory==p['inventory']
        for i,row in enumerate(report['rows']):
            folder=GALLERY/f'{i+1:03d}';folder.mkdir()
            target=row['target'];copy_archived_audio(ARCHIVE/target['referenceAudio']['file'],folder/'target.wav')
            earlier=row['retained'];verify_archived_audio(ARCHIVE,earlier['audio'])
            copy_archived_audio(ARCHIVE/earlier['audio']['file'],folder/'previous.wav')
            old,sr=sf.read(folder/'previous.wav',dtype='float32');assert sr==44100
            seen={audio_hash(old)}
            options=[{**earlier,'role':'previous','label':'Earlier single voice','file':'previous.wav',
                'provenance':{**earlier['provenance'],'retainedArchive':str(ARCHIVE),'retainedCandidateId':earlier['id'],
                    'archiveManifestSha256':file_hash(ARCHIVE/'manifest.json'),'auditionTransform':'Exact archived PCM'}}]
            for role,key in [('single','selectedSingle'),('selected','selectedMix')]:
                c=row[key];params,wave=renderer.render(c['params'],uncached=True)
                assert params==c['params'] and np.array_equal(wave,read_wave(c))
                heard=audition_pcm(wave);assert audio_hash(heard)==c['auditionHash']
                if c['auditionHash'] in seen:continue
                seen.add(c['auditionHash']);name=role+'.wav';sf.write(folder/name,heard,44100,subtype='PCM_16')
                decoded,rate=sf.read(folder/name,dtype='float32');assert rate==44100 and np.array_equal(decoded,heard)
                options.append(dict(synth='Mixr',params=params,seed=0,sourceHash=p['inventory']['sourceHash'],
                    role=role,label='Two synth voices' if role=='selected' else 'New single voice',file=name,
                    provenance=dict(method='actual-Mixr-pair-search' if role=='selected' else 'actual-Mixr-single-control',
                        protocolSha256=file_hash(ROOT/'protocol.json'),reportSha256=file_hash(ROOT/'results.json'),
                        compositionInventory=p['inventory'],softPeriodicity=c['soft'],preferenceNeuralV2=c['preference'],
                        auditionMatchObjective=c['legacy'],auditionHash=c['auditionHash'],auditionWavSha256=file_hash(folder/name),
                        auditionTransform='Single peak normalization and PCM16',actualMixrReplay=True)))
            assert 2<=len(options)<=3
            records.append(dict(folder=folder.name,source=target['source'],candidates=options,
                note='Repeated external reference: earlier option, newly rendered single voice, and two-source Mixr. Choose closest and how close.'))
    metadata=dict(experiment='mixr-transfer-v1-listening',complete=True,targetCount=4,
        galleryTitle='Can two synth voices improve these recreations?',galleryIntro=[
            'Four external sounds: three rejected cases and one roughly similar cloth sound.',
            'Compare the earlier option with a new single voice and a two-voice Mixr patch. All options are actual synth renders; no reference audio is used as a layer.',
            'Choose the closest, then how close. This tests composition search, not a newly trained neural model.'],
        scope=p['scope'],selectionPolicy=p['selection'],humanReviewRequired=True,scriptSha256=file_hash(__file__),
        reportSha256=file_hash(ROOT/'results.json'),protocolSha256=file_hash(ROOT/'protocol.json'),
        uiCodeHashes={q.name:file_hash(q) for q in BASE.glob('quick_*') if q.is_file()})
    model=export_coverage(GALLERY,records,metadata)
    _json_write(BASE/'evaluations/mixr-transfer-v1-listening-audit.json',dict(complete=True,experimentId=model['experimentId'],
        targetCount=4,optionCounts=[len(r['candidates']) for r in records],resultsSha256=file_hash(GALLERY/'results.json'),
        htmlSha256=file_hash(GALLERY/'index.html'),scriptSha256=file_hash(__file__),
        audioFiles={str(q.relative_to(GALLERY)):file_hash(q) for q in sorted(GALLERY.glob('*/*.wav'))}))
    print(json.dumps(dict(experimentId=model['experimentId'],options=[len(r['candidates']) for r in records])),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run','gallery']);args=parser.parse_args()
    {'freeze':freeze,'run':run,'gallery':gallery}[args.stage]()
