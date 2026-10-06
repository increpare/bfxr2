"""Measure native source tails of the predeclared starting patches."""
import json
from pathlib import Path
from multisynth.timeline import TimelineRenderer
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');protocol=BASE/'runs/joint-events-v1/protocol.json'
output=Path(__file__).with_suffix('.json')
if output.exists():raise FileExistsError('Preserve audit')
p=json.loads(protocol.read_text());rows=[]
with TimelineRenderer() as renderer:
    assert renderer.inventory==p['inventory']
    for entry in p['rows']:
        pp=entry['initial']['params'];layers=json.loads(pp['layers']);sources=[]
        for j,layer in enumerate(layers):
            _,wave=renderer.source(layer,seed=pp['seed'])
            end=layer['start']+len(wave)/44100/(2**(layer['pitch']/12))
            overlap=max(0.,end-layers[j+1]['start']) if j+1<len(layers) else None
            sources.append(dict(synth=layer['synth'],start=layer['start'],end=end,overlapNextSeconds=overlap))
        rows.append(dict(name=entry['target']['source']['name'],sources=sources))
result=dict(complete=True,scriptSha256=file_hash(__file__),protocolSha256=file_hash(protocol),rows=rows,
    interpretation='Waveform support overlap, not perceptual tail audibility. Sources have no crop-length constraint once assembled.')
_json_write(output,result);print(json.dumps(result))
