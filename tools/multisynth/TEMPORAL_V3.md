# Temporal inverse experiment, 2026-10-04

This iteration trains separate Bfxr, Transfxr and Pluckr inverse models and
compares their actual synthesized output. It is a development experiment.
Numerical improvements do not establish convincing or evocative reproduction;
regular listening includes cases where every automated check agrees.

## Training and architecture comparison

The frozen dataset contains 75,776 examples from 22 engines. Bfxr, Transfxr and
Pluckr each have 12,288 examples, including 8,192 additional structured examples
per engine. The other engines and original rows are preserved. Native and
structured examples receive equal aggregate training weight. Normalization uses
training rows only. Splits group identical control vectors, but do not establish
preset-family or recording-family generalization.

Each of the three engines has a matched flat model, an ordered temporal model,
and a four-solution temporal model: nine completed 90-epoch runs, using their
best validation checkpoints. An independent CPU forward pass through all 1,843
validation rows per engine reproduced the reported losses within 2.13e-8. The
loss functions themselves are shared tested code, not independent implementations.
The temporal one-solution models trained on MPS; the other runs used CPU. This
device difference is a remaining experimental confound.

The temporal input is the existing coarse relative/absolute descriptor reshaped
into ordered streams. This does not yet recover the old Bfxr model's fine onset
resolution. Shared cross-engine pretraining is deferred to a separate ablation.
The former Bfxr model and its exact listening audio remain available.

The selected bundle uses four-solution Bfxr, flat Transfxr and temporal Pluckr.
Selection used the same development probes reported below; these results are
optimistic model-selection measurements, not independent validation.

## Actual-render development probes

All arms propose four patches per engine, render their controls and seeds with
the actual DSP, and retain exact float WAVs. Twenty fixed probes include nine
stationary pitched sounds, eight moving sounds and three native examples. Their
exact controls were excluded from training. Related sound families can still
occur in training.

| Selection scope | Model | Mean matching distance | Static pitch within 1 semitone | Motion direction | Lower distance than v2 |
| --- | --- | ---: | ---: | ---: | ---: |
| Known source engine, 4 candidates | v2 | 2.3173 | 6/9 | 8/8 | — |
| Known source engine, 4 candidates | Selected bundle | 1.7477 | 7/9 | 7/8 | 14/20 |
| All three engines, 12 candidates | v2 | 1.9384 | 5/9 | 5/8 | — |
| All three engines, 12 candidates | Selected bundle | 1.4357 | 8/9 | 7/8 | 16/20 |

The unrestricted comparison uses no source-engine hint. Known-engine results
diagnose inverse reconstruction separately from routing. A lower distance can
still accompany a worse audible pitch or gesture. All-temporal unrestricted
selection has a lower mean distance than the selected bundle (1.3844), but only
7/9 stationary pitches pass; there is no universal winner across the measures.

Four additional high-pitch probes expose an unresolved weakness: none of the
three newly trained architectures gets within one semitone on any of them,
versus one of four for v2. The bird reference also exposes disagreement between
pitch estimators, including an octave error. More training alone has not solved
the input/estimator limitation. A clean-tone probe isolates a concrete input
problem: the coarse pitch descriptor reports about 1,002 Hz for 2,000 Hz and
1,575 Hz for 3,200 Hz. Its lag range cannot represent pitches above 2,205 Hz
directly, and endpoint selection can cause octave errors below that ceiling.
The older diagnostic is accurate on those two probes but itself halves a
4,000 Hz sine. Neither estimator should be treated as unconditional ground
truth. See `evaluations/temporal-v3-pitch-input-probe.json`. High-resolution,
confidence-aware input is the next architecture hypothesis to test after this
listening checkpoint.

## Listening checkpoint

Six references were fixed before new model inference: spinout, bird, book close,
robot talk, charm2 and egg jump. The first five are familiar regression cases;
egg jump adds a new quick-listening reference. They are not an unseen holdout.
See `evaluations/temporal-v3-listening-targets-errata.json` for correction of the
frozen target manifest's erroneous previous-rating flags. The manifest itself
is retained unchanged to preserve its recorded hash and selection provenance.

Every new approximation competes with exact earlier audio and the original Bfxr
baseline where available. Each expert's best raw proposal gets 384 actual-DSP
refinement trials; the lowest-distance raw or refined output becomes the new
option. Reliable, already matched pitch and motion are guarded during refinement.
These safeguards remain hypotheses needing human evaluation. Original Bfxr on
the new jump reference uses its historical 2,000-evaluation search. This listening
comparison measures complete pipelines, not equal-budget architecture effects.
Of 72 raw proposals across the six real references, 71 were audible. One Bfxr
proposal for charm2 was silent and is retained as an explicit failure in the
diagnostics; it is not replaced or counted as an audible candidate. The final
audit independently repeats that inference to verify the reported failure.

Generation was resumed after an empty-history lookup failed on the new sixth
reference. The five completed rows were retained with verified reference and
candidate PCM. The repaired generator records its prior manifest hash and each
folder's generating code hash; it does not relabel older output as newly rendered.
Thirteen evaluation/export tests cover the repaired path and repeated resumption.

The quick interface retains cached WebAudio, playback from the beginning,
automatic progression and best/tie/none choices. Choosing the least bad option
does not imply adequacy. Optional notes such as “close enough”, “still far off”,
or a specific failure help distinguish those cases without mandatory extra clicks.

All historical feedback exports, exact audition PCM and identities remain
archived. No new preference labels are inferred from these numerical results.
The hypothesis log records human observations separately from proposed acoustic
explanations. Future short batches will regularly include consensus successes,
uncertain cases and representative coverage, rather than using human ears only
as a tie-breaker.

## Reproducibility

- `evaluations/temporal-v3-data-audit.json`: data preservation and exclusions.
- `evaluations/temporal-v3-training-audit.json`: nine checkpoint/validation audits.
- `evaluations/temporal-v3-comparison.json`: known-engine and unrestricted results,
  per-case identities and hashes.
- `runs/temporal-v3/high-pitch-comparison/results.json`: four high-pitch probes,
  all proposed control patches, rendered audio identities and per-arm results.
  `evaluations/temporal-v3-high-pitch-summary.json` retains the compact results
  and full report hash in Git.
- `evaluations/temporal-v3-routing-audit.py.txt`: unrestricted aggregation.
- `evaluations/temporal-v3-listening-audit.py.txt`: final controls, score, audition
  PCM and historical identity checks.
- `runs/temporal-v3`: ignored immutable local data, model checkpoints and full
  rendered diagnostic reports. `hybrid-experts/assembly.json` binds selection;
  each linked engine has its own complete training report.
- `runs/temporal-v3-listening`: generated listening page, full candidate controls,
  diagnostics and audio. Its feedback is a new experiment with separate identity.

All training in this iteration ran on the Mac. No desktop training job was
dispatched; the hardware recommendation still requires a same-workload benchmark.
