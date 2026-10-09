# Working agreement for the sound-matching work

Goal: given a sound, produce an editable preset on one of the app's synths
that a listener rates as close to it. Code lives in `tools/sfxmatch/`
(see its README). The older `tools/multisynth/` and `tools/neural_invert/`
experiments are kept for reference and as baselines; do not extend them.

## How progress is measured

- **One benchmark.** `tools/sfxmatch/benchmark.json` is frozen: 50 external
  recordings and 43 native presets. Do not add, drop or swap targets.
- **One rating protocol.** Blind 1–5 likeness per candidate, via
  `python -m sfxmatch.benchmark page`. Ratings go in
  `tools/sfxmatch/ratings/` and `benchmark score` prints the trend.
- **Benchmark ratings happen at milestones, not per tweak.** Ask for a
  benchmark session only when the automatic numbers below have moved clearly
  and you have a complete system to compare with the last rated one.
- **Development listening is welcome when it answers a consequential
  question** (for example "can any synth reach this kind of sound?"). The
  listener wants to stay involved. Keep it off the benchmark targets, say
  beforehand what each answer would change, and never spend a session
  settling one hyperparameter on five sounds.
- **A failed search is not proof of a limit.** A close match proves a sound
  is reachable; a miss may be the search or the objective. Show the listener
  several different candidates before concluding a synth cannot do something.
- **One objective.** `sfxmatch.objective` is fixed. It agrees with the
  listener on roughly two thirds of close calls, so use it to get into the
  right neighbourhood and to compare systems in aggregate, not to split hairs
  between two finalists. Do not fit or reweight it using ratings; a few
  hundred pairs cannot support that, and every attempt so far failed its own
  test. Change it only for a mechanical defect you can show (v2 fixed one:
  spectral balance was barely charged), set any new weight in advance, and
  re-run the reach probe to test the change. `python -m sfxmatch.agreement`
  is the test set, but pairwise agreement cannot show what an objective does
  when it drives a search: listen to its optimum.
- **Models are judged by the audio they produce.** `python -m
  sfxmatch.evaluate` re-renders predictions for held-out native sounds and
  scores them. Parameter error and validation loss are for debugging only.

## How to work

- Data is free and rendering is fast (about 200 examples/s on a quiet
  machine). If a model is underfitting or overfitting, the first move is more
  data and more training, not a new loss term. Check the scaling curve in
  `LOG.md` before generating more; it flattened after about 500k examples.
- For seeding a search, retrieve from the library first. The trained model is
  no better as a seed source and is for cases where a library cannot ship.
- Search budgets are thousands of renders per synth, not hundreds. Use
  `sfxmatch.search`.
- Record each experiment as one short entry in `tools/sfxmatch/LOG.md`:
  what you expected, what you changed, the numbers, the verdict. Nothing else.
- Do not write protocol files, hash manifests, replay audits, HTTP audits,
  "frozen" run directories or per-experiment evaluation scripts. Tests cover
  correctness; git covers provenance.
- `tools/sfxmatch/runs/` is disposable and ignored. Never commit it.
- Never edit `js/`. The shipped synths are the ground truth; the headless
  renderer loads them unmodified.
- Run things from `tools/` with `uv run`. Tests: `uv run pytest
  tests/test_sfxmatch.py tests/test_sfxmatch_render.py`.
