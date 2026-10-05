"""Audit saved actual audio and summarize three controlled inverse arms."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from match.objective import MatchObjective
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.pitch_v5_features import FEATURE_CODE_HASH


def wave(path, file_sha, pcm_sha):
    assert file_hash(path) == file_sha, path
    samples, rate = sf.read(path, dtype='float32')
    assert rate == 44100 and audio_hash(samples) == pcm_sha, path
    return samples


def main():
    reports = {}
    audited = 0
    for name in ('paired', 'high-pitch'):
        path = Path('tools/multisynth/runs/pitch-v5')/name/'results.json'
        data = json.loads(path.read_text())
        assert data['metadata']['complete']
        assert data['metadata']['v5DiagnosticCodeHash'] == FEATURE_CODE_HASH
        rows = []
        for row in data['results']:
            target = wave(row['referenceWaveFile'], row['referenceWaveFileSha256'], row['referenceAudioHash'])
            target_pitch = descriptor_pitch(target)
            assert target_pitch == row['v5TargetPitch']
            objective = MatchObjective(target)
            record = {k:row[k] for k in ('id','family','sourceSynth','referenceAudioHash')}
            record.update(targetPitch=target_pitch, arms={})
            for version, arm in row['arms'].items():
                candidates = arm['candidates']
                for candidate in candidates:
                    samples = wave(candidate['waveFile'], candidate['waveFileSha256'], candidate['audioHash'])
                    pitch = descriptor_pitch(samples)
                    assert pitch == candidate['v5Pitch']
                    assert compare_descriptor_pitch(target_pitch, pitch) == candidate['v5PitchComparison']
                    actual = objective.score(samples)
                    assert abs(actual-candidate['score']) < 1e-6, (row['id'], version, actual, candidate['score'])
                    audited += 1
                for key, pool in (('selected', [c for c in candidates if c['synth']==row['sourceSynth']]), ('unrestrictedSelected', candidates)):
                    expected = min(pool,key=lambda c:c['score']) if pool else None
                    assert arm[key] == expected
                compact = {'candidateAccounting':arm['totalAccounting'], 'failures':arm['failures']}
                for label, key in (('sourceEngine','selected'), ('unrestricted','unrestrictedSelected')):
                    c = arm[key]
                    compact[label] = None if c is None else {k:c[k] for k in ('synth','score','audioHash','v5Pitch','v5PitchComparison')}
                comparisons = [c['v5PitchComparison'] for c in candidates]
                compact['proposalPitchCoverage'] = {
                    'medianWithinOneSemitone':sum(c['medianErrorSemitones'] is not None and c['medianErrorSemitones']<=1 for c in comparisons),
                    'bestTargetActiveFractionWithinOneSemitone':max((c['activeFrameWithinOneSemitoneFraction'] for c in comparisons if c['activeFrameWithinOneSemitoneFraction'] is not None),default=None),
                    'meaning':'Diagnostic coverage across all proposals, including other engines. Pitch alone does not establish likeness.'}
                record['arms'][version] = compact
            rows.append(record)
        reports[name] = {'reportPath':str(path),'reportSha256':file_hash(path),'metadata':data['metadata'],'summary':data['summary'],'results':rows}
    result = {'complete':True,'auditScriptSha256':file_hash(__file__),'auditedActualWavs':audited,
        'featureCodeSha256':FEATURE_CODE_HASH,'trainingAuditSha256':file_hash('tools/multisynth/evaluations/pitch-v5-training-audit.json'),
        'scope':'Fixed development probes, not independent generalization or human validation. Every saved float WAV, objective score, selection and v5 descriptor diagnostic recomputed. Contours use relative active-sound time; pitch medians and direction alone do not certify likeness.',
        'reports':reports}
    Path('tools/multisynth/evaluations/pitch-v5-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    for name, report in reports.items():
        print(name,json.dumps(report['summary']),flush=True)


if __name__ == '__main__':
    main()
