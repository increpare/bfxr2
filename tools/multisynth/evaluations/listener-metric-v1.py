"""Frozen group-held-out listener metric experiment on archived external sounds."""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from multisynth.listener_metric import source_groups,fit,bindings,RECIPE
from multisynth.preference import training_pairs,PreferenceMetric,score_summary,grouped_folds
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/listener-metric-v1'
OLD=BASE/'models/preference-neural-v2.json'
PLAN=Path('docs/superpowers/plans/2026-10-06-listener-metric.md')


def freeze():
    if ROOT.exists():raise FileExistsError('Preserve listener experiment')
    archives=sorted(BASE.glob('listening_data/*/manifest.json'));records=[]
    for p in archives:
        for t in json.loads(p.read_text())['targets']:
            records.append(dict(reference=t['referenceAudio']['pcmSha256'],source=t['source']))
    groups=source_groups(records)
    p=dict(complete=True,archives={str(a.parent):dict(manifestSha256=file_hash(a),feedbackSha256=file_hash(a.parent/'feedback.json')) for a in archives},
           groups=groups,groupCount=len(set(groups.values())),recipe=RECIPE,bindings=bindings(),scriptSha256=file_hash(__file__),
           planSha256=file_hash(PLAN),oldMetricSha256=file_hash(OLD),groupPolicy='Connected exact reference PCM, source SHA and conservative tag/collection-directory labels. Native references excluded.',
           scope='Retrospective grouped preference prediction, not generated likeness. Current frozen preference comparator trained on some older labels. No absolute score inferred from adequacy or none/tie.')
    assert p['groupCount']>=5
    ROOT.mkdir();_json_write(ROOT/'protocol.json',p)
    _json_write(BASE/'evaluations/listener-metric-v1-protocol.json',p|dict(protocolSha256=file_hash(ROOT/'protocol.json')))
    print(json.dumps(dict(archives=len(archives),externalPCM=len(groups),connectedGroups=p['groupCount'])),flush=True)


def verify(p):
    receipt=json.loads((BASE/'evaluations/listener-metric-v1-protocol.json').read_text())
    assert receipt['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert p['scriptSha256']==file_hash(__file__) and p['bindings']==bindings() and p['recipe']==RECIPE
    assert p['planSha256']==file_hash(PLAN) and p['oldMetricSha256']==file_hash(OLD)
    for root,a in p['archives'].items():
        assert file_hash(Path(root)/'manifest.json')==a['manifestSha256'] and file_hash(Path(root)/'feedback.json')==a['feedbackSha256']


def extract():
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    if (ROOT/'data.json').exists():raise FileExistsError('Preserve extracted evidence')
    data=training_pairs(list(p['archives']));paths={}
    for root in p['archives']:
        m=json.loads((Path(root)/'manifest.json').read_text())
        for a in [t['referenceAudio'] for t in m['targets']]+[c['audio'] for c in m['candidates']]:
            paths.setdefault(a['pcmSha256'],Path(root)/a['file'])
    keep=np.array([ref in p['groups'] for ref in data.groups]);observations=[o for o,k in zip(data.observations,keep) if k]
    x=data.x[keep];y=data.y[keep];refs=data.groups[keep];groups=np.array([p['groups'][ref] for ref in refs])
    waves={};cache={};objectives={};soft=[]
    def wave(pcm):
        if pcm not in waves:
            w,rate=sf.read(paths[pcm],dtype='float32');assert rate==44100;waves[pcm]=w
        return waves[pcm]
    def score(ref,cand):
        key=(ref,cand)
        if key not in cache:
            if ref not in objectives:objectives[ref]=SoftPeriodicityObjective(wave(ref))
            cache[key]=float(objectives[ref].score(wave(cand)))
        return cache[key]
    for i,o in enumerate(observations):
        soft.append(score(o['referencePcmSha256'],o['candidatePcmSha256A'])-score(o['referencePcmSha256'],o['candidatePcmSha256B']))
        if (i+1)%64==0:print(json.dumps(dict(extracted=i+1,total=len(observations))),flush=True)
    values=np.column_stack([x,soft]);assert np.isfinite(values).all()
    np.savez_compressed(ROOT/'data.npz',x=values,y=y,references=refs,groups=groups)
    meta=dict(complete=True,observations=observations,archiveSummary=data.summary,allStrictPairs=len(data.y),
        excludedNativePairs=int((~keep).sum()),externalPairs=len(y),referenceCount=len(set(refs)),groupCount=len(set(groups)),
        protocolSha256=file_hash(ROOT/'protocol.json'),dataSha256=file_hash(ROOT/'data.npz'),
        softScores=[dict(reference=r,candidate=c,score=value) for (r,c),value in cache.items()])
    verify(p);_json_write(ROOT/'data.json',meta)
    print(json.dumps({k:meta[k] for k in ('allStrictPairs','excludedNativePairs','externalPairs','referenceCount','groupCount')}),flush=True)


def train():
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    if (ROOT/'evaluation.json').exists():raise FileExistsError('Preserve evaluation')
    meta=json.loads((ROOT/'data.json').read_text());assert meta['complete'] and meta['dataSha256']==file_hash(ROOT/'data.npz')
    with np.load(ROOT/'data.npz',allow_pickle=False) as d:x,y,refs,groups=(d[k] for k in ('x','y','references','groups'))
    predictions=np.empty(len(y));fold_ids=np.empty(len(y),int);folds=[]
    for i,(tr,te) in enumerate(grouped_folds(groups,RECIPE['folds'])):
        assert not set(groups[tr])&set(groups[te]) and not set(refs[tr])&set(refs[te])
        model=fit(x[tr],y[tr],refs[tr]);predictions[te]=x[te]@(model.weights/model.scales);fold_ids[te]=i
        folds.append(dict(fold=i,trainGroups=sorted(set(groups[tr])),testGroups=sorted(set(groups[te])),
            trainReferences=sorted(set(refs[tr])),testReferences=sorted(set(refs[te])),
            trainPairs=int(tr.sum()),testPairs=int(te.sum()),weights=model.weights.tolist(),scales=model.scales.tolist(),
            scores=score_summary(predictions[te],y[te],refs[te])))
    old=PreferenceMetric.load(OLD);old_predictions=x[:,:20]@(old.weights/old.scales)
    scores={name:score_summary(values,y,refs) for name,values in [('listener-heldout',predictions),('old-preference-historical',old_predictions),('soft-periodicity',x[:,-1])]}
    new=scores['listener-heldout']['referenceBalancedAccuracy'];prior=scores['old-preference-historical']['referenceBalancedAccuracy'];soft=scores['soft-periodicity']['referenceBalancedAccuracy']
    gate=bool(new>=prior+RECIPE['gateOldImprovement'] and new>=soft)
    recent=np.array([o['archive']=='2026-10-06-pair-inverse-v1-quick-01' for o in meta['observations']])
    recent_scores={name:score_summary(values[recent],y[recent],refs[recent]) for name,values in [('listener-heldout',predictions),('old-preference-historical',old_predictions),('soft-periodicity',x[:,-1])]}
    for i,o in enumerate(meta['observations']):o.update(fold=int(fold_ids[i]),heldoutDifference=float(predictions[i]),oldDifference=float(old_predictions[i]),softDifference=float(x[i,-1]))
    result=dict(complete=True,gatePassed=gate,scores=scores,recentScores=recent_scores,folds=folds,observations=meta['observations'],
        counts={k:meta[k] for k in ('allStrictPairs','excludedNativePairs','externalPairs','referenceCount','groupCount')},
        protocolSha256=file_hash(ROOT/'protocol.json'),dataJsonSha256=file_hash(ROOT/'data.json'),dataSha256=file_hash(ROOT/'data.npz'),
        codeBindings=bindings(),scope=p['scope'],limitations=['Source/tag grouping is conservative but does not certify every related take.',
            'One listener, repeated references, and selected historical candidates; no prospective synthesis result follows from ranking accuracy.',
            'Uncertainty is substantial; fixed gate is an experiment continuation rule, not statistical significance.'])
    if gate:
        model=fit(x,y,refs);model.save(ROOT/'metric.json',dict(protocolSha256=result['protocolSha256'],dataSha256=result['dataSha256'],gatePassed=True,groupedScores=scores,scope=p['scope']))
        result['modelSha256']=file_hash(ROOT/'metric.json')
    verify(p);_json_write(ROOT/'evaluation.json',result)
    _json_write(BASE/'evaluations/listener-metric-v1-evaluation.json',result|dict(fullReportSha256=file_hash(ROOT/'evaluation.json')))
    print(json.dumps(dict(gatePassed=gate,scores=scores,recentScores=recent_scores,counts=result['counts'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','extract','train']);a=parser.parse_args()
    dict(freeze=freeze,extract=extract,train=train)[a.stage]()
