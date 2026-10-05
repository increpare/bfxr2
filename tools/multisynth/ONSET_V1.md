# Fine onset inverse experiment: neither arm promoted

The latest human round had **zero convincing recreations**. Relative preferences
remain useful, but are not adequacy labels. This experiment tested whether adding
fine onset detail improves inverse candidate generation before asking for more
listening work.

Both Bfxr and Transfxr used 12,288 existing examples, identical splits, seeds,
initial weights, optimization and 90 epochs. The treatment adds a 64-band,
128-frame onset stream at a 128-sample hop; the matched control masks it. Both
retain the coarse whole-sound stream. Bandwidth also changes, so this is not a
pure temporal-resolution ablation.

All 24,576 source waveforms replayed exactly through actual DSP. Independent
sampled feature extraction matched the stored arrays. Saved checkpoints reproduce
full validation loss on CPU within 2.58e-8. Parameter validation loss improved for
both engines, but the actual rendered candidate checks did not clear the gate.

| Engine | Control mean distance | Onset mean distance | Static median pitch passes, control → onset |
| --- | ---: | ---: | ---: |
| Bfxr | 4.3984 | 4.0252 | 8/12 → 6/12 |
| Transfxr | 3.5752 | 3.4785 | 11/12 → 11/12 |

These are 32 fixed validation targets per engine, four proposals per target,
without search. Bfxr improves mean distance by 8.48% but regresses pitch; Transfxr
improves by 2.71%, below the predeclared 5% threshold. All targets have candidates
and none are silent. Neither model is promoted. Transfxr's better secondary
development-probe result does not override its failed primary gate. These are
checkpoint-validation examples, not untouched generalization or human evidence.

The [render audit](evaluations/onset-v1-render-audit.json) checks all candidate
file/PCM hashes and independently re-renders and rescores selected candidates.
It reuses recorded pitch diagnostics and nonselected scores; `allVerified` refers
to that stated scope. Two gate errors found during review were corrected:
comparisons now require complete populations in both arms, and increased silence
cannot hide behind fewer other failures. Original reports and their executing
source snapshot remain unchanged; corrected gates are in the separate audit.

Other retained evidence:

- [Data audit](evaluations/onset-v1-data-audit.json) and
  [checkpoint audit](evaluations/onset-v1-training-audit.json).
- [Old Bfxr search contribution](evaluations/onset-v1-search-contribution.json):
  retained staged optimization lowers actual matching distance on 15/16 shared
  probes relative to four raw neural guesses (mean 5.585 → 3.409). Different
  search budgets and starts prevent attribution solely to neural initialization.
- [Decoder inspection](evaluations/onset-v1-decoder-comparison.json): the actual
  working old Bfxr checkpoint is version 1 with a shared numeric head. Its code's
  optional waveform-specific heads were not used. That proposed historical
  explanation is disproved.

Checkpoints, raw reports, FLOAT candidate WAVs and five real-reference proposal
pools are retained under `runs/onset-v1/`. No new listening page was published.
Fine onset detail alone did not solve candidate generation. The older pipeline's
audio-based training and search remain material differences to investigate,
subject to actual-render pitch and gesture checks.
