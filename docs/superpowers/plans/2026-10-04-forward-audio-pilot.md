# Forward audio pilot implementation plan

> Use superpowers:subagent-driven-development for the isolated forward module,
> followed by spec and quality review. Standing user autonomy covers execution.

**Goal:** Establish whether a learned audio forward model supplies trustworthy
gradients before applying real-audio inverse training across synths.

**Architecture:** Three independent differentiable controls-to-descriptor MLPs,
frozen v2 shards/splits, train-only normalization, group-balanced loss, explicit
validation gate, then actual-DSP before/after checks on fixed fresh controls.

**Stack:** Existing Python tools venv, PyTorch/MPS, NumPy, shipped DSP renderer.

- [ ] Root: retain exact sixth feedback archive and qualitative statement. Write
  human-review JSON, with relative winners, heard-only pairs and no scalar scores.
  Audit the saved v2 selected/reference boundaries, documenting the unsupported
  absolute-quality interpretation and the experimental pitch gate's forced choice.
- [ ] Implementer owns `tools/neural_invert/forward.py` and
  `tools/tests/test_neural_forward.py`. API `ForwardModel(spec, hidden=256)`;
  `encode_controls(unit, categories, spec)` supports hard integer categories and
  a list of differentiable soft logits; `feature_loss(prediction,target)` returns
  total/group errors; `train_forward(data,output,engines,epochs=40,device=None,
  hidden=256,batch_size=128,seed=20261007,threads=1,learning_rate=.001)` creates a
  fresh output and independently selected per-engine checkpoints and training
  report; `load_forward(path)` returns model/metadata with checked provenance.
  CLI `python -m neural_invert.forward --data ... --output ... --engines Bfxr
  Transfxr Pluckr --epochs40 --device mps`. Require finite inputs, canonical
  dimensions/category bounds, train-only normalization, ignored peak gain,
  complete metadata, deterministic no-drop train/val, and baseline/group gate.
- [ ] TDD: tests fail before implementing imports/API; test hard/soft category
  equivalence and finite nonzero gradients, gain independence, nine groups full
  coverage, constant baseline, unsupported TEXT rejection, output overwrite
  prevention and checkpoint load mismatch. Test tiny actual-format shard data
  through one-epoch training/reload without writing old artifacts.
- [ ] Spec review then quality review; fix findings before full training. Root
  trains40epochs in existing venv on MPS with approved escalation if necessary.
  Preserve failure/non-passing gates and summaries without claim of likeness.
- [ ] Root: only for predictive-gate-passing models, implement a separate
  `forward_probe.py` with regression tests for fixed categorical/RNG anchors,
  frozen weights/gradient-through-unit, fresh output and actual-DSP score binding.
  Evaluate the20 frozen source-engine targets with100gradient steps,.01lr; save
  all before/after scores/audio/controls and apply predeclared actual-DSP gate.
- [ ] Document measured outcomes, archive/code/reports commit, preserve prior
  defaults. A successful pilot enables the next training stage; a failed one is
  explicitly a failed architectural hypothesis, not another listening delivery.
