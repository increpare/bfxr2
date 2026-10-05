"""Review the submitted partial v2 choices and exact candidate-scoped adequacy."""
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth import features
from multisynth.preference import PreferenceMetric, training_pairs
from multisynth.quick_feedback import validate_choice
from neural_invert.coverage_selection import rejection_reasons
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth')
ARCHIVE=BASE/'listening_data/2026-10-05-native-mixture-quick-01'
REPORT=BASE/'runs/native-mixture-v1-listening/results.json'
OUTPUT=Path(__file__).with_suffix('.json')


def wave(audio):
    path=(ARCHIVE/audio['file']).resolve();assert path.is_relative_to(ARCHIVE.resolve())
    pcm,rate=sf.read(path,dtype='int16',always_2d=True)
    assert rate==44100 and pcm.shape[1]==1
    assert hashlib.sha256(str((rate,pcm.shape)).encode()+pcm.astype('<i2').tobytes()).hexdigest()==audio['pcmSha256']
    return pcm[:,0].astype('float32')/32768


def main():
    if OUTPUT.exists():raise FileExistsError('Preserve original review; use a new version')
    torch.set_num_threads(1)
    manifest=json.loads((ARCHIVE/'manifest.json').read_text());report=json.loads(REPORT.read_text())
    receipt=BASE/'evaluations/native-mixture-v1-listening-audit.json';audit=json.loads(receipt.read_text())
    assert audit['complete'] and audit['resultsSha256']==file_hash(REPORT) and audit['experimentId']==manifest['experimentId']
    sources={r['source']['name']:r for r in report['results']}
    candidates={c['id']:c for c in manifest['candidates']}
    metric_path=BASE/'models/preference-neural-v2.json';metric=PreferenceMetric.load(metric_path)
    data=training_pairs([ARCHIVE]);scores={};rows=[];labels=[]
    for target in manifest['targets']:
        name=target['source']['name'];assert target['source']==sources[name]['source']
        reference=wave(target['referenceAudio']);objective=MatchObjective(reference)
        descriptor=features.describe(reference);pitch=descriptor_pitch(reference)
        choice=validate_choice(target['choice'],[c['id'] for c in target['candidates']])
        heard=set(choice['auditionedCandidateIds']);preferred=set(choice['preferredCandidateIds'])
        adequacy=choice.get('adequacy');options=[]
        for item in target['candidates']:
            c=candidates[item['id']];audio=wave(c['audio']);cp=descriptor_pitch(audio)
            distances=dict(MatchObjective=float(objective.score_batch([audio])[0]),
                preferenceNeuralV2=float(metric.distances(descriptor,features.describe(audio))[0]))
            assert abs(distances['MatchObjective']-c['provenance']['auditionMatchObjective'])<1e-7
            absolute=('not-close' if choice['kind']=='none' and c['id'] in choice['presentedCandidateIds'] else
                      adequacy['level'] if adequacy and c['id'] in adequacy['candidateIds'] else None)
            scores[c['id']]=distances
            option=dict(id=c['id'],role=c['role'],pcmSha256=c['audio']['pcmSha256'],heard=c['id'] in heard,
                preferred=c['id'] in preferred,absoluteLikeness=absolute,auditionScores=distances,
                pitch=cp,pitchComparison=compare_descriptor_pitch(pitch,cp))
            options.append(option)
            if absolute is not None:labels.append(dict(targetId=target['id'],candidateId=c['id'],
                referencePcmSha256=target['referenceAudio']['pcmSha256'],candidatePcmSha256=c['audio']['pcmSha256'],
                label=absolute,source='none-are-close' if choice['kind']=='none' else 'immediate-adequacy'))
        source=target['source']['sourceTarget'];family=source.get('baseId',source['id'])
        a=next(o for o in options if o['role']=='previous');b=next(o for o in options if o['role']=='selected')
        guard=rejection_reasons(pitch,dict(score=a['auditionScores']['MatchObjective'],pitch=a['pitch'],pitchComparison=a['pitchComparison']),
                               dict(score=b['auditionScores']['MatchObjective'],pitch=b['pitch'],pitchComparison=b['pitchComparison']))
        rows.append(dict(name=name,targetId=target['id'],referencePcmSha256=target['referenceAudio']['pcmSha256'],
            referenceFamily=family,kind=choice['kind'],adequacy=adequacy,
            preferredRoles=[o['role'] for o in options if o['preferred']],options=options,
            oldPitchGuardRejectsNewBecause=guard,metricWinners={m:min(options,key=lambda o:o['auditionScores'][m])['role'] for m in distances},note=target['note']))
    pairs=[]
    for observation in data.observations:
        assert observation['preferenceSign']==1 and observation['labelSource']=='direct-choice'
        a,b=observation['candidateA'],observation['candidateB']
        pairs.append({**observation,'winnerRole':candidates[a]['role'],'loserRole':candidates[b]['role'],
            'metricAgrees':{m:scores[a][m]<scores[b][m] for m in scores[a]}})
    assert len(rows)==5 and len(candidates)==10 and len(pairs)==4
    missing=[r['source']['name'] for r in report['results'] if r['source']['name'] not in {r['name'] for r in rows}]
    assert missing==['Warbling sweep']
    out=dict(complete=True,partialSubmission=True,scriptSha256=file_hash(__file__),experimentId=manifest['experimentId'],
        feedbackSha256=file_hash(ARCHIVE/'feedback.json'),manifestSha256=file_hash(ARCHIVE/'manifest.json'),
        galleryReportSha256=file_hash(REPORT),galleryAuditSha256=file_hash(receipt),
        metricHashes={'preferenceNeuralV2':file_hash(metric_path)},archiveSummary=manifest['summary'],
        trainingPairSummary=data.summary,strictHeardPairs=len(pairs),rows=rows,pairs=pairs,
        explicitQualitativeLabels=labels,unsubmittedReferences=missing,
        metricAgreement={m:dict(correct=sum(p['metricAgrees'][m] for p in pairs),pairs=len(pairs)) for m in scores[a]},
        interpretation=[
          'Three new mixture predictions are preferred and explicitly very close: two additional native controls and low-pass filtered bouncing rise. These are actual human positives, not inferred from lower metrics.',
          'Neither Footsteppr recreation is close despite the large numerical improvement for retrained single. Do not promote that transfer as successful.',
          'The earlier Boomr recreation wins and is roughly similar; its new lower-distance mixture alternative loses. The older candidate now has absolute evidence for this session.',
          'Wide sweep is very close despite worse descriptor contour error. A rule vetoing every such deterioration would reject this human-approved result; the diagnostic does not establish its psychoacoustic cause.',
          'No scalar likeness/usefulness values were submitted. Candidate-scoped qualitative labels are retained without conversion to 1-5 scores.',
          'Five of six references submitted. Missing clean warble is unknown, not a skip, tie, rejection, or confirmation of regression.',
          'This outcome-selected diagnostic does not establish a population success rate or success on tagged real recordings. Keep transformed bouncing rise grouped with its clean family.',
          'No model retrained or globally promoted by this review. Retain the mixture as a complementary source and preserve old expert strengths.'])
    _json_write(OUTPUT,out)
    print(json.dumps(dict(choices=[(r['name'],r['kind'],r['preferredRoles'],r['adequacy']) for r in rows],metricAgreement=out['metricAgreement'],
                         guards=[(r['name'],r['oldPitchGuardRejectsNewBecause']) for r in rows],labels=len(labels),unsubmitted=missing)),flush=True)

if __name__=='__main__':main()
