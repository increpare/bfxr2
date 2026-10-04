# Forward audio-loss pilot after the v2 human rejection

The user reports that only charm2.wav was approximated. Its winner is the exact
previous Transfxr audio, not v2's Pluckr. Relative best choices for bird and card
are not absolute successes. Preserve attachment bytes and lossless audio, plus
the qualitative statement separately; never turn it into invented 1–5 labels.

V2's control-supervised inverse predictor and the original Bfxr pipeline differ
in a testable way: original Bfxr also used a frozen differentiable forward model
and real-audio feature loss. More selector weights cannot generate missing
candidates. Changing the encoder at the same time would obscure the audio-loss
experiment. Under the user's standing autonomous authorization, first test a
bounded forward-model prerequisite, preserving every existing model/gallery.

Train separate control-to-feature MLPs for Bfxr, Transfxr and Pluckr on the exact
frozen v2 shards and existing train/validation split. These three numeric engines
have no text transcription dependency and structured acoustic coverage. Inputs
are canonical unit controls and categorical one-hot vectors; soft categorical
logits must remain differentiable for future inverse training. Volume is removed
by the descriptor. RNG anchors are not learned: report this limitation, especially
for noisy/string material, and never claim exact waveform synthesis.

Outputs are the existing full-sound 4083-dimensional descriptors, including
relative/absolute spectrum, envelope, pitch/voicing and duration. Gain at -2 is
ignored. Normalize from each engine's training rows only; floor feature std at
.025. Give nine nonoverlapping feature groups equal weight (relative/absolute
spectrum, relative/absolute envelope, relative/absolute pitch, combined voicing,
duration, RMS), avoiding
silent spectral tails dominating the temporal groups. Record exact boundaries.

Use two hidden layers, width256, GELU, AdamW and cosine scheduling; 40 epochs,
batch128, seed20261007, learning rate.001. Select each engine's best checkpoint
by held-out feature loss, recording group losses and its training-mean predictor
baseline. Dataset, DSP, feature/schema, normalization, seed and code provenance
must be bound. Outputs require a fresh path. Existing inverse load/predict stays
unchanged. No real tagged audio is a synthetic control label.

Before using this forward model for new inverse training, require every pilot
engine's validation loss at most .8 of its training-mean baseline, and pitch,
voicing and envelope group loss at most the corresponding baseline. This is a
predeclared predictive gate, not perceptual validation.

Then test actual-DSP gradients on the 20 already-frozen fresh benchmark sources
from these engines (three native, nine static, eight moving). Start with v2's
known-source raw controls, keep categorical/text/RNG anchors fixed, optimize only
continuous controls for100steps at learning rate.01, render before/after with
actual shipped DSP and unchanged seeds. Preserve both surrogate and actual
feature loss, MatchObjective, pitch/gesture diagnostics, controls and WAV hashes.
Accept the gradient pilot only if actual feature loss improves on at least15/20
and mean actual loss decreases without losing reliable pitch on any previously
reliable tonal case. Neither gate establishes real-SFX likeness. If a gate fails,
report the failure and keep this model out of production; do not request another
human listening round of an unvalidated candidate generator.

User authorization permits proceeding without a design approval interruption.
The isolated branch and frozen v2 data are reused; no DSP/features/old model edits.
