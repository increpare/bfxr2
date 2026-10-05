"""Freeze validated historical pairs, source families and exact audio locations."""
import json
from pathlib import Path
import numpy as np
import torch
from multisynth.preference import training_pairs, grouped_folds
from multisynth.embedding import family_groups
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth')
OUT=BASE/'runs/embedding-v1'

def main():
    torch.set_num_threads(1)
    if (OUT/'data.json').exists():raise FileExistsError('Preserve frozen data')
    archives=sorted(p.parent for p in (BASE/'listening_data').glob('*/manifest.json'))
    assert len(archives)==14
    data=training_pairs(archives)
    refs=[];audio={}
    for root in archives:
        m=json.loads((root/'manifest.json').read_text())
        for target in m['targets']:
            a=target['referenceAudio']
            refs.append(dict(pcm=a['pcmSha256'],source=target['source'],archive=root.name))
            audio[a['pcmSha256']]=dict(root=str(root),info=a)
        for c in m['candidates']:
            a=c['audio'];audio[a['pcmSha256']]=dict(root=str(root),info=a)
    groups=family_groups(refs)
    by_pcm={r['pcm']:g for r,g in zip(refs,groups)}
    families=np.array([by_pcm[p] for p in data.groups])
    folds=np.empty(len(families),int)
    for i,(tr,te) in enumerate(grouped_folds(families)):
        assert not set(families[tr]) & set(families[te]);folds[te]=i
    needed={o[k] for o in data.observations for k in ['referencePcmSha256','candidatePcmSha256A','candidatePcmSha256B']}
    OUT.mkdir(parents=True,exist_ok=True)
    payload=dict(archives=data.archives,summary=data.summary,observations=data.observations,
        x=data.x.tolist(),y=data.y.tolist(),families=families.tolist(),folds=folds.tolist(),
        references=[dict(**r,family=g) for r,g in zip(refs,groups)],audio={k:audio[k] for k in sorted(needed)})
    _json_write(OUT/'data.json',payload)
    protocol=dict(dataSha256=file_hash(OUT/'data.json'),prepareScriptSha256=file_hash(__file__),
        designSha256=file_hash('docs/superpowers/specs/2026-10-05-perceptual-embedding-design.md'),
        archives=data.archives,pairs=len(data.y),families=len(set(families)),uniquePairAudio=len(needed),
        folds=[dict(fold=i,testFamilies=sorted(set(families[folds==i])),testPairs=int(sum(folds==i))) for i in range(5)],
        gate='Hybrid >= .05 improvement in family-balanced accuracy over same-fold baseline, and no strict-pair accuracy loss',
        status='historical-development-screen-not-independent-test')
    _json_write(BASE/'evaluations/embedding-v1-protocol.json',protocol)
    print(json.dumps({k:protocol[k] for k in ['pairs','families','uniquePairAudio']}),flush=True)

if __name__=='__main__':main()
