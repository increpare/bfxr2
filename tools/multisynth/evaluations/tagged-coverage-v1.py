"""Test reachable candidate coverage using real preset controls from training data."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.coverage import verify_archived_audio
from multisynth.features import describe as perceptual_describe
from multisynth.preference import PreferenceMetric
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture_eval import read_wave, write_wave
from neural_invert.data import file_hash, verify_dataset_files, _json_write
from neural_invert.evaluate import refine_candidate, serializable
from neural_invert.experiment import audition_pcm
from neural_invert.features import describe, FEATURE_HASH, FEATURE_CODE_HASH, DIM
from neural_invert.forward import FEATURE_GROUPS

BASE = Path('tools/multisynth')
OUT = BASE/'runs/tagged-coverage-v1'
ARCHIVE = BASE/'listening_data/2026-10-05-specialists-tagged-quick-01'
PRIOR = BASE/'runs/specialists-tagged-v1/results.json'
PLAN = Path('docs/superpowers/plans/2026-10-05-tagged-coverage-diagnostic.md')
METRIC = BASE/'models/preference-neural-v2.json'
DATA = [BASE/'runs/neural-v2/data-certified-v2', BASE/'runs/specialists-v1/fit-data/Boomr',
        BASE/'runs/specialists-v1/fit-data/Footsteppr']
NO_PITCH = ('relativePitch','absolutePitch','combinedVoicing')


class AuditionObjective(MatchObjective):
    def score_batch(self,waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])


class PreferenceObjective:
    def __init__(self,reference,metric):
        self.target = perceptual_describe(reference)
        self.metric = metric

    def score_batch(self,waves):
        return np.asarray([float(self.metric.distances(self.target,perceptual_describe(audition_pcm(w)))[0])
            if w is not None and len(w) else 1e6 for w in waves])


def controls_key(c):
    return json.dumps([c['synth'],c['params'],c['seed']],sort_keys=True)


def freeze():
    if OUT.exists():
        raise FileExistsError('Fresh diagnostic required')
    manifest = json.loads((ARCHIVE/'manifest.json').read_text())
    assert len(manifest['targets'])==5
    for target in manifest['targets']:
        assert target['choice']['kind']=='best' and target['choice']['adequacy']['level'] in ('similar','least-bad')
    bindings = []
    for path in DATA:
        data = json.loads((path/'manifest.json').read_text())
        assert data['complete'] and data['featureHash']==FEATURE_HASH and data['featureCodeHash']==FEATURE_CODE_HASH
        verify_dataset_files(path,data)
        bindings.append(dict(path=str(path.resolve()),manifestSha256=file_hash(path/'manifest.json'),engines=data['engines']))
    OUT.mkdir()
    _json_write(OUT/'protocol.json',dict(complete=True,scriptSha256=file_hash(__file__),designSha256=file_hash(PLAN),
        archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),priorReportSha256=file_hash(PRIOR),
        metricSha256=file_hash(METRIC),datasets=bindings,topPerEnginePerRoute=4,refinementStartsPerMetric=2,
        budgetPerStart=128,seed=20261117,groups=FEATURE_GROUPS,pitchLightExcludedGroups=NO_PITCH,
        scope='Five repeated development cases. Retrieval from optimization rows only; pitch-light retrieval is exploratory. Frozen scorers. No inverse retraining, no source-family holdout, no equal-compute claim.'))
    print('Frozen protocol '+file_hash(OUT/'protocol.json'),flush=True)


def run():
    protocol = json.loads((OUT/'protocol.json').read_text())
    assert protocol['scriptSha256']==file_hash(__file__) and not (OUT/'results.json').exists()
    assert file_hash(ARCHIVE/'manifest.json')==protocol['archiveManifestSha256']
    assert file_hash(PRIOR)==protocol['priorReportSha256'] and file_hash(METRIC)==protocol['metricSha256']
    manifest = json.loads((ARCHIVE/'manifest.json').read_text())
    previous = json.loads(PRIOR.read_text())
    prior_rows = {r['target']['source']['sha256']:r for r in previous['rows']}
    candidates = {c['id']:c for c in manifest['candidates']}
    metric = PreferenceMetric.load(METRIC)
    torch.set_num_threads(1)
    shards = []
    with Renderer() as renderer:
        for binding in protocol['datasets']:
            path = Path(binding['path'])
            assert file_hash(path/'manifest.json')==binding['manifestSha256']
            data = json.loads((path/'manifest.json').read_text())
            verify_dataset_files(path,data)
            assert data['sourceHash']==renderer.inventory['sourceHash']
            for engine in data['engines']:
                meta = json.loads((path/(engine+'.json')).read_text())
                assert meta['spec']==renderer.specs[engine]
                ids = np.asarray(meta['train'],dtype=np.int64)
                assert not set(ids)&set(meta['val']+meta.get('test',[]))
                with np.load(path/(engine+'.npz'),allow_pickle=False) as z:
                    packed = z['features'].copy()
                x = packed[ids].astype(np.float32)
                assert x.shape==(len(ids),DIM) and np.all(np.isfinite(x))
                mean = x.mean(axis=0);std = np.maximum(x.std(axis=0),.025)
                shards.append(dict(path=path,manifestSha256=binding['manifestSha256'],engine=engine,meta=meta,ids=ids,
                    packed=packed,mean=mean,std=std,features=(x-mean)/std))
        print(json.dumps(dict(indexRows=sum(len(s['ids']) for s in shards),shards=len(shards))),flush=True)
        results = []
        for index,target in enumerate(manifest['targets']):
            started = time.monotonic()
            dest = OUT/f'{index+1:03d}';dest.mkdir()
            verify_archived_audio(ARCHIVE,target['referenceAudio'])
            reference,rate = sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert rate==44100
            reference_info = write_wave(dest/'target.wav',reference)
            winner = candidates[target['choice']['preferredCandidateIds'][0]]
            verify_archived_audio(ARCHIVE,winner['audio'])
            winner_wave,rate = sf.read(ARCHIVE/winner['audio']['file'],dtype='float32');assert rate==44100
            objective,preference = AuditionObjective(reference),PreferenceObjective(reference,metric)
            exact_objective = MatchObjective(reference)
            descriptor = perceptual_describe(reference)
            def scores(pcm):
                return dict(matching=float(exact_objective.score_batch([pcm])[0]),
                    preference=float(metric.distances(descriptor,perceptual_describe(pcm))[0]))
            baseline = dict(candidateId=winner['id'],pcmHash=audio_hash(winner_wave),scores=scores(winner_wave))
            heard_hashes = set()
            for item in target['candidates']:
                c = candidates[item['id']];verify_archived_audio(ARCHIVE,c['audio'])
                w,_ = sf.read(ARCHIVE/c['audio']['file'],dtype='float32');heard_hashes.add(audio_hash(w))
            query = describe(reference)
            retrieved = {}
            for shard in shards:
                q = (query-shard['mean'])/shard['std']
                delta = (shard['features']-q)**2
                group_losses = {name:np.concatenate([delta[:,a:b] for a,b in ranges],axis=1).mean(axis=1)
                    for name,ranges in FEATURE_GROUPS.items()}
                route_scores = dict(allGroups=np.mean(list(group_losses.values()),axis=0),
                    pitchLight=np.mean([v for k,v in group_losses.items() if k not in NO_PITCH],axis=0))
                for route,distance in route_scores.items():
                    for rank,local in enumerate(np.argsort(distance,kind='stable')[:4]):
                        source_index = int(shard['ids'][local]);source = shard['meta']['rows'][source_index]
                        c = dict(synth=shard['engine'],params=source['params'],seed=source['seed'])
                        key = controls_key(c)
                        evidence = dict(dataset=str(shard['path']),manifestSha256=shard['manifestSha256'],
                            sourceRow=source_index,route=route,rank=rank,retrievalDistance=float(distance[local]))
                        if key in retrieved:
                            retrieved[key]['provenance']['retrieval'].append(evidence);continue
                        params,raw = renderer.render(c['synth'],c['params'],c['seed'])
                        assert params==c['params'] and audio_hash(raw)==source['audioHash']
                        packed = np.asarray(describe(raw),dtype=np.float16)
                        assert np.array_equal(packed,shard['packed'][source_index])
                        assert hashlib.sha256(packed.astype('<f2').tobytes()).hexdigest()==source['packedFeatureHash']
                        assert np.max(np.abs(raw))>1e-6
                        pcm = audition_pcm(raw)
                        assert audio_hash(pcm)!=audio_hash(reference)
                        c.update(wave=raw,scores=scores(pcm),sourceHash=renderer.inventory['sourceHash'],
                            provenance=dict(method='training-control-retrieval',retrieval=[evidence],
                                originalAudioHash=source['audioHash'],protocolSha256=file_hash(OUT/'protocol.json')))
                        retrieved[key]=c
            raw_candidates = list(retrieved.values())
            print(json.dumps(dict(target=index+1,name=target['source']['name'],retrieved=len(raw_candidates),phase='refine')),flush=True)
            refined = []
            for arm,score_object in [('matching',objective),('preference',preference)]:
                starts,seen = [],set()
                for c in sorted(raw_candidates,key=lambda c:c['scores'][arm]):
                    if c['synth'] not in seen:
                        starts.append(c);seen.add(c['synth'])
                    if len(starts)==2:break
                assert len(starts)==2
                for slot,c in enumerate(starts):
                    seed = protocol['seed']+index*1009+slot*71+(400 if arm=='preference' else 0)
                    result = refine_candidate({**c,'score':c['scores'][arm]},renderer,score_object,128,seed)
                    result['provenance']['refinement']['scoreName']=arm
                    result['scores']=scores(audition_pcm(result['wave']))
                    assert abs(result['score']-result['scores'][arm])<1e-6
                    refined.append(result)
            pools = {}
            for label,rows in [('retrieved',raw_candidates),('refined',refined)]:
                pools[label]=[]
                for slot,c in enumerate(rows):
                    raw = c['wave'];pcm = audition_pcm(raw)
                    info = write_wave(dest/f'{label}-{slot}.wav',raw)
                    pools[label].append({**serializable(c),**info,'auditionHash':audio_hash(pcm)})
            prior = prior_rows[target['source']['sha256']]
            retained = []
            for rows in prior['pools'].values():
                for c in rows:
                    raw = read_wave(c);pcm = audition_pcm(raw)
                    s = scores(pcm)
                    assert abs(s['matching']-c['score'])<1e-6 and abs(s['preference']-c['preferenceDistance'])<1e-7
                    retained.append({**c,'scores':s,'provenance':{**c['provenance'],'retainedReportSha256':protocol['priorReportSha256']}})
            pools['retainedNeural']=retained
            all_candidates = pools['retrieved']+pools['refined']+retained
            novel = [c for c in all_candidates if c['auditionHash'] not in heard_hashes]
            choices = {arm:min(novel,key=lambda c:c['scores'][arm]) for arm in ('matching','preference')}
            qualifying = any(c['scores'][arm]<baseline['scores'][arm]-1e-6 for arm,c in choices.items())
            summary = {label:{arm:min(c['scores'][arm] for c in pool) for arm in ('matching','preference')}
                for label,pool in pools.items()}
            result = dict(target=target,reference=reference_info,baseline=baseline,pools=pools,choices=choices,
                qualifying=qualifying,summary=summary,seconds=time.monotonic()-started,folder=dest.name)
            _json_write(dest/'result.json',result);results.append(result)
            print(json.dumps(dict(done=index+1,summary=summary,baseline=baseline['scores'],qualifying=qualifying,
                choiceOrigins={k:c['provenance'].get('method',c.get('origin')) for k,c in choices.items()})),flush=True)
    report = dict(complete=True,scriptSha256=file_hash(__file__),protocolSha256=file_hash(OUT/'protocol.json'),
        rows=results,indexRows=sum(len(s['ids']) for s in shards),qualifying=sum(r['qualifying'] for r in results))
    _json_write(OUT/'results.json',report)
    _json_write(BASE/'evaluations/tagged-coverage-v1-evaluation.json',dict(complete=True,reportSha256=file_hash(OUT/'results.json'),
        scriptSha256=file_hash(__file__),protocolSha256=file_hash(OUT/'protocol.json'),indexRows=report['indexRows'],
        qualifying=report['qualifying'],rows=[dict(source=r['target']['source'],baseline=r['baseline'],summary=r['summary'],
            selected={k:dict(synth=c['synth'],scores=c['scores'],auditionHash=c['auditionHash'],provenance=c['provenance']) for k,c in r['choices'].items()}) for r in results],
        scope=protocol['scope']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['freeze','run'])
    args=parser.parse_args();torch.set_num_threads(1)
    {'freeze':freeze,'run':run}[args.action]()
