class Stackr extends PresetSynth {
    name = 'Stackr';
    tooltip = 'Little events made from layers of your other sounds.';
    static DSP = Stackr_DSP;
    hide_params = ['masterVolume', 'layers'];
    param_info = [
        ...PresetSynth.common_params,
        ['Spacing', 'Stretch or compress the pauses between layers.', 'spacing', 1, 0.5, 1.5],
        {type:'TEXT', name:'layers', default_value:'[]', max_length:60000}
    ];
    recipes = [
        {id:'spell_launch',name:'Spell Launch',tip:'A gathering glow, a bolt, and a small impact.',values:{spacing:[0.8,1.2]},layers:[['Transfxr','portal_bloom',0,0.45],['Transfxr','laser_zip',0.7,0.9],['Clonkr','glass_ping',0.95,0.7]]},
        {id:'door_unlock',name:'Door Unlock',tip:'A lock clicks, a mechanism turns, the door settles.',values:{spacing:[0.85,1.2]},layers:[['Clonkr','loose_bolts',0,0.65],['Machinr','heavy_door',0.22,0.8],['Clonkr','wood_knock',1.3,0.9]]},
        {id:'treasure',name:'Treasure',tip:'A latch, a scattering of coins, a discovery.',values:{spacing:[0.8,1.3]},layers:[['Machinr','camera_shutter',0,0.7],['Clonkr','coin_drop',0.18,0.65],['Jinglr','discovery',0.35,0.8]]},
        {id:'slime_jump',name:'Slime Jump',tip:'Suction, a rubbery leap, and an undignified landing.',values:{spacing:[0.7,1.25]},layers:[['Squishr','suction_cup',0,0.75],['Transfxr','bubble_drop',0.2,0.65],['Squishr','wet_splat',0.7,0.9]]},
        {id:'robot_boot',name:'Robot Boot',tip:'A servo wakes up and reports success.',values:{spacing:[0.8,1.2]},layers:[['Machinr','servo',0,0.8],['Machinr','tiny_motor',0.3,0.5],['Transfxr','power_up',0.75,0.8]]},
        {id:'glass_spell',name:'Glass Spell',tip:'A bright crack with a magical answering chime.',values:{spacing:[0.8,1.15]},layers:[['Clonkr','ceramic_crack',0,0.9],['Clonkr','glass_ping',0.12,0.7],['Transfxr','clockwork_bird',0.25,0.7]]},
        {id:'storm_portal',name:'Storm Portal',tip:'Wind passes through a shimmering doorway.',values:{spacing:[0.7,1.3]},layers:[['Weathr','wind',0,0.35],['Transfxr','portal_bloom',0.2,0.8],['Clonkr','metal_clang',1,0.45]]},
        {id:'cartoon_crash',name:'Cartoon Crash',tip:'A spring, a thud, and loose pieces rolling away.',values:{spacing:[0.8,1.3]},layers:[['Squishr','springy_goo',0,0.8],['Clonkr','rubber_thud',0.28,0.9],['Clonkr','loose_bolts',0.5,0.7]]}
    ];
    constructor() { super(); this.initialize_presets(); }
    create_random_template() { this.set_param('layers',[]); return ['Stack',this.params]; }
    create_editor(tab, parent) { return new StackEditor(tab, parent); }

    static sources() {
        return [typeof Bfxr === 'undefined' ? null : Bfxr,
            typeof Footsteppr === 'undefined' ? null : Footsteppr,
            typeof Transfxr === 'undefined' ? null : Transfxr,
            typeof Chattr === 'undefined' ? null : Chattr,
            typeof Clonkr === 'undefined' ? null : Clonkr,
            typeof Machinr === 'undefined' ? null : Machinr,
            typeof Weathr === 'undefined' ? null : Weathr,
            typeof Jinglr === 'undefined' ? null : Jinglr,
            typeof Squishr === 'undefined' ? null : Squishr,
            typeof Crittr === 'undefined' ? null : Crittr,
            typeof Signlr === 'undefined' ? null : Signlr,
            typeof Fractr === 'undefined' ? null : Fractr,
            typeof Riftr === 'undefined' ? null : Riftr,
            typeof Swarmr === 'undefined' ? null : Swarmr,
            typeof Tappr === 'undefined' ? null : Tappr,
            typeof Rustlr === 'undefined' ? null : Rustlr,
            typeof Notifr === 'undefined' ? null : Notifr,
            typeof Tickr === 'undefined' ? null : Tickr,
            typeof Holor === 'undefined' ? null : Holor,
            typeof Boomr === 'undefined' ? null : Boomr,
            typeof Pewpr === 'undefined' ? null : Pewpr,
            typeof Zappr === 'undefined' ? null : Zappr,
            typeof Whooshr === 'undefined' ? null : Whooshr,
            typeof Bouncr === 'undefined' ? null : Bouncr,
            typeof Rollr === 'undefined' ? null : Rollr,
            typeof Breathr === 'undefined' ? null : Breathr,
            typeof Choirr === 'undefined' ? null : Choirr,
            typeof Pluckr === 'undefined' ? null : Pluckr,
            typeof Glitchr === 'undefined' ? null : Glitchr,
            typeof Pulser === 'undefined' ? null : Pulser,
            typeof Rumblr === 'undefined' ? null : Rumblr].filter(Boolean);
    }
    static source(name) { const Constructor = this.sources().find(c => c.name === name); return Constructor ? new Constructor() : null; }

    static sanitize_source(synth, params) {
        // Older synths' apply_params accepts arbitrary keys; validate each known control here.
        // Apply editable scores last: generator controls can otherwise replace saved notes.
        const controls = synth.param_info.map(info => synth.get_param_normalized(info));
        controls.sort((a,b) => Number(a.type === 'TEXT') - Number(b.type === 'TEXT'));
        for (const info of controls) {
            const name = info.name;
            if (params && Object.prototype.hasOwnProperty.call(params, name)) synth.set_param(name, params[name]);
        }
        return JSON.parse(JSON.stringify(synth.params));
    }

    set_param(name, value, check_locked = false) {
        if (name !== 'layers') return super.set_param(name, value, check_locked);
        if (check_locked && this.locked_param(name)) return;
        let layers;
        try { layers = typeof value === 'string' ? JSON.parse(value.slice(0,60000)) : value; } catch { layers = []; }
        const number = (v, fallback, min, max) => Number.isFinite(v) ? SoundDSP.clamp(v,min,max) : fallback;
        const valid = [];
        for (const layer of (Array.isArray(layers) ? layers : []).slice(0,6)) {
            if (!layer || typeof layer !== 'object') continue;
            const synth = Stackr.source(layer.synth);
            if (!synth) continue;
            valid.push({synth:synth.name,name:typeof layer.name === 'string' ? layer.name.slice(0,40) : synth.name,
                params:Stackr.sanitize_source(synth,layer.params),start:number(layer.start,0,0,4),
                gain:number(layer.gain,0.8,0,1),pitch:number(layer.pitch,0,-12,12)});
        }
        this.params.layers = JSON.stringify(valid);
        this.sound_params = null;
    }
    get_layers() { return JSON.parse(this.params.layers); }

    add_source(synth, name) {
        if (synth.name === 'Stackr') return false;
        const layers = this.get_layers();
        if (layers.length >= 6) return false;
        layers.push({synth:synth.name,name:name || synth.name,params:synth.params,start:0,gain:0.8,pitch:0});
        this.set_param('layers',layers);
        return true;
    }

    generate_recipe(id) {
        const recipe = this.recipes.find(entry => entry.id === id);
        if (!recipe) return;
        const locked = this.locked_param('layers');
        super.generate_recipe(id);
        if (locked) return;
        const layers = recipe.layers.map(([name, category, start, gain]) => {
            let synth = Stackr.source(name);
            if (!synth) synth = Stackr.source('Transfxr');
            if (!synth) return null;
            if (synth['generate_' + category]) synth['generate_' + category]();
            else synth.create_random_template();
            // Ambience supplies a bed for a short effect rather than a full long loop.
            if (synth.name === 'Weathr') synth.set_param('duration', 3);
            return {synth:synth.name,name:category.replace(/_/g,' '),params:synth.params,
                start:Math.max(0,start * (0.9 + Math.random() * 0.2)),
                gain:gain * (0.85 + Math.random() * 0.15),pitch:(Math.random() - 0.5) * 2};
        }).filter(Boolean);
        this.set_param('layers',layers,true);
    }
    randomize_params() { this.generate_recipe(this.recipes[Math.floor(Math.random() * this.recipes.length)].id); }
    mutate_params() {
        super.mutate_params();
        if (this.locked_param('layers')) return;
        const layers = this.get_layers().map(layer => ({...layer,
            start:layer.start + (Math.random() - 0.5) * 0.08,
            gain:layer.gain + (Math.random() - 0.5) * 0.08,
            pitch:layer.pitch + (Math.random() - 0.5) * 0.7}));
        this.set_param('layers',layers,true);
    }

    static render_source(layer, seed = 0.5) {
        const synth = this.source(layer.synth);
        if (!synth) return new Float32Array(1);
        this.sanitize_source(synth,layer.params);
        const originalRandom = Math.random;
        Math.random = SoundDSP.rng(seed);
        try {
            synth.generate_sound();
            return synth.sound.getBuffer();
        } finally { Math.random = originalRandom; }
    }
    generate_sound() {
        if (this.sound) this.sound.stop();
        this.layer_durations = [];
        const pcm = Stackr_DSP.render(this.params, layer => Stackr.render_source(layer,this.params.seed),
            (layer,duration) => this.layer_durations.push(duration));
        this.sound = RealizedSound.from_buffer(pcm);
        this.sound_params = JSON.stringify(this.params);
    }
}
