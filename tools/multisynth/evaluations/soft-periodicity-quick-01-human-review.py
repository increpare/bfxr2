"""Bind specialist choices to exact archived PCM; do not infer scalar ratings."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.coverage import verify_archived_audio
from multisynth.features import describe
from multisynth.preference import PreferenceMetric, training_pairs
from multisynth.quick_feedback import validate_choice
from neural_invert.data import file_hash, _json_write

BASE = Path('tools/multisynth')
ARCHIVE = BASE/'listening_data/2026-10-05-soft-periodicity-quick-01'
REPORT = BASE/'runs/soft-periodicity-v1-listening/results.json'
OUTPUT = Path(__file__).with_suffix('.json')


def wave(info):
    verify_archived_audio(ARCHIVE, info)
    samples, rate = sf.read(ARCHIVE/info['file'], dtype='float32')
    assert rate == 44100 and samples.ndim == 1 and np.all(np.isfinite(samples))
    return samples


def main():
    if OUTPUT.exists():
        raise FileExistsError('Preserve original human review')
    torch.set_num_threads(1)
    manifest = json.loads((ARCHIVE/'manifest.json').read_text())
    report = json.loads(REPORT.read_text())
    audit_path = BASE/'evaluations/soft-periodicity-v1-listening-audit.json'
    audit = json.loads(audit_path.read_text())
    assert audit['complete'] and audit['resultsSha256'] == file_hash(REPORT)
    assert audit['experimentId'] == manifest['experimentId']
    sources = {r['source']['name']: r['source'] for r in report['results']}
    candidates = {c['id']: c for c in manifest['candidates']}
    metric_path = BASE/'models/preference-neural-v2.json'
    metric = PreferenceMetric.load(metric_path)
    data = training_pairs([ARCHIVE])
    scores, rows, labels = {}, [], []
    for target in manifest['targets']:
        name = target['source']['name']
        assert target['source'] == sources[name]
        reference = wave(target['referenceAudio'])
        objective, descriptor = MatchObjective(reference), describe(reference)
        soft=SoftPeriodicityObjective(reference)
        choice = validate_choice(target['choice'], [c['id'] for c in target['candidates']])
        heard = set(choice['auditionedCandidateIds'])
        preferred = set(choice['preferredCandidateIds'])
        adequacy = choice.get('adequacy')
        options = []
        for item in target['candidates']:
            c = candidates[item['id']]
            audio = wave(c['audio'])
            distances = dict(MatchObjective=float(objective.score_batch([audio])[0]),
                preferenceNeuralV2=float(metric.distances(descriptor, describe(audio))[0]))
            distances['softPeriodicity']=float(soft.score(audio))
            if c['provenance'].get('searchArm'):
                assert abs(distances['MatchObjective']-c['provenance']['auditionMatchObjective'])<1e-7
                assert abs(distances['softPeriodicity']-c['provenance']['softPeriodicity'])<1e-7
            absolute = ('not-close' if choice['kind'] == 'none' and c['id'] in choice['presentedCandidateIds'] else
                adequacy['level'] if adequacy and c['id'] in adequacy['candidateIds'] else None)
            scores[c['id']] = distances
            options.append(dict(id=c['id'], role=c['role'], synth=c['synth'],
                checkpointSha256=c['provenance'].get('checkpointHash'), searchArm=c['provenance'].get('searchArm'),
                pcmSha256=c['audio']['pcmSha256'], heard=c['id'] in heard,
                preferred=c['id'] in preferred, absoluteLikeness=absolute, scores=distances))
            if absolute is not None:
                labels.append(dict(targetId=target['id'], candidateId=c['id'],
                    referencePcmSha256=target['referenceAudio']['pcmSha256'],
                    candidatePcmSha256=c['audio']['pcmSha256'], label=absolute))
        rows.append(dict(name=name, targetId=target['id'], kind=choice['kind'], adequacy=adequacy,
            preferredRoles=[o['role'] for o in options if o['preferred']], options=options,
            metricWinners={m:min(options,key=lambda o:o['scores'][m])['role'] for m in distances}, note=target['note']))
    pairs = []
    for observation in data.observations:
        assert observation['preferenceSign'] == 1 and observation['labelSource'] == 'direct-choice'
        a,b = observation['candidateA'], observation['candidateB']
        pairs.append({**observation, 'winnerRole':candidates[a]['role'], 'loserRole':candidates[b]['role'],
            'metricAgrees':{m:scores[a][m] < scores[b][m] for m in scores[a]}})
    missing = [name for name in sources if name not in {r['name'] for r in rows}]
    assert len(rows) == 5 and len(candidates) == 15 and len(pairs) == 6 and len(labels) == 7
    assert missing == []
    result = dict(complete=True, partialSubmission=False, scriptSha256=file_hash(__file__),
        experimentId=manifest['experimentId'], feedbackSha256=file_hash(ARCHIVE/'feedback.json'),
        manifestSha256=file_hash(ARCHIVE/'manifest.json'), galleryReportSha256=file_hash(REPORT),
        galleryAuditSha256=file_hash(audit_path), metricHashes={'preferenceNeuralV2':file_hash(metric_path)},
        archiveSummary=manifest['summary'], trainingPairSummary=data.summary, rows=rows, pairs=pairs,
        explicitQualitativeLabels=labels, unsubmittedReferences=missing,
        metricAgreement={m:dict(correct=sum(p['metricAgrees'][m] for p in pairs), pairs=len(pairs)) for m in scores[a]},
        interpretation=[
            'Five references judged. All three candidates auditioned except block hit, whose export records only the chosen soft-search Transfxr as heard.',
            'Soft-search Squishr footstep wins and is very-close. Soft-search Transfxr block hit is selected and similar, but produces no strict comparison labels against unheard alternatives.',
            'Brick rejects all three. Earlier Transfxr cloth is least-bad; earlier Bfxr laser is similar. The same laser PCM previously had least-bad adequacy; preserve both session observations rather than claiming new synthesis improvement.',
            'Six strict heard preference pairs and seven candidate-scoped labels: one very-close, two similar, one least-bad and three not-close. No scalar ratings inferred.',
            'One convincing real tagged recreation establishes a useful reachable Squishr region. It does not justify universal scorer promotion or success on other references. Next investigate a dedicated inverse expert with broad synthetic training and separately reserved native/real transfer checks.'])
    _json_write(OUTPUT,result)
    print(json.dumps(dict(choices=[(r['name'],r['kind'],r['preferredRoles'],r['adequacy']['level'] if r['adequacy'] else None) for r in rows],
        metricAgreement=result['metricAgreement'],labels=len(labels))),flush=True)


if __name__ == '__main__':
    main()
