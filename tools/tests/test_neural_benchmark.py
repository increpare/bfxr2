"""Paired benchmark: new controls, shared baselines, and honest pitch diagnostics."""
import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest

from multisynth.renderer import Renderer
from neural_invert.data import parameter_hash


def test_fresh_draw_excludes_controls_even_when_render_seed_changes():
    from neural_invert.benchmark import draw_target
    class TinyRenderer:
        specs = {'Tiny': {'presets': ['native']}}
        inventory = {'sourceHash': 'actual'}
        def sample(self, name, preset, seed): return {'phrase': 'C4', 'control': seed % 17}
        def render(self, name, params, seed): return params, np.ones(4096, np.float32)
    renderer = TinyRenderer()
    first = draw_target(renderer, 'Tiny', 'native', set(), 41)
    rejected = {parameter_hash({'synth': 'Tiny', 'params': first['sourceParams']})}
    next_target = draw_target(renderer, 'Tiny', 'native', rejected, 41)
    replay = draw_target(renderer, 'Tiny', 'native', rejected, 41)
    assert next_target['parameterHash'] not in rejected
    assert next_target['sourceSeed'] != first['sourceSeed']
    assert next_target['sourceParams'] == replay['sourceParams']
    assert next_target['rejections'][0]['reason'] == 'excluded controls'


def test_pitch_trajectory_keeps_direction_and_marks_unvoiced_samples_null():
    from neural_invert.benchmark import pitch_diagnostic, compare_pitch
    rate = 44100
    t = np.arange(rate) / rate
    def chirp(start, end):
        hz = start + (end-start)*t
        return (.4*np.sin(2*np.pi*np.cumsum(hz)/rate)).astype(np.float32)
    rise = pitch_diagnostic(chirp(180, 450))
    fall = pitch_diagnostic(chirp(450, 180))
    assert len(rise['contourHz']) == 16
    assert rise['direction'] == 1 and fall['direction'] == -1
    assert rise['excursionSemitones'] > 8
    assert compare_pitch(rise, fall, 'moving')['directionMatches'] is False
    assert compare_pitch(rise, rise, 'moving')['contourErrorSemitones'] == pytest.approx(0)
    silent = pitch_diagnostic(np.zeros(rate, np.float32))
    assert silent['medianHz'] is None and silent['contourHz'] == [None]*16
    assert compare_pitch(rise, silent, 'moving')['contourErrorSemitones'] is None


def test_summary_counts_missing_roles_and_unvoiced_finalists():
    from neural_invert.benchmark import summarize
    pitched = {'voicedFraction': 1., 'medianHz': 300.}
    unvoiced = {'voicedFraction': 0., 'medianHz': None}
    row = {'synth': 'Bfxr', 'score': 2., 'pitch': unvoiced,
           'pitchComparison': {'absolutePitchErrorSemitones': None}}
    records = [{'family': 'static', 'sourceSynth': 'Bfxr', 'targetPitch': pitched,
                'arms': {'v1': {'candidates': {'knownRaw': None, 'unrestrictedRaw': row,
                       'neuralRefined': None, 'selected': row, 'original': row}}}}]
    summary = summarize(records, ['v1'], ['Bfxr', 'Other'])
    selected = summary['arms']['v1']['static']['selected']
    assert selected['count'] == 1 and selected['missing'] == 0
    assert selected['pitchUnreliableOrMissing'] == 1
    assert selected['voicedTargetUnvoicedFinalist'] == 1
    assert selected['meanScore'] == 2
    assert summary['arms']['v1']['static']['knownRaw']['missing'] == 1
    assert summary['broadCoverage']['missingEngines'] == ['Bfxr', 'Other']
    json.dumps(summary, allow_nan=False)


def test_wrong_training_binding_fails_before_output_created(tmp_path, monkeypatch):
    import neural_invert.benchmark as benchmark
    data = tmp_path/'data'; data.mkdir()
    (data/'manifest.json').write_text('{}')
    monkeypatch.setattr(benchmark, 'load_model', lambda path: (None, {'dataManifestHash': 'wrong'}))
    output = tmp_path/'output'
    args = SimpleNamespace(model=['bad='+str(tmp_path/'checkpoint')], data=[data], output=output,
                           bfxr_checkpoint=tmp_path/'original', seed=51, jobs=1, budget=1, bfxr_budget=1)
    with pytest.raises(ValueError, match='training data'):
        benchmark.run(args)
    assert not output.exists()


def test_frozen_original_is_shared_without_mutable_aliasing():
    from neural_invert.benchmark import FrozenOriginal
    wave = np.ones(4096, np.float32)
    adapter = FrozenOriginal({'wave': wave, 'params': {'x': .5}, 'score': 1.,
                              'provenance': {'evaluations': 10}}, budget=8, seed=51)
    a = adapter.approximate(wave, None, budget=8, seed=51)
    a['params']['x'] = 0
    assert adapter.approximate(wave, None, budget=8, seed=51)['params']['x'] == .5
    with pytest.raises(ValueError, match='budget or seed'):
        adapter.approximate(wave, None, budget=9, seed=51)


def test_actual_dsp_controlled_probes_calibrate_and_replay():
    from neural_invert.benchmark import draw_target, pitch_diagnostic
    with Renderer() as renderer:
        for name in ('Bfxr', 'Transfxr', 'Pluckr'):
            for hz in (137, 311, 673):
                target = draw_target(renderer, name, 'static', set(), 552+hz, hz=hz)
                canonical, replay = renderer.render(name, target['sourceParams'], target['sourceSeed'])
                assert canonical == target['sourceParams']
                assert hashlib.sha256(replay.astype('<f4').tobytes()).hexdigest() == target['audioHash']
                assert target['calibration']['absoluteSemitones'] < .5
                assert target['targetPitch']['voicedFraction'] >= .6
        for name in ('Bfxr', 'Transfxr'):
            for gesture in ('rise', 'fall', 'jump', 'vibrato'):
                target = draw_target(renderer, name, 'moving', set(), 2251, gesture=gesture)
                pitch = target['targetPitch']
                assert pitch['voicedFraction'] >= .6
                assert pitch['excursionSemitones'] >= (.2 if gesture == 'vibrato' else 2.)
                if gesture in ('rise', 'fall', 'jump'):
                    assert pitch['direction'] == (-1 if gesture == 'fall' else 1)
                _, replay = renderer.render(name, target['sourceParams'], target['sourceSeed'])
                assert pitch_diagnostic(replay) == pitch


def test_frozen_original_rejects_different_target_pcm():
    from neural_invert.benchmark import FrozenOriginal
    wave = np.ones(4096, np.float32)
    adapter = FrozenOriginal({'wave': wave, 'score': 1}, budget=1, seed=2, target_wave=wave)
    with pytest.raises(ValueError, match='target PCM'):
        adapter.approximate(wave*.5, None, budget=1, seed=2)


def test_motion_summary_reports_direction_and_excursion_missing_denominators():
    from neural_invert.benchmark import summarize
    candidate = {'synth': 'Transfxr', 'score': 1, 'pitch': {'medianHz': 300},
                 'pitchComparison': {'directionMatches': False, 'excursionErrorSemitones': 3,
                                     'contourErrorSemitones': 5}}
    records = [{'sourceSynth': 'Bfxr', 'family': 'moving', 'targetPitch': {'medianHz': 300},
                'arms': {'v1': {'candidates': {'selected': candidate}}}},
               {'sourceSynth': 'Bfxr', 'family': 'moving', 'targetPitch': {'medianHz': 300},
                'arms': {'v1': {'candidates': {'selected': None}}}}]
    result = summarize(records, ['v1'], ['Bfxr'])['arms']['v1']['moving']['selected']
    assert result['movingDirectionMatches'] == 0
    assert result['movingDirectionReliableCount'] == 1
    assert result['movingDirectionUnreliableOrMissing'] == 1
    assert result['meanExcursionErrorSemitones'] == 3
    assert result['excursionUnreliableOrMissing'] == 1


def test_preflight_unions_every_row_and_rejects_dataset_corruption(tmp_path):
    from neural_invert.benchmark import validate_inputs
    from neural_invert.data import generate_dataset, file_hash
    with Renderer() as renderer:
        engines = [s['name'] for s in renderer.inventory['synths'] if s.get('collectionCompatible')]
        models = {'arm': (None, {'dataManifestHash': None, 'sourceHash': renderer.inventory['sourceHash'],
                                'engines': engines, 'specs': {n: renderer.specs[n] for n in engines}})}
        paths = [tmp_path/'a', tmp_path/'b']
        for path, seed in zip(paths, [199, 299]):
            generate_dataset(path, per_synth=4, jobs=1, seed=seed, synths=['Bfxr'])
        models['arm'][1]['dataManifestHash'] = file_hash(paths[0]/'manifest.json')
        excluded, bindings, _ = validate_inputs(models, paths, renderer)
        for path in paths:
            shard = json.loads((path/'Bfxr.json').read_text())
            assert all(parameter_hash(row) in excluded for row in shard['rows'])
            assert set(shard['train']) | set(shard['val']) == set(range(4))
        assert len(bindings) == 2
        saved = paths[1]/'Bfxr.npz'
        saved.write_bytes(saved.read_bytes()+b'corrupt')
        with pytest.raises(ValueError, match='integrity'):
            validate_inputs(models, paths, renderer)


def test_fresh_native_plan_covers_all_engines_and_controlled_families():
    from neural_invert.benchmark import create_targets
    with Renderer() as renderer:
        targets = create_targets(renderer, set(), seed=20261006)
        repeated = create_targets(renderer, {t['parameterHash'] for t in targets}, seed=20261006)
        assert len(targets) == 39
        assert len([t for t in targets if t['family'] == 'native']) == 22
        assert len([t for t in targets if t['family'] == 'static']) == 9
        assert len([t for t in targets if t['family'] == 'moving']) == 8
        assert not {t['parameterHash'] for t in targets} & {t['parameterHash'] for t in repeated}
        assert len({t['parameterHash'] for t in targets}) == 39


def test_control_exclusion_ignores_random_anchors_and_gain_but_keeps_text():
    from neural_invert.benchmark import control_hash
    with Renderer() as renderer:
        spec = renderer.specs['Pluckr']
        params = renderer.sample('Pluckr', spec['presets'][0], 1)
        changed = dict(params, seed=.111, masterVolume=.777)
        assert control_hash(spec, params) == control_hash(spec, changed)
        spec = renderer.specs['Jinglr']
        params = renderer.sample('Jinglr', spec['presets'][0], 1)
        changed = dict(params, phrase=params['phrase']+' C4')
        assert control_hash(spec, params) != control_hash(spec, changed)


def test_paired_actual_dsp_evaluation_runs_original_once_and_saves_every_finalist(tmp_path, monkeypatch):
    import soundfile as sf
    import neural_invert.benchmark as benchmark
    import neural_invert.predict as prediction
    with Renderer() as renderer:
        target = benchmark.draw_target(renderer, 'Transfxr', 'static', set(), 491, hz=311)
        params = target['sourceParams']
        baseline_params, baseline_wave = renderer.render('Bfxr', renderer.specs['Bfxr']['defaults'], 9)
    folder = tmp_path/'one'; folder.mkdir()
    path = folder/'target.wav'; sf.write(path, target.pop('wave'), 44100, subtype='FLOAT')
    target.update(id='one', waveFile=str(path), evaluationSeed=77)
    calls = []
    class Original:
        def __init__(self, *args): pass
        def approximate(self, wave, objective, budget, seed):
            calls.append((benchmark.audio_hash(wave), budget, seed))
            return {'synth': 'Bfxr', 'params': baseline_params, 'seed': 9, 'wave': baseline_wave,
                    'score': float(objective.score_batch([baseline_wave])[0]), 'expert': 'original-bfxr',
                    'provenance': {'evaluations': 11}}
    monkeypatch.setattr(benchmark, 'OriginalBfxr', Original)
    monkeypatch.setattr(benchmark, 'load_model', lambda path: (object(), {'checkpointHash': 'fixed'}))
    monkeypatch.setattr(prediction, 'predict', lambda *args, **kwargs: [
        {'synth': 'Transfxr', 'params': params, 'seed': 17, 'provenance': {'test': 'paired actual DSP'}}])
    config = {'output': str(tmp_path), 'models': {'v1': 'one.pt', 'v2': 'two.pt'},
              'modelHashes': {'v1': 'fixed', 'v2': 'fixed'}, 'bfxrCheckpoint': 'original.pt',
              'bfxrBudget': 12, 'budget': 1}
    record = benchmark.evaluate_target((config, target))
    assert calls == [(target['audioHash'], 12, 77)]
    for arm in record['arms'].values():
        assert arm['originalSharedAcrossArms'] and arm['evaluationSeed'] == 77
        assert len(arm['allRaw']) == len(arm['allRefined']) == 1
        assert arm['actualRefinedStarts'] == 1
        for row in list(arm['candidates'].values())+arm['allRaw']+arm['allRefined']:
            pcm, rate = sf.read(row['waveFile'], dtype='float32')
            assert rate == 44100 and benchmark.audio_hash(pcm) == row['audioHash']
        assert arm['candidates']['knownRaw']['synth'] == 'Transfxr'
    assert record['arms']['v1']['candidates']['original']['audioHash'] == record['arms']['v2']['candidates']['original']['audioHash']
    assert (folder/'report.json').exists()


def test_exact_control_replay_rejects_renderer_disagreement():
    from neural_invert.benchmark import exact_replay
    row = {'synth': 'Any', 'params': {'x': 1}, 'seed': 12, 'wave': np.ones(4096, np.float32)}
    class ChangedRenderer:
        def render(self, *args): return row['params'], row['wave']*.5
    with pytest.raises(ValueError, match='control replay'):
        exact_replay(row, ChangedRenderer(), None)
