from copy import deepcopy
import pytest
import torch


def test_expansion_preserves_donor_and_first_prediction_but_breaks_symmetry():
    from neural_invert.coverage_mixture import expand_expert
    from neural_invert.temporal import TemporalExpert
    from multisynth.renderer import Renderer
    with Renderer() as renderer:
        spec = deepcopy(renderer.specs['Transfxr'])
    torch.manual_seed(12)
    base = TemporalExpert(spec, 1, 'flat').eval()
    original = deepcopy(base.state_dict())
    expanded = expand_expert(base, seed=24)
    same = expand_expert(base, seed=24)
    x = torch.randn(3, 4083)
    a, b = base(x), expanded(x)
    torch.testing.assert_close(a['continuous'][:, 0], b['continuous'][:, 0], rtol=0, atol=0)
    for p, q in zip(a['categorical'], b['categorical']):
        torch.testing.assert_close(p[:, 0], q[:, 0], rtol=0, atol=0)
    assert all(not torch.equal(b['continuous'][:, 0], b['continuous'][:, i]) for i in range(1, 4))
    assert torch.equal(b['mode_logits'], torch.zeros(3, 4))
    for key, value in original.items():
        assert torch.equal(base.state_dict()[key], value)
    for key, value in expanded.state_dict().items():
        assert torch.equal(same.state_dict()[key], value)
    with pytest.raises(ValueError): expand_expert(expanded)


def test_validation_sums_weighted_likelihood_and_unweighted_responsibility():
    from neural_invert.coverage_mixture import energy_statistics
    energy = torch.tensor([[0., 1.], [2., 0.]])
    logits = torch.zeros_like(energy)
    weights = torch.tensor([.5, 1.5])
    stats = energy_statistics(energy, logits, weights)
    expected = -.1 * torch.logsumexp(logits.log_softmax(-1) - energy/.1, -1)
    assert stats['lossSum'] == pytest.approx(float((expected*weights).sum()))
    assert stats['bestEnergySum'] == 0
    assert sum(stats['responsibilitySum']) == pytest.approx(2)
    assert stats['winnerCounts'] == [1, 1]
    with pytest.raises(ValueError): energy_statistics(energy, logits, torch.tensor([-1., 1.]))


def test_expanded_model_all_heads_receive_finite_training_gradients():
    from neural_invert.coverage_mixture import expand_expert
    from neural_invert.temporal import TemporalExpert, acoustic_energy, mixture_loss
    from neural_invert.schema import ControlSchema
    from multisynth.renderer import Renderer
    with Renderer() as renderer: spec = deepcopy(renderer.specs['Transfxr'])
    model = expand_expert(TemporalExpert(spec, 1, 'flat'))
    continuous, categorical = ControlSchema(spec).encode(spec['defaults'])
    labels = dict(continuous=torch.tensor(continuous)[None].repeat(2, 1),
                  categorical=torch.tensor(categorical)[None].repeat(2, 1))
    pred = model(torch.randn(2, 4083))
    loss, _ = mixture_loss(acoustic_energy(pred, labels, spec), pred['mode_logits'])
    loss.backward()
    for head in model.numeric_heads:
        assert torch.isfinite(head.weight.grad).all() and head.weight.grad.abs().sum() > 0


def test_fresh_targets_exclude_prior_and_training_groups_and_deduplicate():
    from neural_invert.coverage_mixture_eval import fresh_targets
    rows=[dict(parameterHash=h, params={'i':i}, seed=i, audioHash=str(i))
          for i,h in enumerate(['training','previous','fresh','fresh','another'])]
    meta=dict(rows=rows,splits=dict(oldTrain=[0],newTrain=[],newVal=[1,2,3,4]))
    selected=fresh_targets(meta,{'previous'},2,123)
    assert {r['parameterHash'] for r in selected}=={'fresh','another'}
    assert selected==fresh_targets(meta,{'previous'},2,123)
    with pytest.raises(ValueError): fresh_targets(meta,{'previous'},3,123)
    meta['splits']['newVal'].append(0)
    with pytest.raises(ValueError): fresh_targets(meta,{'previous'},2,123)


def test_summary_retains_failures_without_scoring_missing_comparators_as_wins():
    from neural_invert.coverage_mixture_eval import summarize
    candidate=dict(score=2., pitchComparison=dict(medianErrorSemitones=None))
    row=dict(target=dict(group='other-synth'), targetPitch=dict(reliable=False),
             selected=dict(baseline=candidate,single=None,mixture=candidate),
             numericDiversity=dict(baseline=1,single=0,mixture=4))
    result=summarize([row])['other-synth']
    assert result['single']['missing']==1
    assert result['mixture']['pairedWithSingle']==0
    assert result['mixture']['winsOverSingle']==0
    assert result['mixture']['pairedWithBaseline']==1
