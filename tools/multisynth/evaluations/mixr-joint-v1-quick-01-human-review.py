"""Audit partial repeated-reference judgments without inventing unheard pairs."""
import json
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
ARCHIVE=BASE/'listening_data/2026-10-06-mixr-joint-v1-quick-01'
GALLERY=BASE/'runs/mixr-joint-v1-listening'
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
    audit_path=BASE/'evaluations/mixr-joint-v1-listening-audit.json'
    audit=json.loads(audit_path.read_text())
    assert audit['complete'] and audit['resultsSha256']==file_hash(GALLERY/'results.json')
    assert audit['experimentId']==manifest['experimentId']
    model=coverage_model(GALLERY,report['results'],report['metadata'])
    assert model['experimentId']==manifest['experimentId']
    records={t['id']:r for t,r in zip(model['targets'],report['results'])}
    candidates={c['id']:c for c in manifest['candidates']}
    metric_path=BASE/'models/preference-neural-v2.json';metric=PreferenceMetric.load(metric_path)
    data=training_pairs([ARCHIVE]);assert not data.observations
    rows=[];labels=[];earlier_heard={}
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
            assert all(abs(value-c['provenance'][key if key!='MatchObjective' else 'auditionMatchObjective'])<1e-7
                       for key,value in scores.items())
            response_label=('not-close' if choice['kind']=='none' and c['id'] in choice['presentedCandidateIds'] else
                adequacy['level'] if adequacy and c['id'] in adequacy['candidateIds'] else None)
            stamp=(reference_pcm,c['audio']['pcmSha256'])
            option=dict(id=c['id'],role=c['role'],arm=c['provenance'].get('arm'),synth=c['synth'],
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
        rows.append(dict(folder=record['folder'],name=target['source']['name'],targetId=target['id'],
            referencePcmSha256=reference_pcm,kind=choice['kind'],adequacy=adequacy,
            preferredRoles=[o['role'] for o in options if o['preferred']],options=options,note=target['note']))
    # Match by trial identity, not filename: each reference appears in two trials.
    submitted={r['targetId'] for r in rows}
    missing=[dict(targetId=t['id'],folder=t['folder'],name=t['name']) for t in model['targets'] if t['id'] not in submitted]
    assert len(rows)==5 and len(candidates)==15 and len(labels)==13
    assert [r['folder'] for r in rows]==['001','002','003','004','005']
    assert [r['folder'] for r in missing]==['006','007','008']
    assert Counter(l['label'] for l in labels)=={'not-close':9,'similar':4}
    assert sum(l['heardInThisTrial'] for l in labels)==11
    assert [o['role'] for o in rows[0]['options'] if not o['heardInThisTrial']]==['pair']
    winner=next(o for o in rows[4]['options'] if o['preferred'])
    assert winner['role']=='previous' and not winner['heardInThisTrial']
    assert winner['earlierHeardTrialIds']==[rows[0]['targetId']]
    first=next(o for o in rows[0]['options'] if o['role']=='previous')
    assert winner['pcmSha256']==first['pcmSha256'] and first['responseScopedLikeness']=='not-close'
    result=dict(complete=True,partialSubmission=True,submittedTrials=5,totalTrials=8,distinctReferences=4,
        experimentId=manifest['experimentId'],scriptSha256=file_hash(__file__),
        feedbackSha256=file_hash(ARCHIVE/'feedback.json'),manifestSha256=file_hash(ARCHIVE/'manifest.json'),
        galleryReportSha256=file_hash(GALLERY/'results.json'),galleryAuditSha256=file_hash(audit_path),
        metricHashes={'preferenceNeuralV2':file_hash(metric_path)},archiveSummary=manifest['summary'],
        trainingPairSummary=data.summary,rows=rows,pairs=[],metricAgreement=None,
        responseScopedQualitativeLabels=labels,unsubmittedTrials=missing,
        interpretation=[
            'Partial export: first five of eight trials; four unique references. Match trial identities, not filenames, when finding unsubmitted trials.',
            'Soft block: hit none-close with pair not recorded as auditioned, door none-close, laser none-close, cloth similar tie. No very-close recreation.',
            'First preference-block trial selects exact earlier hit mixture as similar, not either newly optimized candidate. Winner is not recorded as heard in this trial, but identical reference/candidate PCM was heard in trial001.',
            'Preserve this explicit preference and adequacy without fabricating current-trial playback. Conservative existing training loader creates zero strict heard pairs. Missing playback logs are not proof that the listener never heard the clip elsewhere.',
            'Thirteen response-scoped labels (nine not-close, four similar), eleven supported by playback in their own trial. The unheard soft hit pair has no independently audition-supported rejection. Do not train it as a demonstrated bad approximation.',
            'Exact earlier hit audio receives none-close in trial001 and similar in trial005. Keep both contextual observations; do not invent an audio improvement or collapse them into a scalar truth.',
            'Numerically winning joint fitting has not established improved audible recreation. New fitting results are not approved training teachers. Remaining preference-block door, laser and cloth trials are pending; do not publish another batch or draw a completed eight-trial verdict.'])
    _json_write(OUTPUT,result)
    print(json.dumps(dict(submittedTrials=5,unsubmitted=[r['folder'] for r in missing],strictPairs=0,
        responseScopedLabels=13,labelsHeardInTrial=11,veryClose=0)),flush=True)


if __name__=='__main__':main()
