# Jinglr instrument palette

Sixteen exact voices: two characters from each of Jinglr's eight instrument families. Every voice plays the same 1.19-second C4–E4–G4–C5 tune. The different attack, tone, and decay come from the instrument seed; the notes and musical knobs stay fixed.

Listen to the [24.6-second audition reel](jinglr_instrument_palette.wav). Families play in order, with voice A followed by voice B and a 0.2-second gap between examples. Each phrase and its tail plays completely. The reel applies mild level matching (0.75–1.35×); individual WAVs keep Sound Volume at 0.5.

## Try the instruments

Use **Open Data** to load [JinglrPalette.bcol](JinglrPalette.bcol). It opens Jinglr and replaces only that tab’s sound list. Save your current collection first if you want to keep those sounds.

The ten-digit **Seed** contains five melody digits followed by five instrument-character digits. Choose the instrument family, then enter a listed seed to restore an example. The instrument buttons reseed only its character; **Reseed melody** changes only the tune.

## Fixed musical settings

Melody seed **10153**; C major; octave 4; Rise contour; Even rhythm; 4 notes; tempo 126 BPM; swing 0; brightness 0.65; decay 0.45; echo 0; Sound Volume 0.5. These controls and that melody seed reconstruct the same tune without importing the collection.

Both examples in each family were selected from a small seed search for different spectral balances and envelopes. A has the lower measured high-frequency energy ratio of the pair. These are comparison points, not limits on the family’s range.

## Voice codes and reel timestamps

| Start | End | Family | Voice | Seed |
| --- | --- | --- | --- | --- |
| 00:00.00 | 00:01.38 | Pluck | [A](0_pluck_57721.wav) | 1015357721 |
| 00:01.58 | 00:02.96 | Pluck | [B](0_pluck_61803.wav) | 1015361803 |
| 00:03.16 | 00:04.48 | Bell | [A](1_bell_61803.wav) | 1015361803 |
| 00:04.68 | 00:06.07 | Bell | [B](1_bell_99991.wav) | 1015399991 |
| 00:06.27 | 00:07.62 | Chip | [A](2_chip_57721.wav) | 1015357721 |
| 00:07.82 | 00:09.19 | Chip | [B](2_chip_99991.wav) | 1015399991 |
| 00:09.39 | 00:10.79 | Flute | [A](3_flute_10001.wav) | 1015310001 |
| 00:10.99 | 00:12.33 | Flute | [B](3_flute_22361.wav) | 1015322361 |
| 00:12.53 | 00:13.84 | Keys | [A](4_keys_31415.wav) | 1015331415 |
| 00:14.04 | 00:15.40 | Keys | [B](4_keys_12537.wav) | 1015312537 |
| 00:15.60 | 00:16.91 | Reed | [A](5_reed_27182.wav) | 1015327182 |
| 00:17.11 | 00:18.46 | Reed | [B](5_reed_31415.wav) | 1015331415 |
| 00:18.66 | 00:19.96 | FM | [A](6_fm_99991.wav) | 1015399991 |
| 00:20.16 | 00:21.53 | FM | [B](6_fm_10001.wav) | 1015310001 |
| 00:21.73 | 00:23.10 | Strings | [A](7_strings_27182.wav) | 1015327182 |
| 00:23.30 | 00:24.60 | Strings | [B](7_strings_12537.wav) | 1015312537 |

## Rebuild

From the repository root:

```sh
node tools/render/jinglr_palette.js
```

An optional output-folder argument writes the palette elsewhere. The script writes sixteen 44.1 kHz mono PCM16 WAVs, the reel, the editable collection, this guide, and [validation.json](validation.json). Generated WAVs are ignored by Git.

The renderer verifies finite, audible, bounded audio; exact saved-parameter and two-seed PCM reproducibility; unchanged musical controls; and spectral/envelope differences within each pair. Individual RMS is 0.0731–0.1632, with maximum peak 0.4357.
