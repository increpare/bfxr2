# Smooth periodicity diagnostic and bounded search

**Goal:** Remove a demonstrated hard-pitch discontinuity from an experimental
matching objective, then test whether actual-render refinement benefits.
**Architecture:** Keep the legacy matcher frozen. An opt-in subclass replaces
pitch, voicing, slope and pitch-motion penalties with smooth normalized
short-time autocorrelation comparisons over 96 log-spaced lags (90–4000 Hz).
All envelope, coverage, timbre and mel terms remain unchanged. No global pitch
or duration invariance is inferred from the five edited-source judgments.

Evidence: a -59.5 dB RMS waveform difference on wooden footstep receives 2.82
legacy distance, almost entirely from hard pitch and slope estimates, and loses
to a substantially faded attack. The listener explicitly prefers the near-identity
version as very close. The existing learned scorer already gets this pair right.

Alternative choices are confidence-threshold tuning or removing pitch entirely.
A continuous periodicity map avoids a single estimated pitch flipping between
harmonic peaks while retaining periodic structure. It may blur useful pitch
information; test that directly on tones, rising/falling sweeps and native sounds.
Use positive and negative ACF values, fixed zero padding, Hann-window correction,
no discrete peak selection. Normalize frame energy with the same small numerical
floor; clip corrected correlation to [-1,1]. Compare mean absolute map error
(weight4) and adjacent-frame map-motion error (weight1). These weights are fixed
before historical evaluation, not fitted to the five new labels.

- Reproduce the discontinuity and retain component-level exact-audio evidence.
- Add tests for near-identity stability, nonzero pitch/register discrimination,
  rising-vs-falling motion, unchanged legacy behavior, and batch/cache contract.
- Implement `multisynth/soft_periodicity.py`, isolated from original checkpoints.
- Audit all historical strict preferences and fixed synthetic probes. Reject
  further search if overall pair accuracy decreases versus legacy matching or
  synthetic invariance/discrimination tests fail. Historical analysis is
  development, not independent validation. Latest calibration labels stay separate.
- If the screen passes, refine fixed starts on tagged sounds with equal mutation
  budgets under legacy and experimental objectives; retain original Bfxr/previous
  human winners. Only actual distinct outputs with exact replay go to a new page.
- Preserve all feedback and the user's permission for up to20 useful trials in
  the current UI. Questions must remain adjacent to the currently heard sound.
