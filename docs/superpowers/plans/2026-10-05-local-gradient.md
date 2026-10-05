# Local gradient diagnostic implementation plan

Execute inline using the existing plan-execution workflow.

**Goal:** Determine whether a frozen Transfxr surrogate gives safe local descent
directions on 32 new development cases, before inverse audio fine-tuning.

**Architecture:** An isolated gradient helper computes one local direction. A
one-shot evaluator replays frozen onset-v1 controls and all bounded proposals
through actual DSP, storing immutable PCM and independently computed diagnostics.
Existing checkpoint-bound source modules remain unchanged.

**Tech stack:** Python, PyTorch autograd, NumPy, existing native synth renderer.

1. Test `local_step(unit, gradient, radius, direction)` against known derivatives:
   max-norm steps, unit bounds, reversed signs, zero-gradient identity, invalid
   numeric inputs. Test primary gate against pitch regression and missing cases.
2. Implement the helper and gate in `tools/neural_invert/local_gradient.py`.
   Descent uses `unit - direction * radius * gradient/max(abs(gradient))`.
   Direction is +1 for descent, -1 for the reversed control. Reject nonfinite
   inputs and zero/negative radius; preserve identity when the gradient is zero.
3. Implement `tools/multisynth/evaluations/local-gradient-v1.py`: verify source
   report/PCM, forward checkpoint and unseen target controls; render 32 cases,
   six proposals each, with fixed categories/seed. Save per-case progress and
   final summary in a fresh ignored run directory.
4. Run focused tests, then execute the primary predeclared evaluation on CPU.
   Report every radius/direction separately. Never choose a winner across radii
   and count it as the primary arm. Failed/missing cases prevent passing.
5. Review the result and preserve a compact outcome and manifest in evaluations.
   If the primary gate fails, keep the frozen forward model rejected for inverse
   audio training. No listening request follows this numerical diagnostic.

Completed: 32 cases, primary gate failed (23 improvements and one direction
loss); all six diagnostic arms retained. Independent review verified every saved
WAV and summary, and training exclusions. Review preflight/provenance guards are
fixed; original evaluator retained beside raw results. See
`tools/multisynth/evaluations/local-gradient-v1-summary.json`.
