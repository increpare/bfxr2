"""Exploratory tempo-range diagnostic, after observing external boundary proposals.

Not part of the original gate. Reuses held-out components, with new schedules.
No checkpoint, threshold, listening target or frozen pipeline is changed.
"""
import json
from pathlib import Path
import numpy as np
import torch
from multisynth.timeline import TimelineRenderer
from multisynth.event_split import split_events
from neural_invert.event_timing import TimingNet,features,decode,match_events
from neural_invert.experiment import audition_pcm
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/event-timing-v1'
OUT=BASE/'evaluations/event-timing-v1-tempo-stress.json'
assert not OUT.exists(), 'Keep exploratory diagnostic immutable'
torch.set_num_threads(1)
manifest=json.loads((ROOT/'data-manifest.json').read_text());rows=json.loads((ROOT/'rows.json').read_text())
protocol=json.loads((ROOT/'protocol.json').read_text())
model=TimingNet();model.load_state_dict(torch.load(ROOT/'best.pt',weights_only=False)['model']);model.eval()
frozen=dict(scriptSha256=file_hash(__file__),checkpointSha256=file_hash(ROOT/'best.pt'),
    parentManifestSha256=file_hash(ROOT/'data-manifest.json'),sourceRowsSha256=file_hash(ROOT/'rows.json'),
    externalProposalProtocolSha256=file_hash(BASE/'runs/learned-events-v1/protocol.json'),
    scales=[.5,1.5],scope='Exploratory after seeing external boundary proposals. Known held-out native components rescheduled at half/one-and-a-half start spacing. Source duration/pitch/gain unchanged, so overlap also changes. Not an untouched test or gate revision.')
_json_write(ROOT/'tempo-stress-protocol.json',frozen)
results=[]
with TimelineRenderer() as renderer,torch.no_grad():
    assert renderer.inventory==protocol['inventory']
    for i in manifest['splits']['test']:
        row=rows[i]
        for scale in frozen['scales']:
            params=dict(row['params']);layers=json.loads(params['layers'])
            for layer in layers:layer['start']*=scale
            params['layers']=json.dumps(layers);canonical,wave=renderer.render(params)
            audio=audition_pcm(wave);x=features(audio);prob=model(torch.from_numpy(x)[None]).sigmoid()[0].numpy()
            truth=[l['start'] for l in json.loads(canonical['layers'])][1:]
            result=dict(id=row['id'],scale=scale,truth=truth,nativeHash=audio_hash(wave))
            for arm,cuts in [('learned',decode(prob,len(audio))),('heuristic',split_events(audio))]:
                predicted=[x/44100 for x in cuts[1:-1]]
                result[arm]=dict(**match_events(truth,predicted),predicted=predicted,countCorrect=len(truth)==len(predicted))
            results.append(result)
summaries={}
for scale in frozen['scales']:
    group=[r for r in results if r['scale']==scale];summaries[str(scale)]={}
    for arm in ('learned','heuristic'):
        counts={k:sum(r[arm][k] for r in group) for k in ('tp','fp','fn')};tp,fp,fn=(counts[k] for k in ('tp','fp','fn'))
        summaries[str(scale)][arm]=dict(**counts,f1=2*tp/max(1,2*tp+fp+fn),countAccuracy=sum(r[arm]['countCorrect'] for r in group)/len(group),targets=len(group))
_json_write(OUT,dict(complete=True,protocol=frozen,summaries=summaries,rows=results))
print(json.dumps(summaries),flush=True)
