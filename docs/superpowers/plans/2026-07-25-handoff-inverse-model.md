# Handoff — inverse model / WAV→bfxr (2026-07-25)

Pass this to a cold agent. Do **not** re-litigate closed bets without new evidence.

## Where to work

| Item | Value |
| --- | --- |
| Branch | `feature/inverse-model-structure-metric` |
| Tip (at handoff) | `88b6dba` |
| Repo | `/Users/stephenlavelle/Documents/bfxr2` |
| Tools cwd | `cd tools && uv run …` / `PYTHONPATH=.` |
| Baseline ckpt | `.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt` |
| Surrogate ckpt | `.worktrees/inverse-model-next/tools/invert/runs/surrogate/surrogate.pt` |

**Checkout check:** if you land on `master`/`main`, you will **not** see `tools/invert/refine.py` or the 2026-07-25 docs. Switch to the branch above.

Other worktree (older line): `.worktrees/inverse-model-next` on `feature/inverse-model-next-steps` — holds training runs / v7 artifacts; not required for match-only work if checkpoints are reachable via the paths above.

## Product goal (locked)

**Mode C:** optimize **seed + short search** first; treat one-shot as a bonus / path toward “feels instant.”  
Pure one-shot matching seeded quality is **not** the near-term bar (hard-slice one-shot ~1–1.5/5 vs seeded often 3–4/5).

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

## What a retrain would *not* learn from this branch

Structure metric + test-time refine are **search/eval-time**. They do not change training data, labels, or loss. Retrain only if you change the **training** side again.

v5 data / v7 trains already happened (structured sampler, retro, cull, real FT). Results: `docs/superpowers/plans/2026-07-24-inverse-model-data-retrain-results.md`.

## Suggested next bet

**(2) Multi-hypothesis seeding** — from next-bets:

- Emit top‑K diverse param/wavetype hypotheses (beyond today’s `predict_wave` top‑k), score with existing `MatchObjective`, keep best as CMA seed (and/or one-shot pick).
- Attacks ill-posed inverse / mode collapse; fits mode C (search already does the heavy lifting).
- Literature pointer: generative / multi-modal param prediction (e.g. ISMIR 2025 flow-matching / Param2Tok style); practically start cheaper (dropout, noise, or score all top‑k renders) before a full generative head.

**(3) Sharper surrogate → real-FT** — deprioritized until a proxy proves useful at inference; bet (1) argues the current surrogate gradient **hurts** hard-slice one-shots.

Also still true from older next-directions: synth capability ceiling on unreachable timbres; length/envelope issues partly mitigated elsewhere.

## Key files on this branch

| Path | Role |
| --- | --- |
| `docs/superpowers/plans/2026-07-25-inverse-model-next-bets.md` | Strategy + ranked bets + decision log |
| `docs/superpowers/plans/2026-07-25-test-time-refine-results.md` | Bet (1) FAIL listen table |
| `docs/superpowers/specs/2026-07-25-inverse-model-test-time-refine-design.md` | Bet (1) design (historical) |
| `docs/superpowers/plans/2026-07-25-inverse-model-test-time-refine.md` | Bet (1) implementation plan |
| `docs/superpowers/plans/2026-07-24-gate-a-results.md` | Structure-metric Gate A/B FAIL |
| `tools/invert/refine.py` | Test-time refine (default unused) |
| `tools/match/match.py` | `--seed-model`, `--one-shot`, `--surrogate-refine-*`, Stage 3 `--refine-steps` |
| `tools/match/structure.py` / `structure_probes.py` | Structure term (default weight 0) |
| `tools/match/listen_compare.py` | Gate B baseline vs candidate page |
| `tools/match/listen_refine_compare.py` | Raw vs refined vs seeded page |
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

1. Confirm branch tip ≥ `88b6dba`.
2. Read `2026-07-25-inverse-model-next-bets.md` end-to-end.
3. **Brainstorm → design → plan** for bet **(2) multi-hypothesis seeding** (do not jump straight into code).
4. Or ask the human whether to park / PR-merge this branch as “negative results + disabled defaults” before starting (2).

## Out of scope unless human asks

- Re-enabling `structure_pitch` by default
- Enabling `--surrogate-refine-steps` by default
- Another 500k→1M data ladder with the same recipe
- Retraining “because Gate B / refine failed”
