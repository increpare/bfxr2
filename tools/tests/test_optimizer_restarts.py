import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import (
    ARP_EXTRA_BUDGET_FRACTION,
    NO_PROGRESS_RESTART_LIMIT,
    OptimizeSettings,
    StagedOptimizer,
)


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


def _opt(budget: int = BUDGET, **kw) -> StagedOptimizer:
    space = ParamSpace()
    settings = OptimizeSettings(
        budget=budget, verbose=False, wave_types=[0], arp_seeds=False, **kw
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
    """Guard against an infinite loop if every restart evaluates nothing."""
    opt = _opt(restarts=True)
    calls = {"n": 0}

    def _noop(start, max_iters, *, popsize=None, cma_seed=None):
        calls["n"] += 1

    opt._run_cma = _noop
    opt.s.budget = 10**9
    opt._run_restarts([0])
    # bails after NO_PROGRESS_RESTART_LIMIT *consecutive* barren restarts
    assert calls["n"] == NO_PROGRESS_RESTART_LIMIT


def test_one_barren_restart_does_not_abandon_the_budget():
    """A single restart whose CMA stops at initialisation must not end the
    loop: bailing there left most of a 200000 budget unspent, which is exactly
    the early-stopping artifact the probe exists to rule out."""
    opt = _opt(restarts=True)
    opt.s.budget = 10**9
    calls = {"n": 0}

    def _spotty(start, max_iters, *, popsize=None, cma_seed=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return  # barren restart: evaluates nothing
        opt.evals += 10  # subsequent restarts spend fine
        if calls["n"] >= 6:
            opt.s.budget = 0  # stop the loop via the budget, not the guard

    opt._run_cma = _spotty
    opt._run_restarts([0])
    assert calls["n"] >= 6
    assert opt.evals >= 50


def test_a_barren_restart_between_productive_ones_resets_the_counter():
    opt = _opt(restarts=True)
    opt.s.budget = 10**9
    calls = {"n": 0}
    # barren, barren, productive, barren, barren, productive, then 3 barren
    pattern = [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1]

    def _patterned(start, max_iters, *, popsize=None, cma_seed=None):
        i = calls["n"]
        calls["n"] += 1
        if i < len(pattern) and pattern[i]:
            opt.evals += 10

    opt._run_cma = _patterned
    opt._run_restarts([0])
    # stops at index 8 (the third consecutive barren restart), i.e. 9 calls;
    # the two earlier barren pairs must not have ended the loop
    assert calls["n"] == 9


def test_restarts_off_does_not_invoke_the_loop():
    opt = _opt()

    def _boom(wave_types):
        raise AssertionError("_run_restarts must not run when restarts=False")

    opt._run_restarts = _boom
    opt.run()  # must not raise


# --- arp allowance vs restarts: identical treatment across arms -----------


def _stage_budgets(budget: int, restarts: bool) -> dict:
    """Budget ceiling each post-stage-2 stage sees, and the order they run."""
    opt = _opt(budget=budget, restarts=restarts)
    opt.arp_units = [np.full(opt.space.dim, 0.5)]  # pretend arp was detected
    seen: dict = {"order": []}

    def _fake_restarts(wave_types):
        seen["order"].append("restarts")
        seen["restarts"] = opt.s.budget

    def _fake_arp(wave_types):
        seen["order"].append("arp")
        seen["arp"] = opt.s.budget

    opt._run_restarts = _fake_restarts
    opt._run_arp_stage = _fake_arp
    opt.run()
    seen["final_budget"] = opt.s.budget
    return seen


def test_restarts_run_before_the_arp_stage():
    """If arp went first it could eat its 1.5x allowance and leave the restart
    loop already out of budget -- so an arp-detected target would silently get
    no restarts at all."""
    seen = _stage_budgets(200000, restarts=True)
    assert seen["order"] == ["restarts", "arp"]


def test_restarts_spend_against_the_plain_budget_and_arp_gets_extra_on_top():
    seen = _stage_budgets(200000, restarts=True)
    assert seen["restarts"] == 200000
    assert seen["arp"] == 200000 + int(ARP_EXTRA_BUDGET_FRACTION * 200000)
    assert seen["final_budget"] == 200000  # restored after the arp stage


def test_arms_keep_the_intended_100x_ratio_on_arp_targets():
    """Both probe arms must get the same treatment at every stage: main
    pipeline up to `budget`, then arp's additive allowance on top."""
    base = _stage_budgets(2000, restarts=False)
    big = _stage_budgets(200000, restarts=True)
    assert base["order"] == ["arp"]  # restarts=False path untouched
    assert base["arp"] == 3000
    assert big["arp"] == 300000
    assert big["arp"] / base["arp"] == 100


def test_main_pipeline_is_bit_identical_with_and_without_the_arp_stage():
    """Load-bearing invariant: arp runs on ADDITIONAL budget AFTER the main
    pipeline, so the main result is identical to running with arp off and the
    final result is min(main, arp) -- provably no regression."""
    plain = _opt(restarts=True)
    plain.run()

    with_arp = _opt(restarts=True)
    with_arp.arp_units = [np.full(with_arp.space.dim, 0.5)]
    mark: dict = {}

    def _spy(wave_types):
        mark["evals"] = with_arp.evals
        mark["best"] = min(with_arp.archive).score

    with_arp._run_arp_stage = _spy
    with_arp.run()

    assert mark["evals"] == plain.evals
    assert mark["best"] == min(plain.archive).score


from match.match import build_parser


def test_restarts_flag_defaults_off():
    args = build_parser().parse_args(["x.wav", "-o", "out"])
    assert args.restarts is False


def test_restarts_flag_can_be_enabled():
    args = build_parser().parse_args(["x.wav", "-o", "out", "--restarts"])
    assert args.restarts is True
