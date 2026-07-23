# Target samples

Drop sound files here (wav/flac/ogg/aiff/mp3) that you'd like the matcher to
approximate with bfxr sounds. Short one-shot sfx work best.

Wavs are typically gitignored. In a git worktree this directory may be empty —
symlink or copy samples from the main checkout before running
`invert.eval_targets` (default `--targets` is this folder).

Then run:

```sh
cd tools
uv run python -m match.batch targets/ -o batch_out/ --html-report
```

and open `batch_out/index.html` to listen to target-vs-match comparisons.
