class Transfxr extends SynthBase {
    name = 'Transfxr';
    version = '1.0.0';
    tooltip = 'Move between two sound states: set the start, the destination and the journey.';
    canvas_bg_logo = 'img/logo_transfxr.png';
    header_properties = ['waveType'];
    permalocked = ['masterVolume'];
    hide_params = ['masterVolume'];
    static tweenfunctions = Transfxr_DSP.curves;
    static preset_families = typeof TRANSFXR_PRESET_FAMILIES === 'undefined' ? [] : TRANSFXR_PRESET_FAMILIES;

    static transitionParam(name, display_name, tooltip, start, end, curve = 'Linear') {
        return {type:'KNOB_TRANSITION', name, display_name, tooltip,
            default_value_l:start, default_value_r:end, min:0, max:1,
            default_tween:curve, curves: this.tweenfunctions.map(c => c[0])};
    }

    param_info = [
        ['Sound Volume', 'Overall volume of the current sound.', 'masterVolume', 0.5, 0, 1],
        {type:'BUTTONSELECT', name:'waveType', display_name:'Voice', tooltip:'The oscillator beneath the changing sound.',
            default_value:0, columns:4, header:true,
            values:BfxrWaveforms.choices.map(([label,tip,id])=>[label,tip,
                ({2:0,4:1,1:2,0:3,8:4,6:5,7:6,3:7,11:8,9:9,5:10,10:11})[id]])},
        ['Duration', 'Time to travel along the curves, in seconds. Echo can ring out afterwards.', 'duration', 0.65, 0.05, 4],
        Transfxr.transitionParam('pitch', 'Pitch', 'Start and destination pitch, from 40 Hz to 5120 Hz. Equal spacing is equal musical intervals.', 0.48, 0.25, 'Ease Out'),
        Transfxr.transitionParam('tone', 'Filter', 'Low-pass cutoff: dark and muffled to bright and open.', 0.9, 0.45),
        Transfxr.transitionParam('noise', 'Noise', 'Blend a pitched voice into airy noise.', 0, 0),
        Transfxr.transitionParam('vibrato', 'Wobble', 'Depth of an eight-cycle-per-second pitch wobble.', 0, 0.15, 'Ease In'),
        Transfxr.transitionParam('level', 'Level', 'Volume along the journey, before the attack and release fades.', 0.85, 0.45),
        ['Attack', 'Fade-in time in seconds, within the duration.', 'attack', 0.008, 0, 1],
        ['Release', 'Fade-out time in seconds, within the duration.', 'release', 0.18, 0, 1],
        ['Resonance', 'Emphasize the moving filter frequency.', 'resonance', 0.15, 0, 1],
        ['Echo', 'Repeating, fading reflections after the voice.', 'echo', 0.15, 0, 0.8]
    ];

    // Original exact recipes remain available for saved examples and rendering tools.
    static examples = [
        {name:'Laser Zip', id:'laser_zip', tip:'A bright little bolt with a falling tail.',
            params:{waveType:2,duration:0.22,attack:0,release:0.14,resonance:0.32,echo:0.14,
                pitch:[0.82,0.22,'Ease Out'],tone:[0.95,0.25],level:[0.9,0.25]}},
        {name:'Bubble Drop', id:'bubble_drop', tip:'A plump, bouncing water droplet.',
            params:{duration:0.38,attack:0.003,release:0.26,echo:0.18,
                pitch:[0.29,0.68,'Bounce'],tone:[0.9,0.65],level:[0.95,0.1]}},
        {name:'Portal Bloom', id:'portal_bloom', tip:'A slow shimmering opening into somewhere else.',
            params:{waveType:2,duration:1.9,attack:0.5,release:0.65,resonance:0.55,echo:0.62,
                pitch:[0.18,0.5,'Smooth'],tone:[0.1,0.85,'Pulse'],noise:[0.08,0.32,'Pulse'],
                vibrato:[0.03,0.65,'Ease In'],level:[0.45,0.95,'Pulse']}},
        {name:'Power Up', id:'power_up', tip:'Five rising steps, ready for the next level.',
            params:{waveType:3,duration:0.72,attack:0.01,release:0.16,resonance:0.12,echo:0.38,
                pitch:[0.35,0.64,'Steps'],tone:[0.55,0.95,'Ease In'],level:[0.7,0.9]}},
        {name:'Soft Landing', id:'soft_landing', tip:'A low, cushioned thump dissolving into dust.',
            params:{waveType:1,duration:0.58,attack:0.004,release:0.5,resonance:0.2,echo:0,
                pitch:[0.25,0.02,'Ease Out'],tone:[0.6,0.08,'Ease Out'],noise:[0.3,0.6],level:[1,0]}},
        {name:'Clockwork Bird', id:'clockwork_bird', tip:'A tiny brass bird trying out its voice.',
            params:{waveType:1,duration:0.44,attack:0.012,release:0.12,resonance:0.3,echo:0.32,
                pitch:[0.62,0.85,'Triangle'],tone:[0.7,1],vibrato:[0.05,0.8,'Ease In'],level:[0.8,0.55]}},
        {name:'Ghost Signal', id:'ghost_signal', tip:'A distant transmission losing its shape.',
            params:{duration:1.45,attack:0.22,release:0.55,resonance:0.65,echo:0.65,
                pitch:[0.62,0.35,'Smooth'],tone:[0.75,0.3],noise:[0,0.4,'Ease In'],
                vibrato:[0.9,0.05,'Ease Out'],level:[0.75,0.12]}},
        {name:'Airlock', id:'airlock', tip:'A resonant rush of air settling into silence.',
            params:{waveType:2,duration:1.15,attack:0.12,release:0.5,resonance:0.75,echo:0.12,
                pitch:[0.1,0.04],tone:[0.12,0.85,'Triangle'],noise:[0.95,1],level:[0.7,0.95,'Pulse']}}
    ];

    templates = [
        ...(Transfxr.preset_families.length ? Transfxr.preset_families.map(p =>
            [p.name,p.tip,'generate_family_'+p.id,p.name.replace(/ /g,'')]) :
            Transfxr.examples.map(p => [p.name,p.tip,'generate_'+p.id,p.name.replace(/ /g,'')])),
        ['Randomize','Find a new journey; locked controls stay put.','randomize_params','Random'],
        ['Mutate','Nudge both endpoints of unlocked controls.','mutate_params','Mutant']
    ];

    constructor() {
        super();
        this.post_initialize();
        for (const example of Transfxr.examples) this['generate_'+example.id] = () => this.generate_example(example.id);
        for (const family of Transfxr.preset_families) this['generate_family_'+family.id] = () => this.generate_family(family.id);
    }

    apply_params(params, check_locked = false) {
        // File/link input is data, not a guarantee of finite, in-range controls.
        for (const info of this.param_info) {
            const name = this.get_param_normalized(info).name;
            if (Object.prototype.hasOwnProperty.call(params, name)) this.set_param(name, params[name], check_locked);
        }
    }

    generate_example(id, vary = true) {
        const example = Transfxr.examples.find(p => p.id === id);
        this.reset_params(true);
        const shift = vary ? (Math.random() - 0.5) * 0.045 : 0;
        for (const [key, value] of Object.entries(example.params)) {
            if (Array.isArray(value)) {
                this.set_param(key, {start:value[0] + (key==='pitch'?shift:0),
                    end:value[1] + (key==='pitch'?shift:0),curve:value[2] || 'Linear'}, true);
            } else this.set_param(key, value, true);
        }
    }

    generate_family(id) {
        const family = Transfxr.preset_families.find(p => p.id === id);
        if (!family) throw new Error('Unknown Transfxr family: '+id);
        this.reset_params(true);
        this.apply_params(PresetFamily.sample(family), true);
    }

    create_random_template() {
        if (Transfxr.preset_families.length) {
            const family = Transfxr.preset_families[Math.floor(Math.random() * Transfxr.preset_families.length)];
            this.generate_family(family.id);
            return [family.name.replace(/ /g,''),this.params];
        }
        const example = Transfxr.examples[Math.floor(Math.random() * Transfxr.examples.length)];
        this.generate_example(example.id);
        return [example.name.replace(/ /g,''),this.params];
    }

    randomize_params() {
        super.randomize_params();
        this.set_param('duration', 0.15 + Math.random() * 1.65, true);
        this.set_param('attack', Math.random() * this.params.duration * 0.25, true);
        this.set_param('release', Math.random() * this.params.duration * 0.6, true);
        this.set_param('level', {start:0.4 + Math.random()*0.6,end:0.15 + Math.random()*0.75,curve:'Linear'}, true);
    }

    format_transition_value(name, value) {
        if (name === 'pitch') return Math.round(Transfxr_DSP.frequency(value)) + ' Hz';
        if (name === 'tone') {
            const hz = Transfxr_DSP.cutoff(value);
            return hz < 1000 ? Math.round(hz) + ' Hz' : (hz/1000).toFixed(1) + ' kHz';
        }
        return Math.round(value * 100) + '%';
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(Transfxr_DSP.render(this.params));
        this.sound_params = JSON.stringify(this.params);
    }
}
