"""Synthetic ranking probes for pitch-structure failures.

Each probe is a (target, good, bad) triple of bfxr param dicts. The objective
passes a probe when it scores `good` below `bad`. No real product WAVs are
needed, so this is the daily engineering gate.

Handicap tiers. With `good` rendered as a near-copy of `target` the current
objective already scores 14/14 — the probe tests no trade-off and is useless.
The failure that actually happens in search is a *structurally correct but
timbrally imperfect* candidate losing to a *timbrally perfect but structurally
wrong* one. So `good` carries a deliberate handicap:

  gate tier (`good`)     same waveType, ~2 semitones off, envelope wobble
  report tier (`severe`) additionally a different waveType

Only the gate tier is asserted. Requiring structure to beat a whole-waveType
error would need a penalty ~3x larger, which would swamp timbre matching on
real targets.

Structure families use sustainTime=0.6 (~71 frames): at sustainTime=0.3 (22
frames) the note detector misses the middle note of a 3-note arpeggio.

    PYTHONPATH=. uv run python -m match.structure_probes
    PYTHONPATH=. uv run python -m match.structure_probes --describe
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

from .objective import MatchObjective
from .renderer import BfxrRenderer

RENDER_SEED = 1234
PASS_THRESHOLD = 12  # of len(PROBES); spec Section 1

_S = dict(sustainTime=0.6, decayTime=0.15)   # target / bad
_G = dict(sustainTime=0.6, decayTime=0.18)   # good: envelope wobble


def _t(**kw) -> dict:
    return {**_S, **kw}


def _g(**kw) -> dict:
    return {**_G, **kw}


@dataclass(frozen=True)
class Probe:
    id: str
    family: str
    target: dict
    good: dict
    bad: dict
    severe: dict


@dataclass(frozen=True)
class ProbeResult:
    id: str
    family: str
    good: float
    bad: float
    severe: float
    passed: bool
    severe_passed: bool
    margin: float


# pitch_jump_amount values, via notes.pitch_jump_param_from_ratio:
#   +0.61  -> ratio 1.50 (+7 st)      -0.2236 -> ratio 0.667 (-7 st)
#   +0.45  -> ratio 1.22 (+3.5 st)    +0.58   -> ratio 1.43 (+6.2 st)
#   -0.21  -> ratio 0.694 (-6.3 st)
# frequency_slide 0.10 sweeps 320->461 Hz (+6.1 st); -0.10 sweeps 884->614 Hz.
PROBES: list[Probe] = [
    Probe("notes_2_up_gliss", "notes_2_up",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.30, frequency_slide=0.10),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_2_up_flat", "notes_2_up",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.3318),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_2_down_gliss", "notes_2_down",
          _t(waveType=2, frequency_start=0.50, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.50, frequency_slide=-0.10),
          _g(waveType=0, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_2_down_flat", "notes_2_down",
          _t(waveType=2, frequency_start=0.50, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.4519),
          _g(waveType=0, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_3_arp_gliss", "notes_3_arp",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.33, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.66),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68),
          _t(waveType=2, frequency_start=0.30, frequency_slide=0.10),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68)),
    Probe("notes_3_arp_count", "notes_3_arp",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.33, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.66),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68),
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68)),
    Probe("gliss_up_steps", "gliss_up",
          _t(waveType=2, frequency_start=0.30, frequency_slide=0.10),
          _g(waveType=2, frequency_start=0.318, frequency_slide=0.10),
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.58,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.318, frequency_slide=0.10)),
    Probe("gliss_down_steps", "gliss_down",
          _t(waveType=2, frequency_start=0.50, frequency_slide=-0.10),
          _g(waveType=2, frequency_start=0.53, frequency_slide=-0.10),
          _t(waveType=2, frequency_start=0.50, pitch_jump_amount=-0.21,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.53, frequency_slide=-0.10)),
    Probe("dir_flip_up", "dir_flip",
          _t(waveType=2, frequency_start=0.35, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.368, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.35, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.368, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55)),
    Probe("dir_flip_down", "dir_flip",
          _t(waveType=2, frequency_start=0.45, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.478, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.45, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.478, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55)),
    Probe("mute_tail_tone", "mute_tail",
          dict(waveType=2, frequency_start=0.35, sustainTime=0.6, decayTime=0.3),
          dict(waveType=2, frequency_start=0.368, sustainTime=0.58, decayTime=0.32),
          dict(waveType=2, frequency_start=0.35, sustainTime=0.08, decayTime=0.05),
          dict(waveType=0, frequency_start=0.368, sustainTime=0.58, decayTime=0.32)),
    Probe("mute_tail_sweep", "mute_tail",
          dict(waveType=2, frequency_start=0.30, frequency_slide=0.06,
               sustainTime=0.6, decayTime=0.3),
          dict(waveType=2, frequency_start=0.318, frequency_slide=0.06,
               sustainTime=0.58, decayTime=0.32),
          dict(waveType=2, frequency_start=0.30, frequency_slide=0.06,
               sustainTime=0.06, decayTime=0.05),
          dict(waveType=0, frequency_start=0.318, frequency_slide=0.06,
               sustainTime=0.58, decayTime=0.32)),
    Probe("noise_onset_mute", "noise_onset",
          dict(waveType=3, frequency_start=0.45, sustainTime=0.3, decayTime=0.3),
          dict(waveType=3, frequency_start=0.42, sustainTime=0.32, decayTime=0.28),
          dict(waveType=3, frequency_start=0.45, sustainTime=0.03, decayTime=0.03),
          dict(waveType=3, frequency_start=0.30, sustainTime=0.32, decayTime=0.28)),
    Probe("noise_onset_tone", "noise_onset",
          dict(waveType=3, frequency_start=0.45, sustainTime=0.3, decayTime=0.3),
          dict(waveType=3, frequency_start=0.42, sustainTime=0.32, decayTime=0.28),
          dict(waveType=2, frequency_start=0.45, sustainTime=0.3, decayTime=0.3),
          dict(waveType=3, frequency_start=0.30, sustainTime=0.32, decayTime=0.28)),
]

# The six that fail against the pre-structure-term objective. These must pass.
STRUCTURE_IDS = (
    "notes_2_up_gliss",
    "notes_2_down_gliss",
    "notes_3_arp_gliss",
    "notes_3_arp_count",
    "gliss_up_steps",
    "gliss_down_steps",
)


def evaluate(objective_factory=MatchObjective) -> list[ProbeResult]:
    """Render every probe and score good/bad/severe against its target."""
    results: list[ProbeResult] = []
    with BfxrRenderer() as renderer:
        for probe in PROBES:
            waves = []
            for params in (probe.target, probe.good, probe.bad, probe.severe):
                wave = renderer.render(params, seed=RENDER_SEED)
                if wave is None or len(wave) == 0:
                    raise RuntimeError(f"probe {probe.id}: render failed")
                waves.append(wave)
            target, good, bad, severe = waves
            objective = objective_factory(target)
            g = objective.score(good)
            b = objective.score(bad)
            s = objective.score(severe)
            results.append(ProbeResult(
                id=probe.id, family=probe.family,
                good=g, bad=b, severe=s,
                passed=g < b, severe_passed=s < b, margin=b - g,
            ))
    return results


def _describe() -> int:
    """Print the detected structure of each probe wave — use this when
    retuning params, so a probe never silently stops testing what it names."""
    import numpy as np
    import torch

    from .audio import normalize_peak
    from .features import FeatureExtractor, frame_count
    from .notes import detect_note_sequence

    extractor = FeatureExtractor()

    def structure_of(wave) -> str:
        length = max(len(wave), 4096)
        batch = torch.zeros(1, length + 2048)
        batch[0, : len(wave)] = torch.from_numpy(
            normalize_peak(np.asarray(wave, dtype=np.float32)).copy()
        )
        feats = extractor.extract(batch).slice(0, frame_count(length))
        notes = detect_note_sequence(
            feats.f0_log2[0].numpy(), feats.voiced[0].numpy()
        )
        return f"{len(notes)} notes {[round(hz, 1) for hz, _ in notes]}"

    with BfxrRenderer() as renderer:
        for probe in PROBES:
            print(f"{probe.id}:")
            for role in ("target", "good", "bad", "severe"):
                wave = renderer.render(getattr(probe, role), seed=RENDER_SEED)
                print(f"    {role:8s} {structure_of(wave)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="match.structure_probes")
    parser.add_argument("--describe", action="store_true",
                        help="print detected note structure per probe wave")
    args = parser.parse_args(argv)
    if args.describe:
        return _describe()

    results = evaluate()
    print(f"{'id':22s} {'good':>7s} {'bad':>7s} {'margin':>8s} {'severe':>7s}  gate")
    for r in results:
        print(f"{r.id:22s} {r.good:7.3f} {r.bad:7.3f} {r.margin:+8.3f} "
              f"{r.severe:7.3f}  {'PASS' if r.passed else 'FAIL'}"
              f"{'' if r.severe_passed else '  (severe FAIL)'}")
    n_pass = sum(r.passed for r in results)
    n_severe = sum(r.severe_passed for r in results)
    print(f"\ngate (mild): {n_pass}/{len(results)}  "
          f"(threshold {PASS_THRESHOLD})")
    print(f"report (severe): {n_severe}/{len(results)}")
    failed = [r.id for r in results if not r.passed]
    if failed:
        print("failed: " + ", ".join(failed))
    return 0 if n_pass >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
