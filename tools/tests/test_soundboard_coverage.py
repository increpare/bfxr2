from pathlib import Path
import json
import numpy as np
import pytest

from multisynth.soundboard import BoardRenderer, choose_candidates

SNAPSHOT = Path(__file__).resolve().parents[1]/'multisynth/runs/soundboard-db9f5f8'


@pytest.mark.skipif(not SNAPSHOT.exists(),reason='Pinned Soundboard snapshot is local')
def test_soundboard_single_and_composite_replay():
    with BoardRenderer(SNAPSHOT) as renderer:
        entries = renderer.inventory['entries']
        assert entries and renderer.inventory['sourceHash']
        for entry in [next(e for e in entries if not e['composite']),
                      next(e for e in entries if e['composite'])]:
            a = renderer.sample(entry['verb'],entry['index'],1234)
            b = renderer.sample(entry['verb'],entry['index'],1234)
            assert a['params'] == b['params']
            params,wave = renderer.render(a['params'],1234)
            _,copy = renderer.render(params,1234)
            np.testing.assert_array_equal(wave,copy)
            assert np.isfinite(wave).all() and np.max(np.abs(wave)) > 0
            assert len(json.loads(params['sources'])) == (2 if entry['composite'] else 1)


def test_global_choice_does_not_use_tag_and_alternative_is_distinct():
    rows = [{'verb':'hit','entry':0,'signature':'A'}, {'verb':'coin','entry':0,'signature':'B'},
            {'verb':'hit','entry':1,'signature':'C'}]
    scores = np.array([.2,.1,.3])
    a = choose_candidates(rows,scores,'hit')
    b = choose_candidates(rows,scores,'coin')
    assert a['automatic'] == b['automatic'] == 1
    assert a['guided'] == 0
    assert len(set(a.values())) == len(a)
