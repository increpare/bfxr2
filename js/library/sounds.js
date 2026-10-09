// Portable data, existing preset generators and PCM synthesis; no playback or DOM.
const LibrarySounds = {
    engine(name) {
        if (!Object.prototype.hasOwnProperty.call(BFXR_SYNTHS, name)) {
            throw new Error('Unknown synth: ' + name);
        }
        return new BFXR_SYNTHS[name]();
    },

    seed(value) {
        if (value === undefined) return global.Math.random();
        if (typeof value !== 'string' && (typeof value !== 'number' || !Number.isFinite(value))) {
            throw new TypeError('A preset seed must be a finite number or string');
        }
        let hash = 2166136261;
        const text = typeof value + ':' + value;
        for (let i = 0; i < text.length; i++) hash = Math.imul(hash ^ text.charCodeAt(i), 16777619);
        return (hash >>> 0) / 4294967296;
    },

    seeded(seed, action) {
        const previous = Math.random;
        Math.random = SoundDSP.rng(seed);
        try { return action(); } finally { Math.random = previous; }
    },

    categories(synth) {
        if (synth.name === 'Footsteppr') return Footsteppr_DSP.terrains.map(id => [id, id]);
        return synth.templates.filter(template => template[2].startsWith('generate_'))
            .map(template => [template[2].replace(/^generate_(?:family_)?/, ''), template[2]]);
    },

    preset(name, id, seed) {
        const synth = this.engine(name);
        const category = this.categories(synth).find(entry => entry[0] === id);
        if (!category) throw new Error('Unknown preset for ' + name + ': ' + id);
        const renderSeed = this.seed(seed);
        this.seeded(renderSeed, () => {
            if (name === 'Footsteppr') {
                synth.randomize_params();
                synth.set_param('terrain', Footsteppr_DSP.terrains.indexOf(id));
            } else synth[category[1]]();
        });
        return {synth_type: name, version: synth.version, params: JSON.parse(JSON.stringify(synth.params)), renderSeed};
    },

    normalize(input) {
        if (typeof input === 'string') {
            try { input = JSON.parse(input); } catch { throw new TypeError('Invalid sound JSON'); }
        }
        if (!input || typeof input !== 'object' || !input.params ||
            typeof input.params !== 'object' || Array.isArray(input.params)) {
            throw new TypeError('A sound needs synth_type and a params object');
        }
        const synth = this.engine(input.synth_type);
        const renderSeed = input.renderSeed === undefined ? 0.5 : input.renderSeed;
        if (!Number.isFinite(renderSeed) || renderSeed < 0 || renderSeed > 1) {
            throw new TypeError('renderSeed must be a number between 0 and 1');
        }
        const params = Mixr.sanitize_source(synth, JSON.parse(JSON.stringify(input.params)));
        return {synth_type: synth.name, version: synth.version, params, renderSeed};
    },

    render(sound) {
        const synth = this.engine(sound.synth_type);
        synth.apply_params(sound.params);
        return this.seeded(sound.renderSeed, () => synth.render());
    },

    mutate(sound, amount, seed) {
        if (amount === 0) return sound;
        return this.seeded(seed, () => {
            const synth = this.engine(sound.synth_type);
            synth.apply_params(sound.params);
            // Melody control setters normally regenerate notes; preserve the saved score here.
            const batching = synth.batching;
            if ('batching' in synth) synth.batching = true;
            for (const row of synth.param_info) {
                const info = synth.get_param_normalized(row);
                if (['masterVolume', 'seed', 'instrumentSeed'].includes(info.name) ||
                    !['RANGE', 'KNOB_TRANSITION'].includes(info.type) || Math.random() < .5) continue;
                const offset = () => (Math.random() * 2 - 1) * amount * (info.max_value - info.min_value);
                const value = synth.params[info.name];
                synth.set_param(info.name, info.type === 'KNOB_TRANSITION'
                    ? {...value, start: value.start + offset(), end: value.end + offset()}
                    : value + offset());
            }
            if ('batching' in synth) synth.batching = batching;
            if (synth.name === 'Mixr') {
                synth.set_param('sources', synth.get_sources().map(source => source && ({...source,
                    params: this.mutate({synth_type: source.synth, params: source.params,
                        renderSeed: source.renderSeed ?? sound.renderSeed}, amount, Math.random()).params})));
            }
            return {...sound, params: JSON.parse(JSON.stringify(synth.params))};
        });
    }
};
