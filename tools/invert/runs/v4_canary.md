# Invert v4 pack canary

Clean isolated-knob renders through the v4 pack (pad/crop, hop=128, t_abs, unblurred mel).
Wave type: 0 (Square), N=40 per sweep. Uses `defaults_unit()` (bipolar slides stay at 0.5).

## Correlations

| probe | corr | stretch-era / diagnosis ref |
| --- | --- | --- |
| mean voiced f0 ↔ frequency_start | **0.791** | clean ~0.90; isolated stretch pack ~0.73 |
| log_duration ↔ sustain+decay | **0.960** | clean ~0.88 |
| env_width (#frames > -60dB) ↔ sustain (sus+dec covary) | 0.753 | — |
| voiced_frac ↔ sustain (sus+dec covary) | nan | — |
| env_width ↔ sustain (decay fixed) | 0.824 | — |
| log_duration ↔ sustain (decay fixed) | 0.994 | — |
| native_frames ↔ sustain (decay fixed) | **0.824** | stretch-era ≈ destroyed (always 128) |

## Timing sanity

- native real frames (median): 127
- min/max native frames: 4 / 127
- sustain-only native frames min/max: 32 / 127

## Verdict

SOFT PASS — identifiable axes readable; proceed to v4 regen/train.
