# Quick listening feedback

The neural-v1 listening run now defaults to one reference and at most three
distinct options: automatic expert choice, original Bfxr and previous best.
The labels A/B/C hide the methods, and a deterministic shuffle stays stable on
reload. Exact audio aliases appear once. Raw neural predictions remain in
**Detailed ratings**.

Press **Start listening** once to hear Reference → A → B → C. Choose the option
that captures the reference's feel best; one choice saves and advances, with
optional autoplay of the next comparison. **None are close**, **About equal**
and **Skip** are separate judgments. Playback ending never advances by itself.
Five new decisions offer a break. Copy feedback whenever convenient.

Shortcuts: R reference, A/B/C replay, 1/2/3 choose, 0 none, T equal, S skip,
Space sequence/stop, Left undo the last choice made in the current visit.
The original scalar ratings and notes are preserved, and fully rated primary
sets count as already judged. Local saving remains scoped to the same
experiment and browser origin; copying JSON is still the handoff to long-term
archives. A failed browser save stays visibly marked.

## Playback and data

Quick playback uses decoded Web Audio buffers. The current and next comparisons
are fetched/decoded ahead of time. Every replay creates a fresh source at
offset zero, stops the previous source, and uses the same gain. Stop cancels
pending playback and sequence advances. Switching views or hiding the page
stops audio. Failed preparation permits an explicit Skip without claiming the
clips were heard. Detailed mode retains the existing native players.

Ratings-only exports remain schema 2; choices use schema 3. A target's choice
records its kind, presented IDs, auditioned IDs and preferred ID. A clip counts
as auditioned after half its duration or natural completion. This is evidence
of playback, not proof of attention. No numeric likeness/usefulness ratings
are inferred. Immutable archival retains the choice and exact PCM audio.
Preference training uses a heard winner against other heard, distinct clips;
ties, rejections, skips and unheard options produce no strict preference label.
Explicit choice pairs supersede conflicting scalar pairs in the same session.

Refresh an existing gallery without touching frozen results:

```python
import json
from pathlib import Path
from multisynth.coverage_feedback import export_coverage
p = Path('tools/multisynth/runs/neural-v1-listening')
r = json.loads((p / 'results.json').read_text())
export_coverage(p, r['results'], r['metadata'], html_only=True)
```

## Verification, 2026-10-04

- 17 focused JavaScript tests cover choices, legacy ratings, replay from zero,
  decode caching/retry, stale playback, Stop during preparation, manual ended
  status, persistence warnings and missing-clip Skip.
- 60 focused Python tests cover old schemas, schema-3 validation, immutable
  PCM archival/idempotence, heard-only training and HTML-only refresh.
- Separate-origin browser smoke checks cover complete sequence playback,
  audition evidence, one-click advance, replay, keyboard rejection, undo,
  reload/resume, two-option deduplication, five-decision break, details/back,
  and JSON copying. Test choices never entered the user's feedback origin or
  versioned human archives.
- Current gallery refresh preserves experiment
  `98b618ba0e85c9c62a4cf6f7bb25f8700f46e5bcd79b8b6e8094cd7b49e1da71`
  and all 74 WAV/JSON artifact bytes.

This changes feedback collection. It does not retrain the inversion model or
establish an audible improvement; the next human feedback will guide that work.
