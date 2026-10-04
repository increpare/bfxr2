# Architecture review, 2026-10-04

This review follows the user's request to reconsider architecture, preprocessing,
training data, human supervision and training hardware. It steers the continuing
inverse-synthesis project; it does not establish a new audible success.

## What the older Bfxr pipeline did differently

The old inverse model used a temporal Conv1d encoder and ordered readout, with
64 mel channels and six explicit acoustic contours. Its feature hop was 128
samples at 44.1 kHz. It also had actual-renderer parameter sensitivity weights
and an optional easy-parameter curriculum. The recovered v7_real_ft run adapted
to real audio for five epochs through its frozen spectral surrogate. These are
distinct differences from the newer flat shared descriptor MLP. They are plausible
contributors to the difference in quality, not isolated causal findings.

The older input is not itself an ideal full-sound representation: its 128-frame
prefix can omit later events. Preserve its onset resolution while adding a
whole-event representation and explicit duration, rather than blindly copying
its crop. The current 48-frame relative and 32-frame absolute descriptors are a
cheap temporal baseline, not equivalent to the old fine-hop features.

The recent forward pilot predicts held-out descriptors better than the mean,
but its unconstrained control gradients failed actual-render verification. Even
actual descriptor distance sometimes improved while pitch became worse. Neither
a good surrogate validation score nor a lower matching distance establishes
perceptual success. See FORWARD_AUDIO_PILOT.md for measured results.

## Recommended components

1. An audio encoder preserves onset/attack detail and complete event order.
   Inputs should include multi-resolution spectral information, confidence-weighted
   pitch, voicing, amplitude envelope, onsets and noise/timbre information. Normalize
   recording gain without erasing relative dynamics; retain duration and padding
   masks. Unvoiced texture must not be assigned a fictitious pitch target.
2. Separate synth parameter heads predict categorical structure and several
   compatible continuous patches. A single averaged vector can fall between
   valid explanations. Start with a compact temporal CNN; a transformer is a
   subsequent controlled comparison, not a prerequisite. A text LLM can help
   name or describe presets, but is not the primary waveform-to-controls model.
3. Render proposed patches with the real synths. Rank target/candidate audio
   pairs using explicit acoustic checks plus a preference model trained from
   human choices. Identifying the creator synth and choosing the best reproducer
   are different targets. Keep the exact older Bfxr and previous winning audio
   available as baselines.
4. Use actual-render search to refine safely. Do not route real-audio training
   through a surrogate until its local optimization steps pass pitch, gesture
   and actual-render tests. Retain synthetic supervision during real adaptation.

Mixr is a later composition head: decide layers/events, predict their individual
patches and mixing controls, then verify the combined sound. Starting there
adds ambiguity before the individual inverses work reliably.

## Training data and leakage controls

Use native presets, mutations, sparse-control examples and acoustic coverage
examples. Cover frequency logarithmically, duration, attack/tail, rise/fall/jump,
repetition, vibrato, pitched/noisy sounds and texture families. Balance these
families so extra easy tones do not displace useful native sound coverage.

Every example binds synth revision, full controls, random seed, rendered audio,
feature version and split membership. Split related patches/preset families and
recording families together; random row splits alone do not establish generalization.
Keep synthetic inversion tests and tagged real-audio holdouts separate.

All synths can teach a shared acoustic representation. Same-patch gain changes
and suitable random realizations can be positive examples; pitch shifts, time
stretching and reordered events should not automatically be called equivalent.
Include hard negative pairs with similar spectra but different pitch or gesture.

Cross-engine parameter labels require fitting synth B to synth A's audio and
verifying B's actual render. Mark those fits as approximate with measured quality;
never use A's controls as B's labels. Shared representation training can use all
native synth audio before those cross-engine fits exist.

## Controlled experiment order

The temporal-mixture design is a hypothesis, not a demonstrated solution.
Do not introduce all its ingredients in the first comparison.

1. Train independent one-solution temporal experts without cross-synth warm-up
   on the expanded frozen data. Compare against the flat v2 model under equal
   candidate/render budgets. Separate architecture gains from extra-data gains
   with a flat-v2 retrain on the same expanded data. If the coarse descriptor
   input fails, add a separately versioned high-resolution input pipeline before
   increasing model size. Do not mutate historical feature code.
2. Compare a multiple-solution head using the same input, data and training recipe.
3. Compare all-engine representation warm-up to random initialization. Native
   source-engine classification is auxiliary only; it must not become the router.
4. Add actual-verified cross-engine fits and tagged real-audio adaptation once
   basic synthetic inversion is reliable. Evaluate family-held-out real audio.
5. Select short listening sets containing claimed successes where methods agree,
   uncertain/disagreement cases, and representative coverage cases. Human review
   is a regular checkpoint, including when every automated measure agrees.
   Human feedback remains necessary to establish likeness.

## Human oracle

Retain original exports and exact audio identities indefinitely. Relative winners
are preference labels, not absolute success labels: the user explicitly reported
only charm2 as actually approximated in the latest five-item set.

The user explicitly corrected an uncertainty-only oracle policy on 2026-10-04:
ears are essential even when models and metrics agree, and perceptual theories
must develop from listening. For a six-item batch, target two claimed successes,
two uncertain/disagreement cases and two representative coverage cases. This is
a sampling policy, not an absolute quota if there are no claimed successes.
Preserve the liked cached WebAudio, restart-from-zero playback,
autoplay and one-click progression. A compact choice can record A/B/Neither,
with an optional "close enough" modifier or optional failure reason (pitch,
gesture, texture). Do not require reasons on every trial. Fun/usefulness is a
separate optional judgment for future preset exploration.

Train a small target/candidate preference scorer from heard comparisons, retaining
ties, skips and absolute rejection without inventing scalar labels. Use confidence
and held-out recording families; sparse personal feedback is not a license for
a large unconstrained reward model. Occasionally include fixed old baselines to
detect regressions and changing score calibration.

Maintain a hypothesis log with the listening observations that support or refute
each proposed acoustic rule (attack character, pitch motion, event timing,
roughness/texture, tail and other emergent distinctions). Test proposed rules on
new recording families as well as the clips that motivated them. Model/metric
consensus is not a substitute for this empirical psychoacoustic work. Never
promote objective agreement into a claim of audible success before listening.

## Hardware evidence and recommendation

Local system_profiler on 2026-10-04 reports Apple M1 Max, ten CPU cores (eight
performance/two efficiency), 32 GPU cores and 64 GB unified memory. Prior small
forward pilot training took approximately 12-22 seconds per engine for 40 epochs
on MPS, excluding synthesis and feature generation.

The desktop's 2026-10-03 test outputs in the existing "Investigate GPU Memory
Leak on Check" chat identify NVIDIA GeForce RTX 4080 SUPER and nvidia-smi reports
16376 MiB total GPU memory. This is historical inventory, not a live training
benchmark. Desktop CPU, host RAM, CUDA PyTorch installation and currently free
VRAM have not been checked from this local task. No desktop job was dispatched.

Prefer the desktop CUDA GPU for larger temporal models and repeated experiments,
subject to a same-workload benchmark. Keep the Mac for development, rendering,
data preparation and listening delivery, or run independent experiments on it.
Use independent jobs/checkpoints on the two machines, not synchronized training
over the LAN. Transfer versioned immutable data once, then transfer checkpoints
and compact reports. Actual DSP/audio parity must be checked on Windows before
moving rendering there. The model should fit GPU memory; the Mac's 64 GB shared
memory and desktop's 16 GB dedicated VRAM are not directly comparable capacities.

## Primary research and applicability

- [DDSP-SFX (Liu, Jin, Gunawan, 2024)](https://www.dafx.de/paper-archive/2024/papers/DAFx24_paper_51.pdf)
  explicitly models transients and uses harmonic confidence to avoid pitched
  artifacts in noisy effects. Their experiments concern footsteps, gunshots and
  motors using their own differentiable synthesizer; this motivates our input
  and loss design, not a claim about our existing engines.
- [Learning to Solve Inverse Problems for Perceptual Sound Matching (Han et al.)](https://arxiv.org/abs/2311.14213)
  derives parameter geometry from synthesis and auditory features. A practical
  adaptation is measuring actual-DSP local acoustic sensitivity rather than
  treating all normalized controls equally. Our non-differentiable engines and
  failed surrogate require separate validation.
- [Universal audio synthesizer control with normalizing flows (Esling et al.)](https://arxiv.org/abs/1907.00971)
  connects audio inference with organized latent control and preset exploration.
  It supports investigating a distribution of patches; it does not validate our
  proposed four-component mixture or its exact training settings.
- [NVIDIA RTX 4080 family specifications](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4080-family/)
  specify 16 GB memory for RTX 4080 SUPER. Training throughput should be measured
  with our workload rather than inferred from game benchmarks or core counts.
