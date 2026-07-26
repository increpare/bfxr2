# Handoff — inverse model / WAV→bfxr (2026-07-25)

Pass this to a cold agent. Do **not** re-litigate closed bets without new evidence.

## Where to work

| Item | Value |
| --- | --- |
| Branch | `feature/inverse-model-structure-metric` |
| Tip (at handoff) | `>= e3f3834` (scored headroom results) |
| Repo | `/Users/stephenlavelle/Documents/bfxr2` |
| Tools cwd | `cd tools && uv run …` / `PYTHONPATH=.` |
| Baseline ckpt | `.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt` |
| Surrogate ckpt | `.worktrees/inverse-model-next/tools/invert/runs/surrogate/surrogate.pt` |

**Checkout check:** if you land on `master`/`main`, you will **not** see `tools/invert/refine.py` or the 2026-07-25 docs. Switch to the branch above.

Other worktree (older line): `.worktrees/inverse-model-next` on `feature/inverse-model-next-steps` — holds training runs / v7 artifacts; not required for match-only work if checkpoints are reachable via the paths above.

## Read first — headroom verdict: REACHABILITY CEILING

The completed 100x-budget probe selects the next project. Do not start from the
older multi-hypothesis suggestion.

- Seeded held-out objective improved only **+3.2%** on the real hard slice
  versus **+46.9%** on reachable in-domain controls. The real/in-domain floor
  ratio grew **1.328 → 2.420**.
- At the measured 200 000-evaluation endpoint, `big_unseeded` was slightly
  better in objective than `big_seeded` (2.2877 vs 2.3441 median); at 2 000
  evaluations seeded was also slightly worse (2.4226 vs 2.3891). The current
  seed did not improve hard-slice median quality at either endpoint.
  Time-to-quality was not measured, so no speed benefit was established.
- Single-listener blind scores were `baseline_seeded` mean/median
  **2.80/3.00**, `big_seeded` **2.35/1.75** with **0 wins / 6 ties / 4 losses**,
  and `big_unseeded` **2.30/1.50** with **2/3/5**. The sole 5/5 was an isolated
  `big_unseeded` cursor win.
- The **metric ceiling did not fire** because its >=10% objective-improvement
  precondition was not met. For this one listener on the ten-target slice,
  100x did not show a general audible gain; the listen does not reopen
  objective work.

Consequences: multi-hypothesis seeding is de-selected as the next project
because it does not address the pre-registered median reachability result, a
sharper surrogate remains deprioritized, and **synth capability /
pairs-of-sounds is selected next**. This finite-endpoint result does not prove
that a learned seed could never find an unobserved basin; reopen seeding only
with new evidence that seed quality is binding. It is also not a claim that
every target is unreachable: Throw and Break Brick showed seeded objective
reductions, and a shipping budget around 10k is candidate objective upside
only after a separate listen gate.

One `big_unseeded` White-noise candidate severely overfit its render seed
(2.6120 search score vs 10.6469 held-out). `avg_seeds=1` is a live risk for
White noise, especially at larger budgets; do not treat the other held-out
ties as proof that render-seed overfit is generally absent.

Full evidence:
`docs/superpowers/plans/2026-07-25-headroom-probe-results.md`.

## Product goal (locked)

**Mode C:** optimize **seed + short search** first; treat one-shot as a bonus / path toward “feels instant.”  
Pure one-shot matching seeded quality is **not** the near-term bar (hard-slice one-shot ~1–1.5/5 vs seeded often 3–4/5).

Capability expansion supports this product mode by widening what seed + short
search can reach; it does not replace Mode C with a different fitting mode.

Strategy essay: `docs/superpowers/plans/2026-07-25-inverse-model-next-bets.md`

## What already works (do not forget)

- **Seeded search** is where the impressive results are (Gate B: Throw/leeneBell/cursor 3–4/5).
- **Pitch-jump arp seeding** (earlier on the branch) drives discrete-note wins — **not** the structure metric.
- **v7 real FT** is the best relative one-shot baseline vs v6 (ears 20–12), still far from product-ready absolute quality.
- In-domain bfxr presets / spectral training machinery work; OOD real SFX is the hard regime.

## Closed negative results (do not retry as-is)

### 1. Sound-level `structure_pitch` in the match objective — Gate B FAILED

- Probes: mild 8/14 → **14/14** (engineering win).
- Hard-slice listen: baseline vs candidate **identical on 9/10**; no audible win.
- Doc: `docs/superpowers/plans/2026-07-24-gate-a-results.md` §7.
- **Shipping default:** `FeatureWeights.structure_pitch = 0.0`.
- Opt-in: `--structure-objective` (replaces old `--legacy-objective` polarity).
- Probes still force the term on (`match.structure_probes`).

### 2. Test-time Adam refine through `SurrogateSynth` — listen FAILED

- Implemented and wired; default **off**.
- Hard-slice ears: refined mean **1.32** vs raw **1.55**; `mario 2 - jump` → **0** (mute/trash).
- MatchObjective also worse on all 10 refined one-shots.
- Doc: `docs/superpowers/plans/2026-07-25-test-time-refine-results.md`.
- CLI: `--surrogate-refine-steps` / `--surrogate-refine-lr` / `--surrogate`  
  (**Not** `--refine-steps` — that is Stage 3 FD steepest descent.)
- Code kept: `tools/invert/refine.py`, match/eval_targets wiring, `tools/match/listen_refine_compare.py`.
- Listen page artifact: `tools/invert/runs/tt_refine_listen.html` (gitignored runs/).

**Do not** burn another cycle retuning lr/steps for bet (1) without a new theory (e.g. much better surrogate). Plan said: on fail → leave default 0, move on.

### 3. Multi-hypothesis seeding — DE-SELECTED by headroom

- This was the former bet (2), not an implemented failure.
- At the 200 000-evaluation endpoint plus restarts, `big_unseeded` had a
  slightly lower objective than `big_seeded` (2.2877 vs 2.3441 median).
- At 2 000 evaluations, seeded was also slightly worse (2.4226 vs 2.3891).
- Thus the current seed did not improve hard-slice median quality at either
  measured endpoint. The probe did not compare matched time-to-quality, so it
  established no speed benefit.
- This de-selects multi-hypothesis seeding as the next project because it does
  not address the pre-registered median reachability result. It does not prove
  every possible learned seed would fail to find an unobserved basin.
- Reopen only with new evidence that seed quality is binding.

## What a retrain would *not* learn from this branch

Structure metric + test-time refine are **search/eval-time**. They do not change training data, labels, or loss. Retrain only if you change the **training** side again.

v5 data / v7 trains already happened (structured sampler, retro, cull, real FT). Results: `docs/superpowers/plans/2026-07-24-inverse-model-data-retrain-results.md`.

## Selected next project

**(4) Synth capability / pairs-of-sounds.**

The headroom probe measured the missing premise for capability work: the
existing search still improves substantially on reachable in-domain controls
at 100x budget, while the real hard-slice median barely moves. The next project
should expand the reachable sound set.

New work must start with **brainstorm → design → implementation plan**. This
handoff intentionally does not choose a synth extension, pairing scheme,
segmentation strategy, or model architecture.

**(3) Sharper surrogate → real-FT** remains deprioritized. Bet (1) showed the
current surrogate gradient hurts hard-slice one-shots, and headroom showed
the current seed did not improve median quality at the measured endpoints.

## Key files on this branch

| Path | Role |
| --- | --- |
| `docs/superpowers/plans/2026-07-25-inverse-model-next-bets.md` | Strategy + ranked bets + decision log |
| `docs/superpowers/plans/2026-07-25-headroom-probe-results.md` | **Authoritative REACHABILITY CEILING verdict**, arm/objective/listen evidence, render-seed risk |
| `docs/superpowers/specs/2026-07-25-headroom-probe-design.md` | Pre-registered ceiling decision rule and scope |
| `docs/superpowers/plans/2026-07-25-headroom-probe.md` | Headroom implementation and run plan (historical) |
| `docs/superpowers/plans/2026-07-25-test-time-refine-results.md` | Bet (1) FAIL listen table |
| `docs/superpowers/specs/2026-07-25-inverse-model-test-time-refine-design.md` | Bet (1) design (historical) |
| `docs/superpowers/plans/2026-07-25-inverse-model-test-time-refine.md` | Bet (1) implementation plan |
| `docs/superpowers/plans/2026-07-24-gate-a-results.md` | Structure-metric Gate A/B FAIL |
| `tools/invert/refine.py` | Test-time refine (default unused) |
| `tools/match/match.py` | `--seed-model`, `--one-shot`, `--surrogate-refine-*`, Stage 3 `--refine-steps` |
| `tools/match/structure.py` / `structure_probes.py` | Structure term (default weight 0) |
| `tools/match/listen_compare.py` | Gate B baseline vs candidate page |
| `tools/match/listen_refine_compare.py` | Raw vs refined vs seeded page |
| `tools/match/headroom.py` | Four-arm real/control headroom driver and held-out rescoring |
| `tools/invert/predict.py` | `predict_wave` top‑k seeds |
| `tools/invert/surrogate.py` | `SurrogateSynth` |

## Hard-slice targets (listen gate set)

From `match.listen_compare.HARD_SLICE`:

`Mario 1 - Jump`, `Mario 2 - Throw`, `Mario 3 - jump (nes)`, `Mario 3 - jump (snes)`, `Mario Break Brick`, `mario 2 - jump`, `mega_man_ii_one-up`, `mega_man_iii_cursor`, `mega_man_ii_beam-out`, `chrono_trigger_leeneBell`

## Claims discipline

- **Engineering gates** (probes, MSE drop) ≠ **claim gates** (human listen on hard slice).
- Metric deltas alone must not declare improvement (synth FT already fooled one-shot medians vs ears).
- Prefer A/B listen pages with scores hidden.

## Immediate agent TODO (if continuing)

1. Confirm branch tip `>= e3f3834` (scored headroom results).
2. Read `2026-07-25-headroom-probe-results.md` and
   `2026-07-25-inverse-model-next-bets.md` end-to-end.
3. **Brainstorm → design → plan** the selected **synth capability /
   pairs-of-sounds** project. Do not jump straight into code or pre-select an
   architecture from this handoff.
4. Confirm with the human whether to begin that new project on a fresh branch
   after integrating this results branch.

## Out of scope unless human asks

- Re-enabling `structure_pitch` by default
- Enabling `--surrogate-refine-steps` by default
- Shipping the ~10k budget candidate without its own listen gate
- Enabling `restarts` by default or otherwise changing shipping search defaults
- Changing `avg_seeds` defaults without a separate design and listen gate
- Reopening multi-hypothesis seeding without evidence that the seed is binding
- Another 500k→1M data ladder with the same recipe
- Retraining “because Gate B / refine failed”
