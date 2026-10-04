"""Actual-render provenance and budget checks for the input ablation."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf


def test_failed_source_engine_does_not_hide_unrestricted_output(tmp_path):
    from multisynth.renderer import Renderer
    from neural_invert.pitch_eval import evaluate_candidates
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
    from neural_invert.pitch_eval import evaluate_candidates
    class NeverRender:
        def render(self, *args):
            raise AssertionError('must validate first')
    row = dict(synth='Bfxr', params={}, seed=1, provenance={})
    with pytest.raises(ValueError, match='budget'):
        evaluate_candidates([row, row], np.ones(3000), 'Bfxr', 'native', NeverRender(), tmp_path/'out', count=1)
    assert not (tmp_path/'out').exists()
