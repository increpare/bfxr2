"""Alternate similarity metrics for library nearest-neighbor bake-offs.

Each metric maps audio → analysis space and defines a distance (lower = closer).
Library-side transforms are meant to be computed once and reused across targets.
"""
from __future__ import annotations

import numpy as np
import torch
import torchaudio

from .audio import SAMPLE_RATE, normalize_peak
from .features import FeatureExtractor
from .objective import CandidateCache, MatchObjective


def _to_48k(x: np.ndarray) -> np.ndarray:
    x = normalize_peak(np.asarray(x, dtype=np.float32))
    t = torch.from_numpy(x).unsqueeze(0)
    return torchaudio.functional.resample(t, SAMPLE_RATE, 48000).squeeze(0).numpy().astype(
        np.float32
    )


class CurrentMetric:
    name = "current"

    def distances_to_library(
        self,
        target: np.ndarray,
        library: list[np.ndarray],
        lib_cache: CandidateCache | None = None,
        chunk: int = 64,
    ) -> np.ndarray:
        obj = MatchObjective(target)
        if lib_cache is not None:
            return obj.score_candidates(lib_cache)
        out = np.empty(len(library), dtype=np.float64)
        for i in range(0, len(library), chunk):
            batch = library[i : i + chunk]
            out[i : i + len(batch)] = obj.score_batch(batch)
        return out


class HarmonicMetric:
    name = "harmonic"
    K = 8
    WEIGHTS = np.array([1.5, 0.75, 1.0, 1.25])

    def __init__(self):
        self.fx = FeatureExtractor()
        self.window = torch.hann_window(2048)

    def embed(self, wave: np.ndarray) -> np.ndarray:
        w = torch.from_numpy(normalize_peak(np.asarray(wave, dtype=np.float32))).unsqueeze(0)
        if w.shape[1] < 2048:
            w = torch.nn.functional.pad(w, (0, 2048 - w.shape[1]))
        feats = self.fx.extract(w)
        frames = w.unfold(1, 2048, 512)
        T = min(frames.shape[1], feats.voiced.shape[1])
        voiced = feats.voiced[0, :T]
        f0 = (2.0 ** feats.f0_log2[0, :T]).clamp(min=40.0)
        if not bool(voiced.any()):
            return np.zeros(4, dtype=np.float64)

        mag = torch.fft.rfft(frames[0, :T] * self.window).abs()
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
                idx = int(round(hz * 2048 / SAMPLE_RATE))
                lo, hi = max(1, idx - 2), min(mag.shape[1] - 1, idx + 2)
                amps.append(float(mag[t, lo : hi + 1].max()))
            a = np.asarray(amps, dtype=np.float64)
            an = a / max(a[0], 1e-12)
            richness = float(a[1:].sum() / (a.sum() + 1e-12))
            ks = np.arange(1, self.K + 1, dtype=np.float64)
            mask = an > 0.05
            slope = (
                float(np.polyfit(ks[mask], np.log10(an[mask] + 1e-12), 1)[0])
                if mask.sum() >= 2
                else 0.0
            )
            odd, even = a[0::2].sum(), a[1::2].sum()
            odd_even = float((odd - even) / (odd + even + 1e-12))
            band_hi = max(2, int(self.K * fund * 2048 / SAMPLE_RATE) + 1)
            band_hi = min(band_hi, mag.shape[1])
            harmonicity = float(min(1.0, a.sum() / (float(mag[t, 1:band_hi].sum()) + 1e-12)))
            rows.append([richness, slope, odd_even, harmonicity])
        if not rows:
            return np.zeros(4, dtype=np.float64)
        return np.mean(np.asarray(rows), axis=0)

    def embed_library(self, library: list[np.ndarray]) -> np.ndarray:
        return np.stack([self.embed(w) for w in library], axis=0)

    def distances_to_library(
        self, target: np.ndarray, library: list[np.ndarray],
        lib_emb: np.ndarray | None = None,
    ) -> np.ndarray:
        if lib_emb is None:
            lib_emb = self.embed_library(library)
        t = self.embed(target)
        return np.sum(self.WEIGHTS * np.abs(lib_emb - t[None, :]), axis=1)


class ZimtohrliMetric:
    name = "zimtohrli"

    def __init__(self):
        from zimtohrli import Pyohrli
        self.z = Pyohrli()

    @staticmethod
    def resample_library(library: list[np.ndarray]) -> list[np.ndarray]:
        """48kHz peak-normalized copies — call once, reuse across targets."""
        out = []
        for i, w in enumerate(library):
            out.append(_to_48k(w))
            if i > 0 and i % 1000 == 0:
                print(f"  resample 48k {i}/{len(library)}", flush=True)
        return out

    @staticmethod
    def pad_library_equal(lib_48k: list[np.ndarray]) -> tuple[list[np.ndarray], int]:
        """Pad every library clip to the same length (required by Pyohrli)."""
        L = max(len(w) for w in lib_48k)
        padded = [
            w if len(w) == L else np.ascontiguousarray(np.pad(w, (0, L - len(w))))
            for w in lib_48k
        ]
        return padded, L

    def distances_to_library(
        self,
        target: np.ndarray,
        library: list[np.ndarray],
        lib_48k: list[np.ndarray] | None = None,
        lib_len: int | None = None,
    ) -> np.ndarray:
        ta = _to_48k(target)
        if lib_48k is None:
            lib_48k = self.resample_library(library)
            lib_48k, lib_len = self.pad_library_equal(lib_48k)
        elif lib_len is None:
            lib_len = max(len(w) for w in lib_48k)
        L = max(len(ta), lib_len)
        if len(ta) < L:
            ta = np.ascontiguousarray(np.pad(ta, (0, L - len(ta))))
        out = np.empty(len(lib_48k), dtype=np.float64)
        # If target is longer than the pre-padded library, pad candidates on the fly.
        need_pad = L > lib_len
        for i, w48 in enumerate(lib_48k):
            b = w48 if not need_pad else np.ascontiguousarray(np.pad(w48, (0, L - len(w48))))
            out[i] = float(self.z.distance(ta, b))
            if i > 0 and i % 1000 == 0:
                print(f"  zimtohrli {i}/{len(lib_48k)}", flush=True)
        return out


class ClapMetric:
    name = "clap"

    def __init__(self):
        from transformers import ClapModel, ClapProcessor
        self.proc = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
        self.model = ClapModel.from_pretrained("laion/clap-htsat-unfused")
        self.model.eval()

    def embed_many(
        self,
        waves: list[np.ndarray],
        waves_48k: list[np.ndarray] | None = None,
    ) -> np.ndarray:
        ys = waves_48k if waves_48k is not None else [_to_48k(w) for w in waves]
        inputs = self.proc(audio=ys, sampling_rate=48000, return_tensors="pt", padding=True)
        with torch.no_grad():
            out = self.model.get_audio_features(**inputs)
            emb = out.pooler_output if hasattr(out, "pooler_output") else out
            emb = emb / emb.norm(dim=-1, keepdim=True)
        return emb.cpu().numpy().astype(np.float64)

    def embed(self, wave: np.ndarray) -> np.ndarray:
        return self.embed_many([wave])[0]

    def embed_library(
        self,
        library: list[np.ndarray],
        chunk: int = 16,
        lib_48k: list[np.ndarray] | None = None,
    ) -> np.ndarray:
        embs = []
        for i in range(0, len(library), chunk):
            if lib_48k is not None:
                batch_48 = lib_48k[i : i + chunk]
                embs.append(self.embed_many(library[i : i + chunk], waves_48k=batch_48))
            else:
                embs.append(self.embed_many(library[i : i + chunk]))
            done = min(i + chunk, len(library))
            if (i // chunk) % 10 == 0 or done == len(library):
                print(f"  clap embed {done}/{len(library)}", flush=True)
        return np.concatenate(embs, axis=0)

    def distances_to_library(
        self, target: np.ndarray, library: list[np.ndarray],
        lib_emb: np.ndarray | None = None,
    ) -> np.ndarray:
        if lib_emb is None:
            lib_emb = self.embed_library(library)
        t = self.embed(target)
        # cosine distance
        return 1.0 - (lib_emb @ t)


def make_metric(name: str):
    return {
        "current": CurrentMetric,
        "harmonic": HarmonicMetric,
        "zimtohrli": ZimtohrliMetric,
        "clap": ClapMetric,
    }[name]()
