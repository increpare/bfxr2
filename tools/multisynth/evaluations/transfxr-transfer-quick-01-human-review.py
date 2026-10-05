"""Review six submitted choices against frozen metrics on exact audition PCM."""
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth import features,perceptual
from multisynth.preference import PreferenceMetric,training_pairs
from multisynth.train_perceptual import PerceptualMetric
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth')
ARCHIVE=BASE/'listening_data/2026-10-05-transfxr-transfer-quick-01'
REPORT=BASE/'runs/transfxr-transfer-v1-listening/results.json'
OUTPUT=Path(__file__).with_suffix('.json')

def wave(audio):
    p=(ARCHIVE/audio['file']).resolve();assert p.is_relative_to(ARCHIVE.resolve())
    pcm,rate=sf.read(p,dtype='int16',always_2d=True);assert rate==44100 and pcm.shape[1]==1
    assert hashlib.sha256(str((rate,pcm.shape)).encode()+pcm.astype('<i2').tobytes()).hexdigest()==audio['pcmSha256']
    return pcm[:,0].astype('float32')/32768

def main():
    assert not OUTPUT.exists();torch.set_num_threads(1)
    manifest=json.loads((ARCHIVE/'manifest.json').read_text())
    report=json.loads(REPORT.read_text())
    audit_path=BASE/'evaluations/transfxr-transfer-v1-listening-audit.json'
    audit=json.loads(audit_path.read_text())
    assert audit['complete'] and audit['resultsSha256']==file_hash(REPORT) and audit['experimentId']==manifest['experimentId']
    data=training_pairs([ARCHIVE]);candidates={c['id']:c for c in manifest['candidates']}
    model_paths={'preference-neural-v2':BASE/'models/preference-neural-v2.json','perceptual-v5':BASE/'models/perceptual-v5.json'}
    models={};unavailable={}
    for name,cls in [('preference-neural-v2',PreferenceMetric),('perceptual-v5',PerceptualMetric)]:
        try:models[name]=cls.load(model_paths[name])
        except ValueError as error:unavailable[name]=str(error)
    metrics=['MatchObjective',*models];scores={};rows=[]
    for target,source in zip(manifest['targets'],report['results']):
        assert target['source']==source['source']
        reference=wave(target['referenceAudio']);objective=MatchObjective(reference)
        descriptor=features.describe(reference);extra=perceptual.describe(reference) if 'perceptual-v5' in models else None
        choice=target['choice'];heard=set(choice['auditionedCandidateIds']);preferred=set(choice['preferredCandidateIds'])
        options=[]
        for item in target['candidates']:
            c=candidates[item['id']];audio=wave(c['audio'])
            distances={'MatchObjective':float(objective.score_batch([audio])[0])}
            if 'preference-neural-v2' in models:distances['preference-neural-v2']=float(models['preference-neural-v2'].distances(descriptor,features.describe(audio))[0])
            if 'perceptual-v5' in models:distances['perceptual-v5']=float(models['perceptual-v5'].distances(extra,perceptual.describe(audio))[0])
            scores[c['id']]=distances
            options.append(dict(id=c['id'],role=item['role'],pcmSha256=c['audio']['pcmSha256'],heard=c['id'] in heard,
                                preferred=c['id'] in preferred,auditionScores=distances))
        assert len(options)==2 and all(o['heard'] for o in options)
        provenance=target['source']['sourceTarget']
        family=provenance.get('baseId',provenance['id'])
        rows.append(dict(name=target['source']['name'],targetId=target['id'],referencePcmSha256=target['referenceAudio']['pcmSha256'],
            referenceFamily=family,kind=choice['kind'],preferredRoles=[o['role'] for o in options if o['preferred']],
            options=options,absoluteAdequacy='Both rejected as not close' if choice['kind']=='none' else None,
            metricWinners={metric:min(options,key=lambda o:o['auditionScores'][metric])['role'] for metric in metrics},note=target['note']))
    pairs=[]
    for observation in data.observations:
        assert observation['preferenceSign']==1 and observation['labelSource']=='direct-choice'
        a,b=observation['candidateA'],observation['candidateB']
        pairs.append({**observation,'winnerRole':candidates[a]['role'],'loserRole':candidates[b]['role'],
            'metricAgrees':{metric:scores[a][metric]<scores[b][metric] for metric in metrics}})
    assert len(rows)==6 and len(pairs)==4 and len(candidates)==12
    out=dict(complete=True,scriptSha256=file_hash(__file__),experimentId=manifest['experimentId'],
        feedbackSha256=file_hash(ARCHIVE/'feedback.json'),manifestSha256=file_hash(ARCHIVE/'manifest.json'),
        galleryReportSha256=file_hash(REPORT),galleryAuditSha256=file_hash(audit_path),
        metricHashes={name:file_hash(model_paths[name]) for name in models},unavailableMetrics=unavailable,
        archiveSummary=manifest['summary'],trainingPairSummary=data.summary,strictHeardPairs=len(pairs),rows=rows,pairs=pairs,
        metricAgreement={metric:dict(correct=sum(p['metricAgrees'][metric] for p in pairs),pairs=len(pairs)) for metric in metrics},
        interpretation=[
            'Compression sweep is a human tie despite the numerical regression; do not report a perceptually confirmed codec failure from this example.',
            'Transposed-input prediction beats its frozen-clean prediction; filtering the short texture produces a worse preferred recreation than keeping its clean-input prediction.',
            'Combined Transfxr models beat old-eight for the Bfxr and Boomr sources. These are relative preferences; no absolute likeness judgments supplied for those winners.',
            'Both Pluckr-source recreations are rejected as not close. A slightly better score does not establish a useful imitation.',
            'Four strict heard-only pairs are available. Preserve tie and rejection without invented scalar ratings or directional labels.',
            'MP3 and transposed warble share a source family with each other and with the earlier human-approved clean warble. Filtered texture shares its earlier clean source family. Any future preference validation must group these relatives together, not merely split distinct reference PCM hashes.',
            'No model retrained or promoted by this review. Targets are selected diagnostics; do not infer population success rates.'])
    _json_write(OUTPUT,out)
    print(json.dumps(dict(choices=[(r['name'],r['kind'],r['preferredRoles']) for r in rows],metricAgreement=out['metricAgreement'],trainingPairSummary=data.summary)),flush=True)
if __name__=='__main__':main()
