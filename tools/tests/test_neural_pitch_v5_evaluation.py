"""Actual-render provenance and budget checks for the input ablation."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf


def test_failed_source_engine_does_not_hide_unrestricted_output(tmp_path):
    from multisynth.renderer import Renderer
    from neural_invert.pitch_v5_eval import evaluate_candidates
    from neural_invert.data import file_hash
    from neural_invert.benchmark import audio_hash
    import torch
    torch.set_num_threads(1)
    with Renderer() as renderer:
        silent = deepcopy(renderer.specs['Bfxr']['defaults'])
        # Renderer fixes gain at .5; closed filters plus a slow attack are actually silent.
        silent.update(lpFilterCutoff=.01, hpFilterCutoff=1., attackTime=.9)
        params, target = renderer.render('Transfxr', renderer.specs['Transfxr']['defaults'], 123)
        proposals = [dict(synth='Bfxr', params=silent, seed=123, provenance={}),
                     dict(synth='Transfxr', params=params, seed=123, provenance={})]
        result = evaluate_candidates(proposals, target, 'Bfxr', 'native', renderer, tmp_path, count=1)
        assert result['selected'] is None
        chosen = result['unrestrictedSelected']
        assert chosen['synth'] == 'Transfxr'
        assert result['accounting']['Bfxr']['failedRenders'] == 1
        assert result['accounting']['Pluckr']['missingProposals'] == 1
        assert result['totalAccounting']['expected'] == 3
        assert result['totalAccounting']['rendered'] == 1
        assert result['proposals'] == proposals
        assert len(result['failures']) == 1
        path = Path(chosen['waveFile']); wave, rate = sf.read(path, dtype='float32')
        _, replay = renderer.render(chosen['synth'], chosen['params'], chosen['seed'])
        assert rate == 44100 and np.array_equal(wave, replay)
        assert file_hash(path) == chosen['waveFileSha256']
        assert audio_hash(wave) == chosen['audioHash']


def test_invalid_budget_is_rejected_before_render_or_write(tmp_path):
    from neural_invert.pitch_v5_eval import evaluate_candidates
    class NeverRender:
        def render(self, *args):
            raise AssertionError('must validate first')
    row = dict(synth='Bfxr', params={}, seed=1, provenance={})
    with pytest.raises(ValueError, match='budget'):
        evaluate_candidates([row, row], np.ones(3000), 'Bfxr', 'native', NeverRender(), tmp_path/'out', count=1)
    assert not (tmp_path/'out').exists()


def test_corrected_diagnostic_exposes_upper_register_octave_false_pass(tmp_path):
    from multisynth.renderer import Renderer
    from neural_invert.benchmark import probe_controls
    from neural_invert.pitch_v5_eval import evaluate_candidates, conservative_pitch_summary
    import torch
    torch.set_num_threads(1)
    with Renderer() as renderer:
        spec = renderer.specs['Transfxr']
        params,_ = probe_controls(spec, np.random.default_rng(99), 2500)
        _,target = renderer.render('Transfxr',params,1)
        params,_ = probe_controls(spec, np.random.default_rng(99), 5000)
        result = evaluate_candidates([dict(synth='Transfxr',params=params,seed=1,provenance={})],
            target,'Transfxr','static',renderer,tmp_path,count=1)
    chosen = result['selected']
    assert chosen['pitchComparison']['absolutePitchErrorSemitones'] < 1.
    assert chosen['correctedPitchErrorSemitones'] > 11.
    summary = conservative_pitch_summary([dict(family='static',selected=chosen)])
    assert summary['staticWithinOneSemitoneCorrected'] == 0
    assert summary['staticWithinOneSemitoneBoth'] == 0
    assert summary['staticTrackerPassDisagreements'] == 1


def chirp(low, high):
    hz = np.geomspace(low, high, 44100)
    return (.4*np.sin(2*np.pi*np.cumsum(hz)/44100)).astype(np.float32)


def test_v5_contours_reject_same_direction_wrong_excursion():
    from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
    target = descriptor_pitch(chirp(200, 800))
    candidate = descriptor_pitch(chirp(350, 450))
    compared = compare_descriptor_pitch(target, candidate)
    assert target['direction'] == candidate['direction'] == 1
    assert abs(12*np.log2(target['medianHz']/candidate['medianHz'])) < 1
    assert compared['directionMatches'] is True
    assert compared['spanErrorSemitones'] > 15
    assert compared['contourErrorSemitones'] > 4
    assert compared['activeFrameWithinOneSemitoneFraction'] < .2
    assert len(target['contourHz']) == len(target['activeMask']) == 48
    assert target['activeFrames'] >= target['voicedFrames'] > 30
    assert target['spanSemitones'] > 22
    assert target['contourTime'][0] == 0 and target['contourTime'][-1] == 1


def test_v5_contour_missing_frames_count_against_active_tolerance():
    from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
    target = descriptor_pitch(chirp(200, 400))
    missing = deepcopy(target)
    missing['contourHz'] = [None]*48
    missing['medianHz'] = None
    missing['reliable'] = False
    compared = compare_descriptor_pitch(target, missing)
    assert compared['activeFrameWithinOneSemitoneFraction'] == 0
    assert compared['reliableContourPairs'] == 0
    assert compared['contourErrorSemitones'] is None
    assert compared['targetActiveFrames'] == target['activeFrames']


def test_v5_diagnostic_does_not_change_objective_selection(tmp_path, monkeypatch):
    from neural_invert import pitch_v5_eval as evaluation
    wave = chirp(200, 800)
    class Renderer:
        def render(self, synth, params, seed):
            return params, wave*np.float32(params['gain'])
    class Objective:
        def __init__(self, target): pass
        def score_batch(self, waves): return [float(np.sum(w*w)) for w in waves]
    monkeypatch.setattr(evaluation, 'MatchObjective', Objective)
    rows = [dict(synth='Bfxr', params={'gain': g}, seed=1, provenance={}) for g in (1., .2)]
    result = evaluation.evaluate_candidates(rows, wave, 'Bfxr', 'moving', Renderer(), tmp_path, 2)
    assert result['selected']['params']['gain'] == .2
    assert result['selected']['v5PitchComparison']['activeFrameWithinOneSemitoneFraction'] > .9
    assert result['selected']['legacyPitchComparison'] == result['selected']['pitchComparison']
    assert sf.info(result['selected']['waveFile']).subtype == 'FLOAT'


def test_benchmark_has_explicit_three_arms_and_correct_bindings(tmp_path, monkeypatch):
    from neural_invert import pitch_v5_eval as evaluation
    wave = chirp(200, 400)
    target = tmp_path/'target.wav'
    sf.write(target, wave, 44100, subtype='FLOAT')
    from neural_invert.data import file_hash
    from neural_invert.benchmark import audio_hash
    source = dict(id='001', sourceSynth='Bfxr', family='moving', sourceParams={}, sourceSeed=1,
                  sourceHash='dsp', waveFile=str(target), waveFileSha256=file_hash(target), audioHash=audio_hash(wave))
    manifest = tmp_path/'benchmark.json'
    import json
    manifest.write_text(json.dumps({'results': [source]}))
    calls = []
    def load(root, version):
        calls.append((root, version))
        meta = {k: version for k in ('checkpointHash', 'dataManifestHash', 'featureHash', 'featureCodeHash')}
        meta['sourceHash'] = 'dsp'
        return {e: (None, meta) for e in evaluation.ENGINES}, None
    class Renderer:
        inventory = {'sourceHash': 'dsp'}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def render(self, synth, params, seed): return params, wave.copy()
    monkeypatch.setattr(evaluation, 'load_experts', load)
    monkeypatch.setattr(evaluation, 'Renderer', Renderer)
    monkeypatch.setattr(evaluation, 'proposals', lambda bundle,wave,renderer,count: [
        dict(synth=e,params={},seed=i,provenance={}) for e in evaluation.ENGINES for i in range(count)])
    result = evaluation.benchmark(manifest, 'v3', 'v4', 'v5', tmp_path/'output')
    assert calls == [('v3','temporal-v3'), ('v4','pitch-v4'), ('v5','pitch-v5')]
    assert list(result['results'][0]['arms']) == ['temporal-v3','pitch-v4','pitch-v5']
    for arm in result['results'][0]['arms'].values():
        assert len(arm['candidates']) == 12
        assert arm['totalAccounting']['expected'] == arm['totalAccounting']['rendered'] == 12
        assert all('v5PitchComparison' in c and 'legacyPitchComparison' in c for c in arm['candidates'])
    for name in ('pitch_v5_gallery.py', 'pitch_v5_eval.py', 'pitch_v5_features.py', 'pitch_v5_temporal.py', 'pitch_v5_data.py',
                 'pitch_temporal.py', 'pitch_features.py', 'temporal.py', 'features.py'):
        assert name in result['metadata']['codeHashes']
    assert result['metadata']['complete']
    assert result['summary']['pitch-v5']['unrestricted']['legacy']['movingTotal'] == 1


def test_middle_only_voicing_labels_direction_support_and_keeps_active_denominator():
    from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch, diagnostic_summary
    wave = chirp(200, 800)
    rng = np.random.default_rng(772)
    edge = int(.15*44100)
    wave[:edge] = rng.normal(0, .15, edge)
    wave[-edge:] = rng.normal(0, .15, edge)
    pitch = descriptor_pitch(wave)
    assert pitch['reliable'] and pitch['voicedFraction'] >= .6
    assert pitch['contourHz'][0] is None and pitch['contourHz'][-1] is None
    voiced = np.flatnonzero(pitch['voicedMask'])
    support = pitch['directionSupport']
    assert support['startFrameIndices'] == voiced[:3].tolist()
    assert support['endFrameIndices'] == voiced[-3:].tolist()
    assert support['startRelativePositions'] == [pitch['contourTime'][i] for i in voiced[:3]]
    assert support['endRelativePositions'] == [pitch['contourTime'][i] for i in voiced[-3:]]
    assert min(support['startRelativePositions']) > 0
    assert max(support['endRelativePositions']) < 1
    assert 'voiced-span' in pitch['directionMeaning']
    assert 'whole-sound endpoints' in pitch['directionMeaning']
    compared = compare_descriptor_pitch(pitch, pitch)
    assert compared['targetActiveFrames'] == pitch['activeFrames']
    assert compared['activeFramesWithinOneSemitone'] == pitch['voicedFrames']
    assert compared['activeFrameWithinOneSemitoneFraction'] == pytest.approx(pitch['voicedFraction'])
    assert compared['activeFrameWithinOneSemitoneFraction'] < 1
    summary = diagnostic_summary([dict(family='moving', selected={'v5PitchComparison': compared})])
    assert 'voiced-span direction' in summary['meaning']
