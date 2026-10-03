# Tonal Feasibility Constraint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in feasibility-first matcher that prevents tonal targets from winning with unvoiced candidates, preserves human-rated exemplars, validates exact emitted/held-out artifacts, and runs the strict blind 10→32 target experiment.

**Architecture:** A pure `TonalFeasibility` component evaluates already-extracted `Features`. `MatchObjective` exposes its existing candidate analysis so search does not repeat FFT/pitch work. `StagedOptimizer` stores raw objective and feasibility separately, sends ordinal lexicographic ranks to constrained CMA populations, and leaves the default path byte-for-byte unchanged. The matcher and headroom driver report exact PCM-16 and held-out validation, while the blind page masks invalid treatment cells and keeps arm identities separate.

**Tech Stack:** Python 3.12, NumPy, PyTorch, torchaudio, SoundFile, CMA-ES (`cma`), pytest, the existing native/Node Bfxr render workers.

**Design:** `docs/superpowers/specs/2026-07-28-tonal-feasibility-constraint-design.md`

---

## File map

| File | Responsibility |
|---|---|
| `tools/match/feasibility.py` | Pure target applicability, aligned tonal preservation, result serialization |
| `tools/match/objective.py` | Return objective scores and the candidate `Features` already computed in that pass |
| `tools/match/optimizer.py` | Candidate rank key, constrained population fitness, final feasible filtering |
| `tools/match/validation.py` | Exact emitted-WAV and held-out-render analysis |
| `tools/match/exemplars.py` | Validate human-rated manifest, hashes, rating scales, and deduplication |
| `tools/match/match.py` | Opt-in CLI flag, no-feasible outcome, emitted-artifact report |
| `tools/match/headroom.py` | Constrained arm, hard/holdout selection, held-out validity, resumable experiment rows |
| `tools/match/listen_compare.py` | Strict 0–5 blind page, invalid-cell masking, separate decode key |
| `tools/exemplars/human_rated/` | Tracked positive artifacts, provenance, and manual-submission instructions |
| `tools/tests/fixtures/tonal_collapse/` | Exact rejected regression artifacts |
| `tools/tests/test_feasibility.py` | Pure threshold/alignment tests |
| `tools/tests/test_feasibility_regressions.py` | Real positive and negative artifact checks |
| `tools/tests/test_exemplars.py` | Manifest validation tests |
| `tools/tests/test_optimizer_feasibility.py` | Lexicographic ordering and constrained evaluation tests |
| `tools/tests/test_match_feasibility.py` | CLI/report/no-feasible/exact-artifact tests |
| existing headroom/listen/objective tests | Extend current behavior without replacing established coverage |

## Task 1: Pure tonal-feasibility component

**Files:**
- Create: `tools/match/feasibility.py`
- Create: `tools/tests/test_feasibility.py`

- [ ] **Step 1: Write the failing unit tests**

Create `tools/tests/test_feasibility.py`:

```python
import torch

from match.feasibility import (
    CANDIDATE_PRESERVATION_THRESHOLD,
    TARGET_TONAL_THRESHOLD,
    TonalFeasibility,
)
from match.features import Features


def _features(active: list[bool], voiced: list[bool]) -> Features:
    assert len(active) == len(voiced)
    t = len(active)
    zeros = torch.zeros((1, t), dtype=torch.float32)
    return Features(
        env_db=zeros,
        f0_log2=zeros,
        voiced=torch.tensor([voiced], dtype=torch.bool),
        active=torch.tensor([active], dtype=torch.bool),
        centroid_log2=zeros,
        noisiness=zeros,
    )


def test_target_applicability_threshold_is_inclusive():
    below = TonalFeasibility(
        _features([True] * 5, [True, True, True, False, False])
    )
    at = TonalFeasibility(
        _features([True] * 5, [True, True, True, True, False])
    )
    above = TonalFeasibility(_features([True] * 5, [True] * 5))

    assert TARGET_TONAL_THRESHOLD == 0.80
    assert below.applies is False
    assert at.applies is True
    assert above.applies is True


def test_candidate_preservation_threshold_is_inclusive():
    target = _features([True] * 4, [True] * 4)
    gate = TonalFeasibility(target)

    below = gate.evaluate(_features([True] * 4, [True, True, False, False]))
    at = gate.evaluate(_features([True] * 4, [True, True, True, False]))
    above = gate.evaluate(_features([True] * 4, [True] * 4))

    assert CANDIDATE_PRESERVATION_THRESHOLD == 0.75
    assert below.feasible is False
    assert below.deficit == 0.25
    assert at.feasible is True
    assert at.deficit == 0.0
    assert above.feasible is True
    assert above.preservation == 1.0


def test_short_voiced_blip_does_not_pass():
    target = _features([True] * 4, [True] * 4)
    candidate = _features([True], [True])

    result = TonalFeasibility(target).evaluate(candidate)

    assert result.preservation == 0.25
    assert result.feasible is False


def test_voiced_tail_outside_target_tonal_window_does_not_pass():
    target = _features(
        [True, True, False, False],
        [True, True, False, False],
    )
    candidate = _features(
        [False, False, True, True],
        [False, False, True, True],
    )

    result = TonalFeasibility(target).evaluate(candidate)

    assert result.preservation == 0.0
    assert result.feasible is False


def test_non_tonal_target_is_exempt():
    target = _features([True] * 4, [False] * 4)
    candidate = _features([False], [False])

    result = TonalFeasibility(target).evaluate(candidate)

    assert result.applies is False
    assert result.feasible is True
    assert result.preservation == 1.0
    assert result.deficit == 0.0
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
cd tools
uv run pytest tests/test_feasibility.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'match.feasibility'`.

- [ ] **Step 3: Implement the pure component**

Create `tools/match/feasibility.py`:

```python
"""Hard feasibility checks that are separate from perceptual scoring."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import torch

from .features import Features

TARGET_TONAL_THRESHOLD = 0.80
CANDIDATE_PRESERVATION_THRESHOLD = 0.75


@dataclass(frozen=True)
class FeasibilityResult:
    applies: bool
    target_voiced_fraction: float
    preservation: float
    threshold: float
    deficit: float
    feasible: bool

    def to_dict(self) -> dict[str, bool | float]:
        return asdict(self)


def _fit_mask(mask: torch.Tensor, frames: int) -> torch.Tensor:
    flat = mask.reshape(-1).bool()
    if flat.numel() >= frames:
        return flat[:frames]
    pad = torch.zeros(frames - flat.numel(), dtype=torch.bool, device=flat.device)
    return torch.cat((flat, pad))


class TonalFeasibility:
    def __init__(
        self,
        target: Features,
        *,
        target_threshold: float = TARGET_TONAL_THRESHOLD,
        preservation_threshold: float = CANDIDATE_PRESERVATION_THRESHOLD,
    ):
        self.target_threshold = float(target_threshold)
        self.preservation_threshold = float(preservation_threshold)
        self.target_active = target.active.reshape(-1).bool()
        self.target_tonal = (
            target.active.reshape(-1).bool()
            & target.voiced.reshape(-1).bool()
        )
        active_count = int(self.target_active.sum())
        tonal_count = int(self.target_tonal.sum())
        self.target_voiced_fraction = (
            tonal_count / active_count if active_count else 0.0
        )
        self.applies = self.target_voiced_fraction >= self.target_threshold

    def evaluate(self, candidate: Features) -> FeasibilityResult:
        if not self.applies:
            return FeasibilityResult(
                applies=False,
                target_voiced_fraction=self.target_voiced_fraction,
                preservation=1.0,
                threshold=self.preservation_threshold,
                deficit=0.0,
                feasible=True,
            )

        frames = self.target_tonal.numel()
        candidate_tonal = _fit_mask(
            candidate.active & candidate.voiced, frames
        )
        tonal_count = int(self.target_tonal.sum())
        preserved_count = int((self.target_tonal & candidate_tonal).sum())
        preservation = preserved_count / max(tonal_count, 1)
        deficit = max(self.preservation_threshold - preservation, 0.0)
        return FeasibilityResult(
            applies=True,
            target_voiced_fraction=self.target_voiced_fraction,
            preservation=preservation,
            threshold=self.preservation_threshold,
            deficit=deficit,
            feasible=preservation >= self.preservation_threshold,
        )
```

- [ ] **Step 4: Run the unit tests**

Run:

```bash
cd tools
uv run pytest tests/test_feasibility.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit the component**

```bash
git add tools/match/feasibility.py tools/tests/test_feasibility.py
git commit -m "feat(match): add tonal feasibility check"
```

## Task 2: Reuse objective feature extraction

**Files:**
- Modify: `tools/match/objective.py:83-245`
- Modify: `tools/tests/test_objective.py`

- [ ] **Step 1: Add a failing batch-analysis test**

Append to `tools/tests/test_objective.py`:

```python
def test_batch_analysis_reuses_scores_and_marks_missing_wave():
    target = sine(440.0)
    candidate = sine(660.0)
    objective = MatchObjective(target)

    analysis = objective.score_batch_analysis([candidate, None])

    assert analysis.scores.shape == (2,)
    assert analysis.scores[0] == objective.score(candidate)
    assert analysis.scores[1] == FAILED_SCORE
    assert analysis.features[0] is not None
    assert analysis.features[0].active.shape[0] == 1
    assert analysis.features[1] is None
```

`FAILED_SCORE` is already part of the existing import from `match.objective`;
do not duplicate or otherwise change that import.

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
cd tools
uv run pytest tests/test_objective.py::test_batch_analysis_reuses_scores_and_marks_missing_wave -q
```

Expected: failure with `AttributeError: 'MatchObjective' object has no attribute 'score_batch_analysis'`.

- [ ] **Step 3: Add the analysis result and public method**

In `tools/match/objective.py`, add beside `CandidateCache`:

```python
@dataclass
class BatchAnalysis:
    scores: np.ndarray
    features: list[Features | None]
```

Replace `score_components`, `score_batch`, and the `_score_valid` return
contract with:

```python
    def score_components(self, wave: np.ndarray) -> dict[str, float]:
        """Score one candidate, returning the per-term breakdown."""
        _, components, _ = self._score_valid([wave])
        return components[0]

    def score_batch(self, waves: list[np.ndarray | None]) -> np.ndarray:
        return self.score_batch_analysis(waves).scores

    def score_batch_analysis(
        self, waves: list[np.ndarray | None]
    ) -> BatchAnalysis:
        scores = np.full(len(waves), FAILED_SCORE)
        features: list[Features | None] = [None] * len(waves)
        valid_idx = [
            i for i, wave in enumerate(waves)
            if wave is not None and len(wave) > 0
        ]
        if not valid_idx:
            return BatchAnalysis(scores=scores, features=features)

        totals, _, valid_features = self._score_valid(
            [waves[i] for i in valid_idx]
        )
        for i, total, candidate_features in zip(
            valid_idx, totals, valid_features
        ):
            scores[i] = total
            features[i] = candidate_features
        return BatchAnalysis(scores=scores, features=features)

    def _score_valid(
        self, waves: list[np.ndarray]
    ) -> tuple[np.ndarray, list[dict[str, float]], list[Features]]:
```

Inside the existing result loop, append the sliced features immediately after
the existing `cand_features = ...` assignment, then return them as the third
value:

```python
        candidate_features: list[Features] = []
        for row, length in enumerate(lengths):
            cand_features = batch_features.slice(row, frame_count(length))
            candidate_features.append(cand_features)

        return totals, components, candidate_features
```

Do not duplicate or move the existing distance/component calculations inside
that loop; the only insertion there is `candidate_features.append(...)`.

- [ ] **Step 4: Run objective tests**

Run:

```bash
cd tools
uv run pytest tests/test_objective.py -q
```

Expected: all tests in `test_objective.py` pass.

- [ ] **Step 5: Commit the single-pass analysis API**

```bash
git add tools/match/objective.py tools/tests/test_objective.py
git commit -m "refactor(match): expose analyzed candidate features"
```

## Task 3: Preserve and validate human-rated exemplars

**Files:**
- Create: `tools/match/exemplars.py`
- Create: `tools/tests/test_exemplars.py`
- Create: `tools/exemplars/human_rated/manifest.json`
- Create: `tools/exemplars/human_rated/manual/README.md`
- Copy: four `.bfxr` and four exact `.wav` files under `tools/exemplars/human_rated/blind/`

- [ ] **Step 1: Write failing manifest-validation tests**

Create `tools/tests/test_exemplars.py`:

```python
import hashlib
import json

from match.exemplars import validate_manifest


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_accepts_duplicate_observations_but_unique_artifacts(tmp_path):
    (tmp_path / "x.bfxr").write_text("{}")
    (tmp_path / "x.wav").write_bytes(b"wav")
    (tmp_path / "targets").mkdir()
    (tmp_path / "targets" / "target.wav").write_bytes(b"target")
    manifest = {
        "schema_version": 1,
        "artifacts": [{
            "id": "x",
            "target": "target",
            "target_path": "targets/target.wav",
            "bfxr": "x.bfxr",
            "wav": "x.wav",
            "bfxr_sha256": _sha(tmp_path / "x.bfxr"),
            "wav_sha256": _sha(tmp_path / "x.wav"),
            "renderer_version": "1.0.4",
            "render_seed": 1234,
            "source_run": "run",
            "rating_observations": [
                {"kind": "blind", "scale": "legacy_1_to_5",
                 "rating": 4, "arm": "A"},
                {"kind": "blind", "scale": "legacy_1_to_5",
                 "rating": 4, "arm": "B"},
            ],
        }],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    assert validate_manifest(tmp_path / "manifest.json") == []


def test_manifest_rejects_hash_mismatch_and_invalid_scale(tmp_path):
    (tmp_path / "x.bfxr").write_text("{}")
    (tmp_path / "x.wav").write_bytes(b"wav")
    (tmp_path / "targets").mkdir()
    (tmp_path / "targets" / "target.wav").write_bytes(b"target")
    manifest = {
        "schema_version": 1,
        "artifacts": [{
            "id": "x",
            "target": "target",
            "target_path": "targets/missing.wav",
            "bfxr": "x.bfxr",
            "wav": "x.wav",
            "bfxr_sha256": "wrong",
            "wav_sha256": _sha(tmp_path / "x.wav"),
            "renderer_version": "1.0.4",
            "render_seed": "1234",
            "source_run": "",
            "rating_observations": [
                {"kind": "blind", "scale": "unknown", "rating": 4, "arm": "A"},
            ],
        }],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    errors = validate_manifest(tmp_path / "manifest.json")

    assert any("bfxr_sha256" in error for error in errors)
    assert any("unknown rating scale" in error for error in errors)
    assert any("target_path is missing" in error for error in errors)
    assert any("render_seed must be an integer" in error for error in errors)
    assert any("source_run must be a non-empty string" in error for error in errors)


def test_new_scale_accepts_only_half_point_steps(tmp_path):
    (tmp_path / "x.bfxr").write_text("{}")
    (tmp_path / "x.wav").write_bytes(b"wav")
    (tmp_path / "targets").mkdir()
    (tmp_path / "targets" / "target.wav").write_bytes(b"target")
    manifest = {
        "schema_version": 1,
        "artifacts": [{
            "id": "x",
            "target": "target",
            "target_path": "targets/target.wav",
            "bfxr": "x.bfxr",
            "wav": "x.wav",
            "bfxr_sha256": _sha(tmp_path / "x.bfxr"),
            "wav_sha256": _sha(tmp_path / "x.wav"),
            "renderer_version": "1.0.4",
            "render_seed": 1234,
            "source_run": "manual",
            "rating_observations": [
                {"kind": "creator_self_rating", "scale": "quality_0_to_5",
                 "rating": 4.25},
            ],
        }],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    errors = validate_manifest(tmp_path / "manifest.json")

    assert any("half-point" in error for error in errors)
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```bash
cd tools
uv run pytest tests/test_exemplars.py -q
```

Expected: collection fails because `match.exemplars` does not exist.

- [ ] **Step 3: Implement the manifest validator**

Create `tools/match/exemplars.py`:

```python
"""Validation for tracked human-rated matcher artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

RATING_RANGES = {
    "legacy_1_to_5": (1.0, 5.0),
    "quality_0_to_5": (0.0, 5.0),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data: Any = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return [f"manifest unreadable: {type(exc).__name__}: {exc}"]

    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return ["schema_version must be 1"]
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        return ["artifacts must be a list"]

    root = path.parent
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for index, artifact in enumerate(artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{label} must be an object")
            continue
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, str) or not artifact_id:
            errors.append(f"{label}.id must be a non-empty string")
        elif artifact_id in seen_ids:
            errors.append(f"{label}.id duplicates {artifact_id}")
        else:
            seen_ids.add(artifact_id)

        for field in ("target", "target_path", "renderer_version", "source_run"):
            if not isinstance(artifact.get(field), str) or not artifact[field]:
                errors.append(f"{label}.{field} must be a non-empty string")
        if not isinstance(artifact.get("render_seed"), int):
            errors.append(f"{label}.render_seed must be an integer")
        target_rel = artifact.get("target_path")
        if isinstance(target_rel, str) and not (root / target_rel).is_file():
            errors.append(f"{label}.target_path is missing: {target_rel}")

        bfxr_rel = artifact.get("bfxr")
        wav_rel = artifact.get("wav")
        if not isinstance(bfxr_rel, str) or not isinstance(wav_rel, str):
            errors.append(f"{label} must name bfxr and wav files")
            continue
        pair = (bfxr_rel, wav_rel)
        if pair in seen_pairs:
            errors.append(f"{label} duplicates artifact files {pair}")
        seen_pairs.add(pair)

        for field, rel in (("bfxr_sha256", bfxr_rel), ("wav_sha256", wav_rel)):
            artifact_path = root / rel
            if not artifact_path.is_file():
                errors.append(f"{label}.{rel} is missing")
                continue
            expected = artifact.get(field)
            actual = _sha256(artifact_path)
            if expected != actual:
                errors.append(
                    f"{label}.{field} expected {expected!r}, got {actual}"
                )

        observations = artifact.get("rating_observations")
        if not isinstance(observations, list) or not observations:
            errors.append(f"{label}.rating_observations must be non-empty")
            continue
        for obs_index, observation in enumerate(observations):
            obs_label = f"{label}.rating_observations[{obs_index}]"
            scale = observation.get("scale") if isinstance(observation, dict) else None
            if scale not in RATING_RANGES:
                errors.append(f"{obs_label} has unknown rating scale {scale!r}")
                continue
            rating = observation.get("rating")
            if not isinstance(rating, (int, float)):
                errors.append(f"{obs_label}.rating must be numeric")
                continue
            low, high = RATING_RANGES[scale]
            if not low <= float(rating) <= high:
                errors.append(f"{obs_label}.rating is outside {low:g}..{high:g}")
            if float(rating) * 2 != round(float(rating) * 2):
                errors.append(f"{obs_label}.rating must use half-point steps")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="match.exemplars")
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        default=Path("exemplars/human_rated/manifest.json"),
    )
    args = parser.parse_args(argv)
    errors = validate_manifest(args.manifest)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Copy the four unique exact artifacts**

Run from the repository root:

```bash
mkdir -p \
  tools/exemplars/human_rated/blind/chrono_trigger_leeneBell \
  tools/exemplars/human_rated/blind/mega_man_ii_beam-out \
  tools/exemplars/human_rated/blind/mega_man_iii_cursor_baseline \
  tools/exemplars/human_rated/blind/mega_man_iii_cursor_big_unseeded \
  tools/exemplars/human_rated/manual

cp "tools/invert/runs/headroom/baseline_seeded/chrono_trigger_leeneBell/model_seeded/match.bfxr" \
  tools/exemplars/human_rated/blind/chrono_trigger_leeneBell/match.bfxr
cp "tools/invert/runs/headroom/baseline_seeded/chrono_trigger_leeneBell/model_seeded/match.wav" \
  tools/exemplars/human_rated/blind/chrono_trigger_leeneBell/match.wav

cp "tools/invert/runs/headroom/baseline_seeded/mega_man_ii_beam-out/model_seeded/match.bfxr" \
  tools/exemplars/human_rated/blind/mega_man_ii_beam-out/match.bfxr
cp "tools/invert/runs/headroom/baseline_seeded/mega_man_ii_beam-out/model_seeded/match.wav" \
  tools/exemplars/human_rated/blind/mega_man_ii_beam-out/match.wav

cp "tools/invert/runs/headroom/baseline_seeded/mega_man_iii_cursor/model_seeded/match.bfxr" \
  tools/exemplars/human_rated/blind/mega_man_iii_cursor_baseline/match.bfxr
cp "tools/invert/runs/headroom/baseline_seeded/mega_man_iii_cursor/model_seeded/match.wav" \
  tools/exemplars/human_rated/blind/mega_man_iii_cursor_baseline/match.wav

cp "tools/invert/runs/headroom/big_unseeded/mega_man_iii_cursor/model_seeded/match.bfxr" \
  tools/exemplars/human_rated/blind/mega_man_iii_cursor_big_unseeded/match.bfxr
cp "tools/invert/runs/headroom/big_unseeded/mega_man_iii_cursor/model_seeded/match.wav" \
  tools/exemplars/human_rated/blind/mega_man_iii_cursor_big_unseeded/match.wav
```

- [ ] **Step 5: Add the complete manifest**

Create `tools/exemplars/human_rated/manifest.json`:

```json
{
  "schema_version": 1,
  "artifacts": [
    {
      "id": "chrono_trigger_leeneBell_headroom",
      "target": "chrono_trigger_leeneBell",
      "target_path": "../../targets/chrono_trigger_leeneBell.wav",
      "bfxr": "blind/chrono_trigger_leeneBell/match.bfxr",
      "wav": "blind/chrono_trigger_leeneBell/match.wav",
      "bfxr_sha256": "eea081f3452cffb58b16b87b734f37fb60626f7d71fe7326f6e4641593553fe4",
      "wav_sha256": "112fd259d2408d4ced635589920eade8d16d648bb863d1d6724c4bbd721cbaae",
      "renderer_version": "1.0.4",
      "render_seed": 1234,
      "source_run": "invert/runs/headroom",
      "rating_observations": [
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "baseline_seeded"},
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "big_seeded"},
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "big_unseeded"}
      ]
    },
    {
      "id": "mega_man_ii_beam-out_headroom",
      "target": "mega_man_ii_beam-out",
      "target_path": "../../targets/mega_man_ii_beam-out.wav",
      "bfxr": "blind/mega_man_ii_beam-out/match.bfxr",
      "wav": "blind/mega_man_ii_beam-out/match.wav",
      "bfxr_sha256": "da39f92adc770fc6829454db8cd179ae82e86bc186586ecad22f309eb3470b4a",
      "wav_sha256": "fd8410423eb533c7dddd6d25a887916bcbf42fbd93349b228fd0953a334df10c",
      "renderer_version": "1.0.4",
      "render_seed": 1234,
      "source_run": "invert/runs/headroom",
      "rating_observations": [
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "baseline_seeded"},
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "big_seeded"},
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "big_unseeded"}
      ]
    },
    {
      "id": "mega_man_iii_cursor_baseline_headroom",
      "target": "mega_man_iii_cursor",
      "target_path": "../../targets/mega_man_iii_cursor.wav",
      "bfxr": "blind/mega_man_iii_cursor_baseline/match.bfxr",
      "wav": "blind/mega_man_iii_cursor_baseline/match.wav",
      "bfxr_sha256": "49e5cdd51712245a787e590ff732f8f3f1b73acb3bcc2845bba48e49b3c62e3b",
      "wav_sha256": "5293d9314f03df2589519318da27d405db34fd9da4482a9c48538bdca3b55c74",
      "renderer_version": "1.0.4",
      "render_seed": 1234,
      "source_run": "invert/runs/headroom",
      "rating_observations": [
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "baseline_seeded"},
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 4, "arm": "big_seeded"}
      ]
    },
    {
      "id": "mega_man_iii_cursor_big_unseeded_headroom",
      "target": "mega_man_iii_cursor",
      "target_path": "../../targets/mega_man_iii_cursor.wav",
      "bfxr": "blind/mega_man_iii_cursor_big_unseeded/match.bfxr",
      "wav": "blind/mega_man_iii_cursor_big_unseeded/match.wav",
      "bfxr_sha256": "b429b15de1128fdd55ce4f87289c47cac2f6ade433c6d7cfd2599958a59ec3cb",
      "wav_sha256": "dcb8e6c902eb61037807b4453996a4eb0363626bb717ce51b420df582a7f0628",
      "renderer_version": "1.0.4",
      "render_seed": 1234,
      "source_run": "invert/runs/headroom",
      "rating_observations": [
        {"kind": "blind", "scale": "legacy_1_to_5", "rating": 5, "arm": "big_unseeded"}
      ]
    }
  ]
}
```

Create `tools/exemplars/human_rated/manual/README.md`:

```markdown
# Manual reachability witnesses

For each submitted sound, add the `.bfxr`, its seed-1234 render, and one
manifest observation with:

- `kind`: `creator_self_rating`
- `scale`: `quality_0_to_5`
- `rating`: a half-point value from 0 through 5
- optional `note`: the remaining audible mismatch

These entries are reachability evidence, never blind claim-gate ratings.
```

- [ ] **Step 6: Validate the real manifest**

Run:

```bash
cd tools
uv run pytest tests/test_exemplars.py -q
uv run python -m match.exemplars exemplars/human_rated/manifest.json
```

Expected: `3 passed`; validator exits 0 with no output.

- [ ] **Step 7: Commit tracked exemplars**

Because repository `.gitignore` ignores all WAV files, force-add only these
four approved WAVs:

```bash
git add tools/match/exemplars.py tools/tests/test_exemplars.py \
  tools/exemplars/human_rated/manifest.json \
  tools/exemplars/human_rated/manual/README.md \
  tools/exemplars/human_rated/blind/*/match.bfxr
git add -f tools/exemplars/human_rated/blind/*/match.wav
git commit -m "test(match): preserve human-rated exemplars"
```

## Task 4: Real positive and collapse regression fixtures

**Files:**
- Create: `tools/tests/test_feasibility_regressions.py`
- Copy: four `.bfxr` and four exact `.wav` files under `tools/tests/fixtures/tonal_collapse/`

- [ ] **Step 1: Copy the four known collapse artifacts**

Run from the repository root:

```bash
mkdir -p \
  "tools/tests/fixtures/tonal_collapse/Mario 2 - Throw" \
  "tools/tests/fixtures/tonal_collapse/Mario 3 - jump (nes)" \
  "tools/tests/fixtures/tonal_collapse/Mario 3 - jump (snes)" \
  "tools/tests/fixtures/tonal_collapse/mega_man_ii_one-up"

cp "tools/invert/runs/headroom/big_seeded/Mario 2 - Throw/model_seeded/match.bfxr" \
  "tools/tests/fixtures/tonal_collapse/Mario 2 - Throw/match.bfxr"
cp "tools/invert/runs/headroom/big_seeded/Mario 2 - Throw/model_seeded/match.wav" \
  "tools/tests/fixtures/tonal_collapse/Mario 2 - Throw/match.wav"

cp "tools/invert/runs/headroom/baseline_seeded/Mario 3 - jump (nes)/model_seeded/match.bfxr" \
  "tools/tests/fixtures/tonal_collapse/Mario 3 - jump (nes)/match.bfxr"
cp "tools/invert/runs/headroom/baseline_seeded/Mario 3 - jump (nes)/model_seeded/match.wav" \
  "tools/tests/fixtures/tonal_collapse/Mario 3 - jump (nes)/match.wav"

cp "tools/invert/runs/headroom/big_unseeded/Mario 3 - jump (snes)/model_seeded/match.bfxr" \
  "tools/tests/fixtures/tonal_collapse/Mario 3 - jump (snes)/match.bfxr"
cp "tools/invert/runs/headroom/big_unseeded/Mario 3 - jump (snes)/model_seeded/match.wav" \
  "tools/tests/fixtures/tonal_collapse/Mario 3 - jump (snes)/match.wav"

cp "tools/invert/runs/headroom/big_seeded/mega_man_ii_one-up/model_seeded/match.bfxr" \
  "tools/tests/fixtures/tonal_collapse/mega_man_ii_one-up/match.bfxr"
cp "tools/invert/runs/headroom/big_seeded/mega_man_ii_one-up/model_seeded/match.wav" \
  "tools/tests/fixtures/tonal_collapse/mega_man_ii_one-up/match.wav"
```

- [ ] **Step 2: Write the real-artifact regression test**

Create `tools/tests/test_feasibility_regressions.py`:

```python
from pathlib import Path

import pytest

from match.audio import load_audio, prepare_target
from match.feasibility import TonalFeasibility
from match.objective import MatchObjective

TOOLS = Path(__file__).parents[1]
EXEMPLARS = TOOLS / "exemplars" / "human_rated" / "blind"
COLLAPSE = Path(__file__).parent / "fixtures" / "tonal_collapse"


def _result(target_stem: str, candidate: Path):
    objective = MatchObjective(
        prepare_target(TOOLS / "targets" / f"{target_stem}.wav")
    )
    analysis = objective.score_batch_analysis([load_audio(candidate)])
    assert analysis.features[0] is not None
    return TonalFeasibility(objective.target_features).evaluate(
        analysis.features[0]
    )


@pytest.mark.parametrize(
    ("target", "directory"),
    [
        ("chrono_trigger_leeneBell", "chrono_trigger_leeneBell"),
        ("mega_man_ii_beam-out", "mega_man_ii_beam-out"),
        ("mega_man_iii_cursor", "mega_man_iii_cursor_baseline"),
        ("mega_man_iii_cursor", "mega_man_iii_cursor_big_unseeded"),
    ],
)
def test_human_rated_positive_controls_are_feasible(target, directory):
    result = _result(target, EXEMPLARS / directory / "match.wav")
    assert result.applies is True
    assert result.feasible is True


@pytest.mark.parametrize(
    "target",
    [
        "Mario 2 - Throw",
        "Mario 3 - jump (nes)",
        "Mario 3 - jump (snes)",
        "mega_man_ii_one-up",
    ],
)
def test_known_collapses_are_rejected(target):
    result = _result(target, COLLAPSE / target / "match.wav")
    assert result.applies is True
    assert result.feasible is False
    assert result.preservation < 0.75


def test_break_brick_is_non_tonal_and_exempt():
    objective = MatchObjective(
        prepare_target(TOOLS / "targets" / "Mario Break Brick.wav")
    )
    gate = TonalFeasibility(objective.target_features)
    assert gate.applies is False
```

- [ ] **Step 3: Run the regression test**

Run:

```bash
cd tools
uv run pytest tests/test_feasibility_regressions.py -q
```

Expected: `9 passed`.

- [ ] **Step 4: Commit the regression fixtures**

```bash
git add tools/tests/test_feasibility_regressions.py \
  tools/tests/fixtures/tonal_collapse/*/match.bfxr
git add -f tools/tests/fixtures/tonal_collapse/*/match.wav
git commit -m "test(match): lock tonal collapse regressions"
```

## Task 5: Feasibility-first optimizer ordering

**Files:**
- Modify: `tools/match/optimizer.py:88-547`
- Modify: `tools/match/refine.py:100-112`
- Create: `tools/tests/test_optimizer_feasibility.py`

- [ ] **Step 1: Write failing candidate-order tests**

Create `tools/tests/test_optimizer_feasibility.py`:

```python
from types import SimpleNamespace

import numpy as np

from match.bfxr_io import ParamSpace
from match.feasibility import FeasibilityResult
from match.optimizer import (
    Candidate,
    EvaluationBatch,
    StagedOptimizer,
    ordinal_fitness,
)


def _feasibility(preservation: float, feasible: bool) -> FeasibilityResult:
    return FeasibilityResult(
        applies=True,
        target_voiced_fraction=1.0,
        preservation=preservation,
        threshold=0.75,
        deficit=max(0.75 - preservation, 0.0),
        feasible=feasible,
    )


def _candidate(
    score: float,
    *,
    preservation: float = 1.0,
    feasible: bool = True,
    render_failed: bool = False,
) -> Candidate:
    return Candidate(
        score=score,
        wave_type=0,
        unit=np.zeros(2),
        feasibility=_feasibility(preservation, feasible),
        render_failed=render_failed,
    )


def test_feasible_always_outranks_better_objective_infeasible():
    feasible = _candidate(999.0)
    infeasible = _candidate(0.01, preservation=0.0, feasible=False)
    assert min([infeasible, feasible]) is feasible


def test_smaller_deficit_guides_infeasible_population():
    far = _candidate(0.01, preservation=0.0, feasible=False)
    near = _candidate(999.0, preservation=0.70, feasible=False)
    fitness = ordinal_fitness([far, near])
    assert fitness.tolist() == [1.0, 0.0]


def test_renderer_failure_is_worse_than_ordinary_infeasible():
    failed = _candidate(
        0.0, preservation=1.0, feasible=True, render_failed=True
    )
    infeasible = _candidate(999.0, preservation=0.0, feasible=False)
    assert ordinal_fitness([failed, infeasible]).tolist() == [1.0, 0.0]


def test_ordinal_fitness_is_stable_for_equal_keys():
    first = _candidate(1.0)
    second = _candidate(1.0)
    assert ordinal_fitness([first, second]).tolist() == [0.0, 1.0]


def test_stage0_cannot_reselect_lower_score_infeasible():
    optimizer = object.__new__(StagedOptimizer)
    optimizer.space = ParamSpace()
    optimizer.upper = np.ones(optimizer.space.dim)
    optimizer.s = SimpleNamespace(
        seed_units=None, screen_size=2, budget=4
    )
    optimizer._screen_sample = lambda: np.zeros(optimizer.space.dim)
    optimizer._out_of_budget = lambda: False
    optimizer._log = lambda message: None

    infeasible = _candidate(0.01, preservation=0.0, feasible=False)
    feasible = _candidate(999.0)

    def evaluate(units, wave_types):
        candidates = [infeasible, feasible]
        return EvaluationBatch(
            fitness=ordinal_fitness(candidates),
            candidates=candidates,
        )

    optimizer._evaluate = evaluate

    assert optimizer._stage0([0])[0] is feasible
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```bash
cd tools
uv run pytest tests/test_optimizer_feasibility.py -q
```

Expected: import fails because `ordinal_fitness` and the new `Candidate` fields
do not exist.

- [ ] **Step 3: Add candidate rank data and population result**

In `tools/match/optimizer.py`, import:

```python
from .feasibility import FeasibilityResult, TonalFeasibility
```

Remove the now-unused `field` name from the `dataclasses` import. Replace
`Candidate` and add `EvaluationBatch`:

```python
@dataclass
class Candidate:
    score: float
    wave_type: int
    unit: np.ndarray
    feasibility: FeasibilityResult | None = None
    render_failed: bool = False

    def rank_key(self) -> tuple[int, float, float]:
        if self.render_failed:
            return (2, 0.0, self.score)
        if self.feasibility is not None and not self.feasibility.feasible:
            return (1, self.feasibility.deficit, self.score)
        return (0, 0.0, self.score)

    def __lt__(self, other: "Candidate") -> bool:
        return self.rank_key() < other.rank_key()


@dataclass
class EvaluationBatch:
    fitness: np.ndarray
    candidates: list[Candidate]


def ordinal_fitness(candidates: list[Candidate]) -> np.ndarray:
    order = sorted(
        range(len(candidates)),
        key=lambda index: (candidates[index].rank_key(), index),
    )
    fitness = np.empty(len(candidates), dtype=np.float64)
    for rank, index in enumerate(order):
        fitness[index] = float(rank)
    return fitness
```

Add to `OptimizeSettings`:

```python
    preserve_voicing: bool = False
```

In `StagedOptimizer.__init__`, after `self.archive`:

```python
        self.feasibility = (
            TonalFeasibility(objective.target_features)
            if settings.preserve_voicing
            else None
        )
```

- [ ] **Step 4: Make `_evaluate` return candidates plus fitness**

Replace `_evaluate`:

```python
    def _evaluate(
        self, units: list[np.ndarray], wave_types: list[int]
    ) -> EvaluationBatch:
        params = [self.params_for(u, wt) for u, wt in zip(units, wave_types)]
        seeds = range(RENDER_SEED, RENDER_SEED + self.s.avg_seeds)
        all_scores: list[np.ndarray] = []
        all_feasibility: list[list[FeasibilityResult]] = [
            [] for _ in units
        ]
        render_failed = np.zeros(len(units), dtype=bool)

        for seed in seeds:
            waves = self.renderer.render_batch(params, seeds=int(seed))
            render_failed |= np.array(
                [wave is None or len(wave) == 0 for wave in waves]
            )
            if self.feasibility is None:
                all_scores.append(self.objective.score_batch(waves))
                continue
            analysis = self.objective.score_batch_analysis(waves)
            all_scores.append(analysis.scores)
            for index, features in enumerate(analysis.features):
                if features is not None:
                    all_feasibility[index].append(
                        self.feasibility.evaluate(features)
                    )

        scores = np.mean(all_scores, axis=0)
        candidates: list[Candidate] = []
        for index, (unit, wave_type, score) in enumerate(
            zip(units, wave_types, scores)
        ):
            results = all_feasibility[index]
            worst = (
                min(results, key=lambda result: result.preservation)
                if results else None
            )
            candidates.append(Candidate(
                score=float(score),
                wave_type=wave_type,
                unit=unit.copy(),
                feasibility=worst,
                render_failed=bool(render_failed[index]),
            ))

        self.evals += len(units)
        self.archive.extend(candidates)
        best = min(self.archive)
        self.trace.append((self.evals, best.score))
        fitness = (
            ordinal_fitness(candidates)
            if self.feasibility is not None
            else scores.copy()
        )
        return EvaluationBatch(fitness=fitness, candidates=candidates)
```

- [ ] **Step 5: Update every evaluation call site**

Apply these exact patterns in `_stage0`, `_stage0_seeded`, and
`_run_arp_stage`:

```python
batch = self._evaluate(units, [wt] * len(units))
candidate = min(batch.candidates)
```

Store `candidate` directly instead of reconstructing it from the returned
fitness. Compare repeated-wave-type and arp candidates with
`candidate < best[wt]` / `candidate < best`, never `.score`. For CMA:

```python
batch = self._evaluate(units, [start.wave_type] * len(units))
es.tell(xs, batch.fitness.tolist())
```

In both `by_wt` archive-reduction loops in `run()`, replace:

```python
c.score < by_wt[c.wave_type].score
```

with:

```python
c < by_wt[c.wave_type]
```

In `tools/match/refine.py`, keep the unconstrained refinement adapter working:

```python
    def evaluate(units: list[np.ndarray]) -> np.ndarray:
        return np.array(
            [
                float(
                    optimizer._evaluate([unit], [wave_type]).fitness[0]
                )
                for unit in units
            ],
            dtype=np.float64,
        )
```

At final selection in `StagedOptimizer.run`, filter only when the flag is on:

```python
        if self.s.preserve_voicing:
            results = [
                candidate for candidate in results
                if not candidate.render_failed
                and candidate.feasibility is not None
                and candidate.feasibility.feasible
            ]
        if not results:
            self._log(f"done: no feasible candidate, {self.evals} evals")
            return []
```

All `min(...)` and `sorted(...)` calls use `Candidate.__lt__`. Audit the file
with `rg "\\.score <|argmin\\(" tools/match/optimizer.py`: after this change,
no stage or archive survivor selection may bypass `Candidate.__lt__`.
Objective-score comparisons outside candidate selection may remain. Log
`candidate.score`, never ordinal fitness.

- [ ] **Step 6: Run optimizer tests**

Run:

```bash
cd tools
uv run pytest \
  tests/test_optimizer_feasibility.py \
  tests/test_optimizer_restarts.py \
  tests/test_optimizer_duration_floor.py \
  tests/test_refine.py -q
```

Expected: all focused optimizer/refine tests pass.

- [ ] **Step 7: Verify default-off determinism**

Run twice:

```bash
cd tools
uv run pytest tests/test_optimizer_restarts.py::test_main_pipeline_is_bit_identical_with_and_without_the_arp_stage -q
uv run pytest tests/test_roundtrip.py -q -m slow
```

Expected: both commands pass; unconstrained scoring still returns raw objective
fitness.

- [ ] **Step 8: Commit optimizer integration**

```bash
git add tools/match/optimizer.py tools/match/refine.py \
  tools/tests/test_optimizer_feasibility.py
git commit -m "feat(match): rank feasible tonal candidates first"
```

## Task 6: Exact artifact validation and matcher reporting

**Files:**
- Create: `tools/match/validation.py`
- Modify: `tools/match/match.py:29-292`
- Create: `tools/tests/test_match_feasibility.py`

- [ ] **Step 1: Write failing validation tests**

Create `tools/tests/test_match_feasibility.py`:

```python
from pathlib import Path

import numpy as np
import soundfile as sf

from match.audio import SAMPLE_RATE
from match.feasibility import TonalFeasibility
from match.match import build_parser
from match.objective import MatchObjective
from match.validation import analyze_wave, validate_emitted_wav


def _sine(hz: float, seconds: float = 0.2) -> np.ndarray:
    t = np.arange(int(SAMPLE_RATE * seconds), dtype=np.float32) / SAMPLE_RATE
    return (0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_preserve_voicing_flag_defaults_off_and_can_enable():
    parser = build_parser()
    assert parser.parse_args(["x.wav"]).preserve_voicing is False
    assert parser.parse_args(
        ["x.wav", "--preserve-voicing"]
    ).preserve_voicing is True


def test_analyze_wave_returns_components_and_feasibility():
    target = _sine(440.0)
    objective = MatchObjective(target)
    gate = TonalFeasibility(objective.target_features)

    result = analyze_wave(objective, gate, _sine(440.0))

    assert result.valid is True
    assert result.score < 0.01
    assert result.feasibility.feasible is True
    assert "pitch" in result.components


def test_validate_emitted_wav_reads_exact_pcm16(tmp_path: Path):
    target = _sine(440.0)
    objective = MatchObjective(target)
    gate = TonalFeasibility(objective.target_features)
    path = tmp_path / "match.wav"
    sf.write(path, _sine(440.0), SAMPLE_RATE, subtype="PCM_16")

    result = validate_emitted_wav(path, objective, gate)

    assert result.valid is True
    assert result.source == "emitted_pcm16"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd tools
uv run pytest tests/test_match_feasibility.py -q
```

Expected: collection fails because `match.validation` does not exist.

- [ ] **Step 3: Implement validation helpers**

Create `tools/match/validation.py`:

```python
"""Validation of the exact waveform claimed by an experiment."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .audio import load_audio
from .feasibility import FeasibilityResult, TonalFeasibility
from .objective import MatchObjective


@dataclass(frozen=True)
class ArtifactValidation:
    source: str
    score: float
    components: dict[str, float]
    feasibility: FeasibilityResult
    valid: bool

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "score": self.score,
            "components": self.components,
            "feasibility": self.feasibility.to_dict(),
            "valid": self.valid,
        }


def analyze_wave(
    objective: MatchObjective,
    gate: TonalFeasibility,
    wave: np.ndarray,
    *,
    source: str = "memory",
) -> ArtifactValidation:
    analysis = objective.score_batch_analysis([wave])
    features = analysis.features[0]
    if features is None:
        raise ValueError(f"{source} waveform is empty")
    feasibility = gate.evaluate(features)
    components = objective.score_components(wave)
    return ArtifactValidation(
        source=source,
        score=float(analysis.scores[0]),
        components=components,
        feasibility=feasibility,
        valid=feasibility.feasible,
    )


def validate_emitted_wav(
    path: Path,
    objective: MatchObjective,
    gate: TonalFeasibility,
) -> ArtifactValidation:
    return analyze_wave(
        objective,
        gate,
        load_audio(path),
        source="emitted_pcm16",
    )
```

- [ ] **Step 4: Wire the opt-in matcher flag**

In `build_parser()` in `tools/match/match.py`, add:

```python
    p.add_argument(
        "--preserve-voicing",
        action="store_true",
        help="hard feasibility-first search for tonal targets (experimental)",
    )
```

In argument validation, reject combinations outside this experiment:

```python
    if args.preserve_voicing and args.one_shot:
        parser.error("--preserve-voicing requires staged search")
    if args.preserve_voicing and args.refine_steps > 0:
        parser.error("--preserve-voicing does not support --refine-steps")
```

Pass the flag into `OptimizeSettings`:

```python
        preserve_voicing=args.preserve_voicing,
```

Add `"preserve_voicing": args.preserve_voicing` and
`"renderer_version": space.version` to report metadata.

- [ ] **Step 5: Handle no-feasible and exact emitted validation**

Immediately after `results = optimizer.run()`:

```python
        if not results:
            elapsed = time.perf_counter() - t0
            report = {
                "target": str(args.target),
                "target_seconds": len(target) / SAMPLE_RATE,
                "status": "invalid",
                "failure_reason": "no_feasible_candidate",
                "flags": {
                    "preserve_voicing": args.preserve_voicing,
                    "restarts": args.restarts,
                    "avg_seeds": args.avg_seeds,
                    "seed_model": str(args.seed_model) if args.seed_model else None,
                },
                "renderer_version": space.version,
                "budget": args.budget,
                "evals": optimizer.evals,
                "elapsed_seconds": round(elapsed, 1),
                "results": [],
                "trace": optimizer.trace[:: max(1, len(optimizer.trace) // 100)],
            }
            (args.out / "report.json").write_text(json.dumps(report, indent=1))
            print("no feasible candidate", file=sys.stderr)
            return 0
```

Initialize `result_rows: list[dict] = []` immediately before the existing
result-writing loop. For every saved result, construct the row with search
feasibility:

```python
            result_row = {
                "file": f"{stem}.bfxr",
                "score": cand.score,
                "wave_type": cand.wave_type,
                "wave_type_name": space.wave_type_names[cand.wave_type],
                "search_feasibility": (
                    cand.feasibility.to_dict()
                    if cand.feasibility is not None else None
                ),
            }
```

After `sf.write`, validate the exact file when constrained:

```python
            if args.preserve_voicing:
                gate = optimizer.feasibility
                assert gate is not None
                emitted = validate_emitted_wav(
                    args.out / f"{stem}.wav", objective, gate
                )
                result_row["emitted_artifact"] = emitted.to_dict()
            result_rows.append(result_row)
```

Replace the report's existing `"results"` value with `result_rows`. After the
report dictionary is created, set:

```python
        winner_valid = (
            not args.preserve_voicing
            or bool(result_rows[0]["emitted_artifact"]["valid"])
        )
        report["status"] = "ok" if winner_valid else "invalid"
        report["failure_reason"] = (
            None if winner_valid else "emitted_artifact_infeasible"
        )
```

Import `validate_emitted_wav` from `.validation`. Keep the exact PCM-16 WAV
even when invalid; it is diagnostic output, but the driver will mask it.

- [ ] **Step 6: Add no-feasible report coverage**

Append to `tools/tests/test_match_feasibility.py`:

```python
def test_preserve_voicing_rejects_one_shot_and_refine():
    parser = build_parser()
    args = parser.parse_args(["x.wav", "--preserve-voicing"])
    assert args.preserve_voicing is True
```

Add an explicit no-feasible report test:

```python
def test_no_feasible_run_writes_invalid_report_without_winner(
    tmp_path, monkeypatch
):
    target = tmp_path / "target.wav"
    sf.write(target, _sine(440.0), SAMPLE_RATE)
    out = tmp_path / "out"

    class _Renderer:
        version = "test"

        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class _Optimizer:
        evals = 12
        trace = [(12, 3.0)]

        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return []

    monkeypatch.setattr("match.match.BfxrRenderer", _Renderer)
    monkeypatch.setattr("match.match.StagedOptimizer", _Optimizer)

    assert main([
        str(target), "-o", str(out), "--preserve-voicing", "--budget", "12"
    ]) == 0
    report = json.loads((out / "report.json").read_text())
    assert report["status"] == "invalid"
    assert report["failure_reason"] == "no_feasible_candidate"
    assert report["results"] == []
    assert not (out / "match.wav").exists()
```

Add `json` and `main` to the test imports. Then add parser-error coverage by
calling `match.main`:

```python
import pytest
from match.match import main


@pytest.mark.parametrize(
    "extra",
    [["--one-shot", "--seed-model", "best.pt"], ["--refine-steps", "1"]],
)
def test_incompatible_preserve_voicing_modes_exit_two(extra):
    with pytest.raises(SystemExit) as exc:
        main(["x.wav", "--preserve-voicing", *extra])
    assert exc.value.code == 2
```

- [ ] **Step 7: Run matcher-focused tests**

Run:

```bash
cd tools
uv run pytest \
  tests/test_match_feasibility.py \
  tests/test_invert_match_seed.py \
  tests/test_roundtrip.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit matcher reporting**

```bash
git add tools/match/validation.py tools/match/match.py \
  tools/tests/test_match_feasibility.py
git commit -m "feat(match): validate emitted tonal artifacts"
```

## Task 7: Strict blind quality page

**Files:**
- Modify: `tools/match/listen_compare.py:57-169`
- Modify: `tools/tests/test_headroom_page.py`

- [ ] **Step 1: Write failing quality-page tests**

Append to `tools/tests/test_headroom_page.py`:

```python
def test_quality_page_shows_new_scale_without_leaking_arms(tmp_path):
    targets, arms = _setup(tmp_path)
    out = tmp_path / "quality.html"
    key_out = tmp_path / "quality_key.json"

    write_arms_page(
        out,
        key_out,
        targets,
        arms[:2],
        only={"Mario 1 - Jump"},
        quality_gate=True,
    )

    html = out.read_text()
    assert "Could convincingly replace the original" in html
    assert "Clearly the same effect" in html
    assert "half-point" in html
    assert all(name not in html for name, _ in arms[:2])


def test_invalid_arm_cell_is_masked_even_when_wav_exists(tmp_path):
    targets, arms = _setup(tmp_path)
    out = tmp_path / "quality.html"
    key_out = tmp_path / "quality_key.json"
    eligible = {("Mario 1 - Jump", "baseline_seeded")}

    write_arms_page(
        out,
        key_out,
        targets,
        arms[:2],
        only={"Mario 1 - Jump"},
        eligible=eligible,
        quality_gate=True,
    )

    html = out.read_text()
    assert html.count("<audio controls") == 2  # original + valid arm
    assert "INVALID" in html
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd tools
uv run pytest tests/test_headroom_page.py -q
```

Expected: `TypeError` because `write_arms_page` does not accept
`quality_gate` or `eligible`.

- [ ] **Step 3: Add validity masking and the approved rubric**

Extend the function signature:

```python
def write_arms_page(
    out: Path,
    key_out: Path,
    targets_dir: Path,
    arms: list[tuple[str, Path]],
    mode: str = "model_seeded",
    only: set[str] | None = None,
    shuffle_seed: int = 0,
    *,
    eligible: set[tuple[str, str]] | None = None,
    quality_gate: bool = False,
) -> None:
```

When adding an arm cell:

```python
        for name, root in order:
            allowed = eligible is None or (target_path.stem, name) in eligible
            if allowed:
                cells.append(
                    _cell(_read(root / safe / mode / "match.wav"))
                )
            else:
                cells.append("<td class='miss'>INVALID</td>")
```

Use this complete approved rubric when `quality_gate` is true:

```python
    quality_intro = (
        "<p>Rate every candidate in half-point steps from 0 to 5. "
        "<b>5</b>: could convincingly replace the original. "
        "<b>4</b>: clearly the same effect; minor imperfections only. "
        "<b>3</b>: recognizable, but materially wrong. "
        "<b>2</b>: shares some traits but is not usable. "
        "<b>1</b>: barely related or badly degenerate. "
        "<b>0</b>: silent, broken, or unrelated. "
        "The treatment passes only if every result is at least 4.</p>"
        if quality_gate else
        "<p>Score each lettered column 0-5 against the original.</p>"
    )
```

Replace the old hard-coded score paragraph with `quality_intro`, followed by
the existing warning that columns are reshuffled and arm names are withheld.

- [ ] **Step 4: Run page tests**

Run:

```bash
cd tools
uv run pytest tests/test_headroom_page.py tests/test_listen_compare.py -q
```

Expected: all page tests pass.

- [ ] **Step 5: Commit the page**

```bash
git add tools/match/listen_compare.py tools/tests/test_headroom_page.py
git commit -m "feat(match): add strict blind quality gate page"
```

## Task 8: Constrained headroom arm and held-out validity

**Files:**
- Modify: `tools/match/headroom.py:29-356`
- Modify: `tools/tests/test_headroom_driver.py`
- Modify: `tools/tests/test_headroom_rescore.py`

- [ ] **Step 1: Write failing constrained-arm tests**

In `tools/tests/test_headroom_driver.py`, replace the exact-arm assertion with:

```python
def test_arm_matrix_matches_the_spec():
    assert set(ARMS) == {
        "baseline_seeded",
        "big_seeded",
        "baseline_unseeded",
        "big_unseeded",
        "big_seeded_constrained",
    }
    assert ARMS["big_seeded_constrained"] == {
        "budget": 200000,
        "seed_model": True,
        "restarts": True,
        "preserve_voicing": True,
    }
```

Retain assertions for the four old arms, adding
`"preserve_voicing": False` to each expected dictionary.

Add:

```python
def test_constrained_arm_passes_only_the_new_flag(tmp_path, monkeypatch):
    seen = {}

    def _fake_match_main(argv):
        seen["argv"] = argv
        out = tmp_path / "constrained"
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps({
            "status": "ok",
            "evals": 200000,
            "elapsed_seconds": 1.0,
            "trace": [],
            "results": [{
                "file": "match.bfxr",
                "score": 2.0,
                "wave_type": 0,
                "wave_type_name": "Square",
                "search_feasibility": {"feasible": True},
                "emitted_artifact": {"valid": True},
            }],
        }))
        return 0

    monkeypatch.setattr("match.headroom.match_main", _fake_match_main)
    monkeypatch.setattr(
        "match.headroom.heldout_validation_for_run",
        lambda *args, **kwargs: {
            "score": 2.1,
            "valid": True,
            "feasibility": {"feasible": True},
        },
    )

    row = run_arm(
        tmp_path / "t.wav",
        tmp_path / "constrained",
        "big_seeded_constrained",
        ckpt=tmp_path / "best.pt",
        jobs=None,
        rng_seed=0,
    )

    assert "--preserve-voicing" in seen["argv"]
    assert row["valid"] is True
```

Add target-set parser coverage:

```python
def test_target_set_defaults_to_hard_and_accepts_holdout():
    parser = build_parser()
    base = ["--targets", "targets", "--ckpt", "best.pt", "-o", "out"]
    assert parser.parse_args(base).target_set == "hard"
    assert parser.parse_args(base + ["--target-set", "holdout"]).target_set == "holdout"
```

Import `build_parser`.

- [ ] **Step 2: Add held-out validation test**

In `tools/tests/test_headroom_rescore.py`, add imports for
`heldout_validation` from `match.headroom`, `TonalFeasibility`, and
`MatchObjective`, then add:

```python
def test_heldout_validation_reports_feasibility():
    target = np.sin(np.linspace(0, 100, 8192)).astype(np.float32)
    objective = MatchObjective(target)
    gate = TonalFeasibility(objective.target_features)
    renderer = _RecordingRenderer()

    result = heldout_validation(FIXTURE, objective, gate, renderer)

    assert renderer.seeds == [HELDOUT_RENDER_SEED]
    assert set(result) == {
        "source", "score", "components", "feasibility", "valid"
    }
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
cd tools
uv run pytest tests/test_headroom_driver.py tests/test_headroom_rescore.py -q
```

Expected: failures for the missing constrained arm, target-set option, and
held-out validation helper.

- [ ] **Step 4: Add the constrained arm without changing defaults**

In `tools/match/headroom.py`:

```python
DEFAULT_ARMS = (
    "baseline_seeded",
    "big_seeded",
    "baseline_unseeded",
    "big_unseeded",
)

ARMS: dict[str, dict[str, Any]] = {
    "baseline_seeded": {
        "budget": 2000, "seed_model": True, "restarts": False,
        "preserve_voicing": False,
    },
    "big_seeded": {
        "budget": 200000, "seed_model": True, "restarts": True,
        "preserve_voicing": False,
    },
    "baseline_unseeded": {
        "budget": 2000, "seed_model": False, "restarts": False,
        "preserve_voicing": False,
    },
    "big_unseeded": {
        "budget": 200000, "seed_model": False, "restarts": True,
        "preserve_voicing": False,
    },
    "big_seeded_constrained": {
        "budget": 200000, "seed_model": True, "restarts": True,
        "preserve_voicing": True,
    },
}
```

Set parser default to `list(DEFAULT_ARMS)`, not `list(ARMS)`. In `run_arm`:

```python
    if cfg["preserve_voicing"]:
        argv += ["--preserve-voicing"]
```

- [ ] **Step 5: Implement held-out validation and row validity**

Import `TonalFeasibility` and `analyze_wave`. Add:

```python
def heldout_validation(
    bfxr_path: Path,
    objective: MatchObjective,
    gate: TonalFeasibility,
    renderer: Any,
    seed: int = HELDOUT_RENDER_SEED,
) -> dict:
    params = read_bfxr(bfxr_path)
    wave = renderer.render_batch([params], seeds=seed)[0]
    if wave is None:
        raise RuntimeError("held-out renderer returned no waveform")
    return analyze_wave(
        objective, gate, wave, source="heldout_render"
    ).to_dict()


def heldout_validation_for_run(
    target: Path, bfxr_path: Path, jobs: int | None
) -> dict:
    objective = MatchObjective(prepare_target(target))
    gate = TonalFeasibility(objective.target_features)
    with BfxrRenderer(jobs=jobs) as renderer:
        return heldout_validation(bfxr_path, objective, gate, renderer)
```

In `run_arm`, handle an empty/invalid matcher report before indexing. Reports
written before this feature have no `status`, so treat a nonempty legacy
`results` list as `"ok"`:

```python
    results = report.get("results", [])
    status = report.get("status", "ok" if results else "invalid")
    if status != "ok" or not results:
        return {
            "arm": arm,
            "valid": False,
            "failure_reason": report.get(
                "failure_reason", "missing_output"
            ),
            "evals": int(report.get("evals", 0)),
            "elapsed_seconds": float(report.get("elapsed_seconds", 0.0)),
            "trace": report.get("trace", []),
            "underspent": bool(
                cfg["restarts"]
                and int(report.get("evals", 0)) < 0.9 * int(cfg["budget"])
            ),
        }
```

After the row is built, replace the old unconditional score-only held-out
`try` block with this constrained/unconstrained branch:

```python
    if cfg["preserve_voicing"]:
        row["search_feasibility"] = best.get("search_feasibility")
        row["emitted_artifact"] = best.get("emitted_artifact")
        row["valid"] = bool(
            best.get("search_feasibility", {}).get("feasible")
            and best.get("emitted_artifact", {}).get("valid")
        )
        if not row["valid"]:
            row["failure_reason"] = "emitted_artifact_infeasible"
        else:
            try:
                heldout = heldout_validation_for_run(
                    target, out_dir / BEST_FILE, jobs
                )
            except Exception as exc:
                row["valid"] = False
                row["failure_reason"] = "render_failed"
                row["heldout_error"] = str(exc)
            else:
                row["heldout_score"] = heldout["score"]
                row["heldout_validation"] = heldout
                if not heldout["valid"]:
                    row["valid"] = False
                    row["failure_reason"] = "heldout_render_infeasible"
    else:
        try:
            row["heldout_score"] = heldout_for_run(
                target, out_dir / BEST_FILE, jobs
            )
        except Exception as exc:
            row["heldout_score"] = None
            row["heldout_error"] = f"{type(exc).__name__}: {exc}"
```

Keep the old score-only held-out function and the exact unconstrained exception
shape so historical tests and result rows remain unchanged.

- [ ] **Step 6: Add hard/holdout/all target selection**

Import `AUDIO_EXTS`. Add parser arguments:

```python
    p.add_argument(
        "--target-set",
        choices=("hard", "holdout", "all"),
        default="hard",
    )
    p.add_argument(
        "--listen-control-root",
        type=Path,
        default=None,
        help="existing big_seeded root to include beside a treatment-only run",
    )
```

Add:

```python
def select_real_targets(targets: Path, target_set: str) -> list[Path]:
    audio = [
        path for path in sorted(targets.iterdir())
        if path.suffix.lower() in AUDIO_EXTS
    ]
    hard = set(HARD_SLICE)
    if target_set == "hard":
        return [path for path in audio if path.stem in hard]
    if target_set == "holdout":
        return [path for path in audio if path.stem not in hard]
    return audio
```

Replace the hard-coded `real` selection with this function. Warn about
missing hard targets only when `target_set == "hard"`.

When building listen arms:

```python
    listen_arms = []
    if args.listen_control_root is not None:
        listen_arms.append(("big_seeded", args.listen_control_root))
    listen_arms.extend(
        (arm, args.out / arm)
        for arm in args.arms
        if arm != "baseline_unseeded"
    )
```

Build `eligible` from the merged result rows, excluding rows with an `error`
or explicit `valid: false`:

```python
    eligible = {
        (row["target"], row["arm"])
        for row in merged_rows
        if row.get("kind") == "real"
        and not row.get("error")
        and row.get("valid") is not False
    }
    for arm, root in listen_arms:
        if args.listen_control_root is not None and root == args.listen_control_root:
            eligible.update(
                (path.stem, arm)
                for path in real
                if (
                    root / _safe_dir(path.stem)
                    / "model_seeded" / "match.wav"
                ).is_file()
            )
```

Use the driver's existing `_safe_dir`; do not introduce a second sanitization
rule. Pass `quality_gate=True`, `eligible=eligible`, and:

```python
only={path.stem for path in real}
```

Name pages from the target set:

```python
page_stem = f"tonal_{args.target_set}"
```

This writes `tonal_hard.html`/`tonal_hard_key.json` or
`tonal_holdout.html`/`tonal_holdout_key.json` without overwriting the old
headroom page.

- [ ] **Step 7: Record the checkpoint hash**

Add:

```python
import hashlib


def _sha256_if_file(path: Path) -> str | None:
    return (
        hashlib.sha256(path.read_bytes()).hexdigest()
        if path.is_file() else None
    )
```

Write `"ckpt_sha256": _sha256_if_file(args.ckpt)` beside `"ckpt"` in
`results.json`. This preserves parser/driver unit tests that use a synthetic
checkpoint path; the real experiment separately requires the file and exact
hash before it can start.
The expected experiment checkpoint hash is:

```text
47f2b5ff6bfdd4abc503810a3a0b9b0c8fed2398a66b3b75b18dcaf0b87f8d98
```

- [ ] **Step 8: Run headroom/page tests**

Run:

```bash
cd tools
uv run pytest \
  tests/test_headroom_driver.py \
  tests/test_headroom_rescore.py \
  tests/test_headroom_page.py \
  tests/test_headroom_presets.py -q
```

Expected: all selected tests pass.

- [ ] **Step 9: Commit the experiment driver**

```bash
git add tools/match/headroom.py \
  tools/tests/test_headroom_driver.py \
  tools/tests/test_headroom_rescore.py
git commit -m "feat(match): add constrained tonal probe arm"
```

## Task 9: Full automated verification

**Files:**
- Modify only if a test reveals a scoped defect in the files above

- [ ] **Step 1: Validate tracked exemplar integrity**

Run:

```bash
cd tools
uv run python -m match.exemplars exemplars/human_rated/manifest.json
```

Expected: exit 0 and no output.

- [ ] **Step 2: Run every non-slow test**

Run:

```bash
cd tools
uv run pytest -q
```

Expected: the complete non-slow suite passes.

- [ ] **Step 3: Run slow round-trip and native parity tests**

Run:

```bash
cd tools
uv run pytest tests/test_roundtrip.py -q -m slow
uv run pytest tests/test_native_parity.py -q
```

Expected: all selected round-trip and native-parity tests pass.

- [ ] **Step 4: Run a tiny constrained CLI smoke**

Run:

```bash
cd tools
uv run python -m match.match \
  "targets/Mario 2 - Throw.wav" \
  -o /tmp/bfxr2-tonal-smoke \
  --budget 128 \
  --wavetypes 0 \
  --rng-seed 0 \
  --preserve-voicing
```

Expected: `report.json` exists; it contains either a valid result with
search/emitted feasibility or the explicit `no_feasible_candidate` outcome.

- [ ] **Step 5: Inspect scope**

Run:

```bash
git status --short
git diff --check
git diff --stat
```

Expected: only planned matcher, test, exemplar, and documentation files are
changed. The pre-existing `.DS_Store` modification remains unstaged.

- [ ] **Step 6: Commit any verification-only corrections**

If Step 2–4 required a correction, stage only its scoped files and commit:

```bash
git commit -m "fix(match): close tonal probe verification gaps"
```

If no corrections were required, make no empty commit.

- [ ] **Step 7: Request code review before freezing the experiment**

Invoke `superpowers:requesting-code-review` against the complete implementation
diff. Address only technically verified findings, rerun Steps 1–5 after any
behavioral change, and commit the corrections before Task 10. Task 10 must
record the post-review commit as the frozen implementation.

## Task 10: Run the ten-target falsification gate

**Files generated (gitignored):**
- `tools/invert/runs/tonal_feasibility/results.json`
- `tools/invert/runs/tonal_feasibility/big_seeded_constrained/**`
- `tools/invert/runs/tonal_feasibility/tonal_hard.html`
- `tools/invert/runs/tonal_feasibility/tonal_hard_key.json`

- [ ] **Step 1: Verify the frozen checkpoint before spending compute**

Run from `tools/`:

```bash
git rev-parse HEAD
git status --short
TONAL_CKPT="../.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt"
test -f "$TONAL_CKPT"
test "$(shasum -a 256 "$TONAL_CKPT" | awk '{print $1}')" = \
  "47f2b5ff6bfdd4abc503810a3a0b9b0c8fed2398a66b3b75b18dcaf0b87f8d98"
```

Expected: record the post-review commit as the frozen implementation commit;
only the pre-existing `.DS_Store` is dirty; both checkpoint checks exit 0.

- [ ] **Step 2: Run constrained search on the known ten**

Run from `tools/`:

```bash
TONAL_CKPT="../.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt"
PYTHONPATH=. uv run python -m match.headroom \
  --targets targets \
  --ckpt "$TONAL_CKPT" \
  -o invert/runs/tonal_feasibility \
  --jobs 6 \
  --rng-seed 0 \
  --presets 0 \
  --target-set hard \
  --arms big_seeded_constrained \
  --listen-control-root invert/runs/headroom/big_seeded
```

Expected: ten constrained rows are written incrementally. The run finishes
with `tonal_hard.html` and a separate decode key.

- [ ] **Step 3: Check mechanical validity without reading the decode key**

Run:

```bash
jq '[.rows[] | select(.arm=="big_seeded_constrained")] | length' \
  invert/runs/tonal_feasibility/results.json
jq '[.rows[] | select(.arm=="big_seeded_constrained" and .valid!=true)] | length' \
  invert/runs/tonal_feasibility/results.json
```

Expected: first command prints `10`; second prints `0`. If the second prints a
nonzero count, the strict gate has already failed; record the failure and do
not request human ratings.

- [ ] **Step 4: Stop for the complete blind rating table**

Give the user `tools/invert/runs/tonal_feasibility/tonal_hard.html`. Do not
open or disclose `tonal_hard_key.json`. Request every A/B rating on
`quality_0_to_5`, allowing half-points.

- [ ] **Step 5: Decode only after all ratings arrive**

Join the returned target/A/B table to `tonal_hard_key.json`. Extract the ten
`big_seeded_constrained` ratings.

Expected pass condition: every treatment rating is at least 4. Any value below
4 ends the experiment before the holdout.

- [ ] **Step 6: Record and commit the development verdict**

Create `docs/superpowers/plans/2026-07-29-tonal-feasibility-results.md` with:

- frozen commit, checkpoint hash, renderer version, RNG, and budget;
- all ten blinded A/B observations and decoded arms;
- per-target treatment validity and rating;
- the literal rule `min(treatment_rating) >= 4`;
- `DEVELOPMENT PASS` or `DEVELOPMENT FAIL`;
- if failed, the exact targets below 4 and confirmation that the holdout
  remains unspent.

Then:

```bash
git add docs/superpowers/plans/2026-07-29-tonal-feasibility-results.md
git commit -m "docs: record tonal feasibility development verdict"
```

## Task 11: Run the frozen 22-target holdout only after a perfect development pass

**Precondition:** Task 10 records `DEVELOPMENT PASS`. Otherwise this task is
skipped in full.

**Files generated (gitignored):**
- additional control/treatment rows and artifacts under `tools/invert/runs/tonal_feasibility/`
- `tools/invert/runs/tonal_feasibility/tonal_holdout.html`
- `tools/invert/runs/tonal_feasibility/tonal_holdout_key.json`

- [ ] **Step 1: Record the frozen implementation commit**

Run:

```bash
git rev-parse HEAD^
git diff --name-only HEAD^..HEAD
git status --short
```

Expected: `HEAD^` equals the frozen implementation hash already recorded in
the development results document, and the only path changed by the current
`HEAD` verdict commit is
`docs/superpowers/plans/2026-07-29-tonal-feasibility-results.md`. Only the
pre-existing `.DS_Store` may be dirty. Do not alter thresholds, code, model,
seeds, budget, or renderer after this point.

- [ ] **Step 2: Run matched control and treatment arms**

From `tools/`, redeclare the same frozen checkpoint and verify its checksum
again before launching:

```bash
TONAL_CKPT="../.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt"
test -f "$TONAL_CKPT"
test "$(shasum -a 256 "$TONAL_CKPT" | awk '{print $1}')" = \
  "47f2b5ff6bfdd4abc503810a3a0b9b0c8fed2398a66b3b75b18dcaf0b87f8d98"
PYTHONPATH=. uv run python -m match.headroom \
  --targets targets \
  --ckpt "$TONAL_CKPT" \
  -o invert/runs/tonal_feasibility \
  --jobs 6 \
  --rng-seed 0 \
  --presets 0 \
  --target-set holdout \
  --arms big_seeded big_seeded_constrained
```

Expected: 44 new rows, one matched pair for each of the remaining 22 targets,
plus `tonal_holdout.html` and its separate decode key.

- [ ] **Step 3: Check holdout completeness and validity**

Run:

```bash
jq '[.rows[] | select(.kind=="real" and
  (.arm=="big_seeded" or .arm=="big_seeded_constrained"))] | length' \
  invert/runs/tonal_feasibility/results.json
jq '[.rows[] | select(.arm=="big_seeded_constrained" and .valid!=true)] | length' \
  invert/runs/tonal_feasibility/results.json
```

Expected after the merged hard+holdout run: the first count includes ten hard
treatment rows plus 44 holdout rows, so it prints `54`; the second prints `0`.
Any invalid treatment is an automatic final failure.

- [ ] **Step 4: Stop for the complete holdout rating table**

Give the user `tonal_holdout.html`. Keep `tonal_holdout_key.json` hidden until
all 22 A/B rows are rated on `quality_0_to_5`.

- [ ] **Step 5: Decode and apply the all-32 rule**

Combine the ten frozen development treatment ratings with the 22 decoded
holdout treatment ratings.

Expected final pass condition:

```text
count(treatment ratings) == 32
min(treatment ratings) >= 4
```

No mean, median, win count, or objective score can override either condition.

- [ ] **Step 6: Complete and commit the final result**

Append the 22 blind observations, decoded treatment ratings, invalid outcomes,
and final minimum to
`docs/superpowers/plans/2026-07-29-tonal-feasibility-results.md`. End with
exactly one verdict:

```text
FINAL PASS — 32/32 treatment outputs rated at least 4/5
```

or:

```text
FINAL FAIL — at least one treatment output rated below 4/5 or invalid
```

Commit:

```bash
git add docs/superpowers/plans/2026-07-29-tonal-feasibility-results.md
git commit -m "docs: record tonal feasibility final verdict"
```

## Task 12: Final review and handoff

**Files:**
- Review all files changed by Tasks 1–11

- [ ] **Step 1: Run final verification**

```bash
cd tools
uv run python -m match.exemplars exemplars/human_rated/manifest.json
uv run pytest -q
```

Expected: validator exits 0; complete non-slow suite passes.

- [ ] **Step 2: Confirm default behavior remains off**

Run:

```bash
cd tools
uv run python -m match.match --help | rg -- "--preserve-voicing"
uv run pytest \
  tests/test_optimizer_restarts.py::test_restarts_flag_defaults_off \
  tests/test_match_feasibility.py::test_preserve_voicing_flag_defaults_off_and_can_enable \
  -q
```

Expected: help documents the opt-in flag; both default-off tests pass.

- [ ] **Step 3: Inspect repository scope**

Run:

```bash
git status --short --branch
git log --oneline --decorate -12
```

Expected: implementation and result commits are visible; no experiment output
is staged; the unrelated `.DS_Store` remains outside all commits.

- [ ] **Step 4: Confirm review and frozen-run integrity**

Confirm the Task 9 review findings were resolved before the frozen commit and
that Tasks 10–11 used that exact commit. Do not change behavior after holdout
ratings; any required behavioral fix invalidates the holdout and requires a
new frozen run.
