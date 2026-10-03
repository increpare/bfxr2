# Interface sounds

40 editable sounds: eight randomized categories in each of five new tabs. Every preset click makes another variation.

Open **Interface.bcol** with **Open Data**, or drag it onto Bfxr. This replaces the lists in these five tabs; save your collection first if needed. Select an example to hear and edit it. All five also work as copied layers in Stackr.

The [15.4-second reel](interface_showcase.wav) plays fifteen complete sounds with 0.3-second gaps. Levels are balanced for the reel; individual WAVs match their saved settings exactly.

| Start | Tab | Sound |
| --- | --- | --- |
| 0.00 s | Tappr | Focus |
| 0.39 s | Tappr | Select |
| 0.84 s | Tappr | Back |
| 1.29 s | Rustlr | Card Flick |
| 1.80 s | Rustlr | Bag Open |
| 2.76 s | Rustlr | Zip Pouch |
| 3.59 s | Notifr | Message |
| 4.13 s | Notifr | Denied |
| 4.77 s | Notifr | Achievement |
| 6.22 s | Tickr | Count Coins |
| 7.87 s | Tickr | Level Fill |
| 9.87 s | Tickr | Countdown |
| 13.25 s | Holor | Cursor Trail |
| 13.74 s | Holor | Target Lock |
| 14.61 s | Holor | Data Reveal |

## Tappr

Tactile UI contacts: down and up strokes, small body resonances and an optional electronic accent.

| Preset | Length |
| --- | --- |
| [Focus](tappr_focus.wav) | 0.09 s |
| [Select](tappr_select.wav) | 0.15 s |
| [Back](tappr_back.wav) | 0.15 s |
| [Toggle On](tappr_toggle_on.wav) | 0.25 s |
| [Toggle Off](tappr_toggle_off.wav) | 0.18 s |
| [Disabled](tappr_disabled.wav) | 0.09 s |
| [Panel Open](tappr_panel_open.wav) | 0.23 s |
| [Panel Close](tappr_panel_close.wav) | 0.29 s |

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

## Notifr

Short notifications shaped by tone groups, intervals, spacing and urgency.

| Preset | Length |
| --- | --- |
| [Message](notifr_message.wav) | 0.23 s |
| [Quest Update](notifr_quest_update.wav) | 0.38 s |
| [Objective Done](notifr_objective_done.wav) | 0.66 s |
| [Achievement](notifr_achievement.wav) | 1.15 s |
| [Low Health](notifr_low_health.wav) | 0.88 s |
| [Warning](notifr_warning.wav) | 0.63 s |
| [Denied](notifr_denied.wav) | 0.35 s |
| [Connected](notifr_connected.wav) | 0.23 s |

## Tickr

Progress clocks: counted ticks accelerate or slow down, climb or fall, and finish with a separate cue.

| Preset | Length |
| --- | --- |
| [Count Coins](tickr_count_coins.wav) | 1.35 s |
| [Level Fill](tickr_level_fill.wav) | 1.70 s |
| [Combo Build](tickr_combo_build.wav) | 0.63 s |
| [Countdown](tickr_countdown.wav) | 3.08 s |
| [Research](tickr_research.wav) | 1.77 s |
| [Scan](tickr_scan.wav) | 0.74 s |
| [Lockpick](tickr_lockpick.wav) | 1.41 s |
| [Download](tickr_download.wav) | 1.29 s |

## Holor

Holographic gestures: frequency sidebands, moving spectral bands and comb coloration.

| Preset | Length |
| --- | --- |
| [Cursor Trail](holor_cursor_trail.wav) | 0.19 s |
| [Radial Menu](holor_radial_menu.wav) | 0.23 s |
| [Map Ping](holor_map_ping.wav) | 0.34 s |
| [Target Lock](holor_target_lock.wav) | 0.57 s |
| [Drag / Drop](holor_drag_drop.wav) | 0.18 s |
| [Panel Swipe](holor_panel_swipe.wav) | 0.30 s |
| [Tooltip](holor_tooltip.wav) | 0.14 s |
| [Data Reveal](holor_data_reveal.wav) | 0.78 s |

## Rebuild

`node tools/render/interface_examples.js` regenerates this collection, 40 WAVs, the reel and validation report. An optional argument chooses another output directory. WAVs are generated locally and ignored by Git.

Every example is checked for finite, bounded, audible audio, faded edges and bit-identical sound after reloading its saved parameters. See [validation.json](validation.json).
