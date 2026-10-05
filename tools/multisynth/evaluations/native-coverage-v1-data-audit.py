"""Verify original prefix, disjoint controls/PCM/features, and retained split counts."""
import json
from pathlib import Path
import numpy as np
from neural_invert.data import file_hash,_json_write

source=Path('tools/multisynth/runs/temporal-v3/data')
expanded=Path('tools/multisynth/runs/native-coverage-v1/data')
output=Path('tools/multisynth/evaluations/native-coverage-v1-data-audit.json')
if output.exists():raise FileExistsError('Fresh audit output required')
old=json.loads((source/'Transfxr.json').read_text())
new=json.loads((expanded/'Transfxr.json').read_text())
manifest=json.loads((expanded/'manifest.json').read_text())
assert manifest['complete']
assert file_hash(expanded/'Transfxr.json')==manifest['metadataSha256']
assert file_hash(expanded/'Transfxr.npz')==manifest['npzSha256']
count=len(old['rows']);assert count==manifest['oldCount']
assert new['rows'][:count]==old['rows'] and new['spec']==old['spec']
assert new['splits']['oldTrain']==old['train'] and new['splits']['oldVal']==old['val']
with np.load(source/'Transfxr.npz') as a,np.load(expanded/'Transfxr.npz') as b:
    assert set(a.files)==set(b.files)
    for key in a.files:
        left,right=a[key],b[key][:count]
        assert left.dtype==right.dtype and left.shape==right.shape and left.tobytes()==right.tobytes()
splits=new['splits'];rows=new['rows']
train=splits['oldTrain']+splits['newTrain'];held=splits['oldVal']+splits['newVal']+splits['reserved']
assert set(train).isdisjoint(held) and len(set(train+held))==len(rows)
overlaps={k:len({rows[i][k] for i in train}&{rows[i][k] for i in held}) for k in ('parameterHash','audioHash','packedFeatureHash')}
assert not any(overlaps.values())
result=dict(complete=True,scriptSha256=file_hash(__file__),sourceManifestSha256=file_hash(source/'manifest.json'),
    expandedManifestSha256=file_hash(expanded/'manifest.json'),originalRows=count,totalRows=len(rows),
    originalPrefixByteExact=True,originalSplitsUnchanged=True,counts={k:len(v) for k,v in splits.items()},
    exactTrainHoldoutOverlaps=overlaps,
    replayVerification='Builder independently re-rendered16 randomly selected rows per new shard and reproduced packed features exactly; see bound expanded manifest. This audit does not repeat all DSP renders.',
    generalizationScope='Distinct generated control draws; preset families are shared, not held out.')
_json_write(output,result);print(json.dumps(result),flush=True)
