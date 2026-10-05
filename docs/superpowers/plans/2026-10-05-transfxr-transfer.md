# Transfxr robustness and transfer plan

Execute inline under existing autonomous authorization, using executing-plans.

Goal: answer robustness/transfer empirically without equating synth capacity
with quality of the current inverse model.

- [x] Freeze target manifest and transformation recipes before inference.
- [x] Run private `transfxr-transfer-v1.py` on 64 altered/clean self targets,
      all other active synths, and five repeated real targets. Save all candidates.
- [x] Replay selected outputs; independently rescore, recompute pitch diagnostics
      and paired summaries. Verify source, checkpoint and transformation bindings.
- [x] Review interpretation and report limitations alongside measured outcomes.

Completed 90 targets, zero missing/failed proposals. Source audit: 29 exact DSP
sources, 64 exact perturbations, five exact real PCM copies. Candidate audit:
1,170 files verified, 235 selected DSP replays/rescores, zero score error.
Six fixed listening cases exported; HTML/results/18 WAVs verified over HTTP.
Browser opens at 0/6 judgments; no assistant choices entered.
