## How to run

Run `make serve` from the project directory (requires Node.js and Make). It serves the current directory on an available local port and prints a link to Bfxr. Open that link in your browser; press Ctrl+C in the terminal to stop the server.

You can also run `node tools/serve.js` directly. No compilation or npm install is needed to serve the app. There's an optional compilation step if you want to make everything tiny.

## How to compile

Install dependencies once with `npm ci` (`npm.cmd ci` in Windows PowerShell), then run `make` from the project directory to build the website. You need Node.js and Make; Perl and an external gzip command are not required. You can also run `make build` or `node compile.js`.

The build refreshes templates, bundles JavaScript and CSS into `bin/index.html`, and generates `bin/index.html.gz`. Upload the **contents** of `bin/` to the website root: `index.html`, `index.html.gz`, `favicon.ico`, `favicon.svg`, and the entire `img/` folder. Replace both HTML files together to keep the compressed version current.

Use `make serve` for the local development server.

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
