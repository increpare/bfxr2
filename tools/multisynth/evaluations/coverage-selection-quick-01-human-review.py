"""Preserve explicit preferences without inventing adequacy or playback evidence."""
import json
from pathlib import Path
from multisynth.preference import training_pairs
from neural_invert.data import file_hash, _json_write

archive=Path('tools/multisynth/listening_data/2026-10-05-coverage-selection-quick-01')
gallery=Path('tools/multisynth/runs/coverage-selection-v1-listening/results.json')
manifest=json.loads((archive/'manifest.json').read_text())
raw=json.loads((archive/'feedback.json').read_text())
report=json.loads(gallery.read_text())
assert manifest['experimentId']==raw['experimentId']=='3afd5c29406ff55b3877ecefd48debf7174e7c871b7ff54f1f39c7454665b5e8'
data=training_pairs([archive])
records=[]
for target,source in zip(manifest['targets'],report['results']):
    assert target['source']==source['source']
    choice=target['choice']
    candidates={c['id']:c for c in manifest['candidates'] if c['targetId']==target['id']}
    winners=[candidates[cid] for cid in choice['preferredCandidateIds']]
    actual=source['source']['sourceTarget']['sourceParams']
    records.append(dict(name=target['source']['name'],kind=choice['kind'],
        preferredRoles=[c['role'] for c in winners],preferredCandidateIds=choice['preferredCandidateIds'],
        referencePcmSha256=target['referenceAudio']['pcmSha256'],
        auditionedCandidateIds=choice['auditionedCandidateIds'],
        absoluteAdequacy=None,notes=target['note'],
        controlEvidence={key:dict(target=actual[key],previous=source['candidates'][0]['params'][key],
            expanded=source['candidates'][1]['params'][key]) for key in ('duration','attack','release','pitch','level','vibrato')},
        descriptorDistances={c['role']:c['score'] for c in source['candidates']}))
out=dict(complete=True,experimentId=manifest['experimentId'],scriptSha256=file_hash(__file__),
    feedbackSha256=file_hash(archive/'feedback.json'),manifestSha256=file_hash(archive/'manifest.json'),
    galleryReportSha256=file_hash(gallery),summary=manifest['summary'],trainingPairSummary=data.summary,
    strictHeardPairs=len(data.y),records=records,
    interpretation=['Expanded model explicitly preferred on both gesture references; texture judged a tie.',
        'No scalar ratings, notes or absolute adequacy judgments were supplied. Do not infer convincing recreations or extend the previous batch\'s zero-convincing verdict to this batch.',
        'Warbling sweep playback telemetry is empty. Retain its explicit submitted choice, but the existing heard-only training policy does not create a strict pair from it. This is missing telemetry, not proof the user did not listen.',
        'Bouncing rise produces one strict heard-only training pair. Texture tie stays tie evidence, with no directional training label.',
        'Known source controls show closer duration on both preferred gestures; warble ending level also becomes closer. These observations do not establish what caused the human preference.',
        'Expanded bouncing-rise release remains substantially below the source setting. The preference is compatible with remaining recreation errors.',
        'Targets were deliberately selected after numerical evaluation, share synth preset families, and are synthetic. No population win rate or real-recording transfer follows.'])
destination=Path('tools/multisynth/evaluations/coverage-selection-quick-01-human-review.json')
if destination.exists():raise FileExistsError('Fresh review required')
_json_write(destination,out)
print(json.dumps(dict(summary=out['summary'],strictHeardPairs=out['strictHeardPairs'],preferences=[(r['name'],r['kind'],r['preferredRoles']) for r in records])),flush=True)
