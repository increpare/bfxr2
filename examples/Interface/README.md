# Interface sounds

8 editable inventory sounds from Rustlr. Every preset click makes another variation.

Open **Interface.bcol** with **Open Data**, or drag it onto Bfxr. This replaces the lists in Rustlr; save your collection first if needed. Select an example to hear and edit it. These sounds also work as sources in Mixr.

The [2.0-second reel](interface_showcase.wav) plays three complete sounds with 0.3-second gaps. Levels are balanced for the reel; individual WAVs match their saved settings exactly.

| Start | Tab | Sound |
| --- | --- | --- |
| 0.00 s | Rustlr | Card Flick |
| 0.50 s | Rustlr | Bag Open |
| 1.47 s | Rustlr | Zip Pouch |

## Rustlr

Inventory handling: textured paper, cloth, leather, plastic, foil and zipper movements.

| Preset | Length |
| --- | --- |
| [Card Flick](rustlr_card_flick.wav) | 0.20 s |
| [Page Turn](rustlr_page_turn.wav) | 0.67 s |
| [Bag Open](rustlr_bag_open.wav) | 0.67 s |
| [Equip Gear](rustlr_equip_gear.wav) | 0.62 s |
| [Item Slide](rustlr_item_slide.wav) | 0.39 s |
| [Cloth Fold](rustlr_cloth_fold.wav) | 0.45 s |
| [Wrapper](rustlr_wrapper.wav) | 0.69 s |
| [Zip Pouch](rustlr_zip_pouch.wav) | 0.53 s |

## Rebuild

`node tools/render/interface_examples.js` regenerates this collection, 8 WAVs, the reel and validation report. An optional argument chooses another output directory. WAVs are generated locally and ignored by Git.

Every example is checked for finite, bounded, audible audio, faded edges and bit-identical sound after reloading its saved parameters. See [validation.json](validation.json).
