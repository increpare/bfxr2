# Transfxr input robustness and external-source matching

The user's overspecialization concern is supported by this first controlled
check: clean native self-inversion is not evidence of robust matching. This
experiment tests the frozen inverse models and their selector, not the maximum
representational capacity of the Transfxr synthesizer.

## Scope and procedure

90 targets: eight Transfxr bases with eight variants each (64); one freshly drawn
native sound from each of the other 21 compatible synths; five previously judged
real recordings. The eight bases include three human-reviewed anchors and five
other previously evaluated holdout controls. They are absent from training,
but this is a small development test with shared generator families.

Variants are clean, MP3 at 32/96 kbps, 8-bit quantization, two-pole low-pass at
1800 Hz, high-pass at 350 Hz, and +/-5 semitones using ffmpeg asetrate/resampling
with compensating atempo. The transposition approximately preserves duration
but can introduce artifacts. All variants share the same source gain. FLOAT
copies retain exact scored PCM. Codec/time-stretch tail lengths are padded or
trimmed to the source length; no content alignment is optimized.

The altered audio is the matching target. Eight old proposals are compared to
four old plus four expanded proposals with the existing fixed-baseline guard.
Also retain old-four and expanded-four. No local search is used. Source controls
are used to generate and verify references, never supplied to prediction or
candidate selection. All 90 cases have zero missing or failed proposals, which
is required for the evaluator's accepted-list slices to retain the stated
four-plus-four budget. Do not reuse that slicing with failed proposals.

## Paired robustness result

For each altered target, compare the new ensemble prediction with the unchanged
ensemble prediction made from its clean source. Both are scored against the
same altered target. This avoids interpreting score changes solely caused by
changing the reference as model regression.

| Alteration | New prediction beats frozen clean prediction | Mean new distance | Mean frozen-clean distance |
|---|---:|---:|---:|
| MP3 32 kbps | 1/8 | 4.5723 | 3.1565 |
| MP3 96 kbps | 4/8 | 3.1582 | 3.0522 |
| 8-bit quantization | 3/8 | 3.3258 | 3.1523 |
| Low-pass 1800 Hz | 1/8 | 4.7866 | 3.2870 |
| High-pass 350 Hz | 3/8 | 5.4037 | 4.0225 |
| Up five semitones | 4/8 | 4.6317 | 4.8674 |
| Down five semitones | 6/8 | 4.0886 | 6.2965 |

The heavy-codec and filtering cases expose instability under the current metric.
Lighter compression and 8-bit input have smaller average effects. Transposition
is more encouraging in this sample, particularly downward, but individual pitch
and gesture diagnostics are inconsistent. Neither distance nor tracked median
pitch is a calibrated absolute likeness measure: the human-approved bouncing
rise already has substantial median-pitch error by this tracker.

## Sounds from elsewhere

On the 21 fresh other-synth sounds, ensemble mean distance is 7.5213 versus
7.8980 for old-eight: nine wins, nine losses, three ties. This is mixed transfer,
not broad audible success. One sample per source synth cannot rank engines or
establish Transfxr's capacity. Only six references have reliable target pitch;
the ensemble has a tracked median within a semitone on one of those six.

On the five repeated real references, raw ensemble mean distance is 8.8145 versus
9.9211 for old-eight (three wins, one loss, one tie). No raw ensemble result has
a tracked median within a semitone. This run omits refinement; do not compare
its absolute numbers directly with the earlier 384-trial refinement experiment
or treat improvement over old-eight as a human success.

## Implications and listening check

The Transfxr inverse currently learns from clean synth renders. It needs an
explicit robustness/transfer training test before broad matching claims. For
codec variation, investigate stability training paired with actual-render
checks. For transposition/filtering, train to reproduce the changed audible
result; blindly giving every augmented input the original control label would
teach it to ignore changes the user wants preserved. Transfer failures may arise
from inference, candidate ranking, or synth capacity; this test does not
separate all three.

Six fixed listening probes cover compressed/transposed warble, filtered texture,
and new Bfxr/Boomr/Pluckr targets. The altered-input pairs compare clean-input and
altered-input predictions, both against the altered reference. Other-synth pairs
compare old-eight with the ensemble. These cases were fixed before the complete
run's outcomes were available, and are diagnostic rather than random. The
published source gallery and prior human feedback remain unchanged.

Artifacts: `runs/transfxr-transfer-v1/{targets,results}.json`; tracked source and
selected-render audits `evaluations/transfxr-transfer-v1-{source-audit,audit}.json`.
All 29 DSP sources and 64 perturbations replay exactly; all five real-source PCM
copies match. Candidate audit verifies 1,170 target/candidate files and 235
selected DSP replays/rescores with zero score error. Review identified the
accepted-list budget issue above; the audit requires zero failures and exact
8/4 counts for every row, satisfied by this run.

Listening page: `runs/transfxr-transfer-v1-listening/index.html`, experiment
`8242b8603755b097d7cdba29233b686d1270e5caf185603987090011b080d5bd`.
HTML, results and all 18 audition WAVs match hashes over the local HTTP server.
The browser shows six available comparisons and zero judgments; no assistant
ratings were entered. Likeness feedback on this batch is pending.
