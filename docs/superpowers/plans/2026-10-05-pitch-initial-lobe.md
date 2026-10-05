# Pitch-v5: reject initial autocorrelation ripples

User authority: continue autonomously until a useful human-quality checkpoint.
Do not ask for approval of this routine corrective experiment. Apply
subagent-driven-development, TDD and independent reviews.

## Evidence and scope

Pitch-v4 completed matched retraining and 24 actual-render probes. It is not a
general improvement (paired unrestricted mean 1.4357 -> 1.7054). The more detailed
coverage audit exposed a descriptor defect: 0.75*sin(100 Hz) + 0.1*sin(2000 Hz)
is reported around 2315 Hz despite the stronger fundamental. Actual archived
Bfxr row2059 and Transfxr row2066 reproduce the failure (dominant FFT near167/336
Hz, reported3573/6859 Hz). The earliest-strong-peak rule accepts a small ripple
in the initial positive autocorrelation lobe. Frozen v4 outputs are retained;
its partial listening gallery is not delivered.

Hypothesis: exclude the initial positive autocorrelation lobe and retain the
strongest interpolated peak in each later positive lobe before period selection.
Initial-lobe exclusion alone reduced but did not pass the new regressions;
near-period ripples also need major-peak selection. This adapts the peak-selection
rule from McLeod and Wyvill (2005), section 5, without adopting their full NSDF. Validate actual synth waveforms, missing/weak
fundamentals and high frequencies before any full replay. Preserve v4 modules
and their hashes. Do not change data distribution or architectures in this arm.

## Tasks

- [x] Implement separate pitch_v5_features.py with the v4 public API and exact
  unchanged feature columns. First add regression tests for weak20th partials
  and actual Bfxr/Transfxr whistle waveforms plus prior low/high harmonic tests.
  Investigate initial-lobe exclusion as a single change, retain explicit version,
  configuration and code hashes. Test noise, boundary, short signals, motion,
  gain and unchanged columns. Spec then quality review; freeze before replay.
- [x] Create versioned pitch_v5_data.py and pitch_v5_temporal.py by controlled
  adaptation of reviewed v4 pipeline, retaining source data, rows, labels, splits,
  architecture/recipe/seed and all22 normalization. No monkeypatching. Tests
  must exercise strict replay/loading and compatibility rejection. Review/freeze.
- [x] Re-extract same75,776 source rows, re-train same three90epoch experts,
  audit strict bindings and validation, evaluate same20+4 development probes.
  Keep v3/v4/v5 separate. Judge full contours and actual proposal pools; median
  pitch alone and direction alone cannot establish recreation.
- [ ] Generate a short human comparison only when newly rendered tagged results
  merit it. Retain exact prior human anchors including both charm2 histories.
  Audit real DSP/PCM and browser UX. Archive code/results/limitations; request
  best/tie/none with optional adequacy comments. Human ears remain essential
  even if metrics agree.

### Evaluation implementation detail

Use new pitch_v5_eval.py and pitch_v5_gallery.py; do not edit frozen v4 modules.
The probe runner takes explicit v3, v4 and v5 expert roots, renders four proposals
per each of three synths in every arm, and saves all actual FLOAT audio plus
missing/failure accounting. Source-engine and unrestricted selection stay separate.
The unchanged objective chooses outputs. Retain old pitch diagnostics as legacy;
compute v5 diagnostic medians AND voiced relative-time contours, span and active
frame tolerance for all three arms, with limitations clearly labelled. A steady
median and matching direction alone cannot certify gesture accuracy. Test a same-
direction but wrong-excursion case and the octave false-pass regression.

Gallery uses the same fixed five target manifest and exact archived human anchors,
384 frozen guarded refinement trials per available engine and original seeds.
No v4 partial-gallery candidates are human-labelled or inserted as prior winners.
Strict checkpoint/data and DSP/PCM verification, <=3 distinct quick options,
recorded trial accounting and existing cached-WebAudio UX all remain required.
