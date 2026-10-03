// Category buttons specify ranges, so every click is a new sound in that family.
class PresetSynth extends SynthBase {
    version = '1.0.0';
    header_properties = [];
    permalocked = ['masterVolume'];
    hide_params = ['masterVolume'];
    recipes = [];
    static common_params = [
        ['Sound Volume', 'Overall volume of this sound.', 'masterVolume', 0.5, 0, 1],
        ['Variation', 'A repeatable variation of the texture. Preset buttons choose a fresh one.', 'seed', 0.5, 0, 1]
    ];

    initialize_presets() {
        this.post_initialize();
        // Game-verb presets come first: a recipe with a verb is labelled by the shared vocabulary.
        const verbs = typeof GAME_VERBS === 'undefined' ? [] : GAME_VERBS;
        const order = recipe => { const index = verbs.findIndex(verb => verb.id === recipe.verb); return index < 0 ? verbs.length : index; };
        this.recipes = this.recipes.map((recipe, index) => [recipe, index]).sort((a, b) => order(a[0]) - order(b[0]) || a[1] - b[1]).map(([recipe]) => recipe);
        // A recipe with variants shows its first archetype as its nominal values.
        for (const recipe of this.recipes) if (Array.isArray(recipe.variants) && recipe.variants.length && !Object.keys(recipe.values || {}).length) recipe.values = recipe.variants[0];
        this.templates = this.recipes.map(recipe => {
            const method = 'generate_' + recipe.id;
            this[method] = () => this.generate_recipe(recipe.id);
            const verb = verbs.find(entry => entry.id === recipe.verb);
            const label = verb ? verb.name : recipe.name;
            return [label, recipe.tip || 'Generate another ' + recipe.name.toLowerCase() + '.', method, recipe.name.replace(/[^a-zA-Z0-9]/g, '')];
        });
        this.templates.push(['Randomize','Explore all unlocked controls.','randomize_params','Random'],
            ['Mutate','Nudge the unlocked controls of this sound.','mutate_params','Mutant']);
    }

    // The generator method for a game verb, or null when this engine has no preset for it.
    verb_generator(verb) {
        const recipe = this.recipes.find(entry => entry.verb === verb);
        return recipe ? 'generate_' + recipe.id : null;
    }
    verbs() { return this.recipes.filter(recipe => recipe.verb).map(recipe => recipe.verb); }

    apply_params(params, check_locked = false) {
        if (!params || typeof params !== 'object') return;
        for (const info of this.param_info) {
            const name = this.get_param_normalized(info).name;
            if (Object.prototype.hasOwnProperty.call(params, name)) this.set_param(name, params[name], check_locked);
        }
    }

    generate_recipe(id) {
        const recipe = this.recipes.find(entry => entry.id === id);
        if (!recipe) return;
        this.reset_params(true);
        // A recipe may hold several archetypes behind one button; one is drawn per press.
        const variants = Array.isArray(recipe.variants) && recipe.variants.length ? recipe.variants : null;
        const values = variants ? variants[Math.floor(Math.random() * variants.length)] : recipe.values;
        for (const [name, range] of Object.entries(values)) {
            const info = this.get_param_info(name);
            let value = range;
            if (Array.isArray(range)) {
                value = info.type === 'BUTTONSELECT' ? range[Math.floor(Math.random() * range.length)]
                    : range[0] + Math.random() * (range[1] - range[0]);
            }
            this.set_param(name, value, true);
        }
        this.set_param('seed', Math.random(), true);
        if (this.after_recipe) this.after_recipe(recipe);
    }

    create_random_template() {
        const recipe = this.recipes[Math.floor(Math.random() * this.recipes.length)];
        this.generate_recipe(recipe.id);
        return [recipe.name.replace(/[^a-zA-Z0-9]/g,''), this.params];
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(this.constructor.DSP.render(this.params));
        this.sound_params = JSON.stringify(this.params);
    }

    play() {
        this.generate_sound();
        this.sound.play(this.loop_preview === true);
    }
}
