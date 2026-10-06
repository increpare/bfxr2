"""Retain fresh-transfer judgments and the listener's unresolved playback concern."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import soundfile as sf
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import coverage_model
from multisynth.preference import training_pairs
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ARCHIVE=BASE/'listening_data/2026-10-06-support-transfer-v1-quick-01';GALLERY=BASE/'runs/support-transfer-v1-listening'
OUTPUT=Path(__file__).with_suffix('.json')
if OUTPUT.exists():raise FileExistsError('Preserve human review')
m=json.loads((ARCHIVE/'manifest.json').read_text());r=json.loads((GALLERY/'results.json').read_text())
assert coverage_model(GALLERY,r['results'],r['metadata'])['experimentId']==m['experimentId']
cs={c['id']:c for c in m['candidates']};rows=[];measurements=[]
for t in m['targets']:
 q=t['choice'];heard=set(q['auditionedCandidateIds']);selected=set(q['preferredCandidateIds'])
 rows.append(dict(name=t['source']['name'],kind=q['kind'],adequacy=q.get('adequacy'),note=t['note'],
  options=[dict(id=i['id'],role=cs[i['id']]['role'],aliases=cs[i['id']]['provenance']['selectionAliases'],heard=i['id'] in heard,selected=i['id'] in selected) for i in t['candidates']]))
 for role,info in [('reference',t['referenceAudio'])]+[(cs[i['id']]['role'],cs[i['id']]['audio']) for i in t['candidates']]:
  verify_archived_audio(ARCHIVE,info);w,sr=sf.read(ARCHIVE/info['file'],dtype='float32');assert sr==44100 and np.all(np.isfinite(w))
  measurements.append(dict(name=t['source']['name'],role=role,pcmSha256=info['pcmSha256'],seconds=len(w)/sr,peak=float(abs(w).max()),
   firstSample=float(w[0]),lastSample=float(w[-1]),maxAdjacentStep=float(abs(np.diff(w)).max()),mean=float(w.mean()),
   fullScaleSamples=int(np.count_nonzero(abs(w)>=.999))))
d=training_pairs([ARCHIVE]);counts=Counter(row['adequacy']['level'] if row['adequacy'] else row['kind'] for row in rows)
assert len(rows)==6 and len(cs)==17 and len(measurements)==23 and counts=={'similar':4,'least-bad':1,'none':1}
assert all(o['heard'] for row in rows for o in row['options']) and len(d.observations)==9
result=dict(complete=True,experimentId=m['experimentId'],scriptSha256=file_hash(__file__),feedbackSha256=file_hash(ARCHIVE/'feedback.json'),manifestSha256=file_hash(ARCHIVE/'manifest.json'),
 rows=rows,adequacyCounts=dict(counts),trainingPairSummary=d.summary,waveformMeasurements=measurements,
 listenerContext=dict(verbatim="i don't know if there's a problem with my speakers rn but I'm getting a lot more clicky/glitchy sounds on these pages",status='Unresolved: may concern in-file texture, player transitions, browser/audio-device path, or more than one. Preserve ratings without claiming the listening conditions were clean.'),
 interpretation=['Card event fit similar; snow-footstep whole fit similar; punch original Bfxr similar; cloth belt whole fit least-bad; laser shared whole/event fit similar; 1up none close. No very-close judgment.',
 'All17 options recorded heard; nine ordinal pairs and23 exact audio files. No broad event-fitting advantage.',
 'Peak-normalized PCM stays at0.5, with no full-scale samples; this excludes file-output hard clipping, not distortion already produced inside a synth.',
 'Nonzero endpoints and large adjacent steps are risk indicators, not proof of audible glitches; even the laser reference has near-full-range adjacent steps.',
 'Existing player abruptly stops at the current sample. A separate diagnostic uses a5ms manual-stop release, preserving full natural playback and all published experiment assets. No speaker diagnosis is established.'])
_json_write(OUTPUT,result)
print(json.dumps(dict(adequacyCounts=dict(counts),pairs=len(d.observations),files=len(measurements))))
