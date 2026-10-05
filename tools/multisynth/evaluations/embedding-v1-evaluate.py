"""Identical-family-fold comparison; historical development, not a fresh test."""
import json
from pathlib import Path
import numpy as np
import torch
from multisynth.embedding import cosine, fit_components
from multisynth.preference import PRIOR, PreferenceMetric, score_summary
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth'); RUN=BASE/'runs/embedding-v1'

def main():
    torch.set_num_threads(1)
    output=BASE/'evaluations/embedding-v1-evaluation.json'
    if output.exists():raise FileExistsError('Preserve original evaluation')
    data=json.loads((RUN/'data.json').read_text())
    protocol=json.loads((BASE/'evaluations/embedding-v1-protocol.json').read_text())
    extraction=json.loads((BASE/'evaluations/embedding-v1-extraction.json').read_text())
    assert extraction['complete'] and file_hash(RUN/'data.json')==protocol['dataSha256']==extraction['binding']['dataSha256']
    assert extraction['binding']['encoderSha256']==file_hash(BASE/'embedding.py')
    cached={}
    for record in extraction['records']:
        pcm=record['pcmSha256'];path=RUN/'cache'/(pcm+'.npz')
        assert file_hash(path)==record['embeddingSha256']
        with np.load(path) as f:cached[pcm]={k:f[k].astype(float) for k in f.files}
    x=np.array(data['x']);y=np.array(data['y']);groups=np.array(data['families']);fold=np.array(data['folds'])
    extra=[]
    for o in data['observations']:
        r,a,b=(cached[o[k]] for k in ['referencePcmSha256','candidatePcmSha256A','candidatePcmSha256B'])
        extra.append([cosine(r[k],a[k])-cosine(r[k],b[k]) for k in ['task','style']])
    extra=np.array(extra);all_x=np.column_stack([x,extra])
    predictions={'clap-task':extra[:,0],'clap-style':extra[:,1]}
    frozen=PreferenceMetric.load(BASE/'models/preference-neural-v2.json')
    predictions['historical-frozen-descriptive']=x@(frozen.weights/frozen.scales)
    fits={}
    for name,xx,prior in [('refit-current',x,PRIOR),('hybrid',all_x,np.r_[PRIOR*.8,.1,.1])]:
        pred=np.empty(len(y));models=[]
        for i in range(5):
            tr=fold!=i;te=~tr
            assert not set(groups[tr])&set(groups[te])
            w,s=fit_components(xx[tr],y[tr],groups[tr],prior)
            pred[te]=xx[te]@(w/s)
            models.append(dict(fold=i,weights=w.tolist(),scales=s.tolist(),trainPairs=int(sum(tr)),testPairs=int(sum(te))))
        predictions[name]=pred;fits[name]=models
    scores={k:score_summary(v,y,groups) for k,v in predictions.items()}
    per_family=[]
    for group in sorted(set(groups)):
        ix=groups==group
        per_family.append(dict(family=group,pairs=int(sum(ix)),fold=int(fold[ix][0]),
            references=sorted({o['target'] for o,use in zip(data['observations'],ix) if use}),
            scores={k:score_summary(v[ix],y[ix],groups[ix]) for k,v in predictions.items()}))
    delta=np.array([r['scores']['hybrid']['pairAccuracy']-r['scores']['refit-current']['pairAccuracy'] for r in per_family])
    rng=np.random.default_rng(20261005)
    boots=rng.choice(delta,size=(10000,len(delta)),replace=True).mean(1)
    gain=scores['hybrid']['referenceBalancedAccuracy']-scores['refit-current']['referenceBalancedAccuracy']
    passed=gain>=.05 and scores['hybrid']['pairAccuracy']>=scores['refit-current']['pairAccuracy']
    observations=[]
    for i,o in enumerate(data['observations']):
        observations.append({**o,'family':str(groups[i]),'fold':int(fold[i]),'embeddingDifferences':extra[i].tolist(),
            'predictions':{k:float(v[i]) for k,v in predictions.items()}})
    per_archive={}
    for archive in data['archives']:
        ix=np.array([o['archive']==archive['archive'] for o in observations])
        if ix.any():per_archive[archive['archive']]={k:score_summary(v[ix],y[ix],groups[ix]) for k,v in predictions.items()}
    result=dict(complete=True,scriptSha256=file_hash(__file__),protocolSha256=file_hash(BASE/'evaluations/embedding-v1-protocol.json'),
        extractionSha256=file_hash(BASE/'evaluations/embedding-v1-extraction.json'),scores=scores,fits=fits,
        gate=dict(passed=passed,requiredFamilyBalancedGain=.05,observedGain=gain,
            familyBootstrapGain95Percent=np.quantile(boots,[.025,.975]).tolist()),
        perFamily=per_family,perArchive=per_archive,observations=observations,
        limitations=['Historical development screen: prior experiments and architecture decisions used this feedback.',
            'Conservative provenance grouping catches known transforms/aliases and numeric takes, not every unknown acoustic family.',
            'Frozen historical scorer has trained on some of these judgments; descriptive only, not an unbiased baseline.',
            'A preference screen cannot prove candidate adequacy; no inverse checkpoint is trained or promoted here.',
            'LAION checkpoint is not the Microsoft CLAP style encoder in the cited instrument-timbre study.'])
    _json_write(output,result)
    print(json.dumps(dict(scores=scores,gate=result['gate']),indent=2),flush=True)

if __name__=='__main__':main()
