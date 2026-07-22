# Target samples

Drop sound files here (wav/flac/ogg/aiff/mp3) that you'd like the matcher to
approximate with bfxr sounds. Short one-shot sfx work best.

Then run:

```sh
cd tools
uv run python -m match.batch targets/ -o batch_out/ --html-report
```

and open `batch_out/index.html` to listen to target-vs-match comparisons.
