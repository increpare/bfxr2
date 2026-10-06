"""Representation-level invariants, independent of human preference labels."""
import numpy as np
import torch
from multisynth.support_objective import SupportObjective,analysis_support

torch.set_num_threads(1)

def tone(hz=440,seconds=.15):
    t=np.arange(round(44100*seconds))/44100
    return (.4*np.sin(2*np.pi*hz*t)*np.sin(np.pi*t/seconds)**2).astype(np.float32)

def test_appended_zeros_do_not_improve_or_degrade_a_match():
    target=tone();other=tone(670);obj=SupportObjective(target)
    baseline=obj.score(other)
    assert baseline>.1
    for seconds in (1,4):
        padded=np.pad(other,(0,seconds*44100))
        assert np.array_equal(analysis_support(other),analysis_support(padded))
        assert abs(obj.score(padded)-baseline)<1e-7
    assert abs(SupportObjective(np.pad(target,(0,44100))).score(other)-baseline)<1e-7

def test_support_preserves_onset_and_late_audible_events():
    target=tone();late=np.r_[target,np.zeros(4410),tone()]
    obj=SupportObjective(target)
    assert obj.score(late)>obj.score(target)+.1
    delayed=np.r_[np.zeros(4410),target]
    assert np.all(analysis_support(delayed)[:4410]==0)
    assert obj.score(delayed)>obj.score(target)+.1

def test_quiet_pcm_floor_does_not_extend_support_and_input_unchanged():
    wave=np.r_[tone(),np.full(44100,-1/32768)].astype(np.float32);before=wave.copy()
    result=analysis_support(wave)
    assert len(result)<.2*44100
    assert np.array_equal(before,wave)
    assert np.array_equal(analysis_support(np.zeros(12)),analysis_support(np.zeros(4000)))
