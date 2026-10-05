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
ARCHIVE = BASE/'listening_data/2026-10-06-off-model-transfer-v1-quick-02'
REPORT = BASE/'runs/off-model-transfer-v1-listening/results.json'
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
    audit_path = BASE/'evaluations/off-model-transfer-v1-listening-audit.json'
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
            if 'auditionMatchObjective' in c['provenance']:
                assert abs(distances['MatchObjective']-c['provenance']['auditionMatchObjective'])<1e-7
                assert abs(distances['softPeriodicity']-c['provenance']['softPeriodicity'])<1e-7
                assert abs(distances['preferenceNeuralV2']-c['provenance']['preferenceNeuralV2'])<1e-7
            absolute = ('not-close' if choice['kind'] == 'none' and c['id'] in choice['presentedCandidateIds'] else
                adequacy['level'] if adequacy and c['id'] in adequacy['candidateIds'] else None)
            scores[c['id']] = distances
            options.append(dict(id=c['id'], role=c['role'], synth=c['synth'],
                checkpointSha256=c['provenance'].get('checkpointHash',c['provenance'].get('checkpointSha256')), origin=c['provenance'].get('origin'),
                pcmSha256=c['audio']['pcmSha256'], heard=c['id'] in heard,
                preferred=c['id'] in preferred, absoluteLikeness=absolute, scores=distances))
            if absolute is not None:
                labels.append(dict(targetId=target['id'], candidateId=c['id'],
                    referencePcmSha256=target['referenceAudio']['pcmSha256'],
                    candidatePcmSha256=c['audio']['pcmSha256'], label=absolute))
        rows.append(dict(name=name, targetId=target['id'], kind=choice['kind'], adequacy=adequacy, historicalBfxrSplits=target['source']['historicalBfxrSplits'],
            preferredRoles=[o['role'] for o in options if o['preferred']], options=options,
            metricWinners={m:min(options,key=lambda o:o['scores'][m])['role'] for m in distances}, note=target['note']))
    pairs = []
    for observation in data.observations:
        assert observation['preferenceSign'] == 1 and observation['labelSource'] == 'direct-choice'
        a,b = observation['candidateA'], observation['candidateB']
        pairs.append({**observation, 'winnerRole':candidates[a]['role'], 'loserRole':candidates[b]['role'],
            'metricAgrees':{m:scores[a][m] < scores[b][m] for m in scores[a]}})
    missing = [name for name in sources if name not in {r['name'] for r in rows}]
    assert len(rows) == 8 and len(candidates) == 24 and len(pairs) == 8 and len(labels) == 14
    assert missing == []
    result = dict(complete=True, partialSubmission=False, scriptSha256=file_hash(__file__),
        experimentId=manifest['experimentId'], feedbackSha256=file_hash(ARCHIVE/'feedback.json'),
        manifestSha256=file_hash(ARCHIVE/'manifest.json'), galleryReportSha256=file_hash(REPORT),
        galleryAuditSha256=file_hash(audit_path), metricHashes={'preferenceNeuralV2':file_hash(metric_path)},
        archiveSummary=manifest['summary'], trainingPairSummary=data.summary, rows=rows, pairs=pairs,
        explicitQualitativeLabels=labels, unsubmittedReferences=missing,
        metricAgreement={m:dict(correct=sum(p['metricAgrees'][m] for p in pairs), pairs=len(pairs)) for m in scores[a]},
        interpretation=[
            'Complete cumulative eight-reference export. First five targets unchanged; three new judgments. Earlier four strict pairs must not be counted twice.',
            'Original Bfxr coin wins and is very-close. Its exact file appears in the old real-finetune holdout list, not the training list; this is not proof of family-independent generalization.',
            'Transfxr-mixture footstep and shared Rustlr cloth remain similar. Original Bfxr chain and dedicated Squishr cloth-belt are least-bad. Hit, door and laser reject every displayed option.',
            'The metallic footstep records only its chosen candidate as heard, so no strict pair against unheard options. Eight strict heard pairs in total, four new. Fourteen candidate-scoped labels: one very-close, two similar, two least-bad, nine not-close.',
            'None of the newer synthetic-trained experts receives very-close adequacy in this external batch. Native successes did not transfer to convincing reproductions here.',
            'Next probe actual two-source Mixr composition on three rejected references and one similar control. Compare against exact earlier audio and a single-source control under the same composition renderer. This is an expressive-coverage diagnostic, not a trained Mixr inverse or a quality claim.'])
    earlier=ARCHIVE.with_name('2026-10-06-off-model-transfer-v1-quick-01')
    old=json.loads((earlier/'feedback.json').read_text())
    new={t['id']:t for t in json.loads((ARCHIVE/'feedback.json').read_text())['targets']}
    assert all(t==new[t['id']] for t in old['targets'])
    combined=training_pairs([earlier,ARCHIVE])
    assert len(combined.observations)==8 and combined.summary['duplicateSessionPairs']==4
    result['cumulativeExport']=dict(previousArchive=str(earlier),previousFeedbackSha256=file_hash(earlier/'feedback.json'),
        unchangedTargetCount=5,newTargetCount=3,newStrictPairs=4,combinedDistinctPairs=8,duplicateSessionPairsSkipped=4)
    _json_write(OUTPUT,result)
    print(json.dumps(dict(choices=[(r['name'],r['kind'],r['preferredRoles'],r['adequacy']['level'] if r['adequacy'] else None) for r in rows],
        metricAgreement=result['metricAgreement'],labels=len(labels))),flush=True)


if __name__ == '__main__':
    main()
