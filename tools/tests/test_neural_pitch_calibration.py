"""Pitch calibration uses shipped DSP audio, bounded edits, and conservative selection."""
from copy import deepcopy
import importlib
import json

import numpy as np
import pytest
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, probe_controls
from neural_invert.pitch_v5_eval import descriptor_pitch


torch.set_num_threads(1)


def module():
    assert importlib.util.find_spec('neural_invert.pitch_calibration'), 'calibration component missing'
    return importlib.import_module('neural_invert.pitch_calibration')


@pytest.fixture(scope='module')
def renderer():
    with Renderer() as renderer:
        yield renderer


def controls(renderer, name, hz=220, gesture='stationary'):
    return probe_controls(renderer.specs[name], np.random.default_rng(11), hz, gesture)[0]


def candidate(name, params, seed=713):
    return dict(synth=name, params=params, seed=seed, provenance={'expert': 'frozen-v3'})


def tone(hz=440, length=44100):
    return (.4*np.sin(2*np.pi*hz*np.arange(length)/44100)).astype(np.float32)


@pytest.mark.parametrize('name', ['Bfxr', 'Transfxr', 'Pluckr'])
def test_register_math_immutable_schema_bounds(renderer, name):
    api = module()
    spec = renderer.specs[name]
    params = controls(renderer, name)
    before = deepcopy(params)
    moved = api.shift_register(name, params, 12, spec)
    key = 'frequency_start' if name == 'Bfxr' else 'pitch'
    assert params == before
    assert {k:v for k,v in moved.items() if k != key} == {k:v for k,v in before.items() if k != key}
    if name == 'Bfxr':
        assert (moved[key]**2+.001)/(params[key]**2+.001) == pytest.approx(2)
    elif name == 'Transfxr':
        assert moved[key]['start'] == pytest.approx(params[key]['start']+1/7)
        assert moved[key]['end'] == pytest.approx(params[key]['end']+1/7)
        assert moved[key]['curve'] == params[key]['curve']
        moved[key]['curve'] = 'test mutation'
        assert params == before
    else:
        assert moved[key] == pytest.approx(params[key]+.25)
    custom = deepcopy(spec)
    bound = next(p for p in custom['params'] if p['name'] == key)
    bound.update(min=.2, max=.4)
    for shift, expected in [(-10000, .2), (10000, .4)]:
        result = api.shift_register(name, params, shift, custom)[key]
        if isinstance(result, dict):
            assert result['start'] == result['end'] == expected
        else:
            assert result == expected
    json.dumps(api.POLICY, allow_nan=False)


@pytest.mark.parametrize('shift', [float('nan'), float('inf'), -float('inf')])
def test_invalid_shift(renderer, shift):
    with pytest.raises(ValueError):
        module().shift_register('Bfxr', renderer.specs['Bfxr']['defaults'], shift, renderer.specs['Bfxr'])


def test_unsupported_synth(renderer):
    with pytest.raises(ValueError):
        module().shift_register('unknown', {}, 1, renderer.specs['Bfxr'])


@pytest.mark.parametrize('name', ['Bfxr', 'Transfxr', 'Pluckr'])
def test_real_dsp_static_pitch_improves_with_exact_seed_and_pcm(renderer, name):
    api = module()
    target_params = controls(renderer, name, 440)
    _, target = renderer.render(name, target_params, 713)
    params = controls(renderer, name, 220)
    before = deepcopy(params)
    result = api.calibrate_candidate(candidate(name, params), target, renderer, MatchObjective(target))
    assert params == before
    assert result['accepted'], result
    original, final = result['original'], result['accepted'][-1]
    assert final['v5PitchComparison']['contourErrorSemitones'] < original['v5PitchComparison']['contourErrorSemitones']-5
    assert final['v5PitchComparison']['medianErrorSemitones'] < 1
    assert 1 <= len(result['attempts']) <= 3
    allowed = {'frequency_start','frequency_slide','frequency_acceleration','vibratoDepth','pitch_jump_amount','pitch_jump_2_amount'} if name == 'Bfxr' else {'pitch','vibrato'}
    for row in [original, *result['accepted']]:
        canonical, replay = renderer.render(name, row['params'], row['seed'])
        assert canonical == row['params']
        assert row['seed'] == 713
        assert audio_hash(replay) == row['audioHash'] == audio_hash(row['wave'])
        assert row['provenance']['expert'] == 'frozen-v3'
        assert np.isfinite(row['score'])
        assert {k:v for k,v in row['params'].items() if k not in allowed} == {k:v for k,v in original['params'].items() if k not in allowed}


def test_real_stationary_false_motion_initialization(renderer):
    api = module()
    params = controls(renderer, 'Transfxr', 330, 'rise')
    params['pitch']['curve'] = 'Smooth'
    params['vibrato']['curve'] = 'Ease In'
    _, target = renderer.render('Transfxr', controls(renderer, 'Transfxr', 440), 713)
    result = api.calibrate_candidate(candidate('Transfxr', params), target, renderer, MatchObjective(target))
    assert result['accepted']
    final = result['accepted'][-1]
    assert final['params']['pitch']['start'] == final['params']['pitch']['end']
    assert final['params']['pitch']['curve'] == 'Smooth'
    assert final['params']['vibrato'] == dict(start=0., end=0., curve='Ease In')
    assert final['v5PitchComparison']['spanErrorSemitones'] < .5


@pytest.mark.parametrize('name', ['Bfxr', 'Transfxr'])
def test_real_moving_target_preserves_motion_controls(renderer, name):
    api = module()
    params = controls(renderer, name, 220, 'rise')
    target_params = api.shift_register(name, params, 5, renderer.specs[name])
    _, target = renderer.render(name, target_params, 713)
    result = api.calibrate_candidate(candidate(name, params), target, renderer, MatchObjective(target))
    assert result['attempts']
    assert result['accepted']
    key = 'frequency_start' if name == 'Bfxr' else 'pitch'
    for attempt in result['attempts']:
        p = attempt['requestedParams']
        assert {k:v for k,v in p.items() if k != key} == {k:v for k,v in result['original']['params'].items() if k != key}
        if name == 'Transfxr':
            assert p[key]['end']-p[key]['start'] == pytest.approx(params[key]['end']-params[key]['start'])
            assert p[key]['curve'] == params[key]['curve']


def test_noise_target_retains_original_without_attempt(renderer):
    api = module()
    target = np.random.default_rng(7).normal(0,.2,44100).astype(np.float32)
    params = controls(renderer, 'Transfxr')
    result = api.calibrate_candidate(candidate('Transfxr', params), target, renderer, MatchObjective(target))
    assert result['accepted'] == result['attempts'] == []
    assert result['status'] == 'weak_target'
    selected = api.select_candidates([result['original']], [], target)
    assert selected['selected'] is selected['baseline']
    assert selected['selected']['audioHash'] == result['original']['audioHash']


class SequenceRenderer:
    """Fault-injection renderer; descriptors and scoring still inspect actual PCM."""
    def __init__(self, real, waves):
        self.specs = real.specs
        self.waves = list(waves)
        self.calls = []

    def render(self, synth, params, seed):
        self.calls.append((synth, deepcopy(params), seed))
        value = self.waves[min(len(self.calls)-1, len(self.waves)-1)]
        if isinstance(value, Exception):
            raise value
        return deepcopy(params), value.copy()


@pytest.mark.parametrize('bad', [np.zeros(44100, dtype=np.float32), np.array([np.nan]), np.array([], dtype=np.float32), ValueError('DSP failure')])
def test_invalid_original_raises(renderer, bad):
    api = module()
    fake = SequenceRenderer(renderer, [bad])
    with pytest.raises(ValueError):
        api.calibrate_candidate(candidate('Transfxr', controls(renderer, 'Transfxr')), tone(), fake, MatchObjective(tone()))
    assert len(fake.calls) == 1


@pytest.mark.parametrize('bad,reason', [(np.zeros(44100, dtype=np.float32), 'silent_audio'),
    (ValueError('DSP failure'), 'render_error'), (RuntimeError('worker closed'), 'render_error'),
    (tone(220), 'duplicate_audio'), (tone(440, 46000), 'duration_changed')])
def test_rejected_render_keeps_original_and_stops(renderer, bad, reason):
    api = module()
    fake = SequenceRenderer(renderer, [tone(220), bad])
    result = api.calibrate_candidate(candidate('Transfxr', controls(renderer, 'Transfxr')), tone(), fake, MatchObjective(tone()))
    assert len(fake.calls) == 2
    assert not result['accepted']
    assert result['status'] == reason
    attempt = result['attempts'][0]
    assert not attempt['accepted'] and attempt['reason'] == reason
    assert attempt['requestedParams'] and attempt['seed'] == 713
    assert audio_hash(result['original']['wave']) == audio_hash(tone(220))
    if reason == 'render_error':
        assert attempt['error'] and attempt['canonicalParams'] is None
    else:
        assert attempt['canonicalParams'] and attempt['audioHash'] == audio_hash(bad)


def test_unexpected_render_bug_propagates(renderer):
    api = module()
    fake = SequenceRenderer(renderer, [tone(220), TypeError('programming bug')])
    with pytest.raises(TypeError, match='programming bug'):
        api.calibrate_candidate(candidate('Transfxr', controls(renderer, 'Transfxr')), tone(), fake, MatchObjective(tone()))


def test_unreliable_candidate_preserved(renderer):
    api = module()
    noise = np.random.default_rng(91).normal(0,.1,44100).astype(np.float32)
    fake = SequenceRenderer(renderer, [noise])
    result = api.calibrate_candidate(candidate('Transfxr', controls(renderer, 'Transfxr')), tone(), fake, MatchObjective(tone()))
    assert result['status'] == 'unreliable_candidate'
    assert not result['attempts'] and not result['accepted']


def test_already_correct_static_stops_without_render(renderer):
    api = module()
    fake = SequenceRenderer(renderer, [tone(440)])
    result = api.calibrate_candidate(candidate('Transfxr', controls(renderer, 'Transfxr', 440)), tone(), fake, MatchObjective(tone()))
    assert not result['attempts']
    assert result['status'] == 'tiny_offset'
    assert len(fake.calls) == 1


def test_small_median_offset_does_not_skip_false_motion(renderer):
    api = module()
    t = np.arange(44100)/44100
    hz = 440*2**(.8*np.sin(2*np.pi*4*t)/12)
    wavering = (.4*np.sin(2*np.pi*np.cumsum(hz)/44100)).astype(np.float32)
    params = controls(renderer, 'Transfxr', 440)
    params['vibrato'].update(start=.12, end=.12)
    fake = SequenceRenderer(renderer, [wavering, tone()])
    result = api.calibrate_candidate(candidate('Transfxr', params), tone(), fake, MatchObjective(tone()))
    assert result['attempts'][0]['mode'] == 'stationary_initialization'
    assert result['accepted']


def test_selection_refreshes_stale_scores_and_evidence():
    api = module()
    objective = MatchObjective(tone())
    rows = [dict(candidate('Transfxr', {}, i), wave=tone(hz), score=score,
                 audioHash='stale', v5Pitch={}, v5PitchComparison={})
            for i,hz,score in [(1,440,999999), (2,220,-999999)]]
    result = api.select_candidates(rows, [], tone())
    assert result['baseline']['seed'] == result['selected']['seed'] == 1
    assert result['selected']['score'] == pytest.approx(objective.score(tone()))
    assert result['selected']['audioHash'] == audio_hash(tone())
    assert rows[0]['score'] == 999999
    assert result['eligibility'][1]['eligible'] is False


def test_no_eligible_selection_returns_exact_baseline():
    api = module()
    original = dict(candidate('Transfxr', {'pitch': .2}), wave=tone(220), score=-900)
    result = api.select_candidates([original], [], tone())
    assert result['selected'] is result['baseline']
    assert result['selected']['params'] == original['params']
    assert np.array_equal(result['selected']['wave'], original['wave'])
    assert result['reason'] == 'no_eligible_candidates'


def test_all_target_active_frames_count_in_selection():
    api = module()
    wave = tone()
    noise = np.random.default_rng(773).normal(0,.15,13230).astype(np.float32)
    wave[:6615] = noise[:6615]
    wave[-6615:] = noise[6615:]
    row = dict(candidate('Transfxr', {}), wave=wave)
    result = api.select_candidates([row], [], tone())
    comparison = result['eligibility'][0]['v5PitchComparison']
    assert comparison['activeFrameWithinOneSemitoneFraction'] < .75
    assert comparison['activeFramesWithinOneSemitone']/comparison['targetActiveFrames'] == comparison['activeFrameWithinOneSemitoneFraction']
    assert result['selected'] is result['baseline']
    assert not result['eligibility'][0]['eligible']


def test_invalid_accepted_audio_has_unambiguous_pool_index():
    api = module()
    original = dict(candidate('Transfxr', {}), wave=tone(220))
    accepted = [dict(candidate('Transfxr', {}), wave=np.zeros(100)),
                dict(candidate('Transfxr', {}), wave=tone())]
    result = api.select_candidates([original], accepted, tone())
    records = [r for r in result['eligibility'] if r['pool'] == 'accepted']
    assert sorted(r['index'] for r in records) == [0,1]
    assert result['selected']['audioHash'] == audio_hash(tone())


def pitch_evidence(offsets, active=None):
    """Explicit relative-time evidence to isolate threshold decisions, not DSP claims."""
    offsets = np.asarray(offsets, dtype=float)
    active = np.ones(48, dtype=bool) if active is None else np.asarray(active)
    voiced = np.isfinite(offsets) & active
    hz = 440*np.exp2(offsets/12)
    ids = np.flatnonzero(voiced)
    delta = float(np.median(offsets[ids[-3:]])-np.median(offsets[ids[:3]]))
    return dict(reliable=bool(voiced.sum() >= 3 and voiced.sum()/active.sum() >= .6),
        voicedFraction=float(voiced.sum()/active.sum()), activeFrames=int(active.sum()),
        voicedFrames=int(voiced.sum()), activeMask=active.tolist(), voicedMask=voiced.tolist(),
        contourHz=[float(h) if v else None for h,v in zip(hz,voiced)],
        contourTime=np.linspace(0,1,48).tolist(), medianHz=float(np.median(hz[voiced])),
        spanSemitones=float(np.ptp(offsets[voiced])), startToEndSemitones=delta,
        direction=1 if delta > .5 else -1 if delta < -.5 else 0)


def bind_descriptors(monkeypatch, api, entries):
    evidence = {audio_hash(wave): pitch_evidence(offsets) for wave,offsets in entries}
    monkeypatch.setattr(api, 'descriptor_pitch', lambda wave: deepcopy(evidence[audio_hash(wave)]))


@pytest.mark.parametrize('old,new,reason', [
    ([-12]*48, [0]*44+[np.nan]*4, 'voiced_pairs_decreased'),
    ([-12]*48, list(np.linspace(-1,1,48)), 'span_worsened'),
    ([.5]*44+[4]*4, [0]*38+[2]*10, 'active_fraction_decreased'),
    ([-2]*48, [-1.995]*48, 'no_contour_improvement'),
])
def test_acceptance_rejects_pitch_regressions(renderer, monkeypatch, old, new, reason):
    api = module()
    target, original, proposal = tone(440), tone(220), tone(330)
    bind_descriptors(monkeypatch, api, [(target,[0]*48),(original,old),(proposal,new)])
    fake = SequenceRenderer(renderer, [original, proposal])
    result = api.calibrate_candidate(candidate('Transfxr', controls(renderer,'Transfxr')), target, fake, MatchObjective(target))
    assert result['status'] == reason
    assert result['attempts'][0]['reason'] == reason
    assert not result['accepted']
    assert len(fake.calls) == 2


@pytest.mark.parametrize('new,reason', [
    ([.09]*48, 'baseline_contour_error'),
    ([0]*47+[.4], 'baseline_span_error'),
    ([.2]*47+[1.1], 'baseline_active_fraction'),
])
def test_selection_preserves_reliable_baseline(renderer, monkeypatch, new, reason):
    api = module()
    target, baseline_wave, adjusted_wave = tone(440), tone(220), tone(330)
    bind_descriptors(monkeypatch, api, [(target,[0]*48),(baseline_wave,[0]*48),(adjusted_wave,new)])
    original = dict(candidate('Transfxr', {}), wave=baseline_wave)
    accepted = dict(candidate('Transfxr', {}), wave=adjusted_wave)
    result = api.select_candidates([original], [accepted], target)
    adjusted_record = next(r for r in result['eligibility'] if r['pool'] == 'accepted')
    assert adjusted_record['reason'] == reason
    assert result['selected'] is result['baseline']


def test_maximum_three_renders_and_working_row_advances(renderer, monkeypatch):
    api = module()
    target = tone()
    waves = [tone(hz) for hz in (110,220,330,400)]
    bind_descriptors(monkeypatch, api, [(target, list(np.linspace(0,4,48))),
        *[(wave,list(np.linspace(offset,offset+4,48))) for wave,offset in zip(waves,(-9,-7,-5,-3))]])
    fake = SequenceRenderer(renderer, waves)
    result = api.calibrate_candidate(candidate('Transfxr', controls(renderer,'Transfxr',110,'rise')), target, fake, MatchObjective(target))
    assert len(fake.calls) == 4
    assert len(result['attempts']) == len(result['accepted']) == 3
    assert result['additionalRenderCount'] == 3
    assert sum(a['renderCount'] for a in result['attempts']) == 3
    assert all(a['rendered'] for a in result['attempts'])
    assert result['status'] == 'step_limit'
    for index, row in enumerate(result['accepted']):
        assert row['provenance']['pitchCalibration']['parentAudioHash'] == audio_hash(waves[index])
        assert row['seed'] == 713
    starts = [call[1]['pitch']['start'] for call in fake.calls]
    assert starts[1]-starts[0] == pytest.approx(9/84)
    assert starts[2]-starts[1] == pytest.approx(7/84)
    assert starts[3]-starts[2] == pytest.approx(5/84)


@pytest.mark.parametrize('steps', [-1,4,1.5,True])
def test_invalid_budget_makes_no_render(renderer, steps):
    api = module()
    fake = SequenceRenderer(renderer, [tone(220)])
    with pytest.raises(ValueError, match='max_steps'):
        api.calibrate_candidate(candidate('Transfxr', controls(renderer,'Transfxr')), tone(), fake, MatchObjective(tone()), steps)
    assert fake.calls == []


def test_moving_register_offset_clamped_and_bounds_stop(renderer, monkeypatch):
    api = module()
    target, original = tone(), tone(220)
    bind_descriptors(monkeypatch, api, [(target,list(np.linspace(0,4,48))),
                                       (original,list(np.linspace(-36,-32,48)))])
    fake = SequenceRenderer(renderer, [original, original])
    params = controls(renderer,'Transfxr')
    result = api.calibrate_candidate(candidate('Transfxr',params),target,fake,MatchObjective(target))
    assert result['attempts'][0]['offsetSemitones'] == 24
    assert fake.calls[1][1]['pitch']['start']-fake.calls[0][1]['pitch']['start'] == pytest.approx(24/84)
    params['pitch'].update(start=1.,end=1.)
    fake = SequenceRenderer(renderer,[original])
    result = api.calibrate_candidate(candidate('Transfxr',params),target,fake,MatchObjective(target))
    assert result['status'] == 'bounds_unchanged'
    assert len(fake.calls) == 1


def test_nonfinite_scores_rejected_without_hiding_objective_bugs(renderer):
    api = module()
    class Scores:
        def __init__(self, values): self.values = iter(values)
        def score_batch(self, waves):
            value = next(self.values)
            if isinstance(value, Exception): raise value
            return [value]
    row = candidate('Transfxr',controls(renderer,'Transfxr'))
    with pytest.raises(ValueError, match='nonfinite_score'):
        api.calibrate_candidate(row,tone(),SequenceRenderer(renderer,[tone(220)]),Scores([np.nan]))
    result = api.calibrate_candidate(row,tone(),SequenceRenderer(renderer,[tone(220),tone()]),Scores([1,np.nan]))
    assert result['status'] == 'nonfinite_score' and not result['accepted']
    with pytest.raises(RuntimeError, match='objective bug'):
        api.calibrate_candidate(row,tone(),SequenceRenderer(renderer,[tone(220),tone()]),Scores([1,RuntimeError('objective bug')]))


def test_silent_target_is_weak_and_preserves_audible_baseline(renderer):
    api = module()
    target = np.zeros(44100,dtype=np.float32)
    fake = SequenceRenderer(renderer,[tone(220)])
    result = api.calibrate_candidate(candidate('Transfxr',controls(renderer,'Transfxr')),target,fake,MatchObjective(target))
    assert result['status'] == 'weak_target'
    assert not result['attempts']
    selection = api.select_candidates([result['original']],[],target)
    assert selection['selected'] is selection['baseline']
    assert selection['reason'] == 'weak_target'


@pytest.mark.parametrize('name', ['Bfxr','Transfxr','Pluckr'])
def test_stationary_initialization_changes_only_declared_pitch_head(renderer, name):
    api = module()
    params = deepcopy(renderer.specs[name]['defaults'])
    if name == 'Bfxr':
        params.update(frequency_start=.2,frequency_slide=.1,frequency_acceleration=.2,
            vibratoDepth=.3,pitch_jump_amount=.1,pitch_jump_2_amount=-.1,
            repeatSpeed=.2,squareDuty=.3,min_frequency_relative_to_starting_frequency=.4)
        allowed = {'frequency_start','frequency_slide','frequency_acceleration','vibratoDepth','pitch_jump_amount','pitch_jump_2_amount'}
    elif name == 'Transfxr':
        params['pitch'] = dict(start=.2,end=.4,curve='Bounce')
        params['vibrato'] = dict(start=.1,end=.3,curve='Pulse')
        allowed = {'pitch','vibrato'}
    else:
        params.update(pitch=.2,vibrato=.3,strings=5,inharmonic=.4,tremolo=.3)
        allowed = {'pitch','vibrato'}
    before = deepcopy(params)
    fake = SequenceRenderer(renderer,[tone(220),tone()])
    result = api.calibrate_candidate(candidate(name,params),tone(),fake,MatchObjective(tone()))
    assert result['accepted']
    p = result['accepted'][0]['params']
    assert params == before
    assert {k:v for k,v in p.items() if k not in allowed} == {k:v for k,v in before.items() if k not in allowed}
    if name == 'Bfxr':
        assert p['frequency_start'] == pytest.approx(np.sqrt(440/3528-.001),abs=1e-5)
        assert all(p[k] == 0 for k in allowed-{'frequency_start'})
    elif name == 'Transfxr':
        assert p['pitch']['start'] == p['pitch']['end'] == pytest.approx(np.log2(440/40)/7,abs=1e-5)
        assert p['pitch']['curve'] == 'Bounce'
        assert p['vibrato'] == dict(start=0.,end=0.,curve='Pulse')
    else:
        assert p['pitch'] == pytest.approx(.75,abs=1e-5) and p['vibrato'] == 0


def test_duration_tolerance_uses_original_not_previous_acceptance(renderer, monkeypatch):
    api = module()
    target, original, first, second = tone(), tone(110), tone(220,44761), tone(330,45423)
    bind_descriptors(monkeypatch,api,[(target,list(np.linspace(0,4,48))),
        (original,list(np.linspace(-9,-5,48))),(first,list(np.linspace(-6,-2,48))),
        (second,list(np.linspace(-3,1,48)))])
    fake = SequenceRenderer(renderer,[original,first,second])
    result = api.calibrate_candidate(candidate('Transfxr',controls(renderer,'Transfxr',110,'rise')),target,fake,MatchObjective(target))
    assert len(result['accepted']) == 1
    assert result['status'] == 'duration_changed'
    assert len(result['attempts']) == 2
    assert audio_hash(result['accepted'][0]['wave']) == audio_hash(first)


@pytest.mark.parametrize('kind', ['weak_fraction','few_target_frames','few_aligned_pairs'])
def test_strong_target_and_alignment_thresholds(renderer, monkeypatch, kind):
    api = module()
    target, original = tone(),tone(220)
    target_pitch = pitch_evidence([0]*48)
    original_pitch = pitch_evidence([-12]*48)
    if kind == 'weak_fraction':
        target_pitch = pitch_evidence([0]*38+[np.nan]*10)
    elif kind == 'few_target_frames':
        target_pitch = pitch_evidence([0]*15+[np.nan]*33,[True]*15+[False]*33)
    else:
        original_pitch = pitch_evidence([-12]*15+[np.nan]*33,[True]*15+[False]*33)
    monkeypatch.setattr(api,'descriptor_pitch',lambda wave: deepcopy(target_pitch if audio_hash(wave)==audio_hash(target) else original_pitch))
    result = api.calibrate_candidate(candidate('Transfxr',controls(renderer,'Transfxr')),target,SequenceRenderer(renderer,[original]),MatchObjective(target))
    assert result['status'] == ('unreliable_candidate' if kind == 'few_aligned_pairs' else 'weak_target')
    assert not result['attempts'] and not result['accepted']


def test_motion_direction_mismatch_is_ineligible(monkeypatch):
    api = module()
    target, wrong = tone(),tone(220)
    bind_descriptors(monkeypatch,api,[(target,list(np.linspace(-.4,.4,48))),
                                    (wrong,list(np.linspace(.4,-.4,48)))])
    result = api.select_candidates([dict(candidate('Transfxr',{}),wave=wrong)],[],target)
    assert result['eligibility'][0]['reason'] == 'direction_mismatch'
    assert result['selected'] is result['baseline']


def test_partial_clamp_retains_raw_control_and_residual_evidence(renderer, monkeypatch):
    api = module()
    target, original = tone(), tone(220)
    bind_descriptors(monkeypatch,api,[(target,list(np.linspace(0,4,48))),
                                    (original,list(np.linspace(-12,-8,48)))])
    params = controls(renderer,'Transfxr')
    params['pitch'].update(start=.95,end=.5)
    fake = SequenceRenderer(renderer,[original,original])
    result = api.calibrate_candidate(candidate('Transfxr',params),target,fake,MatchObjective(target))
    attempt = result['attempts'][0]
    assert attempt['rawOffsetSemitones'] == pytest.approx(12)
    assert attempt['offsetSemitones'] == pytest.approx(12)
    assert attempt['clamps'] == [dict(control='pitch.start',requested=pytest.approx(.95+1/7),
                                    applied=1.,min=0,max=1)]
    assert attempt['requestedParams']['pitch']['end'] == pytest.approx(.5+1/7)
    assert attempt['rendered'] is True and attempt['renderCount'] == 1
    assert result['additionalRenderCount'] == 1


def test_wholly_bounded_adjustment_recorded_without_render(renderer, monkeypatch):
    api = module()
    target, original = tone(), tone(220)
    bind_descriptors(monkeypatch,api,[(target,list(np.linspace(0,4,48))),
                                    (original,list(np.linspace(-36,-32,48)))])
    params = controls(renderer,'Transfxr')
    params['pitch'].update(start=1.,end=1.)
    fake = SequenceRenderer(renderer,[original])
    result = api.calibrate_candidate(candidate('Transfxr',params),target,fake,MatchObjective(target))
    assert len(result['attempts']) == 1
    attempt = result['attempts'][0]
    assert attempt['reason'] == result['status'] == 'bounds_unchanged'
    assert attempt['rawOffsetSemitones'] == pytest.approx(36)
    assert attempt['offsetSemitones'] == 24
    assert attempt['requestedParams'] == params
    assert len(attempt['clamps']) == 2
    assert all(c['requested'] == pytest.approx(1+24/84) and c['applied'] == 1 for c in attempt['clamps'])
    assert attempt['rendered'] is False and attempt['renderCount'] == 0
    assert result['additionalRenderCount'] == 0 and len(fake.calls) == 1
    assert attempt['canonicalParams'] is None and attempt['audioHash'] is None
    assert not attempt['accepted'] and not result['accepted']
    json.dumps(attempt,allow_nan=False)


@pytest.mark.parametrize('returned_wave',[tone(220),tone(440)])
def test_canonical_control_duplicate_explicit_even_with_duplicate_audio(renderer, returned_wave):
    api = module()
    params = controls(renderer,'Transfxr')
    class CanonicalDuplicate(SequenceRenderer):
        def render(self,synth,requested,seed):
            _,wave = super().render(synth,requested,seed)
            return deepcopy(params),wave
    fake = CanonicalDuplicate(renderer,[tone(220),returned_wave])
    result = api.calibrate_candidate(candidate('Transfxr',params),tone(),fake,MatchObjective(tone()))
    attempt = result['attempts'][0]
    assert attempt['duplicateCanonicalParams'] is True
    assert attempt['duplicateAudio'] is (audio_hash(returned_wave)==audio_hash(tone(220)))
    assert attempt['reason'] == result['status'] == 'duplicate_canonical_params'
    assert not result['accepted']
    assert attempt['renderCount'] == result['additionalRenderCount'] == 1
    assert len(fake.calls) == 2


@pytest.mark.parametrize('name',['Bfxr','Transfxr','Pluckr'])
def test_extreme_finite_register_shifts_remain_json_finite(renderer,name):
    api = module()
    for offset in (-np.finfo(float).max,np.finfo(float).max):
        moved = api.shift_register(name,controls(renderer,name),offset,renderer.specs[name])
        json.dumps(moved,allow_nan=False)
        key = 'frequency_start' if name == 'Bfxr' else 'pitch'
        values = [moved[key][s] for s in ('start','end')] if name=='Transfxr' else [moved[key]]
        assert all(value == (0 if offset < 0 else 1) for value in values)


@pytest.mark.parametrize('name,expected', [
    ('Bfxr',np.sqrt((.95**2+.001)*2-.001)),('Pluckr',1.2)])
def test_scalar_register_clamp_retains_unbounded_value(renderer,monkeypatch,name,expected):
    api = module()
    target,original = tone(),tone(220)
    bind_descriptors(monkeypatch,api,[(target,list(np.linspace(0,4,48))),
                                    (original,list(np.linspace(-12,-8,48)))])
    params = controls(renderer,name)
    key = 'frequency_start' if name == 'Bfxr' else 'pitch'
    params[key] = .95
    result = api.calibrate_candidate(candidate(name,params),target,
        SequenceRenderer(renderer,[original,original]),MatchObjective(target))
    clamp = result['attempts'][0]['clamps'][0]
    assert clamp == dict(control=key,requested=pytest.approx(expected),applied=1.,min=0,max=1)
    json.dumps(clamp,allow_nan=False)


def test_stationary_initialization_clamp_retains_nominal_request(renderer):
    api = module()
    target = tone(1760)
    result = api.calibrate_candidate(candidate('Pluckr',controls(renderer,'Pluckr')),target,
        SequenceRenderer(renderer,[tone(220),tone(880)]),MatchObjective(target))
    clamp = result['attempts'][0]['clamps'][0]
    assert clamp == dict(control='pitch',requested=pytest.approx(1.25,abs=1e-4),applied=1.,min=0,max=1)


def test_failed_render_counts_against_additional_render_budget(renderer):
    api = module()
    result = api.calibrate_candidate(candidate('Transfxr',controls(renderer,'Transfxr')),tone(),
        SequenceRenderer(renderer,[tone(220),ValueError('DSP failure')]),MatchObjective(tone()))
    assert result['additionalRenderCount'] == 1
    attempt = result['attempts'][0]
    assert attempt['rendered'] is True and attempt['renderCount'] == 1
    assert attempt['reason'] == 'render_error'
    assert attempt['duplicateCanonicalParams'] is None and attempt['duplicateAudio'] is None
