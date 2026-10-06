# Remove the silent-buffer scoring incentive before further listening

A controlled probe on all five latest exact earlier winners finds that appending
one or four seconds of digital zeros lowers historical MatchObjective distance.
Envelope and mel errors are averaged over the longest waveform. A native joint
search produced10.328seconds of output with its last sample above -60dB relative
peak at0.573seconds. A separate verifier also incorrectly audition-normalized an
already exported PCM16 clip a second time; the recovery preserves unchanged search
semantics and requires exact interrupted-output replay. Retain both findings.

## Analysis repair

Keep historical MatchObjective and all earlier experiments immutable. Add an
experimental SupportObjective wrapper: analyze each target/candidate through its
last sample above .001 of peak (-60dB amplitude), plus882samples (20ms) context,
zero-padding that context when needed. Preserve leading silence and every later
above-threshold event. Export/play the complete native PCM unchanged. Silence
maps to a single zero. This is an explicit analysis threshold, not a claim about
all human audibility. Reject use of historical precomputed feature caches.

Tests must show exact appended-zero score invariance for target and candidate,
retained onset-delay and extra-event penalties, quiet PCM-floor tails excluded
from support, and immutable source input. Audit invariance on all five feedback
winners as well, preserving unmodified reference/candidate audio.

## Fresh fixed follow-up

Use the same four heuristic multi-event initial patches, fixed before new fits.
All four remain regardless of score. Both timing-only and joint-control arms use
768 attempts, seed20261107+1009*originalTrialIndex, and the same existing mutation
recipe; only their allowed control families differ. Run independent arms in three
processes. Score one audition export with SupportObjective and verify that exact
PCM using bare SupportObjective, never another export conversion. Persist controls
before final verification. No neural weights change. This is a search-space test
under the corrected experimental analysis policy, not an equal-budget comparison
to the historical2048-attempt run or proof of perceptual improvement.

Publish two new results and the exact latest human winner on each of four external
development references. Merge exact PCM aliases; preserve the buffered UI and
immediate adequacy/mismatch questions. These references overlap historical Bfxr
training. Verify native uncached replay, all scores, constraints, unique complete
trial sets, source hashes and served assets. The earlier joint-events-v1 run is
retained as a scoring diagnostic, not sent out as another listening batch.
