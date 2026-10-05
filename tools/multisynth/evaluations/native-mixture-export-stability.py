"""Read-only export stability audit; no model or descriptor is changed."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from match.audio import normalize_peak
from neural_invert import features
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm
from neural_invert.pitch_v5_eval import descriptor_pitch

BASE = Path('tools/multisynth')
REPORT = BASE/'runs/native-mixture-v1/evaluation/results.json'
ARCHIVE = BASE/'listening_data/2026-10-05-native-mixture-quick-01'
OUTPUT = Path(__file__).with_suffix('.json')


def support(wave):
    active = np.flatnonzero(np.abs(wave) > np.abs(wave).max()*1e-4)
    return active[[0, -1]].tolist() if len(active) else None


def pitch(wave):
    result = descriptor_pitch(wave)
    return {k: result[k] for k in ('medianHz', 'reliable', 'direction',
        'startToEndSemitones', 'activeFrames', 'voicedFrames', 'directionSupport')}


def main():
    if OUTPUT.exists():
        raise FileExistsError('Preserve original audit; use a new version')
    report = json.loads(REPORT.read_text())
    assert report['complete']
    rows = []
    cache = {}
    for row in report['rows']:
        for role, item in [('target', row['target']), *row['selected'].items()]:
            assert file_hash(item['waveFile']) == item['waveFileSha256']
            wave, rate = sf.read(item['waveFile'], dtype='float32')
            assert rate == 44100 and audio_hash(wave) == item['audioHash']
            key = item['audioHash']
            if key not in cache:
                normalized = normalize_peak(wave)
                pcm = audition_pcm(wave)
                a, b = features.describe(normalized), features.describe(pcm)
                cache[key] = dict(
                    raw=pitch(wave), normalized=pitch(normalized), pcm16=pitch(pcm),
                    rawSupport=support(wave), normalizedSupport=support(normalized),
                    pcm16Support=support(pcm), samples=len(wave),
                    maxQuantizationError=float(np.max(np.abs(normalized-pcm))),
                    normalizedToPcmFeatureMeanAbs=float(np.mean(np.abs(a-b))),
                    normalizedToPcmFeatureMaxAbs=float(np.max(np.abs(a-b))))
            rows.append(dict(targetId=row['target']['id'], group=row['target']['group'],
                             role=role, audioHash=key, waveFileSha256=item['waveFileSha256'],
                             **cache[key]))
        if len(rows) % 80 == 0:
            print(json.dumps(dict(audioRoles=len(rows), uniqueAudio=len(cache))), flush=True)

    # Isolate the wide sweep's boundary dependence without editing the actual
    # render, archive or listening page. These are analysis-only counterfactuals.
    selected = next(r for r in report['rows'] if r['target']['id']=='Transfxr-mixture-18808')['selected']['mixture']
    wave, _ = sf.read(selected['waveFile'], dtype='float32')
    normalized, pcm = normalize_peak(wave), audition_pcm(wave)
    start, end = support(normalized)
    qstart, qend = support(pcm)
    assert start == qstart and qend > end
    fixed = pcm.copy()
    fixed[:start] = 0
    fixed[end+1:] = 0
    fixed[[start, end]] = normalized[[start, end]]
    endpoint = normalized.copy()
    endpoint[qend] = pcm[qend]
    counterfactuals = {name: dict(support=support(value), pitch=pitch(value))
        for name, value in [('normalized', normalized), ('pcm16', pcm),
                            ('pcm16WithOriginalSupport', fixed),
                            ('floatWithOneQuantizedTailSample', endpoint)]}
    assert [v['pitch']['direction'] for v in counterfactuals.values()] == [1, -1, 1, -1]
    manifest = json.loads((ARCHIVE/'manifest.json').read_text())
    candidate = next(c for c in manifest['candidates']
                     if c['provenance']['sourceCase']=='Transfxr-mixture-18808' and c['role']=='selected')
    heard, heard_rate = sf.read(ARCHIVE/candidate['audio']['file'], dtype='float32')
    assert heard_rate == 44100 and np.array_equal(heard, pcm)

    def summary(values):
        return dict(audioRoles=len(values),
            normalizedSupportChanges=sum(r['rawSupport']!=r['normalizedSupport'] for r in values),
            pcmSupportChanges=sum(r['normalizedSupport']!=r['pcm16Support'] for r in values),
            normalizationDirectionChanges=sum(r['raw']['direction']!=r['normalized']['direction'] for r in values),
            quantizationDirectionChanges=sum(r['normalized']['direction']!=r['pcm16']['direction'] for r in values),
            reliableOppositeDirection=sum(r['normalized']['direction'] in (-1,1)
                and r['pcm16']['direction']==-r['normalized']['direction'] for r in values),
            medianFeatureMeanAbs=float(np.median([r['normalizedToPcmFeatureMeanAbs'] for r in values])))

    out = dict(complete=True, scriptSha256=file_hash(__file__), reportSha256=file_hash(REPORT),
        feedbackSha256=file_hash(ARCHIVE/'feedback.json'), manifestSha256=file_hash(ARCHIVE/'manifest.json'),
        codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/features.py'),
            Path('tools/neural_invert/pitch_v5_features.py'), Path('tools/neural_invert/pitch_v5_eval.py'),
            Path('tools/neural_invert/experiment.py'), Path('tools/match/audio.py')]},
        summary=summary(rows), byRole={role:summary([r for r in rows if r['role']==role])
                                     for role in ('target', 'baseline', 'single', 'mixture')},
        uniqueAudio=len(cache), rows=rows,
        wideSweep=dict(candidateId=candidate['id'], auditionPcmSha256=candidate['audio']['pcmSha256'],
            boundaryShiftSamples=qend-end, boundaryShiftMilliseconds=1000*(qend-end)/44100,
            originalTailSample=float(normalized[qend]), quantizedTailSample=float(pcm[qend]),
            trimThreshold=float(np.abs(normalized).max()*1e-4), counterfactuals=counterfactuals),
        interpretation=[
            'The wide sweep direction flip is reproduced by changing one tiny tail sample to its exported quantized value, which extends the trim boundary and shifts the entire relative frame grid.',
            'Keeping the original support restores the sign even with quantized interior samples. This isolates boundary sensitivity for this case, not every descriptor discrepancy.',
            'The archived human-approved sound exactly equals the normal audition transform. This is diagnostic instability, not a corrupted gallery render.',
            'The production inverse uses the frozen fullsound descriptor; the v5 diagnostic is separate. Both share threshold-based trimming, but this audit does not establish inverse prediction changes or explain all transfer failures.',
            'Audio-role counts include correlated transformed references and duplicate signals. They are a development diagnostic, not independent perceptual error rates.',
            'No model, frozen feature code, selector, checkpoint, or original listening artifact is modified. Future preprocessing changes need separately versioned compatibility bindings and actual-render evaluation.'])
    _json_write(OUTPUT, out)
    print(json.dumps(dict(summary=out['summary'], byRole=out['byRole'], wideSweep=out['wideSweep'])), flush=True)


if __name__ == '__main__':
    main()
