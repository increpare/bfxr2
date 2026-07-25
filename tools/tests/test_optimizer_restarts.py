import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import OptimizeSettings, StagedOptimizer


class _FakeRenderer:
    """Encodes each param dict as a vector so scores depend on the unit."""

    def render_batch(self, params_list, seeds=0):
        return [
            np.array([p[k] for k in sorted(p)], dtype=np.float64)
            for p in params_list
        ]


class _FakeObjective:
    target_len = 44100

    def __init__(self, dim):
        self.opt = np.full(dim, 0.3)

    def score_batch(self, waves):
        return np.array(
            [float(np.sum((w - self.opt[: len(w)]) ** 2)) for w in waves]
        )


BUDGET = 20000  # far more than a smooth quadratic basin can absorb


def _opt(**kw) -> StagedOptimizer:
    space = ParamSpace()
    settings = OptimizeSettings(
        budget=BUDGET, verbose=False, wave_types=[0], arp_seeds=False, **kw
    )
    # +2: params_dict() adds "waveType" and "masterVolume" on top of
    # space.names, and the fake renderer encodes every key (sorted), so the
    # rendered vector is 2 longer than space.names.
    obj = _FakeObjective(len(space.names) + 2)
    return StagedOptimizer(space, _FakeRenderer(), obj, settings, target=None)


def test_plain_run_leaves_budget_unspent():
    """Precondition for the whole probe: without restarts, CMA converges and
    stops well short of a large budget."""
    opt = _opt()
    opt.run()
    assert opt.evals < 0.5 * BUDGET


def test_restarts_spend_the_budget():
    opt = _opt(restarts=True)
    opt.run()
    assert opt.evals >= 0.9 * BUDGET


def test_restarts_never_score_worse_at_equal_budget():
    plain = _opt()
    plain_best = min(plain.run()).score
    restarted = _opt(restarts=True)
    restarted_best = min(restarted.run()).score
    assert restarted_best <= plain_best + 1e-12


def test_restart_loop_terminates_when_cma_cannot_spend():
    """Guard against an infinite loop if a restart evaluates nothing."""
    opt = _opt(restarts=True)
    calls = {"n": 0}

    def _noop(start, max_iters, *, popsize=None, cma_seed=None):
        calls["n"] += 1

    opt._run_cma = _noop
    opt.s.budget = 10**9
    opt._run_restarts([0])
    assert calls["n"] <= 2  # bails as soon as a restart makes no progress


def test_restarts_off_does_not_invoke_the_loop():
    opt = _opt()

    def _boom(wave_types):
        raise AssertionError("_run_restarts must not run when restarts=False")

    opt._run_restarts = _boom
    opt.run()  # must not raise
