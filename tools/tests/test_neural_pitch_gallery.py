"""Regression checks for the short listening experiment's immutable baselines."""
import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from neural_invert import pitch_gallery as gallery
from neural_invert.data import file_hash
from neural_invert.experiment import audition_pcm, listening_history

ROOT = Path(__file__).resolve().parents[1] / 'multisynth'
ARCHIVES = [ROOT/'listening_data'/f'2026-10-04-{n}-quick-01' for n in ('neural-v2', 'temporal-v3')]
OLD = ROOT/'runs/temporal-v3-listening'


@pytest.fixture(scope='module')
def historical():
    return listening_history(ARCHIVES)


def test_charm_keeps_both_heard_winners_without_claiming_transfxr_lost(historical):
    source = next(t for t in json.loads((ROOT/'evaluations/pitch-v4-listening-targets.json').read_text())['targets']
                  if 'charm2' in t['name'])
    chosen = gallery.baseline_observations(historical, source)
    assert [(role, obs['candidate']['synth']) for role, obs in chosen] == [('previous', 'Bfxr'), ('anchor', 'Transfxr')]
    latest, earlier = [obs for _, obs in chosen]
    assert latest['archive'] == ARCHIVES[1]
    assert earlier['archive'] == ARCHIVES[0]
    latest_choice = latest['target']['choice']
    trans_id = next(c['id'] for c in latest['target']['candidates'] if c['role'] == 'previous')
    assert trans_id not in latest_choice['auditionedCandidateIds']
    with pytest.raises(ValueError, match='Transfxr anchor'):
        gallery.baseline_observations({source['sha256']: [latest]}, source)


def test_archived_pcm_is_copied_exactly_and_aliases_keep_provenance(tmp_path, historical):
    source = next(t for t in json.loads((ROOT/'evaluations/pitch-v4-listening-targets.json').read_text())['targets']
                  if t['tag'] == 'bird')
    role, obs = gallery.baseline_observations(historical, source)[0]
    card = gallery.copy_observation(tmp_path, role, obs)
    samples, rate = sf.read(tmp_path/card['file'], dtype='int16')
    expected, expected_rate = sf.read(obs['archive']/obs['candidate']['audio']['file'], dtype='int16')
    assert rate == expected_rate == 44100
    assert np.array_equal(samples, expected)
    assert gallery.pcm_hash(tmp_path/card['file']) == obs['candidate']['audio']['pcmSha256']
    alias = {**card, 'role': 'original', 'label': 'Original Bfxr'}
    cards = gallery.deduplicate_cards(tmp_path, [card, alias])
    assert len(cards) == 1
    assert cards[0]['provenance']['identicalPcmAliases'][0]['role'] == 'original'


def test_fresh_output_rejected_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match='Fresh output'):
        gallery.run('missing', 'missing', 'missing', [], tmp_path)


def test_target_requires_source_and_old_wav_integrity(tmp_path):
    source = tmp_path/'source.wav'
    sf.write(source, np.array([0.1, -.2, .3], np.float32), 44100, subtype='PCM_16')
    old = tmp_path/'old'; (old/'006').mkdir(parents=True)
    target = old/'006/target.wav'; target.write_bytes(source.read_bytes())
    row = {'folder': '006', 'source': {'path': str(source), 'sha256': file_hash(source)}}
    bindings = {'006': file_hash(target)}
    dest = tmp_path/'copy.wav'
    gallery.copy_target(old, row, dest, {}, bindings)
    assert dest.read_bytes() == target.read_bytes()
    sf.write(target, np.zeros(3), 44100, subtype='PCM_16')
    with pytest.raises(ValueError, match='reference WAV'):
        gallery.copy_target(old, row, dest, {}, bindings)
    source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='Frozen source'):
        gallery.copy_target(old, row, dest, {}, bindings)


def test_seed_uses_old_folder_not_new_order():
    assert gallery.refinement_seed('005', 'Bfxr') == 20261011 + 4*1009
    assert gallery.refinement_seed('002', 'Pluckr') == 20261011 + 1009 + 2*71


def test_selected_audio_uses_exactly_one_audition_transform(tmp_path):
    wave = np.sin(np.arange(2048, dtype=np.float32)*.2)*.731
    class FakeRenderer:
        inventory = {'sourceHash': 'test-dsp'}
        def render(self, synth, params, seed):
            return params, wave.copy()
    class Objective:
        def score_batch(self, waves):
            return [float(np.abs(w).sum()) for w in waves]
    row = {'synth': 'Bfxr', 'params': {'pitch': .2}, 'seed': 4,
           'wave': wave, 'score': 1.0, 'provenance': {}}
    saved = gallery.save_candidate(tmp_path, row, FakeRenderer(), Objective())
    decoded, _ = sf.read(tmp_path/saved['file'], dtype='float32')
    assert np.array_equal(decoded, audition_pcm(wave))
    assert saved['provenance']['auditionWavSha256'] == file_hash(tmp_path/saved['file'])


def test_render_attempts_keep_controls_errors_and_actual_hash():
    class FakeRenderer:
        specs = {}; inventory = {'sourceHash': 'test'}
        def render(self, synth, params, seed):
            if seed == 2:
                raise RuntimeError('failed DSP')
            return {**params, 'canonical': True}, np.array([.1, -.1], dtype=np.float32)
    audit = gallery.RecordingRenderer(FakeRenderer())
    audit.render('Bfxr', {'pitch': 3}, 1)
    with pytest.raises(RuntimeError):
        audit.render('Bfxr', {'pitch': 4}, 2)
    assert len(audit.attempts) == 2
    assert audit.attempts[0]['params']['canonical'] is True
    assert audit.attempts[0]['audioHash']
    assert audit.attempts[1]['requestedParams'] == {'pitch': 4}
    assert audit.attempts[1]['error'] == 'failed DSP'


@pytest.mark.parametrize('counts,silent_engines', [
    ((4, 4, 4), ()), ((4, 0, 2), ()), ((4, 4, 4), ('Transfxr',)),
    ((4, 4, 4), gallery.ENGINES),
])
def test_gallery_pipeline_exports_bound_audio_and_exact_trial_budgets(tmp_path, monkeypatch, counts, silent_engines):
    from multisynth.coverage_feedback import export_coverage, coverage_model
    wave = np.sin(np.arange(2048, dtype=np.float32)*.19)*.2
    old = tmp_path/'old'; folder = old/'006'; folder.mkdir(parents=True)
    sf.write(folder/'target.wav', wave, 44100, subtype='PCM_16')
    sf.write(folder/'original.wav', wave*.3, 44100, subtype='PCM_16')
    source = {'name': 'fixture.wav', 'path': str(folder/'target.wav'),
              'sha256': file_hash(folder/'target.wav'), 'previouslyRatedReference': False}
    old_card = {'role': 'original', 'label': 'Original Bfxr', 'file': 'original.wav',
                'sourceHash': 'old-dsp', 'params': {'gain': .3}, 'seed': 77, 'synth': 'Bfxr',
                'provenance': {'auditionWavSha256': file_hash(folder/'original.wav')}}
    export_coverage(old, [{'folder': '006', 'source': source, 'candidates': [old_card]}], {})
    targets = tmp_path/'targets.json'; targets.write_text(json.dumps({'targets': [source]}))
    class FakeRenderer:
        inventory = {'sourceHash': 'new-dsp'}
        specs = {e: {'params': [{'name': 'gain', 'type': 'KNOB', 'min': .01, 'max': 1}]} for e in gallery.ENGINES}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def render(self, synth, params, seed):
            return params, wave*np.float32(0 if synth in silent_engines else params['gain'])
    class Objective:
        def __init__(self, wave): pass
        def score_batch(self, waves): return [float(np.sum(w*w)) for w in waves]
    models = {e: (None, {'sourceHash': 'new-dsp', 'checkpointHash': e+'-checkpoint'}) for e in gallery.ENGINES}
    guesses = [{'synth': e, 'params': {'gain': .5+i*.1}, 'seed': 20261010, 'provenance': {'mode': i}}
               for e, count in zip(gallery.ENGINES, counts) for i in range(count)]
    monkeypatch.setattr(gallery, 'load_experts', lambda *a: (models, None))
    monkeypatch.setattr(gallery, 'proposals', lambda *a: guesses)
    monkeypatch.setattr(gallery, 'Renderer', FakeRenderer)
    monkeypatch.setattr(gallery, 'MatchObjective', Objective)
    output = tmp_path/'new'
    audible_counts = [0 if e in silent_engines else n for e, n in zip(gallery.ENGINES, counts)]
    if not any(audible_counts):
        with pytest.raises(ValueError, match='No audible'):
            gallery.run(targets, tmp_path/'model', old, [], output, budget=3)
        failed = json.loads((output/'001/failed-generation.json').read_text())
        assert len(failed['failures']) == 12
        assert len(failed['renderAttempts']) == 12
        assert all(a['failedRenders'] == 4 for a in failed['accounting'].values())
        assert not (output/'index.html').exists()
        assert not json.loads((output/'manifest.json').read_text())['complete']
        return
    result = gallery.run(targets, tmp_path/'model', old, [], output, budget=3)
    report = json.loads((output/'results.json').read_text())
    row = report['results'][0]; diag = row['diagnostics']
    assert len(diag['allRaw']) == sum(audible_counts)
    assert len(diag['allRefined']) == sum(n > 0 for n in audible_counts)
    assert diag['refinementAttemptsByEngine'] == {e: 3 if n else 0 for e, n in zip(gallery.ENGINES, audible_counts)}
    for e, count in zip(gallery.ENGINES, counts):
        assert diag['accounting'][e]['missingProposals'] == 4-count
        assert diag['accounting'][e]['failedRenders'] == (count if e in silent_engines else 0)
        assert diag['refinementStatus'][e] == ('completed' if count and e not in silent_engines else 'skipped-no-audible-proposal')
    assert diag['refinementSeeds']['Bfxr'] == 20261011+5*1009
    assert len(row['candidates']) == 2
    assert (output/'001/target.wav').read_bytes() == (folder/'target.wav').read_bytes()
    assert (output/'001/original.wav').read_bytes() == (folder/'original.wav').read_bytes()
    assert report['metadata']['complete']
    assert report['metadata']['proposalSeed'] == 20261010
    assert 'multisynth/quick_audio.js' in report['metadata']['codeHashes']
    assert coverage_model(output, report['results'], report['metadata'])['experimentId'] == result['experimentId']
    altered = json.loads(json.dumps(report)); altered['metadata']['checkpointHashes']['Bfxr'] = 'different'
    assert coverage_model(output, altered['results'], altered['metadata'])['experimentId'] != result['experimentId']
    assert 'window.BfxrQuickChoice' in (output/'index.html').read_text()
    with pytest.raises(ValueError, match='Fresh output'):
        gallery.run(targets, tmp_path/'model', old, [], output, budget=3)
