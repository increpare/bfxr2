# Fine onset evidence for inverse experts

The five-reference calibration batch contains no convincing recreations.
Generation, not just selection, must improve. Inspection finds a concrete
representation difference: old Bfxr uses a 128-sample hop at 44.1 kHz while
newer full-sound features retain only 32 absolute positions over six seconds.
Their 48 relative positions retain broad gesture but cannot substitute for
fixed-time onset detail. This is a candidate cause, not an established cause
of the human failures.

Test an additional onset stream: 64 mel bands, 512-sample Hann FFT, 128-sample
hop, 128 centred frames at 44.1 kHz, peak-normalized, log power with a 72 dB
floor relative to the onset spectrum maximum. Keep trailing silence as silence;
do not stretch short sounds. Use the exact active trim from the existing
whole-sound descriptor. Preserve the entire existing descriptor for pitch,
duration and later events. Silence yields the floor, invalid input fails.

Use the same new two-stream architecture for both arms: frozen-descriptor
encoder plus onset Conv1d encoder, fused to numeric/category mixture heads.
The control arm gets a zero onset stream; the treatment gets actual onset
features. Both see the same rows, splits, normalization, losses, initialization,
minibatch order and training budget. Thus additional information is the intended
variable; this does not isolate onset resolution from the added high-frequency
bandwidth. Preserve frozen v3 as an external comparator.

First use Bfxr and Transfxr, each with the existing 12,288 examples, 90 epochs,
one numeric mode, and four categorical proposals at evaluation. A single mode
keeps this input experiment separate from mode routing. Replay exact source DSP
controls/seeds and verify waveform hashes when building the derived dataset.
Do not touch existing data, code bindings, checkpoints or listening artifacts.

Alternatives considered: another global/conditioned metric refit cannot create
missing candidates; a new differentiable renderer would change both objective
and optimization and the prior forward-gradient pilot already failed actual-DSP
checks. Retain those as separate future experiments.

Evaluate actual DSP output on the existing development probes plus fixed
validation rows (never train these). Report same-engine four-candidate best
objective, pitch diagnostics, failures, and validation parameter loss separately.
Prefer the onset arm only if its mean actual matching objective improves by at
least 5% on fixed validation renders and neither silence count nor reliable
static pitch accuracy worsens; this is permission for listening, not audible
success. Fresh listening must retain exact prior candidates and explicitly ask
for relative preference and adequacy, with human checks even for metric consensus.
