# Sound quality examples

32 editable examples from the sound-quality pass. Open Quality.bcol using Open Data. It replaces the example lists in its included tabs; save your current collection first if needed.

The [26.5-second reel](quality_showcase.wav) plays complete sounds with short gaps. Levels are balanced in the reel; individual WAVs match their saved settings.

| Start | Tab | Sound |
| --- | --- | --- |
| 0.00 s | Fractr | Glass crack |
| 1.15 s | Boomr | Grenade |
| 2.50 s | Rollr | Wood over boards |
| 4.00 s | Rustlr | Paper turn |
| 4.90 s | Tappr | Focus |
| 5.23 s | Tappr | Select |
| 5.64 s | Tappr | Back |
| 6.01 s | Tappr | Panel open |
| 6.53 s | Breathr | Airflow breath |
| 9.58 s | Breathr | Retro breath |
| 11.63 s | Breathr | Snore |
| 14.68 s | Pluckr | Nylon string |
| 16.33 s | Pluckr | Steel string |
| 17.98 s | Pluckr | Rubber string |
| 19.63 s | Pluckr | Glass string |
| 21.28 s | Pluckr | Gravity string |
| 22.93 s | Notifr | Bell 1 |
| 23.63 s | Notifr | Bell 2 |
| 24.33 s | Notifr | Bell 3 |
| 25.03 s | Stackr | Whoosh into impact |

The three bells use the same alert pattern and different instrument seeds. The strings share tuning, excitation seed and editable controls; only their material changes.

Stackr: click New empty stack, make a sound in another tab, then Layer in Stackr. Add another sound the same way. Leave Start at zero to overlay, or increase it to make a sequence. The included Whoosh into impact is an editable example.

Rebuild: `node tools/render/quality_examples.js`. WAVs are generated locally and ignored by Git. All examples are checked for finite bounded audio, faded edges and identical replay after parameter serialization.
