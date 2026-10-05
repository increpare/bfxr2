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

Full retained run: `runs/coverage-selection-v1`. Tracked summary/audit: `evaluations/coverage-selection-v1-audit.json`. The original expanded-model replacement gate remains failed. The separate private equal-budget refinement check on five previously rejected real references is now complete: expanded wins only one of five within Transfxr. See `NATIVE_COVERAGE_V1.md` and `evaluations/native-coverage-v1-real-audit.json`; no listening success is inferred from this synthetic result.

## Small human calibration

`runs/coverage-selection-v1-listening/index.html` contains three deliberately selected new self-inversion comparisons: held-out native targets 17860 (warbling sweep), 17445 (short texture), and 21373 (bouncing rise). Both alternatives have eight scored proposals: old-eight versus guarded four-old/four-expanded. No local search, source controls or generator labels enter prediction/selection. Shared preset families remain a limitation. Target control labels are retained for provenance only.

The question is whether these numerical improvements actually preserve audible gesture and character when exact synth reproduction is possible. One texture has unreliable pitch diagnostics; two tests have reliable moving-pitch evidence. This is a biased diagnostic sample, not a quality-rate estimate. All references and candidates replayed exactly, each audition received one normalization/PCM16 transform, served HTML and all nine WAVs match export hashes, and browser playback completes without entering choices. Relative wins will remain separate from absolute human likeness judgments.

Experiment ID: `3afd5c29406ff55b3877ecefd48debf7174e7c871b7ff54f1f39c7454665b5e8`. Tracked delivery receipt: `evaluations/coverage-selection-v1-listening-audit.json`. The five real-reference refinement pairs are complete and audited; charm2 improvement still does not beat its earlier Bfxr distance and is not offered for another rating.

### Human feedback received

The listener preferred the expanded expert on Warbling sweep and Bouncing rise,
and judged Short texture a tie. Original feedback and all nine exact audition
audios are retained in `listening_data/2026-10-05-coverage-selection-quick-01`.
There are no scalar ratings or absolute adequacy judgments in the export;
whether these are convincing recreations remains unknown. The previous five
real references' zero-convincing verdict is a separate observation.

Warbling sweep has an explicit best choice but no recorded playback IDs. This
is missing telemetry, not evidence that the user did not listen. The current
strict heard-only preference pipeline therefore yields one pair, from Bouncing
rise, while preserving both submitted wins and the tie. See
`evaluations/coverage-selection-quick-01-human-review.json`.

Known source controls show closer duration in both preferred versions and a
closer ending level in Warbling sweep. This does not establish the cause of
preference. Bouncing rise still predicts release 0.2664 against source 0.5916;
its relative win does not remove that error. These three deliberately selected
cases support retaining the expanded expert as a complementary proposal source,
not replacement of the original expert or a claim of reliable real-sound matching.
