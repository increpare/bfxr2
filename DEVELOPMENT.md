## How to run

Uh, it should work just fine. There's an optional compilation step if you want to make everything tiny, but as a default just hosting a local http server and loading index.html should work...

## How to compile

```node compile.js```, then everything should be in the bin directory.

## How to add new sound templates.

So, a template sound effect ('jump', say) is specified in Bfxr (any of the synths) as a .bcol file.   This is then stored in "./templates/[Synth Name]/[Template_Name].bcol" to be referenced in the templates list of the synthesizer you are using.

Sound names in a template look like "varietyname_suffix".  

![image](https://github.com/user-attachments/assets/55b3f8ad-0ea1-415a-8de3-a7a46da356c5)

The sounds are grouped together into varieties, with the idea being that their range of values is the range of possible values of that variety.

![image](https://github.com/user-attachments/assets/2db70ccc-65c5-45a2-9d71-63cdecd033a0)

(Duplicate values are combined already at this stage.)

So in the end we have that a template is a group of 'varieties'. In Bfxr when you hit the generate button, Bfxr picks a variety at at random, then generates a sound with paramaters within the ranges it finds in the exemplar sounds.

(The only reason you'd ever _need_ more than 2 example sounds for a given variety is to allow for more than two BUTTONSELECT values (wave shapes, terrains or what have yous)).

So ok once you've save the .bcol files in the folder, you need to run ```node insert_templates.js" to generate ```js/synths/tempaltes.js```.  It's a bit annoying, but the whole point is being able to easily load/save/tweak .bcol files, which IMO makes the annoyance worthwhile.

If you wish to weight a variety so it appears more often than others, just put a number at the start (multiple digits allowed, e.g. "22coin" will appear ten times more often than "2coin").

(There are some hard-coded tempaltes, i.e. Randomize and Mutate - but any ones defined in ./templates  will overwrite existing ones - e.g. pickup_coin.bcol will override any existing generate_pickup_coin method in Bfxr.js)

## Game verbs and the Soundboard

`GAME_VERBS` in `js/globals.js` is the shared vocabulary. A `PresetSynth` recipe with a `verb` field becomes a verb preset: it is sorted before the engine's character presets, its button reads as the verb's name, and `synth.verb_generator('jump')` finds it. `Mixr.resolve_reference('Whooshr:jump')` (or `'Whooshr:generate_dodge'`) turns a reference into a generator, which is how the Soundboard catalogue in `js/synths/Soundboard.js` names its ingredients. Each catalogue entry is a solo `src` or a `mix` of base and sweetener with `balance`, `align` (0 start, 1 peak, 2 tail) and a weight `w`. Run `node tools/render/verb_inventory.js` after changing presets or the catalogue; `tests/soundboard.test.js` enforces that every ingredient resolves and renders inside its verb's duration class.
