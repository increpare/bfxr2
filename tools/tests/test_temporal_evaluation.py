import numpy as np
import pytest


def test_new_reference_without_history_has_no_previous_candidate():
    from neural_invert.temporal_gallery import previous_candidate
    assert previous_candidate({}, 'new-source') is None
    assert previous_candidate({'new-source': []}, 'new-source') is None


def test_resume_requires_incomplete_matching_inputs(tmp_path):
    import json
    from neural_invert.temporal_gallery import check_resume
    meta = {'complete': False, 'targetManifestSha256': 'a', 'checkpointHashes': {'Bfxr': 'x'},
            'sourceHash': 'd', 'previousReportSha256': 'p', 'refinementBudgetPerEngine': 384,
            'evaluationCodeSha256': 'e', 'codeSha256': 'old'}
    (tmp_path/'manifest.json').write_text(json.dumps(meta))
    assert check_resume(tmp_path, {**meta, 'codeSha256': 'new'})['codeSha256'] == 'old'
    with pytest.raises(ValueError, match='inputs'):
        check_resume(tmp_path, {**meta, 'sourceHash': 'changed'})
    (tmp_path/'results.json').write_text('{}')
    with pytest.raises(ValueError, match='completed'):
        check_resume(tmp_path, meta)


def test_repeated_resume_preserves_original_generation_hash(tmp_path):
    from neural_invert.temporal_gallery import retained_code_map
    (tmp_path/'001').mkdir()
    (tmp_path/'001'/'report.json').write_text('{}')
    first = retained_code_map(tmp_path, {'codeSha256': 'original'})
    assert first == {'001': 'original'}
    second = retained_code_map(tmp_path, {'codeSha256': 'repaired', 'generationCodeByFolder': first})
    assert second == first


def test_resumed_record_rejects_changed_audio_or_source(tmp_path):
    import json
    from neural_invert.data import file_hash
    from neural_invert.temporal_gallery import completed_record
    import soundfile as sf
    source = {'sha256': 'same'}
    sf.write(tmp_path/'selected.wav', np.ones(100, dtype=np.float32)*.1, 44100, subtype='PCM_16')
    row = {'source': source, 'candidates': [{'file': 'selected.wav', 'provenance': {
        'auditionWavSha256': file_hash(tmp_path/'selected.wav')}}]}
    (tmp_path/'report.json').write_text(json.dumps(row))
    assert completed_record(tmp_path, source) == row
    with pytest.raises(ValueError, match='source'):
        completed_record(tmp_path, {'sha256': 'other'})
    sf.write(tmp_path/'selected.wav', np.zeros(100, dtype=np.float32), 44100, subtype='PCM_16')
    with pytest.raises(ValueError, match='audio'):
        completed_record(tmp_path, source)


def test_pitch_guard_requires_two_agreeing_target_estimators():
    from neural_invert.temporal_eval import pitch_consensus
    assert pitch_consensus({'reliable': True, 'medianHz': 440., 'voicedFraction': .95},
                           {'medianHz': 442., 'voicedFraction': .95})
    assert not pitch_consensus({'reliable': True, 'medianHz': 440., 'voicedFraction': .95},
                               {'medianHz': 220., 'voicedFraction': .95})
    assert not pitch_consensus({'reliable': False, 'medianHz': None, 'voicedFraction': .1},
                               {'medianHz': 440., 'voicedFraction': .95})


def test_refinement_cannot_destroy_already_matched_pitch_or_motion():
    from neural_invert.temporal_eval import guard_accepts
    target = {'guardReliable': True, 'medianHz': 440., 'direction': 1}
    before = {'medianHz': 442., 'reliable': True, 'direction': 1}
    assert not guard_accepts(target, before, {'medianHz': 220., 'reliable': True, 'direction': 1})
    assert not guard_accepts(target, before, {'medianHz': 440., 'reliable': True, 'direction': -1})
    assert not guard_accepts(target, before, {'medianHz': None, 'reliable': False, 'direction': None})
    assert guard_accepts(target, before, {'medianHz': 438., 'reliable': True, 'direction': 1})
    assert guard_accepts({**target, 'guardReliable': False}, before,
                        {'medianHz': None, 'reliable': False, 'direction': None})


def test_metric_summary_does_not_count_unreliable_pitch_as_success():
    from neural_invert.temporal_eval import summarize_arm
    rows = [{'family': 'static', 'selected': {'score': .2, 'pitchComparison': {
        'absolutePitchErrorSemitones': None}}},
        {'family': 'static', 'selected': {'score': .3, 'pitchComparison': {
        'absolutePitchErrorSemitones': .5}}},
        {'family': 'moving', 'selected': {'score': .4, 'pitchComparison': {
        'directionMatches': False, 'contourErrorSemitones': 5.}}}]
    result = summarize_arm(rows)
    assert result['staticWithinOneSemitone'] == 1
    assert result['staticTotal'] == 2
    assert result['movingDirectionMatches'] == 0


def test_partial_candidate_budgets_remain_visible():
    from neural_invert.temporal_eval import proposal_accounting
    result = proposal_accounting(4, 2, 1)
    assert result == {'expected': 4, 'proposed': 2, 'rendered': 1,
                      'missingProposals': 2, 'failedRenders': 1, 'missingRendered': 3}


def test_nonfinite_refinement_score_never_replaces_incumbent(monkeypatch):
    from neural_invert import temporal_eval as module
    row = {'synth': 'Test', 'params': {}, 'seed': 1, 'wave': np.ones(4096, dtype=np.float32),
           'score': .5, 'provenance': {}}
    class Renderer:
        specs = {'Test': {}}
    monkeypatch.setattr(module, 'mutate_controls', lambda *a: {})
    monkeypatch.setattr(module, 'rendered_candidates', lambda *a: ([{**row, 'score': float('nan')}], []))
    result = module.refine_guarded(row, Renderer(), None, {'guardReliable': False}, budget=1)
    assert result['score'] == .5
    assert result['provenance']['refinement']['renderFailures'] == 1


def test_original_backend_records_running_renderer_executable():
    from neural_invert.temporal_gallery import backend_provenance
    from match.renderer import BfxrRenderer
    from neural_invert.data import file_hash
    from pathlib import Path
    with BfxrRenderer(jobs=1) as renderer:
        result = backend_provenance(renderer)
        assert result['sourceHash']
        assert result['files']
        for path, digest in result['files'].items():
            assert file_hash(Path(path)) == digest


def test_reference_copy_rejects_gallery_audio_changed_since_archival(tmp_path):
    import soundfile as sf
    from neural_invert.temporal_gallery import copy_reference
    from multisynth.coverage_feedback import _digest
    w = np.arange(100, dtype=np.int16)[:, None]
    sf.write(tmp_path/'reference.flac', w, 44100, subtype='PCM_16')
    sf.write(tmp_path/'target.wav', w, 44100, subtype='PCM_16')
    meta = {'file': 'reference.flac', 'sampleRate': 44100, 'frames': len(w), 'channels': 1,
            'pcmSha256': _digest(str((44100,w.shape)).encode()+w.astype('<i2').tobytes())}
    copy_reference(tmp_path/'target.wav', tmp_path/'copy.wav', tmp_path, meta)
    sf.write(tmp_path/'target.wav', w*2, 44100, subtype='PCM_16')
    with pytest.raises(ValueError, match='reference'):
        copy_reference(tmp_path/'target.wav', tmp_path/'changed.wav', tmp_path, meta)


def test_real_synth_target_replay_rejects_modified_wave():
    from neural_invert.temporal_eval import verify_target
    from neural_invert.benchmark import audio_hash
    from multisynth.renderer import Renderer
    with Renderer() as renderer:
        params, wave = renderer.render('Transfxr', renderer.specs['Transfxr']['defaults'], 32)
        row = {'sourceSynth': 'Transfxr', 'sourceParams': params, 'sourceSeed': 32,
               'sourceHash': renderer.inventory['sourceHash'], 'audioHash': audio_hash(wave)}
        verify_target(row, wave, renderer)
        with pytest.raises(ValueError, match='PCM'):
            verify_target(row, wave * .9, renderer)


def test_exported_new_candidate_replays_exactly_through_single_audition_transform(tmp_path):
    import soundfile as sf
    from neural_invert.temporal_gallery import save_candidate
    from neural_invert.experiment import audition_pcm
    from multisynth.renderer import Renderer
    from match.objective import MatchObjective
    with Renderer() as renderer:
        params, wave = renderer.render('Transfxr', renderer.specs['Transfxr']['defaults'], 123)
        row = {'synth': 'Transfxr', 'params': params, 'seed': 123, 'wave': wave,
               'score': 0., 'provenance': {}}
        result = save_candidate(tmp_path, row, renderer, MatchObjective(wave))
        decoded, rate = sf.read(tmp_path/result['file'], dtype='float32')
        assert rate == 44100
        assert np.array_equal(decoded, audition_pcm(wave))
        assert result['provenance']['actualRenderAudioHash']
        assert result['provenance']['auditionWavSha256']
