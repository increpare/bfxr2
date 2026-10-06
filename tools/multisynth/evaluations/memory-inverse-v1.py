"""Frozen encoder, train-only preset memory, matched native refinement arms."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.bfxr_io import render_worker_cmd
from match.renderer import BfxrRenderer
from multisynth.coverage import verify_archived_audio
from multisynth.preference import PreferenceMetric
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture_eval import write_wave, read_wave
from neural_invert.data import file_hash, _json_write, verify_dataset_files, parameter_hash
from neural_invert.evaluate import rendered_candidates, refine_candidate, serializable
from neural_invert.experiment import audition_pcm
from neural_invert.features import describe as neural_features
from neural_invert.memory import MemoryIndex, encode_features
from neural_invert.predict import load_model, predict

BASE=Path('tools/multisynth'); ROOT=BASE/'runs/memory-inverse-v1'
DATA=BASE/'runs/neural-v2/data'; MODEL=BASE/'runs/neural-v2/acoustic-model'
ARCHIVE=BASE/'listening_data/2026-10-06-fresh-gesture-v1-quick-01'
LATEST=BASE/'listening_data/2026-10-06-control-diagnosis-v1-quick-01'
PLAN=Path('docs/superpowers/plans/2026-10-06-memory-inverse.md')
METRIC=BASE/'models/preference-neural-v2.json'
WRAPPERS=BASE/'evaluations/fresh-gesture-v1.py'
spec=importlib.util.spec_from_file_location('frozen_objectives',WRAPPERS)
objectives=importlib.util.module_from_spec(spec);spec.loader.exec_module(objectives)
CODE=[Path(__file__),WRAPPERS,*[Path('tools/neural_invert')/n for n in
    ('memory.py','predict.py','model.py','features.py','data.py','evaluate.py','schema.py','experiment.py','benchmark.py','coverage_mixture_eval.py')],
    *[BASE/n for n in ('features.py','gesture.py','preference.py','soft_periodicity.py','renderer.py')],
    *[Path('tools/match')/n for n in ('renderer.py','bfxr_io.py','structure.py','objective.py','features.py','audio.py')]]


def archived(info):
    verify_archived_audio(ARCHIVE,info)
    wave,sr=sf.read(ARCHIVE/info['file'],dtype='float32');assert sr==44100
    return wave


def freeze():
    if ROOT.exists():raise FileExistsError('Preserve frozen experiment')
    manifest=json.loads((ARCHIVE/'manifest.json').read_text());by_id={c['id']:c for c in manifest['candidates']}
    targets=[]
    for i,t in enumerate(manifest['targets']):
        assert t['choice']['kind']=='best'
        cid=t['choice']['preferredCandidateIds'][0];assert cid in t['choice']['auditionedCandidateIds']
        parent=by_id[cid];archived(t['referenceAudio']);archived(parent['audio'])
        targets.append(dict(source=t['source'],referenceAudio=t['referenceAudio'],parent=parent,
            parentChoice=t['choice'],parentNote=t['note'],seed=20261029+i*1009))
    assert len(targets)==8
    _,meta=load_model(MODEL)
    assert meta['dataManifestHash']==file_hash(DATA/'manifest.json')
    with Renderer() as renderer:assert renderer.inventory['sourceHash']==meta['sourceHash']
    backend=render_worker_cmd();ROOT.mkdir()
    protocol=dict(complete=True,targets=targets,sourceHash=meta['sourceHash'],
        checkpointSha256=file_hash(MODEL/'best.pt'),dataManifestSha256=file_hash(DATA/'manifest.json'),
        archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),feedbackSha256=file_hash(ARCHIVE/'feedback.json'),
        latestArchiveManifestSha256=file_hash(LATEST/'manifest.json'),latestFeedbackSha256=file_hash(LATEST/'feedback.json'),
        latestReviewSha256=file_hash(BASE/'evaluations/control-diagnosis-v1-quick-01-human-review.json'),
        planSha256=file_hash(PLAN),metricSha256=file_hash(METRIC),codeHashes={str(p):file_hash(p) for p in CODE},
        bfxrBackend=dict(command=backend,sha256=file_hash(backend[0])),
        policy='Eight fixed repeated external development references, all historically in original Bfxr training. Frozen shared22 encoder. Memory fits synthetic train rows only; regression and memory use matched per-engine proposal quotas, two distinct engine refinement starts,128 attempts/start, same seeds and preference scorer. Preserve exact earlier chosen clip. No quality claim before human review.',
        limitations=['Memory preserves full native prototype controls including randomness and text; this is an initialization-method comparison, not a pure test of parameter regression averaging.',
                    'The memory scans a dense bank offline; matched rendered/search budgets do not mean equal total computation or equal representation capacity.',
                    'The shared encoder selected its checkpoint using native validation data. This is external development feedback, not an unseen native validation claim.',
                    'Earlier chosen clips may be least-bad; conflicting contextual human likeness labels are retained, not collapsed.'])
    _json_write(ROOT/'protocol.json',protocol)
    _json_write(BASE/'evaluations/memory-inverse-v1-protocol.json',protocol|{'protocolSha256':file_hash(ROOT/'protocol.json')})
    print(json.dumps(dict(frozen=True,targets=len(targets))),flush=True)


def verify(p):
    checks={MODEL/'best.pt':'checkpointSha256',DATA/'manifest.json':'dataManifestSha256',ARCHIVE/'manifest.json':'archiveManifestSha256',
        ARCHIVE/'feedback.json':'feedbackSha256',LATEST/'manifest.json':'latestArchiveManifestSha256',LATEST/'feedback.json':'latestFeedbackSha256',
        BASE/'evaluations/control-diagnosis-v1-quick-01-human-review.json':'latestReviewSha256',PLAN:'planSha256',METRIC:'metricSha256'}
    assert all(file_hash(path)==p[key] for path,key in checks.items())
    assert all(file_hash(path)==h for path,h in p['codeHashes'].items())
    assert p['bfxrBackend']['command']==render_worker_cmd() and p['bfxrBackend']['sha256']==file_hash(render_worker_cmd()[0])


def fit():
    p=json.loads((ROOT/'protocol.json').read_text());verify(p);torch.set_num_threads(1)
    if (ROOT/'memory').exists():raise FileExistsError('Preserve fitted memory')
    model,meta=load_model(MODEL);manifest=json.loads((DATA/'manifest.json').read_text())
    verify_dataset_files(DATA,manifest)
    assert meta['dataManifestHash']==p['dataManifestSha256'] and manifest['sourceHash']==p['sourceHash']
    vectors=[];rows=[];counts={};started=time.monotonic()
    for name in meta['engines']:
        d=json.loads((DATA/(name+'.json')).read_text())
        assert d['sourceHash']==meta['sourceHash'] and d['featureHash']==meta['featureHash'] and d['featureCodeHash']==meta['featureCodeHash']
        train,val=d['train'],d['val'];assert not set(train)&set(val)
        assert sorted(train+val)==list(range(len(d['rows'])))
        groups={split:{parameter_hash(d['rows'][i]) for i in indices} for split,indices in [('train',train),('val',val)]}
        assert not groups['train']&groups['val']
        with np.load(DATA/(name+'.npz'),allow_pickle=False) as z:
            x=z['features']
            assert len(x)==len(d['rows']) and np.isfinite(x).all()
            for i,row in enumerate(d['rows']):
                assert row['synth']==name and parameter_hash(row)==row['parameterHash']
                assert hashlib.sha256(x[i].astype('<f2').tobytes()).hexdigest()==row['packedFeatureHash']
            vectors.append(encode_features(model,meta,x[train]))
        shard_hash=file_hash(DATA/(name+'.json'))
        rows.extend({**d['rows'][i],'trainingRow':i,'split':'train','shardSha256':shard_hash} for i in train)
        counts[name]=dict(train=len(train),excludedValidation=len(val))
        print(json.dumps(dict(encoded=name,train=len(train))),flush=True)
    metadata=dict(protocolSha256=file_hash(ROOT/'protocol.json'),checkpointSha256=p['checkpointSha256'],
        dataManifestSha256=p['dataManifestSha256'],sourceHash=p['sourceHash'],featureHash=meta['featureHash'],featureCodeHash=meta['featureCodeHash'],
        encoderFrozen=True,selection='Synthetic train split only; no external audio or human labels in fitted memory',counts=counts)
    index=MemoryIndex.fit(np.concatenate(vectors),rows,metadata);index.save(ROOT/'memory')
    loaded=MemoryIndex.load(ROOT/'memory');assert len(loaded.rows)==len(rows) and np.array_equal(loaded.embeddings,index.embeddings)
    receipt=dict(complete=True,**metadata,trainRows=len(rows),embeddingDimensions=index.embeddings.shape[1],
        indexJsonSha256=file_hash(ROOT/'memory/index.json'),indexArraySha256=file_hash(ROOT/'memory/index.npz'),seconds=time.monotonic()-started)
    _json_write(ROOT/'fit.json',receipt);_json_write(BASE/'evaluations/memory-inverse-v1-fit.json',receipt)
    print(json.dumps(receipt),flush=True)


def run():
    p=json.loads((ROOT/'protocol.json').read_text());verify(p);torch.set_num_threads(1)
    assert not (ROOT/'results.json').exists()
    model,meta=load_model(MODEL);memory=MemoryIndex.load(ROOT/'memory');fit=json.loads((ROOT/'fit.json').read_text())
    assert fit['indexJsonSha256']==file_hash(ROOT/'memory/index.json') and fit['indexArraySha256']==file_hash(ROOT/'memory/index.npz')
    assert memory.metadata['protocolSha256']==file_hash(ROOT/'protocol.json')
    metric=PreferenceMetric.load(METRIC);results=[]
    with Renderer() as renderer,BfxrRenderer(jobs=1) as bfxr:
        assert renderer.inventory['sourceHash']==p['sourceHash']
        for i,t in enumerate(p['targets']):
            dest=ROOT/f'{i+1:03d}';reference=archived(t['referenceAudio']);anchor=archived(t['parent']['audio'])
            pref=objectives.PreferenceObjective(reference,metric);soft=objectives.SoftAudition(reference);legacy=objectives.AuditionObjective(reference)
            def save(c,filename):
                exact_replay(c,renderer,bfxr);heard=audition_pcm(c['wave'])
                return {**serializable(c),**write_wave(dest/filename,c['wave']),'sourceHash':p['sourceHash'],
                    'auditionHash':audio_hash(heard),'preferenceDistance':float(pref.score_batch([c['wave']])[0]),
                    'softDistance':float(soft.score_batch([c['wave']])[0]),'legacyDistance':float(legacy.score_batch([c['wave']])[0])}
            if (dest/'result.json').exists():
                r=json.loads((dest/'result.json').read_text());assert r['complete'] and r['target']==t
                assert r['protocolSha256']==file_hash(ROOT/'protocol.json') and r['fitSha256']==file_hash(ROOT/'fit.json')
                for arm in r['arms'].values():
                    for c in arm['raw']+arm['refined']:
                        wave=read_wave(c);exact_replay({**c,'wave':wave},renderer,bfxr)
                        assert audio_hash(audition_pcm(wave))==c['auditionHash']
                results.append(r);continue
            if dest.exists():raise FileExistsError('Incomplete target requires explicit recovery: '+str(dest))
            dest.mkdir();sf.write(dest/'target.wav',reference,44100,subtype='PCM_16');started=time.monotonic()
            print(json.dumps(dict(target=i+1,phase='proposal',name=t['source']['name'])),flush=True)
            regression=predict(model,meta,reference,renderer,per_synth=2);quotas=dict(Counter(c['synth'] for c in regression))
            query=encode_features(model,meta,neural_features(reference)[None])[0]
            nearest=memory.retrieve(query,quotas);assert dict(Counter(c['synth'] for c in nearest))==quotas
            proposals={'regression':[{**c,'origin':'shared22-regression'} for c in regression],
                'memory':[dict(synth=c['synth'],params=c['params'],seed=c['seed'],origin='shared22-memory',
                    provenance=dict(method='learned-embedding-native-memory',checkpointHash=p['checkpointSha256'],
                        dataManifestSha256=p['dataManifestSha256'],indexJsonSha256=fit['indexJsonSha256'],memoryIndex=c['memoryIndex'],
                        embeddingDistance=c['embeddingDistance'],trainingRow=c['trainingRow'],trainingSplit=c['split'],
                        trainingParameterHash=c['parameterHash'],trainingAudioHash=c['audioHash'],shardSha256=c['shardSha256'],
                        inputPcmHash=audio_hash(reference))) for c in nearest]}
            arms={}
            for arm,ps in proposals.items():
                if arm=='memory':
                    for c in ps:
                        canonical,w=renderer.render(c['synth'],c['params'],c['seed'])
                        assert canonical==c['params'] and audio_hash(w)==c['provenance']['trainingAudioHash']
                raw,bad=rendered_candidates(ps,renderer,pref);assert len(raw)>=2
                saved=[save(c,f'{arm}-raw-{j}.wav') for j,c in enumerate(raw)]
                starts=[];seen=set()
                for j in sorted(range(len(raw)),key=lambda j:raw[j]['score']):
                    if raw[j]['synth'] in seen:continue
                    seen.add(raw[j]['synth']);starts.append(j)
                    if len(starts)==2:break
                assert len(starts)==2
                refined=[]
                for slot,j in enumerate(starts):
                    print(json.dumps(dict(target=i+1,phase='refine',arm=arm,synth=raw[j]['synth'])),flush=True)
                    c=refine_candidate(raw[j],renderer,pref,128,t['seed']+slot*71)
                    c['provenance']={**c['provenance'],'rawStartIndex':j,'refinementObjective':'preference-neural-v2',
                        'inputPcmHash':audio_hash(reference)}
                    refined.append(save(c,f'{arm}-refined-{slot}.wav'))
                arms[arm]=dict(proposals=len(ps),validProposals=len(raw),failures=bad,quotas=quotas,raw=saved,refined=refined,
                    starts=starts,attemptedMutations=256,selected=min(saved+refined,key=lambda c:c['preferenceDistance']))
            # Earlier human choice is an exact retained baseline, independent of today's selector.
            parent=t['parent'];old=dict(synth=parent['synth'],params=parent['params'],seed=parent['seed'],
                expert='original-bfxr' if parent['provenance']['origin']=='original-bfxr' else 'actual-multisynth')
            if old['expert']=='original-bfxr':w=bfxr.render(old['params'],seed=old['seed'])
            else:_,w=renderer.render(old['synth'],old['params'],old['seed'])
            assert np.array_equal(audition_pcm(w),anchor)
            old=save({**old,'wave':w,'origin':parent['provenance']['origin'],'provenance':parent['provenance']},'anchor-float.wav')
            row=dict(complete=True,target=t,protocolSha256=file_hash(ROOT/'protocol.json'),fitSha256=file_hash(ROOT/'fit.json'),
                arms=arms,anchor=old,memoryNativeTrainingReplays=len(nearest),seconds=time.monotonic()-started)
            _json_write(dest/'result.json',row);results.append(row)
            print(json.dumps(dict(done=i+1,seconds=round(row['seconds'],1),selected={a:(v['selected']['synth'],v['selected']['preferenceDistance']) for a,v in arms.items()})),flush=True)
    report=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),fitSha256=file_hash(ROOT/'fit.json'),rows=results)
    _json_write(ROOT/'results.json',report)
    _json_write(BASE/'evaluations/memory-inverse-v1-evaluation.json',dict(complete=True,reportSha256=file_hash(ROOT/'results.json'),
        protocolSha256=file_hash(ROOT/'protocol.json'),fitSha256=file_hash(ROOT/'fit.json'),humanQuality='Unknown pending listening',
        rows=[dict(source=r['target']['source'],memoryNativeTrainingReplays=r['memoryNativeTrainingReplays'],
            arms={a:dict(proposals=v['proposals'],validProposals=v['validProposals'],failures=v['failures'],quotas=v['quotas'],
                attemptedMutations=v['attemptedMutations'],selected={k:v['selected'][k] for k in ('synth','origin','preferenceDistance','softDistance','legacyDistance','auditionHash')}) for a,v in r['arms'].items()}) for r in results]))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','fit','run']);args=parser.parse_args()
    {'freeze':freeze,'fit':fit,'run':run}[args.stage]()
