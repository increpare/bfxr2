"""Audit corrected joint fitting, preserving choices separately from playback telemetry."""
import json
import re
from pathlib import Path
from collections import Counter
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.support_objective import SupportObjective
from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import coverage_model
from multisynth.features import describe
from multisynth.preference import PreferenceMetric, training_pairs
from multisynth.quick_feedback import validate_choice
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth')
ARCHIVE=BASE/'listening_data/2026-10-06-joint-support-v2-quick-01'
GALLERY=BASE/'runs/joint-support-v2-listening'
OUTPUT=Path(__file__).with_suffix('.json')


def wave(info):
    verify_archived_audio(ARCHIVE,info)
    samples,rate=sf.read(ARCHIVE/info['file'],dtype='float32')
    assert rate==44100 and samples.ndim==1 and np.all(np.isfinite(samples))
    return samples


def main():
    if OUTPUT.exists():raise FileExistsError('Preserve original review')
    torch.set_num_threads(1)
    manifest=json.loads((ARCHIVE/'manifest.json').read_text())
    report=json.loads((GALLERY/'results.json').read_text())
    audit_path=BASE/'evaluations/joint-support-v2-listening-audit.json'
    audit=json.loads(audit_path.read_text())
    assert audit['complete'] and audit['resultsSha256']==file_hash(GALLERY/'results.json')
    assert audit['experimentId']==manifest['experimentId']
    model=coverage_model(GALLERY,report['results'],report['metadata'])
    assert model['experimentId']==manifest['experimentId']
    records={t['id']:r for t,r in zip(model['targets'],report['results'])}
    candidates={c['id']:c for c in manifest['candidates']}
    metric_path=BASE/'models/preference-neural-v2.json';metric=PreferenceMetric.load(metric_path)
    data=training_pairs([ARCHIVE]);assert len(data.observations)==3
    rows=[];labels=[];earlier_heard={};mismatches=[]
    for target in manifest['targets']:
        record=records[target['id']]
        assert record['source']==target['source']
        reference=wave(target['referenceAudio']);reference_pcm=target['referenceAudio']['pcmSha256']
        soft=SoftPeriodicityObjective(reference);legacy=MatchObjective(reference);descriptor=describe(reference)
        choice=validate_choice(target['choice'],[c['id'] for c in target['candidates']])
        heard=set(choice['auditionedCandidateIds']);preferred=set(choice['preferredCandidateIds'])
        options=[];adequacy=choice.get('adequacy')
        for item in target['candidates']:
            c=candidates[item['id']];audio=wave(c['audio'])
            scores=dict(supportObjective=float(SupportObjective(reference).score(audio)),softPeriodicity=float(soft.score(audio)),MatchObjective=float(legacy.score(audio)),
                        preferenceNeuralV2=float(metric.distances(descriptor,describe(audio))[0]))
            if c['role']!='previous':assert abs(scores['supportObjective']-c['provenance']['wholeSoundScore'])<1e-7
            expected=c['provenance'].get('scores')
            if expected:
                assert abs(scores['softPeriodicity']-expected['soft'])<1e-7
                assert abs(scores['preferenceNeuralV2']-expected['preference'])<1e-7
            elif 'softPeriodicity' in c['provenance']:
                assert abs(scores['softPeriodicity']-c['provenance']['softPeriodicity'])<1e-7
                assert abs(scores['preferenceNeuralV2']-c['provenance']['preferenceNeuralV2'])<1e-7
            response_label=('not-close' if choice['kind']=='none' and c['id'] in choice['presentedCandidateIds'] else
                adequacy['level'] if adequacy and c['id'] in adequacy['candidateIds'] else None)
            stamp=(reference_pcm,c['audio']['pcmSha256'])
            option=dict(id=c['id'],role=c['role'],origin=c['provenance'].get('origin'),selectionAliases=c['provenance']['selectionAliases'],parentCandidateId=c['provenance'].get('parentCandidateId'),arm=c['provenance'].get('arm'),synth=c['synth'],
                pcmSha256=c['audio']['pcmSha256'],heardInThisTrial=c['id'] in heard,
                earlierHeardTrialIds=earlier_heard.get(stamp,[]).copy(),preferred=c['id'] in preferred,
                responseScopedLikeness=response_label,scores=scores)
            options.append(option)
            if response_label:
                labels.append(dict(targetId=target['id'],candidateId=c['id'],referencePcmSha256=reference_pcm,
                    candidatePcmSha256=c['audio']['pcmSha256'],label=response_label,
                    heardInThisTrial=option['heardInThisTrial'],earlierHeardTrialIds=option['earlierHeardTrialIds'],
                    scope='Preserved response scope, not inferred audition or numeric training label'))
        for o in options:
            if o['heardInThisTrial']:
                earlier_heard.setdefault((reference_pcm,o['pcmSha256']),[]).append(target['id'])
        note=target['note']
        if note.startswith('[quick-mismatch-v1] '):
            match=re.fullmatch(r'\[quick-mismatch-v1\] (chosen|tied|all presented) (\[.*\]): (.+)',note)
            assert match, 'Malformed diagnostic note retained in archive'
            scope,raw_ids,reason=match.groups();ids=json.loads(raw_ids)
            expected_ids=choice['preferredCandidateIds'] if choice['kind']=='best' else choice['presentedCandidateIds']
            assert ids==expected_ids and scope=={'best':'chosen','tie':'tied','none':'all presented'}[choice['kind']]
            assert reason in ('pitch','movement/rhythm','texture/timbre','attack/decay','several things','unsure')
            mismatches.append(dict(targetId=target['id'],name=target['source']['name'],candidateIds=ids,
                scope=scope,reason=reason,allScopedCandidatesHeard=all(i in heard for i in ids),rawNote=note))
        rows.append(dict(folder=record['folder'],name=target['source']['name'],targetId=target['id'],
            referencePcmSha256=reference_pcm,kind=choice['kind'],adequacy=adequacy,
            preferredRoles=[o['role'] for o in options if o['preferred']],options=options,note=target['note']))
    submitted={r['targetId'] for r in rows}
    missing=[dict(targetId=t['id'],folder=t['folder'],name=t['name']) for t in model['targets'] if t['id'] not in submitted]
    assert len(rows)==4 and len(candidates)==12 and len(labels)==4 and not missing
    assert Counter(l['label'] for l in labels)=={'similar':3,'least-bad':1}
    assert sum(o['heardInThisTrial'] for r in rows for o in r['options'])==8
    assert len(mismatches)==4 and sum(m['allScopedCandidatesHeard'] for m in mismatches)==3
    wins=Counter(role for r in rows for role in r['preferredRoles'])
    assert wins=={'previous':2,'timeline':1,'joint':1}
    origin_wins=Counter(o['origin'] for r in rows for o in r['options'] if o['preferred'])
    scores={o['id']:o['scores'] for r in rows for o in r['options']}
    pairs=[dict(o,metricAgrees={k:scores[o['candidateA']][k]<scores[o['candidateB']][k] for k in scores[o['candidateA']]}) for o in data.observations]
    result=dict(complete=True,partialSubmission=False,submittedTrials=4,totalTrials=4,distinctReferences=4,
        experimentId=manifest['experimentId'],scriptSha256=file_hash(__file__),
        feedbackSha256=file_hash(ARCHIVE/'feedback.json'),manifestSha256=file_hash(ARCHIVE/'manifest.json'),
        galleryReportSha256=file_hash(GALLERY/'results.json'),galleryAuditSha256=file_hash(audit_path),
        metricHashes={'preferenceNeuralV2':file_hash(metric_path)},archiveSummary=manifest['summary'],
        trainingPairSummary=data.summary,rows=rows,pairs=pairs,
        metricAgreement={k:dict(correct=sum(p['metricAgrees'][k] for p in pairs),pairs=len(pairs)) for k in next(iter(scores.values()))},
        wins=dict(wins),winnerOrigins=dict(origin_wins),mismatches=mismatches,responseScopedQualitativeLabels=labels,unsubmittedTrials=missing,
        interpretation=[
            'Four submitted choices: joint coin similar, timing-only metal footstep similar, previous Transfxr book least-bad, previous Bfxr attack similar. No very-close rating.',
            'Coin has all three options recorded heard and favors new joint fitting over both exact earlier coin and timing-only refinement. Movement/rhythm remains imperfect. This is a local external preference, not broad generalization.',
            'Metal footstep selects timing-only Stackr as similar with pitch mismatch, but the selected clip is absent from recorded audition IDs. Preserve that explicit choice and adequacy; do not infer playback or create heard-only training pairs for it.',
            'Book records timeline and previous heard; joint is not recorded heard. Attack records only previous heard. Missing playback flags do not prove the user did not listen. The current UI requires half the full buffer duration before logging playback, which can miss quick decisions on long-tailed files.',
            'Eight of12 options recorded heard, three strict heard pairs, four response-scoped adequacy labels and four mismatch notes. Do not retroactively alter telemetry or ask the user to reconstruct this session.',
            'Keep the source/timeline alternatives and test fresh external tagged sounds before generalizing the coin result. Future playback telemetry should measure progress through above-threshold signal support, with an explicit versioned policy.'])
    result['recordedHeardOptions']=8
    result['selectedWithoutPlaybackFlag']=[dict(name=r['name'],candidateId=o['id'],label=o['responseScopedLikeness']) for r in rows for o in r['options'] if o['preferred'] and not o['heardInThisTrial']]
    _json_write(OUTPUT,result)
    print(json.dumps(dict(submittedTrials=4,wins=dict(wins),winnerOrigins=dict(origin_wins),mismatches=len(mismatches),strictPairs=len(pairs),metricAgreement=result['metricAgreement'],audioFiles=data.summary['validatedAudioFiles'])),flush=True)


if __name__=='__main__':main()
