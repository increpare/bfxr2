# Actual-render pitch calibration

User authority: continue autonomously until useful human quality input is needed.
The user explicitly emphasizes pitch, event gesture and human listening. Routine
implementation/design questions are already delegated; do not ask for approval.

## Evidence and alternatives

The complete v5 input ablation regresses versus v3 on ordinary probes. Its input
fix is real, but the trained inverse is not promoted. High-register examples are
sparse, and three of four upper-register targets have no close-pitch proposal.
The frozen v3 experts remain the working baseline.

Options: expand and retrain frequency coverage (still desirable, but another
separate data experiment); use known synth frequency mappings with measured
pitch and actual rendering (chosen bounded prerequisite); revive unconstrained
surrogate gradients (previous actual-DSP failure argues against doing that now).
This stage tests a hybrid inference component, not a new learned-model win.

## Scope and algorithm

Create new versioned-policy code; leave all prior modules/checkpoints intact.
Use the frozen v5 pitch diagnostic, with its documented limitations. A target is
strongly pitched only when reliable, voicedFraction >= .8, and at least16 voiced
frames. A target is stationary only when additionally spanSemitones <= .5.
Noisy/unreliable targets retain original proposals and original score selection.

For each actual-rendered Bfxr/Transfxr/Pluckr proposal, keep the original. If both
target and candidate have reliable pitch with at least16 aligned voiced frames,
try at most3 actual-render pitch adjustments, preserving seed, categorical sound
source, timbre, amplitude and envelope controls. Derive a global register shift
from the median signed target-minus-candidate log pitch on aligned frames; bound
each moving-target adjustment to +/-24 semitones. Frequency mappings:
Bfxr f scales with frequency_start^2+.001 (nominal Hz =3528*(s^2+.001));
Transfxr f=40*2^(7*p), shifting both pitch endpoints equally;
Pluckr f=55*2^(4*p). Clamp using real schema bounds and record clamp/no-change.
A moving target never has its pitch-gesture controls flattened.

For a reliably stationary target, the first proposal sets nominal frequency from
the target median and explicitly removes predicted pitch motion only:
Bfxr frequency_slide, frequency_acceleration, vibratoDepth, pitch_jump_amount and
pitch_jump_2_amount become0; Transfxr pitch.start/end equal log2(hz/40)/7 and
vibrato.start/end become0; Pluckr pitch is log2(hz/55)/4 and vibrato becomes0.
Do not alter Bfxr repeat timing, duty, bitcrush, filters, or minimum-frequency
control; do not alter Pluckr string count/inharmonicity/tremolo. Subsequent steps
use measured register residuals, so nominal mapping is not assumed exact.

Accept an adjusted proposal into the pool only if it is finite/audible, retains
candidate pitch reliability, does not lose aligned voiced pairs, keeps sample
length within max(2 samples,2% of original length), improves mean aligned contour
error by at least .01 semitone, does not increase span error by more than .25
semitones, and does not reduce target-active-frame in-tolerance fraction. Rejects,
render errors, silence, duplicate canonical controls, bounds and reasons are
recorded. Stop that candidate after a rejected/non-progressing attempt. Originals
always remain available. There is no surrogate and no unconstrained random search.

## Selection

Baseline is minimum unchanged MatchObjective among originals. The unconstrained
expanded-pool minimum is also reported, separately from the experimental choice.
For a strong target, eligible candidates require reliable pitch, >=.8 voicing,
>=16 aligned pairs, median error <=1 semitone, >=.75 of ALL target-active frames
within1 semitone, matching voiced-span direction, and span error <=max(1 semitone,
.2*target span). This is diagnostic eligibility, not an auditory success label.
Also preserve baseline evidence whenever its pitch is reliable: do not reduce
active-frame tolerance, worsen contour mean by more than .05 semitone or span
error by more than .25, or lose an already matching direction. Select minimum
unchanged MatchObjective among eligible originals+accepted adjustments. If none
qualify, retain the exact original baseline. Unreliable targets use baseline.
This explicitly tests pitch-first selection; higher objective values are reported,
not hidden or reweighted. Relative-time pitch does not establish duration fidelity.

## Verification and resource accounting

Unit tests plus real renderer regression cases must cover noisy/silent targets,
steady tones, moving pitch preservation, bounds, failed/duplicate renders, seed
and nonpitch-control preservation, candidate rejection and safe selection fallback.
Static fixes must be checked on actual Bfxr/Transfxr/Pluckr, not ideal sine alone.

The first production probe consumes the immutable temporal-v3 candidate pools in
runs/pitch-v5/{paired,high-pitch}/results.json. Verify report/audio/DSP identities
and replay originals. Bind all new code, policies, original report/checkpoint
identities, parameters, seeds, failures and every actual FLOAT render. Compare
original, expanded-objective and pitch-first choices on the same24 targets.
Record at most36 additional proposal renders per12-original target; validation
replays are separate overhead. This is not equal-compute training improvement.

Before running, the development gate is: at least3/4 upper-register choices are
pitch-eligible; no previously passing ordinary static median or moving direction
is lost; ordinary moving mean contour/span error does not worsen by more than
.1/.25 semitones; ordinary mean MatchObjective <=1.1 times baseline and high-pitch
mean does not worsen; no missing originals or silent/failed selected outputs.
Failure is retained and diagnosed, not silently relaxed after seeing results.

Only after useful actual results, create a short human comparison from tagged
references with exact previous PCM anchors. Existing heard references may use
cached v3 raw/refined fits and original Bfxr fits as candidate sources, each with
provenance verified before calibration; no human choice labels enter selection.
Publish only genuinely new comparison opportunities (skip redundant identical
candidate/anchor sets), at most5 items, using the existing quick best/tie/none UI.
Retain both charm2 histories when relevant. Human review is required even when
all diagnostics agree. This component alone does not establish a general inverse
model, solve timbre or replace further training/data work.
