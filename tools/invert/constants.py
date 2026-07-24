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
ACCEPT_PEAK = 0.02          # perceptual audibility floor (peak, post-render)
MIN_AUDIBLE_SAMPLES = 882   # ~20 ms @ 44100: reject degenerate "click" renders
TRAIN_CAP_SECONDS = 1.5
FEATURES_MEL_SCALE_IDX = 2  # (512, 128, 64) — hop must match INVERT_CONTOUR_HOP
INVERT_CONTOUR_FRAME = 1024
INVERT_CONTOUR_HOP = 128
SQUARE_ONLY = ("squareDuty", "dutySweep")

# Contour channels (v4): env_db, f0_log2, voiced, t_abs, centroid_log2, noisiness
# Fixed per-channel z-score — estimated on 256 v4 smoke packs, non-pad frames
# only (t_abs > 0). Pad frames excluded so silence-floor / zero-t_abs don't
# dominate. Retrain after any pack change.
CHANNEL_MEAN = (
    -7.22972, 5.82256, 0.610104, 0.174313, 9.36803, 0.374857,
    1.28991, 1.20634, -1.30687, -1.07686, -0.492453, -0.675251, -0.0636056,
    -0.590768, -0.542427, -1.06199, -0.751483, -0.769912, -0.850933, -1.34367,
    -1.17038, -0.895285, -0.930435, -1.13803, -1.21374, -1.08158, -1.07938,
    -1.19986, -1.08448, -1.04881, -1.37811, -1.19947, -1.35423, -1.31702,
    -1.54657, -1.59081, -1.50757, -1.27395, -1.35909, -1.52702, -1.63225,
    -1.60533, -1.66111, -1.71586, -1.68864, -1.63018, -1.7631, -1.73063,
    -1.78791, -1.74279, -1.60989, -1.61657, -1.824, -2.02382, -2.02794,
    -2.06049, -2.19803, -2.18249, -2.14244, -2.1383, -2.18536, -2.27408,
    -2.14101, -2.11888, -2.12398, -2.02859, -1.99517, -1.68701, -1.72071,
    -1.92042,
)
CHANNEL_STD = (
    12.3628, 4.80177, 0.487726, 0.107369, 2.74506, 0.396367,
    4.85062, 4.84413, 5.04835, 5.08898, 5.5816, 5.54387, 5.84038, 5.55311,
    5.53823, 5.25914, 5.2797, 5.32787, 5.38175, 5.20693, 5.25334, 5.50889,
    5.57596, 5.4837, 5.42728, 5.50983, 5.41185, 5.31907, 5.41187, 5.36398,
    5.38329, 5.50289, 5.30107, 5.39821, 5.40071, 5.45338, 5.28949, 5.2942,
    5.32786, 5.37234, 5.3117, 5.34205, 5.2802, 5.24469, 5.29706, 5.32887,
    5.29235, 5.27282, 5.23897, 5.19488, 5.2007, 5.16072, 5.1676, 5.20687,
    5.217, 5.18467, 5.23227, 5.26792, 5.21158, 5.17095, 5.21101, 5.20883,
    5.18925, 5.196, 5.19772, 5.1158, 5.012, 4.99147, 5.01475, 5.10828,
)

# Per-param loss weights ∝ audio sensitivity (invert.observability, n_probes=300,
# real renderer). Mean ~1.0 over audible params; dead params floored at 0.1.
# Order matches ParamSpace.names. Re-measure if the feature pack changes.
IDENTIFIABILITY_WEIGHT = (
    1.012827686551209, 1.2557550252581424, 0.1495392168611331,
    1.222137949335129, 0.5765883847629487, 2.2911418177403333,
    2.1002556929036134, 2.4249052986626953, 2.0377687270254827,
    0.6072757637722106, 0.7825154827625247, 0.27787555881656645,
    1.1425372693726659, 0.5357902183519676, 1.1072275888247904,
    0.8065365618297189, 0.23615529957251552, 0.21434542609329071,
    1.207044036379648, 1.6365168110843595, 0.7340879545118264,
    0.9871723134487911, 0.7128945752631395, 1.2620717357644906,
    0.48192976999209364, 0.1441137410931102, 1.0803041972224556,
    0.2003139394516397, 1.1022281084591865, 1.552265566354059,
)

# Easy-first curriculum: the N most-sensitive params are supervised from epoch 1;
# the rest ramp in (see train.curriculum_weights).
EASY_PARAM_COUNT = 12

assert len(IDENTIFIABILITY_WEIGHT) == N_PARAMS, (
    f"IDENTIFIABILITY_WEIGHT has {len(IDENTIFIABILITY_WEIGHT)}, expected {N_PARAMS}"
)

