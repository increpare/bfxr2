# Neural-v1 quick listening · first partial batch

The user's 2026-10-04 attachment is preserved byte-for-byte in `feedback.json`.
It contains five judgments from the twelve-reference neural-v1 experiment:
four best choices and one rejection. No scalar ratings were supplied.

`manifest.json` verifies the original experiment/candidate identities and stores
all source controls, seeds, provenance and choices. The 24 FLAC files retain the
exact reference and candidate PCM; re-import verifies every decoded sample.
There are 19 distinct retained candidate identities. Diagnostic raw predictions
are archived for provenance but are absent from the presented quick choices.

| Reference | Choice |
| --- | --- |
| attack/spinout.wav | Original Bfxr |
| bird/Bird Sounds.WAV | Previous Soundboard |
| card/bookClose.ogg | Previous Transfxr |
| computer/robo_talk.wav | None are close |
| die/charm2.wav | Selected Transfxr |

All presented options were auditioned. The four winners supply seven strict
ordinal comparisons over four exact reference PCM groups. The rejection remains
explicit evidence of insufficient candidate quality; no scores or pairwise
winner labels are invented for it. This partial, familiar-reference development
batch cannot establish general sound quality or a model improvement.

The user also said the new listening flow was “much better”. That assessment is
about the interface and is kept separate from the sound labels.

See [the machine-readable review](../../evaluations/neural-v1-quick-01-human-review.json).
