"""Frozen eight-file off-model transfer test with scorer alternatives and original Bfxr."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch

from match.audio import prepare_target
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.cli import AUDIO_SUFFIXES, source_info
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture import load as load_mixture
from neural_invert.coverage_mixture_eval import write_wave, read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.evaluate import OriginalBfxr, rendered_candidates, refine_candidate, serializable
from neural_invert.experiment import audition_pcm
from neural_invert.predict import load_model, predict
from neural_invert.temporal import predict_temporal

from multisynth.soft_periodicity import SoftPeriodicityObjective
BASE = Path('tools/multisynth')
OUT = BASE/'runs/off-model-transfer-v1'
GALLERY = BASE/'runs/off-model-transfer-v1-listening'
CORPUS = Path('/Users/stephenlavelle/Documents/bfxr2/tools/targets_non_bfxr_big/tags')
PLAN = Path('docs/superpowers/plans/2026-10-06-off-model-transfer.md')
SHARED = BASE/'runs/neural-v2/acoustic-model'
MIXTURE = BASE/'runs/native-mixture-v1/models/mixture'
SPECIALISTS = BASE/'runs/specialists-v1/models'
SQUISHR = BASE/'runs/squishr-v1/model'
BFXR = Path('/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt')
METRIC = BASE/'models/preference-neural-v2.json'
SEED = 20261201
TAGS = ('footstep','clothes','hit','chains','door','bell','laser','collect')

class AuditionObjective(MatchObjective):
    def score_batch(self,waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])

class SoftAudition(SoftPeriodicityObjective):
    def score_batch(self,waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])

class PreferenceObjective:
    def __init__(self,reference,metric):
        self.target=describe(reference)
        self.metric=metric
    def score_batch(self,waves):
        return np.asarray([float(self.metric.distances(self.target,describe(audition_pcm(w)))[0])
            if w is not None and len(w) else 1e6 for w in waves])

def freeze():
    if OUT.exists():
        raise FileExistsError('Fresh target freeze required')
    paths = {'shared':SHARED/'best.pt', 'Transfxr':MIXTURE/'best.pt',
        'Boomr':SPECIALISTS/'Boomr/best.pt', 'Footsteppr':SPECIALISTS/'Footsteppr/best.pt', 'Squishr':SQUISHR/'best.pt', 'originalBfxr':BFXR}
    hashes = {k:file_hash(p) for k,p in paths.items()}
    prior_hashes, prior_pcm, archives = set(), set(), {}
    for path in sorted((BASE/'listening_data').glob('*/manifest.json')):
        archives[str(path)] = file_hash(path)
        manifest = json.loads(path.read_text())
        for target in manifest['targets']:
            prior_hashes.add(target['source'].get('sha256'))
            verify_archived_audio(path.parent, target['referenceAudio'])
            pcm, rate = sf.read(path.parent/target['referenceAudio']['file'], dtype='float32')
            assert rate == 44100
            prior_pcm.add(audio_hash(pcm))
    rng = np.random.default_rng(SEED)
    rows, rejected = [], []
    for tag in TAGS:
        paths = sorted(p for p in (CORPUS/tag).rglob('*') if p.suffix.lower() in AUDIO_SUFFIXES and p.is_file())
        rng.shuffle(paths)
        for path in paths:
            reason = None
            info = sf.info(path)
            if not .025 <= info.duration <= 1.8:
                reason = 'duration'
            elif file_hash(path) in prior_hashes:
                reason = 'previously-judged-file'
            else:
                wave = audition_pcm(prepare_target(path))
                if not len(wave) or np.max(np.abs(wave)) < 1e-6:
                    reason = 'silence'
                elif audio_hash(wave) in prior_pcm:
                    reason = 'previously-judged-or-selected-pcm'
            if reason:
                rejected.append(dict(name=str(path.relative_to(CORPUS)),reason=reason))
                continue
            prior_pcm.add(audio_hash(wave))
            rows.append(dict(source=source_info(path,CORPUS), tag=tag, sourceSeconds=info.duration,
                auditionHash=audio_hash(wave), auditionSamples=len(wave), seed=SEED+len(rows)*1009))
            break
        else:
            raise ValueError('No eligible unjudged reference in '+tag)
    assert len(rows)==8
    OUT.mkdir()
    for i, row in enumerate(rows):
        folder=OUT/f'{i+1:03d}'
        folder.mkdir()
        wave=audition_pcm(prepare_target(row['source']['path']))
        assert audio_hash(wave)==row['auditionHash']
        sf.write(folder/'target.wav',wave,44100,subtype='PCM_16')
        row['referenceWavSha256']=file_hash(folder/'target.wav')
    _json_write(OUT/'targets.json',dict(complete=True, rows=rows, rejected=rejected, priorArchives=archives,
        scriptSha256=file_hash(__file__), designSha256=file_hash(PLAN), checkpoints=hashes,
        preferenceMetricSha256=file_hash(METRIC), seed=SEED,
        policy='Freeze eight short tagged sources before inference; exclude previously judged exact files and PCM. Categories are sampling strata, never model inputs. Not a family-disjoint test.',
        oldPool='shared22 two/head + Transfxr mixture four + original Bfxr legacy2000',
        newPool='Boomr Footsteppr Squishr four/head; combine neural pools; two distinct engine starts per scorer soft/preference,128/start',
        listeningPolicy='Soft winner, preference winner, original Bfxr; deduplicate exact PCM then highest-ranked distinct preference alternative if fewer than three. All eight references, no score-based dropping.',
        codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/predict.py'),Path('tools/neural_invert/temporal.py'),Path('tools/neural_invert/evaluate.py'),Path('tools/multisynth/soft_periodicity.py'),Path('tools/multisynth/preference.py')]}))
    print(json.dumps(dict(frozen=[r['source']['name'] for r in rows],sha256=file_hash(OUT/'targets.json'))),flush=True)


def run():
    frozen=json.loads((OUT/'targets.json').read_text())
    assert frozen['scriptSha256']==file_hash(__file__)
    for p,h in frozen['codeHashes'].items(): assert file_hash(p)==h
    assert not (OUT/'results.json').exists()
    torch.set_num_threads(1)
    shared=load_model(SHARED); mixture=load_mixture(MIXTURE)
    specialists={name:load_model(SQUISHR if name=='Squishr' else SPECIALISTS/name)
        for name in ('Boomr','Footsteppr','Squishr')}
    for name,meta in [('shared',shared[1]),('Transfxr',mixture[1])]+[(n,m[1]) for n,m in specialists.items()]:
        assert meta['checkpointHash']==frozen['checkpoints'][name]
    assert file_hash(BFXR)==frozen['checkpoints']['originalBfxr']
    assert file_hash(METRIC)==frozen['preferenceMetricSha256']
    metric=PreferenceMetric.load(METRIC)
    rows=[]
    with Renderer() as renderer, BfxrRenderer(jobs=1) as bfxr:
        for _,meta in [shared,mixture,*specialists.values()]:
            assert meta['sourceHash']==renderer.inventory['sourceHash']
        original=OriginalBfxr(BFXR,bfxr)
        for index,target in enumerate(frozen['rows']):
            dest=OUT/f'{index+1:03d}'
            assert file_hash(dest/'target.wav')==target['referenceWavSha256']
            reference,rate=sf.read(dest/'target.wav',dtype='float32')
            assert rate==44100 and audio_hash(reference)==target['auditionHash']
            soft=SoftAudition(reference); legacy=AuditionObjective(reference)
            preference=PreferenceObjective(reference,metric)
            objectives={'soft':soft,'preference':preference}
            def save(c,filename):
                exact_replay(c,renderer,bfxr)
                heard=audition_pcm(c['wave'])
                return {**serializable(c),**write_wave(dest/filename,c['wave']),
                    'sourceHash':renderer.inventory['sourceHash'],'auditionHash':audio_hash(heard),
                    'softDistance':float(soft.score_batch([c['wave']])[0]),
                    'preferenceDistance':float(preference.score_batch([c['wave']])[0]),
                    'legacyDistance':float(legacy.score_batch([c['wave']])[0])}
            if (dest/'result.json').exists():
                row=json.loads((dest/'result.json').read_text())
                assert row['complete'] and row['target']==target
                assert row['targetsSha256']==file_hash(OUT/'targets.json')
                for c in row['raw']+row['refined']+[row['original']]:
                    assert c['sourceHash']==renderer.inventory['sourceHash']
                    wave=read_wave(c); exact_replay({**c,'wave':wave},renderer,bfxr)
                    assert audio_hash(audition_pcm(wave))==c['auditionHash']
                    for field,obj in [('softDistance',soft),('preferenceDistance',preference),('legacyDistance',legacy)]:
                        assert abs(float(obj.score_batch([wave])[0])-c[field])<1e-6
                rows.append(row); continue
            # Never overwrite a partially completed evaluation.
            assert {p.name for p in dest.iterdir()}=={'target.wav'}
            started=time.monotonic()
            print(json.dumps(dict(target=index+1,name=target['source']['name'],phase='proposals')),flush=True)
            proposals=[{**c,'origin':'shared22'} for c in predict(*shared,reference,renderer,per_synth=2)]
            proposals += [{**c,'origin':'Transfxr-mixture'} for c in predict_temporal(*mixture,reference,renderer,count=4)]
            for name,m in specialists.items():
                proposals += [{**c,'origin':name+'-specialist'} for c in predict(*m,reference,renderer,per_synth=4)]
            raw,bad=rendered_candidates(proposals,renderer,soft)
            assert raw
            raw_saved=[save(c,f'raw-{i}.wav') for i,c in enumerate(raw)]
            refined=[]; selection=[]
            for key,obj in objectives.items():
                field='softDistance' if key=='soft' else 'preferenceDistance'
                seen=set(); starts=[]
                for i in sorted(range(len(raw)),key=lambda i:raw_saved[i][field]):
                    if raw[i]['synth'] in seen: continue
                    seen.add(raw[i]['synth']);starts.append(i)
                    if len(starts)==2: break
                assert len(starts)==2
                for slot,i in enumerate(starts):
                    print(json.dumps(dict(target=index+1,phase='refine',scorer=key,synth=raw[i]['synth'])),flush=True)
                    initial={**raw[i],'score':raw_saved[i][field]}
                    candidate=refine_candidate(initial,renderer,obj,128,target['seed']+slot*71)
                    candidate['provenance']={**candidate['provenance'],'refinementObjective':key,
                        'rawStartIndex':i,'inputPcmHash':target['auditionHash']}
                    assert candidate['score']<=initial['score']+1e-7
                    refined.append(save(candidate,f'{key}-refined-{slot}.wav'))
                    selection.append(dict(scorer=key,rawIndex=i,synth=raw[i]['synth'],budget=128))
            print(json.dumps(dict(target=index+1,phase='original-bfxr')),flush=True)
            baseline=original.approximate(reference,legacy,budget=2000,seed=target['seed'])
            baseline['origin']='original-bfxr'
            old=save(baseline,'original-bfxr-float.wav')
            all_candidates=raw_saved+refined+[old]
            proposed=[('soft',min(all_candidates,key=lambda c:c['softDistance'])),
                ('preference',min(all_candidates,key=lambda c:c['preferenceDistance'])),('original',old)]
            finalists=[];seen_pcm=set()
            for role,c in proposed+ [('alternative',c) for c in sorted(all_candidates,key=lambda c:c['preferenceDistance'])]:
                if c['auditionHash'] in seen_pcm: continue
                seen_pcm.add(c['auditionHash'])
                finalists.append(dict(role=role,candidate=c))
                if len(finalists)==3: break
            assert len(finalists)==3 and old['auditionHash'] in seen_pcm
            row=dict(complete=True,target=target,targetsSha256=file_hash(OUT/'targets.json'),
                raw=raw_saved,refined=refined,original=old,finalists=finalists,failures=bad,
                proposals=len(proposals),validProposals=len(raw),starts=selection,
                seconds=time.monotonic()-started,sourceHash=renderer.inventory['sourceHash'])
            _json_write(dest/'result.json',row); rows.append(row)
            print(json.dumps(dict(done=index+1,seconds=round(row['seconds'],1),finalists=[(c['role'],c['candidate']['synth']) for c in finalists])),flush=True)
    result=dict(complete=True,targetsSha256=file_hash(OUT/'targets.json'),scriptSha256=file_hash(__file__),rows=rows)
    _json_write(OUT/'results.json',result)
    _json_write(BASE/'evaluations/off-model-transfer-v1-evaluation.json',dict(complete=True,
        reportSha256=file_hash(OUT/'results.json'),targetsSha256=file_hash(OUT/'targets.json'),scriptSha256=file_hash(__file__),
        rows=[dict(source=r['target']['source'],validProposals=r['validProposals'],failures=r['failures'],starts=r['starts'],
            originalEvaluations=r['original']['provenance']['evaluations'],
            finalists=[dict(role=f['role'],synth=f['candidate']['synth'],origin=f['candidate']['origin'],
                soft=f['candidate']['softDistance'],preference=f['candidate']['preferenceDistance'],legacy=f['candidate']['legacyDistance']) for f in r['finalists']]) for r in rows],
        scope='Eight preselected unjudged tagged files; source families may overlap. Existing frozen checkpoints. Broader candidate pool, not equal-compute model comparison. No human quality claims.'))


def gallery():
    import shutil
    report=json.loads((OUT/'results.json').read_text())
    frozen=json.loads((OUT/'targets.json').read_text())
    assert report['complete'] and len(report['rows'])==8
    assert report['targetsSha256']==file_hash(OUT/'targets.json')
    assert report['scriptSha256']==file_hash(__file__)
    if GALLERY.exists(): raise FileExistsError('Preserve published gallery')
    GALLERY.mkdir()
    metric=PreferenceMetric.load(METRIC)
    assert file_hash(METRIC)==frozen['preferenceMetricSha256']
    records=[]
    with Renderer() as renderer, BfxrRenderer(jobs=1) as bfxr:
        for i,row in enumerate(report['rows']):
            assert row['target']==frozen['rows'][i]
            folder=GALLERY/f'{i+1:03d}'; folder.mkdir()
            src=OUT/folder.name/'target.wav'
            assert file_hash(src)==row['target']['referenceWavSha256']
            shutil.copyfile(src,folder/'target.wav')
            reference,sr=sf.read(src,dtype='float32'); assert sr==44100
            soft=SoftPeriodicityObjective(reference); legacy=MatchObjective(reference)
            descriptor=describe(reference)
            options=[];hashes=set()
            for j,finalist in enumerate(row['finalists']):
                c=finalist['candidate']; wave=read_wave(c)
                assert c['sourceHash']==renderer.inventory['sourceHash']
                exact_replay({**c,'wave':wave},renderer,bfxr)
                pcm=audition_pcm(wave)
                assert audio_hash(pcm)==c['auditionHash'] and audio_hash(pcm) not in hashes
                hashes.add(audio_hash(pcm))
                filename=f'option-{j+1}.wav';sf.write(folder/filename,pcm,44100,subtype='PCM_16')
                heard,rate=sf.read(folder/filename,dtype='float32')
                assert rate==44100 and np.array_equal(heard,pcm)
                assert abs(soft.score(heard)-c['softDistance'])<1e-6
                assert abs(legacy.score(heard)-c['legacyDistance'])<1e-6
                assert abs(float(metric.distances(descriptor,describe(heard))[0])-c['preferenceDistance'])<1e-6
                options.append({**c,'role':finalist['role'],'label':'Comparison option','file':filename,
                    'provenance':{**c['provenance'],'origin':c['origin'],'inputPcmHash':row['target']['auditionHash'],
                        'softPeriodicity':c['softDistance'],'preferenceNeuralV2':c['preferenceDistance'],
                        'auditionMatchObjective':c['legacyDistance'],'auditionWavSha256':file_hash(folder/filename),
                        'auditionTransform':'Single peak normalization and PCM16','targetsSha256':file_hash(OUT/'targets.json'),
                        'reportSha256':file_hash(OUT/'results.json'),'selectionRole':finalist['role']}})
            assert len(options)==3
            records.append(dict(folder=folder.name,source=row['target']['source'],candidates=options,
                note='Unjudged tagged source. Choose the closest, then how close; none close and ties are useful.'))
    metadata=dict(experiment='off-model-transfer-v1-listening',complete=True,targetCount=8,
        galleryTitle='Can the synths recreate these external sounds?',galleryIntro=[
            'Eight short tagged recordings. No native synth test sounds in this round. Take the optional break after five.',
            'The full existing synth pool and original Bfxr are available. Alternatives include disagreements between scoring methods.',
            'Choose the closest, then say how close it feels. None close is useful; a winner need not be a convincing recreation.'],
        humanReviewRequired=True,scope='External files, exact prior feedback file/PCM excluded; source families and earlier model corpora may overlap. No family-disjoint claim.',
        reportSha256=file_hash(OUT/'results.json'),targetsSha256=file_hash(OUT/'targets.json'),scriptSha256=file_hash(__file__),
        selectionPolicy=frozen['listeningPolicy'],uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()})
    model=export_coverage(GALLERY,records,metadata)
    _json_write(BASE/'evaluations/off-model-transfer-v1-listening-audit.json',dict(complete=True,
        experimentId=model['experimentId'],targetCount=8,optionCounts=[len(r['candidates']) for r in records],
        resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),
        reportSha256=file_hash(OUT/'results.json'),scriptSha256=file_hash(__file__),
        audioFiles={str(p.relative_to(GALLERY)):file_hash(p) for p in sorted(GALLERY.glob('*/*.wav'))}))
    print(json.dumps(dict(experimentId=model['experimentId'],targets=8,options=24)),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['freeze','run','gallery'])
    args=parser.parse_args()
    {'freeze':freeze,'run':run,'gallery':gallery}[args.stage]()
