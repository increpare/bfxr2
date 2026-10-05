# Local perceptual cue calibration

**Goal:** Obtain five new, interpretable likeness comparisons after the embedding
screen failed (1.9 percentage-point gain, below frozen five-point threshold).
**Architecture:** Exact archived tagged references -> two fixed, reversible audio
perturbations per reference -> existing buffered A/B questionnaire with immediate
adequacy. This is a loss-calibration experiment, NOT new synth reproductions and
NOT a candidate-generation pilot bypassing the failed screen.

The broad old candidates change many properties simultaneously. This diagnostic
asks which controlled deviation preserves identity better. Perturbations are
chosen now, before scoring them, without tuning strength until metrics disagree.
Both metric-agreement and disagreement trials remain. One comparison per source;
no repeated recall questions. These preferences are local evidence, not universal
pitch-vs-timbre weights or proof of pure perceptual axes (filters, phase vocoders
and level matching can introduce coupled changes).

Five fixed contrasts:
1. Wooden footstep: 30 ms raised-cosine fade from first 1%-peak onset versus
   fourth-order zero-phase lowpass at 2500 Hz.
2. Brick break: time stretch to 125% duration (pitch-preserving phase vocoder)
   versus lowpass 2500 Hz.
3. Charm2: pitch shift +2 semitones, preserved duration, versus lowpass 2500 Hz.
4. Cloth3: time stretch to 125% duration versus lowpass 1800 Hz.
5. Laser: pitch shift +2 semitones versus exponential tail attenuation beginning
   at 60% elapsed time, ending at -18 dB.

Source audio stays exact. Match each processed clip's whole-clip RMS to its
reference, with peak cap .8 and no clipping; save actual gain and whether capped.
No processed audio is a successful inverse training label. Retain transform
parameters, library versions, code/PCM hashes and repeat-render equality checks.

- [ ] Freeze protocol with reference bindings before generation.
- [ ] Generate and repeat-render ten variants deterministically; verify finite,
      nonempty, distinct PCM, no clipping and duration expectations.
- [ ] Export five A/B trials using existing quick UI. State clearly that these
      are deliberately edited originals. Ask closest first, then adequacy.
- [ ] Freeze score predictions; verify every served file against disk and inspect
      page. Request only this short batch, with no retrospective questions.
