from __future__ import annotations

N_FRAMES = 128
N_CONTOURS = 6
N_MELS = 64
N_CHANNELS = N_CONTOURS + N_MELS
N_PARAMS = 30
N_WAVETYPES = 12
# v2: pack_features silence-trims before extract (matches prepare_target)
# v3: mixture sampling (biased/uniform/kknob/preset), augment_p 0.25
# v4: pad/crop (no stretch), hop=128 contours, t_abs replaces active, unblurred mel
DATASET_VERSION = "v4"
SILENCE_PEAK = 1e-3
TRAIN_CAP_SECONDS = 1.5
FEATURES_MEL_SCALE_IDX = 2  # (512, 128, 64) — hop must match INVERT_CONTOUR_HOP
INVERT_CONTOUR_FRAME = 1024
INVERT_CONTOUR_HOP = 128
SQUARE_ONLY = ("squareDuty", "dutySweep")

# Contour channels (v4): env_db, f0_log2, voiced, t_abs, centroid_log2, noisiness
# Fixed per-channel z-score — re-estimated after v4 pack change (Task 2).
# Placeholder zeros until re-estimate; normalize still runs (model will retrain).
CHANNEL_MEAN = (0.0,) * N_CHANNELS
CHANNEL_STD = (1.0,) * N_CHANNELS

