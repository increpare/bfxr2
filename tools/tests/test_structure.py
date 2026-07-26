import math

import torch

from match.features import Features
from match.structure import (
    COUNT_W,
    DIR_W,
    PENALTY_CAP,
    StructureSummary,
    pitch_structure_penalty,
    summarize,
)


def _features(hzs, per=10, voiced=True):
    """Single-row Features with a piecewise-flat pitch track."""
    values = [math.log2(hz) for hz in hzs for _ in range(per)]
    f0 = torch.tensor([values], dtype=torch.float32)
    n = f0.shape[1]
    on = torch.ones(1, n, dtype=torch.bool)
    return Features(
        env_db=torch.zeros(1, n),
        f0_log2=f0,
        voiced=on if voiced else torch.zeros(1, n, dtype=torch.bool),
        active=on,
        centroid_log2=torch.zeros(1, n),
        noisiness=torch.zeros(1, n),
    )


def test_summarize_counts_notes_and_first_interval():
    s = summarize(_features([400, 600, 900]))
    assert s.note_count == 3
    assert s.first_interval_st > 0
    assert abs(s.first_interval_st - 12 * math.log2(600 / 400)) < 0.5


def test_summarize_reports_no_notes_for_a_single_tone():
    assert summarize(_features([440], per=30)).note_count == 0


def test_identical_structure_is_free():
    s = summarize(_features([400, 600]))
    assert pitch_structure_penalty(s, s) == 0.0


def test_two_note_target_penalizes_a_structureless_candidate():
    target = summarize(_features([400, 600]))
    gliss = summarize(_features([440], per=30))
    assert gliss.note_count == 0
    assert pitch_structure_penalty(target, gliss) == PENALTY_CAP


def test_wrong_direction_costs_the_direction_weight():
    target = summarize(_features([400, 600]))
    flipped = summarize(_features([600, 400]))
    assert pitch_structure_penalty(target, flipped) == DIR_W


def test_glide_target_penalizes_invented_jumps():
    glide = StructureSummary(note_count=0, first_interval_st=0.0, voiced_frac=1.0)
    jumpy = summarize(_features([400, 600]))
    assert pitch_structure_penalty(glide, jumpy) == COUNT_W


def test_unpitched_target_disables_the_term():
    noise = StructureSummary(note_count=0, first_interval_st=0.0, voiced_frac=0.0)
    jumpy = summarize(_features([400, 600, 900]))
    assert pitch_structure_penalty(noise, jumpy) == 0.0


def test_penalty_is_bounded():
    target = summarize(_features([400, 600, 900]))
    worst = StructureSummary(note_count=0, first_interval_st=0.0, voiced_frac=1.0)
    assert 0.0 <= pitch_structure_penalty(target, worst) <= PENALTY_CAP


def test_structure_pitch_weight_gates_the_term():
    """FeatureWeights.structure_pitch defaults to 0.0 (off — it failed the
    2026-07-25 listen gate) but the term stays fully recoverable by setting
    the weight back to nonzero; this pins that mechanism."""
    import numpy as np

    from match.features import FeatureWeights
    from match.objective import MatchObjective
    from match.renderer import BfxrRenderer

    params_target = dict(waveType=2, frequency_start=0.30,
                         pitch_jump_amount=0.61, pitch_jump_onset_percent=0.5,
                         sustainTime=0.6, decayTime=0.15)
    params_gliss = dict(waveType=2, frequency_start=0.30,
                        frequency_slide=0.10, sustainTime=0.6, decayTime=0.15)
    with BfxrRenderer() as renderer:
        target = renderer.render(params_target, seed=1234)
        gliss = renderer.render(params_gliss, seed=1234)

    default = MatchObjective(target)
    enabled = MatchObjective(target, weights=FeatureWeights(structure_pitch=1.0))
    assert default.score_components(gliss)["structure_pitch"] == 0.0
    assert enabled.score_components(gliss)["structure_pitch"] > 0.0
    assert default.score(gliss) < enabled.score(gliss)
    assert np.isclose(
        default.score(gliss),
        enabled.score(gliss) - enabled.score_components(gliss)["structure_pitch"],
    )
