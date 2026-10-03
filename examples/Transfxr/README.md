# Transfxr examples

Open **Transfxr** in Bfxr, then click one of the 15 family buttons. Each click varies a complete curated sound state while keeping its family's duration, timbre and trajectory traits. Locks keep your favorite controls in place.

The [revised listening catalogue](survey/index.html) contains 228 curated exemplars, with family filters, six-example comparisons, a tour of typical voices, and links to open each sound in the synth. The [discovery archive](survey/archive.html) preserves the original 512 sounds and exploratory group labels. See [the listening refinement and reproduction commands](survey/README.md). Open `survey/Families.bcol` with **Open Data** to explore exact revised family exemplars.

The original eight recipes are preserved in `Transfxr.bcol`. Open it with **Open Data** for this exact collection:

- **Laser Zip:** a short, bright falling bolt.
- **Bubble Drop:** a rounded droplet with a bouncing pitch.
- **Portal Bloom:** a slow filter opening with a shimmering echo.
- **Power Up:** five ascending arcade notes.
- **Soft Landing:** a low thump fading into dust.
- **Clockwork Bird:** a quick, wobbling mechanical chirp.
- **Ghost Signal:** a distant whistle dissolving into noise.
- **Airlock:** a resonant rush of air.

For each transition, drag the orange **A** and **B** handles up or down to set the two values. Drag the middle of the graph to move both values together. The shape buttons below each graph choose the transition; the selected shape is orange. Triangle and Pulse visit B halfway through and return to A, so their B handle sits in the middle. The graph follows your drag immediately and auditions the sound when you release it. Focus a handle and use the arrow keys for small adjustments, or hold Shift for finer adjustments.

The lock at the left protects the whole row during example generation, Randomize and Mutate. You can still edit a locked row directly.

**Duration** sets the travel time. **Attack** and **Release** fade the voice within that time; overlapping fades soften short sounds. **Echo** can extend beyond the duration. To add air or grit, choose **White** under **Morph to** and shape the **Morph** curve. Pitch and filter readouts show Hz; the other endpoint values are percentages. Drag knobs up/down, use the mouse wheel, or focus them and use arrow keys.

Render exact 44.1 kHz mono WAVs and the combined `transfxr_showcase.wav` demo reel:

```sh
node tools/render/transfxr_examples.js
```

WAV files are generated locally and ignored by Git. The editable `.bcol` collection is included. The reel plays the sounds in the order above, with a quarter-second gap between them.

Run the synthesis and persistence tests with `npm test`.
