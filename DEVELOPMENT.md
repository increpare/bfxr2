## How to run

Uh, it should work just fine. There's an optional compilation step if you want to make everything tiny, but as a default just hosting a local http server and loading index.html should work...

## How to compile

```node compile.js```, then everything should be in the bin directory.

## How to add new sound templates.

So, a preset sound effect ('jump', say) is specified in Bfxr (any of the synths) as a .bcol file.   This is then stored in "./templates/[Synth Name]/[Preset_Name].bcol" to be referenced in the presets field of the synthesizer you are using.

Sound names in a template look like "varietyname_suffix".  

![image](https://github.com/user-attachments/assets/55b3f8ad-0ea1-415a-8de3-a7a46da356c5)

The sounds are grouped together into varieties, with the idea being that their range of values is the range of possible values of that variety.

![image](https://github.com/user-attachments/assets/052c42ae-918c-4b20-be66-67f94c82e4a8)

So in the end we have that a preset is a group of varieties. In Bfxr when you hit the generate button, Bfxr picks a variety at at random, then generates a sound with paramaters within the ranges it finds in the exemplar sounds.

(The only reason you'd ever _need_ more than 2 example sounds for a given variety is to allow for more than two BUTTONSELECT values (wave shapes, terrains or what have yous)).

So ok once you've save the .bcol files in the folder, you need to run ```node insert_templates.js" to generate ```js/synths/tempaltes.js```.  It's a bit annoying, but the whole point is being able to easily load/save/tweak .bcol files, which IMO makes the annoyance worthwhile.
