# Coverage selection v1

Keeping both Transfxr experts is more useful than replacing the old expert. The new selection policy passes its numerical check on 32 additional held-out native control groups. **This is not a human quality result.**

The old four-proposal winner remains available. Additional candidates may win only with lower actual rendered distance and without losing its reliable pitch, previously matched static register/direction, contour support, one-semitone coverage, or mean paired contour accuracy. All candidates compare against that fixed baseline. Unreliable targets use distance alone. Descriptor evidence is now a selection input; preserved metrics are partly guaranteed by construction.

| Fresh-control inference policy | Mean distance | Expanded selections | Individual safeguard losses |
|---|---:|---:|---:|
| Old expert, four proposals | 5.17234 | 0 | 0 |
| Old expert, eight proposals | 4.79809 | 0 | 5 |
| Old eight, guarded | 4.82521 | 0 | 0 |
| Four old + four expanded, unguarded | 4.29990 | 18 | 10 |
| Four old + four expanded, guarded | 4.58439 | 9 | 0 |

The guarded ensemble improves mean distance 11.37% over old-four and 4.45% over old-eight. Safeguards reject 0.28449 of the unguarded mean-distance gain. The new expert is complementary, not universally better. This compares inference systems with explicit budgets; it is not an isolated claim about architecture.

Additional targets were frozen with seed 20261027 before inference. All 32 are distinct new-validation control groups, absent from training and the previous 32 native evaluation targets. Preset families are shared. The earlier 74 targets are reported separately as retrospective development evidence.

Verification: eight selection-policy tests and three coverage-data tests pass. Review found no important policy, split or budget issue. Audit verifies all 384 saved candidate PCM/file hashes, 70 distinct selected DSP replays/rescores with zero error, frozen target identities/exclusions, selection outputs, summaries and gates. Pitch diagnostics are reused, not independently re-estimated.

Full retained run: `runs/coverage-selection-v1`. Tracked summary/audit: `evaluations/coverage-selection-v1-audit.json`. The original expanded-model replacement gate remains failed. A separate private equal-budget refinement check on the five previously rejected real references is the next test of transfer; no listening success is inferred from this synthetic result.
