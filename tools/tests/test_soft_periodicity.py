import numpy as np
import torch
from multisynth.soft_periodicity import SoftPeriodicityObjective
from match.objective import MatchObjective

def tone(hz,duration=.3):
    t=np.arange(round(44100*duration))/44100
    return (.45*np.sin(2*np.pi*hz*t)*np.minimum(t/.01,1)*np.minimum((duration-t)/.02,1)).astype(np.float32)

def test_near_identity_archive_does_not_lose_to_faded_attack():
    import soundfile as sf
    from pathlib import Path
    import json
    root=Path(__file__).resolve().parents[1]/'multisynth/listening_data/2026-10-05-cue-calibration-quick-01'
    m=json.loads((root/'manifest.json').read_text())
    target=next(t for t in m['targets'] if t['source']['name']=='footstep/footstep_wood_000.ogg')
    ids={c['id'] for c in target['candidates']}
    options={c['params']['operation']:c for c in m['candidates'] if c['id'] in ids}
    x,_=sf.read(root/target['referenceAudio']['file'],dtype='float32')
    a,_=sf.read(root/options['attack-fade']['audio']['file'],dtype='float32')
    b,_=sf.read(root/options['lowpass']['audio']['file'],dtype='float32')
    old=MatchObjective(x);new=SoftPeriodicityObjective(x)
    assert old.score(b)>old.score(a)
    assert new.score(b)<.05 and new.score(b)<new.score(a)

def test_preserves_pitch_discrimination_and_self_identity():
    torch.set_num_threads(1)
    for hz in [110,440,1600,3200]:
        ref=tone(hz);o=SoftPeriodicityObjective(ref)
        assert o.score(ref)<1e-6
        assert o.score(tone(hz*1.25))>o.score(tone(hz*1.001))+.1

def test_sweep_direction_and_batch_invariance():
    t=np.arange(16000)/44100
    up=(.4*np.sin(2*np.pi*(300*t+900*t*t))).astype(np.float32)
    near=up+np.random.default_rng(4).normal(0,1e-5,len(up)).astype(np.float32)
    down=up[::-1].copy();o=SoftPeriodicityObjective(up)
    assert o.score(near)<o.score(down)
    np.testing.assert_allclose(o.score_batch([near,down]),[o.score(near),o.score(down)],atol=1e-5)


def test_legacy_cache_cannot_silently_use_old_pitch_loss():
    import pytest
    o=SoftPeriodicityObjective(tone(440))
    with pytest.raises(NotImplementedError):o.precompute_candidates([tone(440)])
    with pytest.raises(NotImplementedError):o.score_candidates(None)
