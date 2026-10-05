"""Audit latest human choices against exact audition PCM and frozen scorers.

This is a descriptive review, not a new trained-model or generalization claim.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth import features, perceptual
from multisynth.preference import PreferenceMetric, training_pairs
from multisynth.train_perceptual import PerceptualMetric

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'tools/multisynth'
ARCHIVE = BASE / 'listening_data/2026-10-05-pitch-calibration-quick-01'
REPORT = BASE / 'runs/pitch-calibration-listening-v1/results.json'
OUTPUT = Path(__file__).with_suffix('.json')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wave(audio):
    path = (ARCHIVE / audio['file']).resolve()
    assert path.is_relative_to(ARCHIVE.resolve())
    pcm, rate = sf.read(path, dtype='int16', always_2d=True)
    assert rate == 44100 and pcm.shape[1] == 1
    assert hashlib.sha256(str((rate, pcm.shape)).encode() + pcm.astype('<i2').tobytes()).hexdigest() == audio['pcmSha256']
    return pcm[:, 0].astype('float32') / 32768


def main():
    assert not OUTPUT.exists(), 'Human review output must be fresh'
    torch.set_num_threads(1)
    manifest = json.loads((ARCHIVE / 'manifest.json').read_text())
    report = json.loads(REPORT.read_text())
    audit_path = BASE / 'evaluations/pitch-calibration-listening-audit.json'
    audit = json.loads(audit_path.read_text())
    assert audit['complete'] and audit['reportSha256'] == sha(REPORT)
    assert audit['experimentId'] == manifest['experimentId']
    data = training_pairs([ARCHIVE])  # Independently validates raw labels and PCM.
    candidates = {c['id']: c for c in manifest['candidates']}
    source_rows = {r['source']['sha256']: r for r in report['results']}
    model_paths = {'preference-neural-v2': BASE / 'models/preference-neural-v2.json',
                   'perceptual-v5': BASE / 'models/perceptual-v5.json'}
    models, unavailable = {}, {}
    for name, cls in [('preference-neural-v2', PreferenceMetric), ('perceptual-v5', PerceptualMetric)]:
        try:
            models[name] = cls.load(model_paths[name])
        except ValueError as exc:
            unavailable[name] = str(exc)  # Never bypass a frozen checkpoint's compatibility check.
    metric_names = ['MatchObjective', *models]
    scores, rows = {}, []
    for target in manifest['targets']:
        reference = wave(target['referenceAudio'])
        objective = MatchObjective(reference)
        base_descriptor = features.describe(reference)
        extra_descriptor = perceptual.describe(reference) if 'perceptual-v5' in models else None
        choice = target['choice']
        heard = set(choice['auditionedCandidateIds'])
        preferred = set(choice['preferredCandidateIds'])
        options = []
        for item in target['candidates']:
            candidate = candidates[item['id']]
            audio = wave(candidate['audio'])
            distances = {'MatchObjective': float(objective.score_batch([audio])[0])}
            if 'preference-neural-v2' in models:
                distances['preference-neural-v2'] = float(models['preference-neural-v2'].distances(base_descriptor, features.describe(audio))[0])
            if 'perceptual-v5' in models:
                distances['perceptual-v5'] = float(models['perceptual-v5'].distances(extra_descriptor, perceptual.describe(audio))[0])
            scores[candidate['id']] = distances
            options.append({'id': candidate['id'], 'role': item['role'], 'synth': candidate['synth'],
                'heard': candidate['id'] in heard, 'preferred': candidate['id'] in preferred,
                'pcmSha256': candidate['audio']['pcmSha256'], 'auditionScores': distances})
        stored = source_rows[target['source']['sha256']]
        selection = stored['diagnostics']['selection']
        winners = [o for o in options if o['preferred']]
        assert choice['kind'] == 'best' and len(winners) == 1 and all(o['heard'] for o in options)
        rows.append({'target': target['source']['name'], 'sourceSha256': target['source']['sha256'],
            'referencePcmSha256': target['referenceAudio']['pcmSha256'], 'note': target['note'],
            'winner': winners[0], 'options': options,
            'calibrationChangedSelectedAudio': selection['selected']['audioHash'] != selection['baseline']['audioHash'],
            'selectionReason': selection['reason'],
            'frozenMetricWinners': {metric: min(options, key=lambda o: o['auditionScores'][metric])['id'] for metric in metric_names}})
    pairs = []
    for observation in data.observations:
        assert observation['preferenceSign'] == 1 and observation['labelSource'] == 'direct-choice'
        a, b = observation['candidateA'], observation['candidateB']
        pairs.append({**observation, 'winnerRole': candidates[a]['role'], 'loserRole': candidates[b]['role'],
            'metricAgrees': {name: scores[a][name] < scores[b][name] for name in metric_names}})
    assert len(rows) == 5 and len(pairs) == 7 and len(candidates) == 12
    changed = [r for r in rows if r['calibrationChangedSelectedAudio']]
    assert len(changed) == 2
    findings = {
        'changedSelectionWins': sum(r['winner']['role'] == 'selected' for r in changed),
        'changedSelectionComparisons': len(changed),
        'winnerRoles': {r['target']: r['winner']['role'] for r in rows},
        'decision': 'Reject automatic promotion of pitch-calibration-v1: neither changed selected output won. Preserve calibrated candidates as experiments, but the passing synthetic pitch gate is not a perceptual release gate.',
        'absoluteAdequacy': 'No scalar ratings or adequacy notes supplied in this JSON; best means relative preference only.',
        'charm': 'The earlier Transfxr anchor now wins a direct heard comparison against the later Bfxr partial success. Earlier sessions did not establish this pair; this is new evidence, not a contradiction.',
        'whistle': 'The selected Transfxr wins against original Bfxr, but it is the unchanged pre-calibration baseline. This supports that candidate, not the calibration step.'}
    result = {'schemaVersion': 1, 'experimentId': manifest['experimentId'], 'archive': str(ARCHIVE.relative_to(ROOT)),
        'feedbackSha256': manifest['feedbackSha256'], 'archiveManifestSha256': sha(ARCHIVE / 'manifest.json'),
        'reportSha256': sha(REPORT), 'audioAuditSha256': sha(audit_path), 'reviewScriptSha256': sha(__file__),
        'frozenModelSha256s': {name: sha(path) for name, path in model_paths.items()},
        'unavailableFrozenMetrics': unavailable,
        'summary': manifest['summary'], 'trainingPairPolicy': data.summary,
        'strictHeardPairs': len(pairs), 'targets': rows, 'pairs': pairs, 'findings': findings,
        'frozenMetricAgreement': {metric: {'strictPairsCorrect': sum(p['metricAgrees'][metric] for p in pairs),
            'strictPairs': len(pairs), 'wholeTargetWinnerCorrect': sum(r['frozenMetricWinners'][metric] == r['winner']['id'] for r in rows),
            'targets': len(rows)} for metric in metric_names},
        'limitations': ['Five selected development targets; no population accuracy claim.',
            'Frozen preference models include prior related reference feedback, especially charm. These are descriptive checks, not an independent holdout.',
            'No causal attribution of human preference to pitch, envelope or timbre from these joint changes.',
            'No parameters, selector thresholds, published audio or prior labels changed.']}
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'findings': findings, 'frozenMetricAgreement': result['frozenMetricAgreement']}, indent=2))


if __name__ == '__main__':
    main()
