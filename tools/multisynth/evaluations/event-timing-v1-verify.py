"""Independently check timing-model data isolation, checkpoint and decision gate."""
import json
from pathlib import Path
import hashlib
from collections import Counter
import numpy as np
import soundfile as sf
import torch
from torch.nn import functional as F
from neural_invert.event_timing import TimingNet,features,targets
from neural_invert.data import file_hash,_json_write
from neural_invert.benchmark import audio_hash
from neural_invert.experiment import audition_pcm
from multisynth.timeline import TimelineRenderer

BASE=Path('tools/multisynth');ROOT=BASE/'runs/event-timing-v1'

def counts(truth,prediction):
    # Independent maximum matching via DP, rather than evaluation's two-pointer matcher.
    a=sorted(truth);b=sorted(prediction);dp=np.zeros((len(a)+1,len(b)+1),dtype=int)
    for i,x in enumerate(a,1):
        for j,y in enumerate(b,1):
            dp[i,j]=max(dp[i-1,j],dp[i,j-1],dp[i-1,j-1]+int(abs(x-y)<=.025+1e-12))
    tp=int(dp[-1,-1]);return dict(tp=tp,fp=len(b)-tp,fn=len(a)-tp)

def main():
    torch.set_num_threads(1)
    protocol=json.loads((ROOT/'protocol.json').read_text());manifest=json.loads((ROOT/'data-manifest.json').read_text())
    training=json.loads((ROOT/'training.json').read_text());result=json.loads((ROOT/'evaluation.json').read_text())
    rows=json.loads((ROOT/'rows.json').read_text());data=np.load(ROOT/'data.npz')
    assert all(x['complete'] for x in (protocol,manifest,training,result))
    assert all(file_hash(p)==h for p,h in protocol['codeHashes'].items())
    assert manifest['protocolSha256']==training['protocolSha256']==result['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert manifest['dataSha256']==file_hash(ROOT/'data.npz') and manifest['rowsSha256']==file_hash(ROOT/'rows.json')
    assert training['checkpointSha256']==result['checkpointSha256']==file_hash(ROOT/'best.pt')
    controls={s:set() for s in ('train','val','test')};pcms={s:set() for s in controls};per=Counter()
    for key,item in protocol['bank'].items():
        source=item['source'];expected=hashlib.sha256(json.dumps({k:source[k] for k in ('synth','params')},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        assert key==expected and file_hash(item['file'])==item['fileSha256']
        wave,sr=sf.read(item['file'],dtype='float32');assert sr==44100 and audio_hash(wave)==item['pcmHash']
        split='train' if int(key[:8],16)%100<50 else 'val' if int(key[:8],16)%100<75 else 'test'
        assert split==item['split'];controls[split].add(key);pcms[split].add(item['pcmHash']);per[split,source['synth']]+=1
    for a,b in [('train','val'),('train','test'),('val','test')]:
        assert controls[a].isdisjoint(controls[b]) and pcms[a].isdisjoint(pcms[b])
    for split in controls:
        assert all(per[split,name]==protocol['pool'][split] for name in protocol['engines'])
        indices=manifest['splits'][split]
        assert len(indices)==protocol['counts'][split] and all(rows[i]['split']==split for i in indices)
        for i in indices:
            row=rows[i];assert set(row['componentIds'])<=controls[split]
            np.testing.assert_array_equal(targets(row['starts']),data['targets'][i])
    assert sorted(sum(manifest['splits'].values(),[]))==list(range(len(rows)))
    checkpoint=torch.load(ROOT/'best.pt',weights_only=False);model=TimingNet();model.load_state_dict(checkpoint['model']);model.eval()
    assert checkpoint['epoch']==training['bestEpoch']==min(training['history'],key=lambda h:h['validation'])['epoch']
    assert len(training['history'])==40 and training['bestValidation']==min(h['validation'] for h in training['history'])
    ids=manifest['splits']['val'];total=0.
    with torch.no_grad():
        for start in range(0,len(ids),64):
            ix=ids[start:start+64];logits=model(torch.from_numpy(data['features'][ix]))
            value=F.binary_cross_entropy_with_logits(logits,torch.from_numpy(data['targets'][ix]),pos_weight=torch.tensor(10.))
            total+=float(value)*len(ix)
    reproduced=total/len(ids)
    assert abs(reproduced-training['bestValidation'])<1e-9
    # Re-render a fixed source-independent sample of each split, plus all stored feature/label shape checks.
    assert data['features'].shape==(len(rows),25,256) and data['targets'].shape==(len(rows),256)
    assert np.isfinite(data['features']).all() and np.isfinite(data['targets']).all()
    replay=0
    with TimelineRenderer() as renderer:
        assert renderer.inventory==protocol['inventory']
        for split in controls:
            ids=manifest['splits'][split]
            for i in ids[::max(1,len(ids)//8)]:
                row=rows[i];params,wave=renderer.render(row['params'],uncached=True);heard=audition_pcm(wave)
                assert params==row['params'] and audio_hash(wave)==row['nativeHash'] and audio_hash(heard)==row['auditionHash']
                np.testing.assert_array_equal(features(heard),data['features'][i]);replay+=1
    test={rows[i]['id']:rows[i] for i in manifest['splits']['test']};summaries={}
    assert len(result['rows'])==3*len(test)
    for kind in ('native','4bit','lowpass1500'):
        group=[r for r in result['rows'] if r['kind']==kind]
        assert len(group)==len(test) and {r['id'] for r in group}==set(test)
        summaries[kind]={}
        for arm in ('learned','heuristic'):
            totals=Counter();correct=0
            for row in group:
                assert row['trueStarts']==test[row['id']]['starts'][1:]
                expected=counts(row['trueStarts'],row[arm]['predicted'])
                assert all(row[arm][k]==v for k,v in expected.items());totals.update(expected)
                cc=len(row['trueStarts'])==len(row[arm]['predicted']);assert cc==row[arm]['countCorrect'];correct+=cc
            tp,fp,fn=(totals[k] for k in ('tp','fp','fn'))
            summary=dict(**totals,precision=tp/max(1,tp+fp),recall=tp/max(1,tp+fn),f1=2*tp/max(1,2*tp+fp+fn),countAccuracy=correct/len(group),targets=len(group))
            assert summary==result['summaries'][kind][arm];summaries[kind][arm]=summary
    native=summaries['native'];passed=bool(native['learned']['f1']>=.75 and native['learned']['f1']>=native['heuristic']['f1']+.10 and native['learned']['countAccuracy']>=.75 and all(summaries[k]['learned']['f1']>=summaries[k]['heuristic']['f1'] for k in ('4bit','lowpass1500')))
    assert result['gatePassed']==passed
    receipt=dict(complete=True,scriptSha256=file_hash(__file__),evaluationSha256=file_hash(ROOT/'evaluation.json'),
        checkpointSha256=file_hash(ROOT/'best.pt'),sourceComponents={k:len(v) for k,v in controls.items()},
        examples=len(rows),independentUncachedReplays=replay,testRowsPerCondition=len(test),
        reproducedValidation=reproduced,gatePassed=passed,
        checks=['Canonical controls and exact source PCM disjoint across splits','Exact40-epoch minimum-validation checkpoint','All labels reconstructed from native schedules','All metric counts and fixed gate independently reconstructed'])
    _json_write(BASE/'evaluations/event-timing-v1-verification.json',receipt);print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
