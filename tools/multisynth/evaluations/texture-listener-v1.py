"""Fixed grouped ablation of six auditory-envelope texture distance blocks."""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from multisynth import texture, texture_listener, listener_metric
from multisynth.preference import training_pairs, PreferenceMetric, grouped_folds, score_summary
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/texture-listener-v1'
OLD=BASE/'models/preference-neural-v2.json'
PLAN=Path('docs/superpowers/plans/2026-10-06-texture-listener.md')
REVIEW=BASE/'evaluations/memory-inverse-v1-quick-01-human-review.json'


def freeze():
    if ROOT.exists():raise FileExistsError('Preserve frozen texture experiment')
    archives=sorted(BASE.glob('listening_data/*/manifest.json'));records=[]
    assert len(archives)==27
    for path in archives:
        for t in json.loads(path.read_text())['targets']:
            records.append(dict(reference=t['referenceAudio']['pcmSha256'],source=t['source']))
    groups=listener_metric.source_groups(records)
    p=dict(complete=True,archives={str(a.parent):dict(manifestSha256=file_hash(a),feedbackSha256=file_hash(a.parent/'feedback.json')) for a in archives},
        groups=groups,groupCount=len(set(groups.values())),recipe=texture_listener.RECIPE,textureConfig=texture.CONFIG,
        bindings=texture_listener.bindings(),scriptSha256=file_hash(__file__),planSha256=file_hash(PLAN),
        reviewSha256=file_hash(REVIEW),oldMetricSha256=file_hash(OLD),
        grouping='Connected reference PCM, file SHA and conservative tag/collection identities; external strict likeness only',
        scope='Retrospective group-held-out preference prediction. Same-data21-component ablation. Historical feedback informed this design; not unbiased prospective synthesis evidence.',
        gate='New reference-balanced accuracy >= ablation +.03, >= frozen preference and >= soft. Fixed before feature extraction; no hyperparameter retries.')
    ROOT.mkdir();_json_write(ROOT/'protocol.json',p)
    _json_write(BASE/'evaluations/texture-listener-v1-protocol.json',p|{'protocolSha256':file_hash(ROOT/'protocol.json')})
    print(json.dumps(dict(frozen=True,archives=len(archives),externalReferences=len(groups),groups=p['groupCount'])),flush=True)


def verify(p):
    assert p['scriptSha256']==file_hash(__file__) and p['bindings']==texture_listener.bindings()
    assert p['recipe']==texture_listener.RECIPE and p['textureConfig']==texture.CONFIG
    assert p['planSha256']==file_hash(PLAN) and p['reviewSha256']==file_hash(REVIEW) and p['oldMetricSha256']==file_hash(OLD)
    for root,hashes in p['archives'].items():
        assert file_hash(Path(root)/'manifest.json')==hashes['manifestSha256'] and file_hash(Path(root)/'feedback.json')==hashes['feedbackSha256']


def extract():
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    if (ROOT/'data.json').exists():raise FileExistsError('Preserve extracted pairs')
    data=training_pairs(list(p['archives']));paths={}
    for root in p['archives']:
        m=json.loads((Path(root)/'manifest.json').read_text())
        for a in [t['referenceAudio'] for t in m['targets']]+[c['audio'] for c in m['candidates']]:
            paths.setdefault(a['pcmSha256'],Path(root)/a['file'])
    keep=np.array([r in p['groups'] for r in data.groups]);obs=[o for o,k in zip(data.observations,keep) if k]
    x=data.x[keep];y=data.y[keep];refs=data.groups[keep];groups=np.array([p['groups'][r] for r in refs])
    waves={};descriptors={};objectives={};cache={}
    def wave(pcm):
        if pcm not in waves:
            w,sr=sf.read(paths[pcm],dtype='float32');assert sr==44100;waves[pcm]=w
        return waves[pcm]
    def tex(pcm):
        if pcm not in descriptors:descriptors[pcm]=texture.describe(wave(pcm))
        return descriptors[pcm]
    def scores(ref,cand):
        if (ref,cand) not in cache:
            if ref not in objectives:objectives[ref]=SoftPeriodicityObjective(wave(ref))
            cache[ref,cand]=np.r_[objectives[ref].score(wave(cand)),texture.components(tex(ref),tex(cand))]
        return cache[ref,cand]
    extra=[]
    for i,o in enumerate(obs):
        ref=o['referencePcmSha256']
        extra.append(scores(ref,o['candidatePcmSha256A'])-scores(ref,o['candidatePcmSha256B']))
        if (i+1)%32==0:print(json.dumps(dict(extracted=i+1,total=len(obs),audioDescriptors=len(descriptors))),flush=True)
    values=np.column_stack([x,extra]);assert values.shape==(len(y),27) and np.isfinite(values).all()
    np.savez_compressed(ROOT/'data.npz',x=values,y=y,references=refs,groups=groups)
    meta=dict(complete=True,observations=obs,archiveSummary=data.summary,allStrictPairs=len(data.y),excludedNativePairs=int((~keep).sum()),
        externalPairs=len(y),referenceCount=len(set(refs)),groupCount=len(set(groups)),
        protocolSha256=file_hash(ROOT/'protocol.json'),dataSha256=file_hash(ROOT/'data.npz'),
        extraScores=[dict(reference=r,candidate=c,values=v.tolist()) for (r,c),v in cache.items()])
    verify(p);_json_write(ROOT/'data.json',meta)
    print(json.dumps({k:meta[k] for k in ('allStrictPairs','excludedNativePairs','externalPairs','referenceCount','groupCount')}),flush=True)


def train():
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    if (ROOT/'evaluation.json').exists():raise FileExistsError('Preserve fixed evaluation')
    data=json.loads((ROOT/'data.json').read_text());assert data['dataSha256']==file_hash(ROOT/'data.npz')
    with np.load(ROOT/'data.npz',allow_pickle=False) as z:x,y,refs,groups=(z[k] for k in ('x','y','references','groups'))
    pred={n:np.empty(len(y)) for n in ('texture-heldout','base21-heldout')};fold_ids=np.empty(len(y),int);folds=[]
    for i,(tr,te) in enumerate(grouped_folds(groups,5)):
        assert not set(groups[tr])&set(groups[te]) and not set(refs[tr])&set(refs[te])
        models={'texture-heldout':texture_listener.fit(x[tr],y[tr],refs[tr]),
                'base21-heldout':listener_metric.fit(x[tr,:21],y[tr],refs[tr])}
        fold=dict(fold=i,trainGroups=sorted(set(groups[tr])),testGroups=sorted(set(groups[te])),
            trainReferences=sorted(set(refs[tr])),testReferences=sorted(set(refs[te])),trainPairs=int(tr.sum()),testPairs=int(te.sum()),models={})
        for name,m in models.items():
            pred[name][te]=x[te,:len(m.weights)]@(m.weights/m.scales)
            fold['models'][name]=dict(weights=m.weights.tolist(),scales=m.scales.tolist(),scores=score_summary(pred[name][te],y[te],refs[te]))
        folds.append(fold);fold_ids[te]=i
    old=PreferenceMetric.load(OLD);pred['old-preference-historical']=x[:,:20]@(old.weights/old.scales);pred['soft-periodicity']=x[:,20]
    scores={n:score_summary(v,y,refs) for n,v in pred.items()}
    acc={n:s['referenceBalancedAccuracy'] for n,s in scores.items()}
    gate=bool(acc['texture-heldout']>=acc['base21-heldout']+.03 and acc['texture-heldout']>=max(acc['old-preference-historical'],acc['soft-periodicity']))
    recent=np.array([o['archive']=='2026-10-06-memory-inverse-v1-quick-01' for o in data['observations']])
    recent_scores={n:score_summary(v[recent],y[recent],refs[recent]) for n,v in pred.items()}
    for i,o in enumerate(data['observations']):o.update(fold=int(fold_ids[i]),differences={n:float(v[i]) for n,v in pred.items()})
    result=dict(complete=True,gatePassed=gate,scores=scores,recentScores=recent_scores,folds=folds,observations=data['observations'],
        counts={k:data[k] for k in ('allStrictPairs','excludedNativePairs','externalPairs','referenceCount','groupCount')},
        protocolSha256=file_hash(ROOT/'protocol.json'),dataJsonSha256=file_hash(ROOT/'data.json'),dataSha256=file_hash(ROOT/'data.npz'),
        codeBindings=texture_listener.bindings(),scope=p['scope'],gatePolicy=p['gate'],
        limitations=['One listener and selected historic candidates; qualitative labels remain separate from strict ranking.',
            'Global texture statistics can miss individual events and order;21 baseline components retain those cues.',
            'Fixed continuation gate is not a statistical significance claim. New audio needs prospective human validation.'])
    if gate:
        m=texture_listener.fit(x,y,refs);m.save(ROOT/'metric.json',dict(protocolSha256=result['protocolSha256'],dataSha256=result['dataSha256'],gatePassed=True,scores=scores,scope=p['scope']))
        result['modelSha256']=file_hash(ROOT/'metric.json')
    verify(p);_json_write(ROOT/'evaluation.json',result)
    _json_write(BASE/'evaluations/texture-listener-v1-evaluation.json',result|{'fullReportSha256':file_hash(ROOT/'evaluation.json')})
    print(json.dumps(dict(gatePassed=gate,scores=scores,recentScores=recent_scores,counts=result['counts'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','extract','train']);args=parser.parse_args()
    dict(freeze=freeze,extract=extract,train=train)[args.stage]()
