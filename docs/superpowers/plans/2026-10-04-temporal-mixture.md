# Temporal mixture inverse implementation plan

> Apply superpowers:subagent-driven-development with fresh implementer, spec
> then quality reviewers. Standing user autonomy authorizes execution.

Goal: train a new safe inverse iteration and deliver6 meaningful listening choices.
Architecture: independent temporal4-mode control experts, balanced synthetic
training, actual-render constrained comparison, unchanged quick UI.
Stack: existing tools Python venv, NumPy/PyTorch MPS, shipped JS DSP.

Architecture review update: first train independent one-mode temporal experts
without warm-up, and a flat-v2 retrain on the same expanded data. Then ablate
multiple modes and shared warm-up separately. Follow
`tools/multisynth/TRAINING_ARCHITECTURE.md` for input resolution, dataset families,
human-oracle semantics and hardware evidence. Do not interpret shared source
classification as a reproduction router. No Windows training job is dispatched.

- [x] Root generates8192 extra structured rows per trio via existing CLI:
  PYTHONPATH=tools python -m neural_invert.structured --base tools/multisynth/runs/neural-v2/data --output tools/multisynth/runs/temporal-v3/data --per-synth8192 --seed20261008 --jobs3.
  Check complete manifest/hash/splits/native preservation and benchmark exclusion.
- [x] Implementer owns new tools/neural_invert/temporal.py and
  tools/tests/test_neural_temporal.py. Write failing tests for temporal packing,
  multiple-mode loss avoiding arithmetic averaging, inactive controls/physical
  pitch, balanced native/structured weights, shared train-only
  normalization, fresh output and strict reload; implement and verify. APIs
  Shared pretraining deferred to its own subsequent ablation; first implement
  TemporalExpert(spec,modes=4,hidden=256), mixture_loss(prediction,labels,spec),
  train_temporal(data,output,engines=trio,epochs=90,modes=4,device=None,
  batch_size=128,seed=20261009,threads=1,encoder_kind='temporal'), load_temporal(path),
  predict_temporal(model,metadata,wave,renderer,count=4,seed=20261010).
  CLI --data --output --engines --epochs --modes --device. No existing code edits.
  Added matched-flat encoder with identical heads/loss/balancing for comparison.
  Independent spec and quality review approved;39 model tests passed.
- [ ] Spec then quality review; root fresh tests then MPS one-mode temporal and
  same-data flat baseline; separately compare4mode and all22 cross-synth warm-up
  ablation on frozen new data, separate outputs. Archive audited training summary.
- [ ] Root implements actual-DSP evaluation/ranking/delivery runner in separate
  new module with TDD/reviews. Uses benchmark20 and same4candidate budgets for
  v2/ablation/mixture. Save source-engine raw+unrestricted comparisons; enforce
  predeclared diagnostic checks and preserve reliable pitch/gesture in actual
  refinement. Revise autonomously if needed until new feedback set is credible.
  Implementation and two-stage review completed;9 evaluation/gallery tests passed.
  Actual full-data training and benchmark execution in progress.
- [ ] Root freezes6 references before new inference; exact archived previous
  PCM and original Bfxr baseline, run actual candidates without reference tags.
  Generate unchanged quick UX. Audit all new actual controls/WAV/score hashes,
  archived winners/reference identities; independent review and isolated-origin
  browser check; localhost/LAN serve/open page. Retain reports+code commit.
- [ ] Final asks for6 best/none choices and copied JSON, clearly distinguishes
  measured diagnostic gains from audible quality that still needs feedback.

Human-oracle correction: regular listening must include claimed successes where
models/metrics agree, representative examples, and uncertain cases. Maintain
the empirical hypothesis log at tools/multisynth/evaluations/perceptual-hypotheses.json.
