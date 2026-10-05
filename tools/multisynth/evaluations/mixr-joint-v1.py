"""Equal-attempt single vs joint two-voice search on fixed external development cases."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.composition import CompositionRenderer
from multisynth.renderer import Renderer
from multisynth.joint_refine import MixSpace, optimize
from multisynth.coverage import verify_archived_audio, copy_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture_eval import write_wave, read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth')
ROOT=BASE/'runs/mixr-joint-v1'
GALLERY=BASE/'runs/mixr-joint-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-mixr-transfer-v1-quick-01'
PRIOR=BASE/'runs/mixr-transfer-v1/results.json'
METRIC=BASE/'models/preference-neural-v2.json'
PLAN=Path('docs/superpowers/plans/2026-10-06-mixr-joint-fit.md')
CODE=[Path(__file__),Path('tools/multisynth/joint_refine.py'),Path('tools/multisynth/search.py'),
      Path('tools/multisynth/soft_periodicity.py'),Path('tools/multisynth/preference.py'),
      Path('tools/multisynth/features.py'),Path('tools/multisynth/gesture.py'),
      Path('tools/multisynth/renderer.py'),Path('tools/match/structure.py'),Path('tools/match/objective.py'),Path('tools/match/features.py'),
      Path('tools/match/audio.py'),Path('tools/neural_invert/experiment.py')]


def bindings():return {str(p):file_hash(p) for p in CODE}


def starts(pool,key):
    ordered=sorted(pool,key=lambda c:c[key]);selected=[];seen=set()
    for c in ordered:
        signature=tuple(sorted(s['synth'] for s in json.loads(c['params']['sources']) if s))
        if signature in seen:continue
        selected.append(c);seen.add(signature)
        if len(selected)==4:break
    for c in ordered:
        if len(selected)==4:break
        if all(c['params']!=s['params'] for s in selected):selected.append(c)
    assert len(selected)==4
    return selected


def freeze():
    if ROOT.exists():raise FileExistsError('Preserve prior run')
    prior=json.loads(PRIOR.read_text());manifest=json.loads((ARCHIVE/'manifest.json').read_text())
    assert prior['complete'] and len(prior['rows'])==len(manifest['targets'])==4
    candidates={c['id']:c for c in manifest['candidates']};entries=[]
    for row in prior['rows']:
        t=next(t for t in manifest['targets'] if t['source']['name']==row['target']['source']['name'])
        verify_archived_audio(ARCHIVE,t['referenceAudio'])
        cid=(t['choice']['preferredCandidateIds'][0] if t['choice']['kind']=='best' else
             next(c['id'] for c in t['candidates'] if c['role']=='previous'))
        retained=candidates[cid];verify_archived_audio(ARCHIVE,retained['audio'])
        arms={f'{structure}-{metric}':starts(row[pool],metric)
              for structure,pool in [('single','singles'),('pair','mixed')] for metric in ('soft','preference')}
        for selected in arms.values():
            for c in selected:read_wave(c)
        entries.append(dict(target=t,retained=retained,starts=arms))
    with CompositionRenderer() as r:inventory=r.inventory
    with Renderer() as r:
        assert r.inventory['sourceHash']==inventory['baseSourceHash']
        specs=r.specs
    protocol=dict(complete=True,entries=entries,inventory=inventory,specs=specs,bindings=bindings(),
        priorReportSha256=file_hash(PRIOR),archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),
        metricSha256=file_hash(METRIC),planSha256=file_hash(PLAN),budgetPerArm=512,seed=20261019,
        scope='Repeated external development cases. Actual DSP search, not neural retraining. Equal mutation attempts and four starts per arm; not equal capacity, prior search cost or wall time. Source identities/seeds fixed; controls co-adapt; no delay or reference waveform layers.',
        selection='Eight trials: four references per scorer, each with exact earlier control and that scorer single/pair winners. Exact audition duplicates removed; no outcome-based target exclusion.')
    ROOT.mkdir();_json_write(ROOT/'protocol.json',protocol)
    _json_write(BASE/'evaluations/mixr-joint-v1-protocol.json',
        {k:v for k,v in protocol.items() if k not in ('entries','specs')}|
        dict(protocolSha256=file_hash(ROOT/'protocol.json'),specsSha256=__import__('hashlib').sha256(json.dumps(specs,sort_keys=True).encode()).hexdigest(),
             targets=[dict(name=e['target']['source']['name'],retained=e['retained']['id'],
                           starts={k:[c['audioHash'] for c in v] for k,v in e['starts'].items()}) for e in entries]))
    print(json.dumps(dict(frozen=len(entries),arms=16,attempts=8192)),flush=True)


def verify(p):
    receipt=json.loads((BASE/'evaluations/mixr-joint-v1-protocol.json').read_text())
    assert receipt['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert p['bindings']==bindings() and p['planSha256']==file_hash(PLAN)
    assert p['priorReportSha256']==file_hash(PRIOR) and p['archiveManifestSha256']==file_hash(ARCHIVE/'manifest.json')
    assert p['metricSha256']==file_hash(METRIC)


def run_one(index):
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    entry=p['entries'][index];folder=ROOT/f'{index+1:03d}'
    if folder.exists():raise FileExistsError('Inspect interrupted output before retry')
    folder.mkdir();begin=time.monotonic()
    ref,rate=sf.read(ARCHIVE/entry['target']['referenceAudio']['file'],dtype='float32');assert rate==44100
    verify_archived_audio(ARCHIVE,entry['target']['referenceAudio'])
    soft=SoftPeriodicityObjective(ref);metric=PreferenceMetric.load(METRIC);target_desc=describe(ref);legacy=MatchObjective(ref)
    scorers=dict(soft=lambda w:float(soft.score(w)),preference=lambda w:float(metric.distances(target_desc,describe(w))[0]))
    arms={}
    with CompositionRenderer() as renderer:
        assert renderer.inventory==p['inventory'];space=MixSpace(p['specs'])
        for ai,(arm,initial) in enumerate(entry['starts'].items()):
            objective=arm.split('-')[1];calls=0
            def evaluate(params):
                nonlocal calls
                canonical,wave=renderer.render(params);heard=audition_pcm(wave)
                if not len(heard) or np.max(np.abs(heard))<1e-6:raise ValueError('Silent candidate')
                score=scorers[objective](heard);calls+=1
                if calls%128==0:print(json.dumps(dict(target=index+1,arm=arm,renders=calls)),flush=True)
                return canonical,score
            result=optimize([c['params'] for c in initial],space,evaluate,budget=p['budgetPerArm'],seed=p['seed']+index*100+ai)
            params,wave=renderer.render(result['params']);canonical,uncached=renderer.render(params,uncached=True)
            assert canonical==params and np.array_equal(wave,uncached)
            heard=audition_pcm(wave);scores={k:f(heard) for k,f in scorers.items()}
            assert abs(scores[objective]-result['score'])<1e-7 and np.all(np.diff(result['trace'])<=0)
            result.update(**write_wave(folder/(arm+'.wav'),wave),scores={**scores,'legacy':float(legacy.score(heard))},
                          auditionHash=audio_hash(heard),nativeReplay=True,sourceHash=renderer.inventory['sourceHash'],
                          sourceSynths=[s['synth'] for s in json.loads(params['sources']) if s])
            arms[arm]=result;_json_write(folder/(arm+'.json'),result)
            print(json.dumps(dict(done=index+1,arm=arm,initial=result['initialScore'],final=result['score'],failures=result['failures'])),flush=True)
    row=dict(target=entry['target'],retained=entry['retained'],arms=arms,seconds=time.monotonic()-begin,complete=True)
    _json_write(folder/'result.json',row);return row


def run():
    p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    if (ROOT/'results.json').exists():raise FileExistsError('Preserve experiment')
    with ProcessPoolExecutor(max_workers=2) as executor:
        futures={executor.submit(run_one,i):i for i in range(4)};rows={}
        for f in as_completed(futures):rows[futures[f]]=f.result()
    rows=[rows[i] for i in range(4)];verify(p)
    result=dict(complete=True,rows=rows,protocolSha256=file_hash(ROOT/'protocol.json'),bindings=bindings())
    _json_write(ROOT/'results.json',result)
    _json_write(BASE/'evaluations/mixr-joint-v1-evaluation.json',dict(complete=True,protocolSha256=result['protocolSha256'],
        reportSha256=file_hash(ROOT/'results.json'),scope=p['scope'],rows=[dict(name=r['target']['source']['name'],seconds=r['seconds'],
        arms={k:{f:v[f] for f in ('initialScore','score','scores','attempts','initialRenders','failures','nativeReplay','auditionHash','sourceSynths')} for k,v in r['arms'].items()}) for r in rows]))


def gallery():
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    report=json.loads((ROOT/'results.json').read_text());assert report['complete'] and len(report['rows'])==4
    assert report['protocolSha256']==file_hash(ROOT/'protocol.json') and report['bindings']==bindings()
    if GALLERY.exists():raise FileExistsError('Preserve published page')
    GALLERY.mkdir();records=[]
    with CompositionRenderer() as renderer:
        assert renderer.inventory==p['inventory']
        # Separate scorer blocks, preserving all four references in each.
        for scorer in ('soft','preference'):
            for row in report['rows']:
                folder=GALLERY/f'{len(records)+1:03d}';folder.mkdir();t=row['target'];earlier=row['retained']
                verify_archived_audio(ARCHIVE,t['referenceAudio'])
                verify_archived_audio(ARCHIVE,earlier['audio'])
                copy_archived_audio(ARCHIVE/t['referenceAudio']['file'],folder/'target.wav')
                copy_archived_audio(ARCHIVE/earlier['audio']['file'],folder/'previous.wav')
                old,_=sf.read(folder/'previous.wav',dtype='float32');seen={audio_hash(old)}
                options=[{**earlier,'role':'previous','file':'previous.wav','label':'Earlier comparison',
                    'provenance':{**earlier['provenance'],'retainedArchive':str(ARCHIVE),'retainedCandidateId':earlier['id'],
                                  'archiveManifestSha256':file_hash(ARCHIVE/'manifest.json'),'auditionTransform':'Exact archived PCM'}}]
                for structure in ('single','pair'):
                    arm=f'{structure}-{scorer}';c=row['arms'][arm]
                    params,wave=renderer.render(c['params'],uncached=True)
                    assert params==c['params'] and np.array_equal(wave,read_wave(c))
                    heard=audition_pcm(wave);assert audio_hash(heard)==c['auditionHash']
                    if c['auditionHash'] in seen:continue
                    seen.add(c['auditionHash']);filename=structure+'.wav';sf.write(folder/filename,heard,44100,subtype='PCM_16')
                    check,rate=sf.read(folder/filename,dtype='float32');assert rate==44100 and np.array_equal(check,heard)
                    options.append(dict(synth='Mixr',params=params,seed=0,sourceHash=p['inventory']['sourceHash'],role=structure,
                        label='Refitted single voice' if structure=='single' else 'Jointly fitted two voices',file=filename,
                        provenance=dict(method='actual-Mixr-joint-search',arm=arm,protocolSha256=file_hash(ROOT/'protocol.json'),
                            reportSha256=file_hash(ROOT/'results.json'),renderSourceHash=p['inventory']['sourceHash'],
                            searchAttempts=c['attempts'],searchSeed=c['seed'],initialScore=c['initialScore'],
                            softPeriodicity=c['scores']['soft'],preferenceNeuralV2=c['scores']['preference'],
                            auditionMatchObjective=c['scores']['legacy'],auditionHash=c['auditionHash'],actualMixrReplay=True)))
                assert 2<=len(options)<=3
                records.append(dict(folder=folder.name,source=t['source'],candidates=options,
                    note='Repeated external reference: earlier comparison, equally budgeted single voice, and jointly fitted pair.'))
    metadata=dict(complete=True,experiment='mixr-joint-v1-listening',targetCount=8,
        galleryTitle='Can fitting voices together improve these sounds?',galleryIntro=[
            'Eight short comparisons, using four external sounds twice with two different ways of choosing the fit.',
            'Each compares an earlier sound with a newly fitted single voice and two voices fitted together. Exact duplicates are removed.',
            'Choose the closest, then how close. These are actual synth patches, with no reference audio used as a layer. This tests fitting, not a newly trained neural model.'],
        scope=p['scope'],selectionPolicy=p['selection'],protocolSha256=file_hash(ROOT/'protocol.json'),
        reportSha256=file_hash(ROOT/'results.json'),scriptSha256=file_hash(__file__),humanReviewRequired=True,
        uiCodeHashes={q.name:file_hash(q) for q in BASE.glob('quick_*') if q.is_file()})
    model=export_coverage(GALLERY,records,metadata)
    receipt=dict(complete=True,experimentId=model['experimentId'],targetCount=8,optionCounts=[len(r['candidates']) for r in records],
        resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),scriptSha256=file_hash(__file__),
        audioFiles={str(q.relative_to(GALLERY)):file_hash(q) for q in sorted(GALLERY.glob('*/*.wav'))})
    _json_write(BASE/'evaluations/mixr-joint-v1-listening-audit.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('experimentId','targetCount','optionCounts')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run','gallery']);args=parser.parse_args()
    {'freeze':freeze,'run':run,'gallery':gallery}[args.stage]()
