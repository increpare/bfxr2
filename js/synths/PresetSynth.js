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
        this.templates = this.recipes.map(recipe => {
            const method = 'generate_' + recipe.id;
            this[method] = () => this.generate_recipe(recipe.id);
            return [recipe.name, recipe.tip || 'Generate another ' + recipe.name.toLowerCase() + '.', method, recipe.name.replace(/[^a-zA-Z0-9]/g, '')];
        });
        this.templates.push(['Randomize','Explore all unlocked controls.','randomize_params','Random'],
            ['Mutate','Nudge the unlocked controls of this sound.','mutate_params','Mutant']);
    }

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
        for (const [name, range] of Object.entries(recipe.values)) {
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

    render() {
        return this.constructor.DSP.render(this.params);
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(this.render());
        this.sound_params = JSON.stringify(this.params);
    }

    play() {
        this.generate_sound();
        this.sound.play(this.loop_preview === true);
    }
}
