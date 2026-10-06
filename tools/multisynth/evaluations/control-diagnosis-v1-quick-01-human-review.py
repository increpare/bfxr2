"""Audit controlled native interventions, retaining ties and contextual adequacy."""
import json
import re
from pathlib import Path
from collections import Counter
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import coverage_model
from multisynth.features import describe
from multisynth.preference import PreferenceMetric, training_pairs
from multisynth.quick_feedback import validate_choice
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth')
ARCHIVE=BASE/'listening_data/2026-10-06-control-diagnosis-v1-quick-01'
GALLERY=BASE/'runs/control-diagnosis-v1-listening'
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
    audit_path=BASE/'evaluations/control-diagnosis-v1-evaluation.json'
    audit=json.loads(audit_path.read_text())
    assert audit['complete'] and audit['resultsSha256']==file_hash(GALLERY/'results.json')
    assert audit['experimentId']==manifest['experimentId']
    model=coverage_model(GALLERY,report['results'],report['metadata'])
    assert model['experimentId']==manifest['experimentId']
    records={t['id']:r for t,r in zip(model['targets'],report['results'])}
    candidates={c['id']:c for c in manifest['candidates']}
    metric_path=BASE/'models/preference-neural-v2.json';metric=PreferenceMetric.load(metric_path)
    data=training_pairs([ARCHIVE]);assert len(data.observations)==5
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
            scores=dict(softPeriodicity=float(soft.score(audio)),MatchObjective=float(legacy.score(audio)),
                        preferenceNeuralV2=float(metric.distances(descriptor,describe(audio))[0]))
            expected=c['provenance'].get('scores')
            if expected:
                assert abs(scores['softPeriodicity']-expected['soft'])<1e-7
                assert abs(scores['preferenceNeuralV2']-expected['preference'])<1e-7
            else:
                assert abs(scores['softPeriodicity']-c['provenance']['softPeriodicity'])<1e-7
                assert abs(scores['preferenceNeuralV2']-c['provenance']['preferenceNeuralV2'])<1e-7
            response_label=('not-close' if choice['kind']=='none' and c['id'] in choice['presentedCandidateIds'] else
                adequacy['level'] if adequacy and c['id'] in adequacy['candidateIds'] else None)
            stamp=(reference_pcm,c['audio']['pcmSha256'])
            option=dict(id=c['id'],role=c['role'],origin=c['provenance'].get('origin'),interventionAxis=c['provenance']['interventionAxis'],interventionIndex=c['provenance']['interventionIndex'],parentCandidateId=c['provenance']['parentCandidateId'],arm=c['provenance'].get('arm'),synth=c['synth'],
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
    assert len(rows)==7 and len(candidates)==21 and len(labels)==15 and not missing
    assert Counter(l['label'] for l in labels)=={'similar':5,'least-bad':10}
    assert sum(o['heardInThisTrial'] for r in rows for o in r['options'])==20
    assert len(mismatches)==7 and all(m['allScopedCandidatesHeard'] for m in mismatches)
    wins=Counter(role for r in rows for role in r['preferredRoles'])
    assert wins=={'previous':3}
    origin_wins=Counter(o['origin'] for r in rows for o in r['options'] if o['preferred'])
    assert origin_wins=={'original-bfxr':1,'shared22':2}
    scores={o['id']:o['scores'] for r in rows for o in r['options']}
    pairs=[dict(o,metricAgrees={k:scores[o['candidateA']][k]<scores[o['candidateB']][k] for k in scores[o['candidateA']]}) for o in data.observations]
    result=dict(complete=True,partialSubmission=False,submittedTrials=7,totalTrials=7,distinctReferences=5,
        experimentId=manifest['experimentId'],scriptSha256=file_hash(__file__),
        feedbackSha256=file_hash(ARCHIVE/'feedback.json'),manifestSha256=file_hash(ARCHIVE/'manifest.json'),
        galleryReportSha256=file_hash(GALLERY/'results.json'),galleryAuditSha256=file_hash(audit_path),
        metricHashes={'preferenceNeuralV2':file_hash(metric_path)},archiveSummary=manifest['summary'],
        trainingPairSummary=data.summary,rows=rows,pairs=pairs,
        metricAgreement={k:dict(correct=sum(p['metricAgrees'][k] for p in pairs),pairs=len(pairs)) for k in next(iter(scores.values()))},
        wins=dict(wins),winnerOrigins=dict(origin_wins),mismatches=mismatches,responseScopedQualitativeLabels=labels,unsubmittedTrials=missing,
        interpretation=[
            'Seven trials over five external development references are complete. Four ties, three unchanged-anchor wins, zero variant wins. All20 recorded-heard clips contribute honestly; one bell perturbation was not recorded heard and contributes no strict pair.',
            'Transfxr oscillator and filter shifts both tie as least-bad with texture/timbre mismatch. Zappr original voltage wins as similar with pitch mismatch; noise-balance variants tie as similar with pitch mismatch. Drier Squishr carpet variants tie as least-bad with texture mismatch.',
            'Original Bfxr laser bitcrush wins as least-bad with pitch mismatch. Original Pluckr bell tuning wins as similar with texture mismatch. No very-close choice this session.',
            'Anchors are exact earlier PCM. Footsteps/laser moved from similar to least-bad, bell from very-close to similar, and case stays similar. Preserve both sessions and context; neither retroactively changes the audio or supplies a timeless numeric label.',
            'Five strict heard pairs and seven explicitly scoped diagnostic notes are retained. Four all-option ties provide useful invariance/ambiguity evidence; do not manufacture strict preference labels from them.',
            'The tested parameter edits did not improve audible likeness. They do not prove all pitch or texture edits useless. Investigate whether actual synthetic training presets provide better starting points than regressed control vectors before more local knob trials.'])
    _json_write(OUTPUT,result)
    print(json.dumps(dict(submittedTrials=7,wins=dict(wins),winnerOrigins=dict(origin_wins),mismatches=len(mismatches),strictPairs=len(pairs),metricAgreement=result['metricAgreement'],audioFiles=data.summary['validatedAudioFiles'])),flush=True)


if __name__=='__main__':main()
