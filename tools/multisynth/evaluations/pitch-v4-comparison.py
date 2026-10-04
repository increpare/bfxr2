"""Summarize controlled pitch retraining without hiding unstable static pitch."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from neural_invert.data import file_hash
from neural_invert.pitch_features import describe, FEATURE_CODE_HASH


def contour(path, target_hz=None, expected_hash=None):
    assert expected_hash and file_hash(path) == expected_hash, str(path)
    wave, rate = sf.read(path, dtype='float32')
    assert rate == 44100
    x = describe(wave)
    active = x[3840:3888] > .05
    voiced = active & (x[3936:3984] >= .6)
    hz = 55*np.exp2(7*x[3888:3936][voiced])
    if not len(hz):
        return {'voicedFraction':0.,'medianHz':None,'activeFramesWithinOneSemitone':0. if target_hz else None}
    percentiles = np.percentile(hz,[10,50,90]).tolist()
    return {'voicedFraction':float(voiced.sum()/max(1,active.sum())),
        'medianHz':percentiles[1], 'pitchHzP10P50P90':percentiles,
        'pitchSpanP10P90Semitones':float(12*np.log2(percentiles[2]/percentiles[0])),
        'activeFramesWithinOneSemitone':float((np.abs(12*np.log2(hz/target_hz))<=1).sum()/max(1,active.sum())) if target_hz else None,
        'meaning':'Corrected tracker diagnostic only; unvoiced active frames count outside tolerance. No human quality threshold.'}


def main():
    reports = {}
    for name in ('paired','high-pitch'):
        path = Path('tools/multisynth/runs/pitch-v4')/name/'results.json'
        data = json.loads(path.read_text()); assert data['metadata']['complete']
        rows = []
        for row in data['results']:
            record = {'id':row['id'],'family':row['family'],'sourceSynth':row['sourceSynth'],'arms':{}}
            reference = contour(row['referenceWaveFile'],expected_hash=row['referenceWaveFileSha256']) if row['family']=='static' else None
            record['staticTargetPitch'] = reference
            for version,arm in row['arms'].items():
                record['arms'][version] = {}
                if reference:
                    candidates = [contour(c['waveFile'],reference['medianHz'],c['waveFileSha256']) for c in arm['candidates']]
                    record['arms'][version]['staticProposalCoverage'] = {
                        'audibleCandidates':len(candidates),
                        'medianWithinOneSemitone':sum(c['correctedPitchErrorSemitones'] is not None and c['correctedPitchErrorSemitones'] <= 1 for c in arm['candidates']),
                        'bestActiveFramesWithinOneSemitone':max((c['activeFramesWithinOneSemitone'] for c in candidates),default=0.),
                        'meaning':'Candidate-generation diagnostic before selection; no human quality threshold.'}

                for label,key in (('sourceEngine','selected'),('unrestricted','unrestrictedSelected')):
                    c = arm[key]
                    record['arms'][version][label] = None if c is None else {
                        'synth':c['synth'],'score':c['score'],'audioHash':c['audioHash'],
                        'pitchComparison':c['pitchComparison'],
                        'correctedMedianPitchErrorSemitones':c['correctedPitchErrorSemitones'],
                        'staticPitchContour':contour(c['waveFile'],reference['medianHz'],c['waveFileSha256']) if reference else None}
            rows.append(record)
        motion = {}
        for version in ('temporal-v3','pitch-v4'):
            chosen = [r['arms'][version]['unrestrictedSelected'] for r in data['results'] if r['family']=='moving']
            motion[version] = {key:float(np.mean([c['pitchComparison'][key] for c in chosen if c and c['pitchComparison'].get(key) is not None])) if any(c and c['pitchComparison'].get(key) is not None for c in chosen) else None for key in ('contourErrorSemitones','excursionErrorSemitones')}
        reports[name] = {'unrestrictedMovingMeanErrors':motion,'reportPath':str(path),'reportSha256':file_hash(path),
            'metadata':data['metadata'],'summary':data['summary'],'results':rows}
    output = {'complete':True,'auditScriptSha256':file_hash(__file__),
        'knownDescriptorDefect':{'status':'compromised-pitch-measurements','report':'tools/multisynth/evaluations/pitch-v4-overtone-failure.json','reportSha256':file_hash('tools/multisynth/evaluations/pitch-v4-overtone-failure.json'),'meaning':'Corrected-tracker medians, spreads, confidence and frame tolerance are outputs of a demonstrated defective estimator. Do not interpret as physical pitch accuracy/instability or true frequency coverage. Old primary tracker also has known octave errors. Objective scores and DSP/audio provenance are unaffected.'},
        'correctedDescriptorCodeSha256':FEATURE_CODE_HASH,
        'trainingAuditSha256':file_hash('tools/multisynth/evaluations/pitch-v4-training-audit.json'),
        'scope':'Fixed development probes; architecture choice inherited from temporal-v3. Neither numerical distance nor median pitch passes establish human likeness. Static contour spread and in-tolerance active-frame fractions expose median-only false reassurance.',
        'reports':reports}
    Path('tools/multisynth/evaluations/pitch-v4-comparison.json').write_text(json.dumps(output,indent=2)+'\n')
    for name,report in reports.items():
        print(name,json.dumps(report['summary']),flush=True)


if __name__ == '__main__':
    main()
