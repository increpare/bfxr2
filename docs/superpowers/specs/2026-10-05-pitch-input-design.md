# Corrected pitch input experiment

The temporal-v3 listening feedback reports two partial matches, two preferences for older output, and one rejection. Preserve every judgment, exact audition waveform, and the qualification that book-close and charm2 remain somewhat off. This experiment addresses the demonstrated octave errors in the input descriptor before changing the network architecture.

## Alternatives and decision

1. Correct the pitch/voicing channels only, keeping data, splits, spectral/envelope channels, architectures, training recipe, search budget and numerical selection fixed. This isolates whether the demonstrated input bug materially contributes to failure. **Do this first.**
2. Add high-resolution onset and whole-event streams. This may capture attacks and gesture better, but changes both information and capacity. Defer until the pitch-only experiment is measured; it is a separate next experiment, not discarded.
3. Increase capacity or add all synth experts immediately. This spends training time before repairing a known misleading input. Defer.

The user's standing authorization is to proceed autonomously until useful human feedback is needed; routine implementation decisions do not need renewed approval.

## Feature contract

Create a separately versioned `pitch_features.py`; never edit the frozen feature or temporal-model modules. Keep the 4083-dimensional layout, and copy every non-pitch/non-voicing value bit-for-bit from the frozen descriptor. Estimate native 44.1 kHz periodicity on centred 2048-sample Hann-window frames at the same frame times used by the old descriptor. Use Hann-weighted DC removal, fourfold band-limited autocorrelation interpolation with correct Nyquist splitting, window-autocorrelation bias correction, neighbour comparisons including range endpoints, parabolic sub-sample lag interpolation, earliest sufficiently strong local maximum, and an explicit unvoiced outcome. A three-native-sample low-frequency guard admits the small finite-window peak displacement near 55 Hz. Support approximately 55–8000 Hz; reject spurious noise periodicity. Sample the new pitch and confidence onto the unchanged relative and absolute timelines. Silence stays well-defined; gain and padding behavior remain unchanged. Bind both new and frozen feature implementation hashes.

Tests must cover clean low/high tones (especially 2000, 2200, 2500, 3200, 4000 Hz), harmonic tones, noise, rising/falling pitch, gain invariance, silence and exact preservation of untouched channels. Characterize boundary limitations honestly rather than optimizing only the four previous failing probes.

## Data and model experiment

Re-render all 75,776 frozen temporal-v3 rows, verifying original canonical controls, render seed, audio hash and sample count. Replace only pitch/voicing columns. Keep all labels, row order, train/validation membership and excluded probes unchanged. Use resumable per-engine output with immutable manifests and reject mismatched input/code/DSP on resume. Each row binds new packed features and original feature hashes. Reuse all 22 engines for train-only normalization, so the normalization population is unchanged. No new wave cache is needed; available disk is approximately 30 GB.

Train the selected v3 architectures with the same 90-epoch recipe and seed: Bfxr temporal four-mode, Transfxr flat one-mode, Pluckr temporal one-mode. New trainer/loader modules can reuse frozen architecture/loss functions without monkeypatching globals. Require full metadata, code, source dataset, new dataset, normalization, report and checkpoint bindings. Reject incomplete models. Actual inference uses the new descriptor and four proposals per engine.

## Evaluation and human check

Replay the 20 development probes and four high-pitch probes; report source-engine and unrestricted selection separately, with all attempted/failed renders. These probes are development evidence, not independent generalization claims. The existing structured Bfxr/Transfxr draws stop at a nominal 1,600 Hz; high-pitch probes also test coverage beyond that structured range. Native Transfxr rows include 181 of 2,048 nominal starting pitches above 2,000 Hz, so this is sparse coverage rather than complete absence. A pitch-input repair alone may not repair that distribution gap; changing the data belongs in a subsequent controlled arm. Compare actual synth audio against frozen v3 outputs at equal raw candidate budgets; control loss alone does not establish better sound. Keep the current objective unchanged so input effects can be assessed, while explicitly retaining its known human-preference conflicts.

If the retrained models produce meaningful candidates, prepare a short quick-listening comparison using cached WebAudio and exact retained baselines. Include the earlier Transfxr charm2 anchor that was not auditioned in the latest session, the latest partial successes, failures and at least one consensus case. Ask for human judgments even if metrics agree. Do not imply a best-of-set choice establishes adequacy.
