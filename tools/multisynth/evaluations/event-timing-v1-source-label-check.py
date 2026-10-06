"""Additional check: every label and source ID matches actual native layer controls."""
import json
from pathlib import Path
from neural_invert.data import file_hash,_json_write
ROOT=Path('tools/multisynth/runs/event-timing-v1')
protocol=json.loads((ROOT/'protocol.json').read_text())
rows=json.loads((ROOT/'rows.json').read_text())
for row in rows:
    layers=json.loads(row['params']['layers'])
    assert [layer['start'] for layer in layers]==row['starts']
    assert len(layers)==len(row['componentIds'])
    for layer,key in zip(layers,row['componentIds']):
        source=protocol['bank'][key]['source']
        assert layer['synth']==source['synth'] and layer['params']==source['params']
        assert protocol['bank'][key]['split']==row['split']
        assert .2<=layer['gain']<=.9 and -6<=layer['pitch']<=6
receipt=dict(complete=True,rows=len(rows),scriptSha256=file_hash(__file__),
    protocolSha256=file_hash(ROOT/'protocol.json'),rowsSha256=file_hash(ROOT/'rows.json'),
    check='Every schedule label and component identity matches the corresponding actual Stackr layer controls.')
_json_write(Path(__file__).with_suffix('.json'),receipt)
print(json.dumps(receipt))
