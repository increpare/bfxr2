"""Independent data/checkpoint checks for the onset input ablation.

Reuses tested feature extraction and per-row acoustic energy, but independently
checks split membership, saved states and weighted validation aggregation.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from multisynth.renderer import Renderer
from neural_invert.data import file_hash, verify_dataset_files
from neural_invert.onset import onset_features, FEATURE_POLICY
from neural_invert.onset_train import load
from neural_invert.temporal import acoustic_energy

ROOT=Path('tools/multisynth/runs/onset-v1')


def data_audit():
    directory=ROOT/'data-parallel'
    derived=json.loads((directory/'manifest.json').read_text())
    assert derived['complete'] and derived['featurePolicy']==FEATURE_POLICY
    source=Path(derived['sourcePath'])
    manifest=json.loads((source/'manifest.json').read_text())
    assert derived['sourceManifestSha256']==file_hash(source/'manifest.json')
    verify_dataset_files(source,manifest)
    rng=np.random.default_rng(20261016)
    report={'derivedManifestSha256':file_hash(directory/'manifest.json'),'engines':{}}
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash']==derived['sourceHash']==manifest['sourceHash']
        for name in derived['engines']:
            metadata=json.loads((source/(name+'.json')).read_text())
            rows=metadata['rows'];x=np.load(directory/(name+'.npy'),mmap_mode='r')
            assert file_hash(directory/(name+'.npy'))==derived['files'][name]['onsetSha256']
            assert x.shape==(len(rows),64,128) and x.dtype==np.float16
            assert np.isfinite(x).all() and x.min()>=-1 and x.max()<=0
            train,val=metadata['train'],metadata['val']
            assert set(train).isdisjoint(val) and sorted(train+val)==list(range(len(rows)))
            assert {rows[i]['parameterHash'] for i in train}.isdisjoint({rows[i]['parameterHash'] for i in val})
            chosen=[int(i) for ids in (train,val) for i in rng.choice(ids,8,replace=False)]
            for i in chosen:
                row=rows[i];params,wave=renderer.render(name,row['params'],row['seed'])
                assert params==row['params']
                assert hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest()==row['audioHash']
                np.testing.assert_array_equal(x[i],onset_features(wave).astype('<f2'))
            report['engines'][name]={'rows':len(rows),'train':len(train),'validation':len(val),
                                    'independentReplayRows':chosen,'exact':True}
    return report


def training_audit():
    torch.set_num_threads(1)
    report={'engines':{}}
    for name in ('Bfxr','Transfxr'):
        report['engines'][name]={}
        paired_metadata=[]
        for arm in ('control','onset'):
            directory=ROOT/'models'/name/arm
            model,metadata=load(directory)
            paired_metadata.append(metadata)
            training=json.loads((directory/'training.json').read_text())
            source=Path(metadata['sourcePath'])
            rowmeta=json.loads((source/(name+'.json')).read_text())
            ids=np.asarray(rowmeta['val'])
            original=np.load(source/(name+'.npz'))
            fine=np.load(Path(metadata['dataPath'])/(name+'.npy'),mmap_mode='r')
            mean,std=[np.asarray(metadata['normalization'][k],np.float32) for k in ('mean','std')]
            rows=rowmeta['rows']
            structured=np.array([bool(rows[i].get('structured')) or rows[i].get('origin')=='structured'
                                 or rows[i].get('mode')=='structured' for i in ids])
            weights=np.ones(len(ids),np.float64)
            if structured.any() and not structured.all():
                weights[structured]=len(ids)/(2*structured.sum())
                weights[~structured]=len(ids)/(2*(~structured).sum())
            errors=[]
            with torch.no_grad():
                for offset in range(0,len(ids),128):
                    batch=ids[offset:offset+128]
                    x=torch.from_numpy((original['features'][batch].astype(np.float32)-mean)/std)
                    y={'continuous':torch.from_numpy(original['continuous'][batch]),
                       'categorical':torch.from_numpy(original['categorical'][batch].astype(np.int64))}
                    prediction=model(x,torch.from_numpy(fine[batch].astype(np.float32)))
                    errors.extend(acoustic_energy(prediction,y,metadata['spec'])[:,0].numpy().tolist())
            recomputed=float(np.mean(np.asarray(errors)*weights))
            assert abs(recomputed-training['bestValidation'])<2e-5,(name,arm,recomputed,training['bestValidation'])
            assert len(training['history'])==90
            assert training['bestEpoch']==min(training['history'],key=lambda x:x['validation'])['epoch']
            report['engines'][name][arm]={'checkpointSha256':metadata['checkpointSha256'],
                'bestEpoch':training['bestEpoch'],'savedValidation':training['bestValidation'],
                'independentCpuValidation':recomputed,'absoluteDifference':abs(recomputed-training['bestValidation']),
                'rows':len(ids),'fullHistorySha256':file_hash(directory/'training.json')}
        a,b=paired_metadata
        for key in ('initialWeightsHash','splitHash','normalization','seed','epochs','batchSize','device','dataManifestSha256'):
            assert a[key]==b[key],key
        report['engines'][name]['pairedConditionsEqual']=True
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['data','training']);p.add_argument('--output',required=True)
    a=p.parse_args();torch.set_num_threads(1)
    out=Path(a.output)
    if out.exists():raise FileExistsError('Use fresh verification output')
    result=data_audit() if a.phase=='data' else training_audit()
    result.update(passed=True,scriptSha256=file_hash(__file__))
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
