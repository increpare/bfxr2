#!/usr/bin/env python3
"""Bake-off: current MatchObjective vs Zimtohrli vs CLAP vs harmonic features.

Scores are distances (lower = more similar). For each case we check whether
the expected winner ranks strictly better than the loser.

Outputs JSON to stdout and tools/bfxr_native/compare_out/metric_bakeoff.json
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torchaudio

TOOLS = Path(__file__).resolve().parents[2]  # .../tools
sys.path.insert(0, str(TOOLS))

from match.audio import SAMPLE_RATE, normalize_peak, prepare_target  # noqa: E402
from match.features import FeatureExtractor, FeatureWeights, feature_distance  # noqa: E402
from match.objective import MatchObjective  # noqa: E402
from match.renderer import BfxrRenderer  # noqa: E402

OUT = TOOLS / "bfxr_native" / "compare_out" / "metric_bakeoff.json"
SEED = 7


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class CurrentMetric:
    name = "current"
    lower_is_better = True

    def __init__(self):
        self._cache: dict[int, MatchObjective] = {}

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        key = id(a)
        if key not in self._cache:
            self._cache[key] = MatchObjective(a)
        return float(self._cache[key].score(b))


class ZimtohrliMetric:
    name = "zimtohrli"
    lower_is_better = True

    def __init__(self):
        from zimtohrli import Pyohrli
        self.z = Pyohrli()

    def _48k(self, x: np.ndarray) -> np.ndarray:
        x = normalize_peak(np.asarray(x, dtype=np.float32))
        t = torch.from_numpy(x).unsqueeze(0)
        y = torchaudio.functional.resample(t, SAMPLE_RATE, 48000).squeeze(0).numpy()
        return y.astype(np.float32)

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(self.z.distance(self._48k(a), self._48k(b)))


class ClapMetric:
    name = "clap"
    lower_is_better = True  # 1 - cosine

    def __init__(self):
        from transformers import ClapModel, ClapProcessor
        self.proc = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
        self.model = ClapModel.from_pretrained("laion/clap-htsat-unfused")
        self.model.eval()
        self._emb_cache: dict[int, torch.Tensor] = {}

    def _embed(self, x: np.ndarray) -> torch.Tensor:
        key = id(x)
        if key in self._emb_cache:
            return self._emb_cache[key]
        x = normalize_peak(np.asarray(x, dtype=np.float32))
        t = torch.from_numpy(x).unsqueeze(0)
        y = torchaudio.functional.resample(t, SAMPLE_RATE, 48000).squeeze(0).numpy()
        inputs = self.proc(audio=y, sampling_rate=48000, return_tensors="pt")
        with torch.no_grad():
            out = self.model.get_audio_features(**inputs)
            emb = out.pooler_output if hasattr(out, "pooler_output") else out
            emb = emb / emb.norm(dim=-1, keepdim=True)
        self._emb_cache[key] = emb
        return emb

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        ea, eb = self._embed(a), self._embed(b)
        return float(1.0 - (ea * eb).sum())


class HarmonicMetric:
    """f0-locked partial profile: richness, slope, odd/even, harmonicity."""
    name = "harmonic"
    lower_is_better = True
    K = 8

    def __init__(self):
        self.fx = FeatureExtractor()
        self.window = torch.hann_window(2048)
        self.freqs = torch.fft.rfftfreq(2048, 1.0 / SAMPLE_RATE)

    def _partials(self, wave: np.ndarray) -> np.ndarray:
        """Return mean [richness, slope, odd_even, harmonicity] over voiced frames."""
        w = torch.from_numpy(normalize_peak(np.asarray(wave, dtype=np.float32))).unsqueeze(0)
        if w.shape[1] < 2048:
            w = torch.nn.functional.pad(w, (0, 2048 - w.shape[1]))
        feats = self.fx.extract(w)
        frames = w.unfold(1, 2048, 512)  # (1, T, 2048)
        T = min(frames.shape[1], feats.voiced.shape[1])
        voiced = feats.voiced[0, :T]
        f0 = (2.0 ** feats.f0_log2[0, :T]).clamp(min=40.0)
        if not bool(voiced.any()):
            return np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)

        specs = torch.fft.rfft(frames[0, :T] * self.window)  # (T, F)
        mag = specs.abs()
        rows = []
        for t in range(T):
            if not bool(voiced[t]):
                continue
            fund = float(f0[t])
            amps = []
            for k in range(1, self.K + 1):
                hz = fund * k
                if hz >= SAMPLE_RATE / 2 - 50:
                    amps.append(0.0)
                    continue
                # nearest bin ±2
                idx = int(round(hz * 2048 / SAMPLE_RATE))
                lo, hi = max(1, idx - 2), min(mag.shape[1] - 1, idx + 2)
                amps.append(float(mag[t, lo : hi + 1].max()))
            a = np.array(amps, dtype=np.float64)
            a1 = max(a[0], 1e-12)
            an = a / a1
            # richness: energy in 2..K vs 1..K
            richness = float(a[1:].sum() / (a.sum() + 1e-12))
            # slope: linear fit of log amps vs k (only where above threshold)
            ks = np.arange(1, self.K + 1, dtype=np.float64)
            mask = an > 0.05
            if mask.sum() >= 2:
                slope = float(np.polyfit(ks[mask], np.log10(an[mask] + 1e-12), 1)[0])
            else:
                slope = 0.0
            odd = a[0::2].sum()
            even = a[1::2].sum()
            odd_even = float((odd - even) / (odd + even + 1e-12))
            # harmonicity: harmonic peak energy / nearby band energy
            harm = a.sum()
            # residual: mean mag away from partials in voiced band
            band = mag[t, 1 : int(self.K * fund * 2048 / SAMPLE_RATE) + 1]
            total = float(band.sum()) + 1e-12
            harmonicity = float(min(1.0, harm / total))
            rows.append([richness, slope, odd_even, harmonicity])
        if not rows:
            return np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        return np.mean(np.asarray(rows), axis=0)

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        va, vb = self._partials(a), self._partials(b)
        # weight slope less (can be noisy); richness/harmonicity more
        w = np.array([1.5, 0.75, 1.0, 1.25])
        return float(np.sum(w * np.abs(va - vb)))


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

@dataclass
class Case:
    group: str
    name: str
    winner: np.ndarray
    loser: np.ndarray
    target: np.ndarray
    note: str = ""


def render(renderer: BfxrRenderer, **params) -> np.ndarray:
    return renderer.render(params, seed=SEED)


def synthetic_cases(renderer: BfxrRenderer) -> list[Case]:
    cases = []
    # rising vs falling
    target = render(renderer, waveType=4, frequency_start=0.3,
                    frequency_slide=0.25, sustainTime=0.3, decayTime=0.35)
    rising = render(renderer, waveType=4, frequency_start=0.27,
                    frequency_slide=0.22, sustainTime=0.28, decayTime=0.33)
    falling = render(renderer, waveType=4, frequency_start=0.3,
                     frequency_slide=-0.25, sustainTime=0.3, decayTime=0.35)
    cases.append(Case("structure", "rising_beats_falling", rising, falling, target,
                      "rising sweep should beat falling against rising target"))

    # noise vs tone for noise target
    target = render(renderer, waveType=3, frequency_start=0.3, sustainTime=0.25, decayTime=0.4)
    noise = render(renderer, waveType=3, frequency_start=0.4, sustainTime=0.2, decayTime=0.35)
    tone = render(renderer, waveType=2, frequency_start=0.3, sustainTime=0.25, decayTime=0.4)
    cases.append(Case("structure", "noise_beats_tone", noise, tone, target))

    # tone vs noise for tonal
    target = render(renderer, waveType=2, frequency_start=0.35, sustainTime=0.25, decayTime=0.35)
    tone = render(renderer, waveType=4, frequency_start=0.33, sustainTime=0.22, decayTime=0.32)
    noise = render(renderer, waveType=3, frequency_start=0.35, sustainTime=0.25, decayTime=0.35)
    cases.append(Case("structure", "tone_beats_noise", tone, noise, target))

    # overtones: richer should beat pure sine against rich target
    target = render(renderer, waveType=0, frequency_start=0.35, sustainTime=0.3, decayTime=0.35,
                    overtones=0.6, overtoneFalloff=0.2, squareDuty=0.3)
    rich = render(renderer, waveType=0, frequency_start=0.34, sustainTime=0.28, decayTime=0.33,
                  overtones=0.55, overtoneFalloff=0.25, squareDuty=0.3)
    pure = render(renderer, waveType=2, frequency_start=0.35, sustainTime=0.3, decayTime=0.35,
                  overtones=0.0, overtoneFalloff=0.0)
    cases.append(Case("timbre", "rich_beats_pure", rich, pure, target,
                      "overtone-rich square should beat sine against rich target"))

    # square vs saw (odd vs all harmonics) against square target
    target = render(renderer, waveType=0, frequency_start=0.4, sustainTime=0.25, decayTime=0.3,
                    squareDuty=0.5)
    square = render(renderer, waveType=0, frequency_start=0.39, sustainTime=0.24, decayTime=0.28,
                    squareDuty=0.5)
    saw = render(renderer, waveType=1, frequency_start=0.4, sustainTime=0.25, decayTime=0.3)
    cases.append(Case("timbre", "square_beats_saw", square, saw, target))

    # identity sanity: identical should beat unrelated
    a = render(renderer, waveType=4, frequency_start=0.4, sustainTime=0.2, decayTime=0.3)
    b = render(renderer, waveType=3, frequency_start=0.5, sustainTime=0.4, decayTime=0.5)
    cases.append(Case("sanity", "identity_beats_other", a, b, a))
    return cases


def real_match_cases() -> list[Case]:
    """target.wav vs its matched .bfxr.wav (winner) vs another match (loser)."""
    targets = TOOLS / "targets"
    pairs = []
    for wav in sorted(targets.glob("*.wav")):
        if wav.name.lower().endswith(".bfxr.wav"):
            continue
        match = wav.with_suffix(".bfxr.wav")
        if not match.exists():
            # try Name.bfxr.wav pattern already covered; also batch_out
            alt = targets / f"{wav.stem}.bfxr.wav"
            match = alt if alt.exists() else None
        if match is None or not match.exists():
            continue
        pairs.append((wav, match))

    cases = []
    for i, (tw, mw) in enumerate(pairs[:8]):
        target = prepare_target(tw)
        winner = prepare_target(mw)
        # loser: another target's match, or another target
        other = pairs[(i + 3) % len(pairs)][1]
        loser = prepare_target(other)
        cases.append(Case(
            "real_match", tw.stem, winner, loser, target,
            f"matched bfxr should beat unrelated match ({other.stem})",
        ))
    return cases


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def eval_case(metric, case: Case) -> dict:
    d_win = metric.distance(case.target, case.winner)
    d_lose = metric.distance(case.target, case.loser)
    ok = d_win < d_lose
    margin = d_lose - d_win
    return {
        "group": case.group,
        "name": case.name,
        "metric": metric.name,
        "d_winner": d_win,
        "d_loser": d_lose,
        "margin": margin,
        "pass": ok,
        "note": case.note,
    }


def main() -> int:
    print("Loading metrics…", flush=True)
    metrics = []
    metrics.append(CurrentMetric())
    try:
        metrics.append(ZimtohrliMetric())
        print("  zimtohrli ready", flush=True)
    except Exception as e:
        print(f"  zimtohrli SKIP: {e}", flush=True)
    try:
        metrics.append(ClapMetric())
        print("  clap ready", flush=True)
    except Exception as e:
        print(f"  clap SKIP: {e}", flush=True)
    metrics.append(HarmonicMetric())
    print("  harmonic ready", flush=True)

    print("Building cases…", flush=True)
    with BfxrRenderer(jobs=2) as renderer:
        cases = synthetic_cases(renderer)
    cases.extend(real_match_cases())
    print(f"  {len(cases)} cases × {len(metrics)} metrics", flush=True)

    rows = []
    for case in cases:
        for metric in metrics:
            # clear current-metric cache keyed on target id when target changes
            row = eval_case(metric, case)
            rows.append(row)
            mark = "PASS" if row["pass"] else "FAIL"
            print(f"  [{mark}] {metric.name:10s} {case.group}/{case.name}: "
                  f"win={row['d_winner']:.4f} lose={row['d_loser']:.4f} "
                  f"Δ={row['margin']:+.4f}", flush=True)

    # summary
    summary = {}
    for m in metrics:
        mrows = [r for r in rows if r["metric"] == m.name]
        summary[m.name] = {
            "n": len(mrows),
            "passed": sum(1 for r in mrows if r["pass"]),
            "by_group": {},
        }
        for g in sorted({r["group"] for r in mrows}):
            grows = [r for r in mrows if r["group"] == g]
            summary[m.name]["by_group"][g] = {
                "passed": sum(1 for r in grows if r["pass"]),
                "n": len(grows),
            }

    payload = {"summary": summary, "rows": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {OUT}", flush=True)
    print("\n=== SUMMARY (pass rate) ===")
    for name, s in summary.items():
        print(f"  {name:10s}  {s['passed']}/{s['n']}  {s['by_group']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
