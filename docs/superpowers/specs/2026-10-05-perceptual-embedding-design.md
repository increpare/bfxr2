# Frozen perceptual representation diagnostic

The broader candidate search has zero convincing matches. Another search using
identical descriptors has weak justification. Three options are more random
coverage, a larger inverse network, or an independent representation benchmark.
Test the third first: it costs no new listening and can falsify a scoring idea.
This is an intermediate step toward inverse training, not an inverse replacement.

Evaluate LAION clap-htsat-unfused final projected embeddings and per-channel
mean/std statistics from the first three transformer stages. The latter is
inspired by https://arxiv.org/html/2507.07764v1, but is NOT a replication: that
paper's style encoder is Microsoft CLAP, and its task is instrument timbre with
pitch/duration controlled. LAION's official converted checkpoint and Transformers
implementation are an accessible first test on our actual SFX judgments.
https://huggingface.co/laion/clap-htsat-unfused

Inputs are exact archived mono PCM, deterministically resampled 44100 to 48000,
right-zero-padded to ten seconds. Reject longer inputs rather than silently
truncating. No repeated audio padding, random crop, amplitude renormalization,
text labels, or control/preset identifiers enter the encoder. Freeze model in
eval mode. Bind immutable upstream revision, weight hashes, installed versions,
preprocessing, input PCM hashes, and cached embedding bytes.

Evaluate strict within-session preferences only; do not turn least-bad into a
positive adequacy label. Group reference aliases by exact PCM/source hashes,
synthetic ancestry and parameter hashes, and conservative real filename stems
(with numeric take suffixes removed). Connected components keep transformed
versions together. Grouped five-fold validation uses training-fold scales and
nonnegative logistic weights. Compare existing 20 features with the same fit
plus two embedding cosine distances; separately report standalone encoders.
All historical evidence is development data; this is not an untouched test.

A hybrid must gain at least five percentage points in family-balanced agreement
over refitting the existing metric on identical folds, without reducing strict
pair accuracy, before it justifies a candidate-generation listening pilot.
Report per-family results and uncertainty; this screening gate is not a claim of
significance or sufficient recreation quality. Do not tune architectures to
these folds after seeing results and report the same folds as independent.
