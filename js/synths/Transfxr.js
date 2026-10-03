class Transfxr extends SynthBase {
    name = 'Transfxr';
    version = '1.0.0';
    tooltip = 'Move between two sound states: set the start, the destination and the journey.';
    canvas_bg_logo = 'img/logo_transfxr.png';
    header_properties = ['waveType'];
    permalocked = ['masterVolume'];
    hide_params = ['masterVolume','waveTo'];
    static tweenfunctions = Transfxr_DSP.curves;
    static preset_families = typeof TRANSFXR_PRESET_FAMILIES === 'undefined' ? [] : TRANSFXR_PRESET_FAMILIES;

    static transitionParam(name, display_name, tooltip, start, end, curve = 'Linear') {
        return {type:'KNOB_TRANSITION', name, display_name, tooltip,
            default_value_l:start, default_value_r:end, min:0, max:1,
            default_tween:curve, curves: this.tweenfunctions.map(c => c[0])};
    }

    param_info = [
        ['Sound Volume', 'Overall volume of the current sound.', 'masterVolume', 0.5, 0, 1],
        {type:'BUTTONSELECT', name:'waveType', display_name:'', tooltip:'The oscillator beneath the changing sound.',
            default_value:0, columns:4, header:true,
            values:BfxrWaveforms.choices.map(([label,tip,id])=>[label,tip,
                ({2:0,4:1,1:2,0:3,8:4,6:5,7:6,3:7,11:8,9:9,5:10,10:11})[id]])},
        ['Duration', 'Time to travel along the curves, in seconds. Echo can ring out afterwards.', 'duration', 0.65, 0.05, 4],
        Transfxr.transitionParam('pitch', 'Pitch', 'Start and destination pitch, from 40 Hz to 5120 Hz. Equal spacing is equal musical intervals.', 0.48, 0.25, 'Ease Out'),
        Transfxr.transitionParam('tone', 'Filter', 'Low-pass cutoff: dark and muffled to bright and open.', 0.9, 0.45),
        Transfxr.transitionParam('vibrato', 'Wobble', 'Depth of an eight-cycle-per-second pitch wobble.', 0, 0.15, 'Ease In'),
        Transfxr.transitionParam('level', 'Level', 'Volume along the journey, before the attack and release fades.', 0.85, 0.45),
        ['Attack', 'Fade-in time in seconds, within the duration.', 'attack', 0.008, 0, 1],
        ['Release', 'Fade-out time in seconds, within the duration.', 'release', 0.18, 0, 1],
        ['Resonance', 'Emphasize the moving filter frequency.', 'resonance', 0.15, 0, 1],
        ['Echo', 'Repeating, fading reflections after the voice.', 'echo', 0.15, 0, 0.8],
        {type:'BUTTONSELECT',name:'waveTo',display_name:'Morph to',default_value:-1,columns:4,
            values:[["Don't morph waveform",'Keep the starting waveform.',-1],...BfxrWaveforms.choices.map(([label,tip,id])=>[label,tip,({2:0,4:1,1:2,0:3,8:4,6:5,7:6,3:7,11:8,9:9,5:10,10:11})[id]])]},
        Transfxr.transitionParam('morph','Morph','Blend from the starting waveform into the chosen destination.',0,1,'Smooth')
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
                pitch:[0.18,0.5,'Smooth'],tone:[0.1,0.85,'Pulse'],waveTo:7,morph:[0.08,0.32,'Pulse'],
                vibrato:[0.03,0.65,'Ease In'],level:[0.45,0.95,'Pulse']}},
        {name:'Power Up', id:'power_up', tip:'Five rising steps, ready for the next level.',
            params:{waveType:3,duration:0.72,attack:0.01,release:0.16,resonance:0.12,echo:0.38,
                pitch:[0.35,0.64,'Steps'],tone:[0.55,0.95,'Ease In'],level:[0.7,0.9]}},
        {name:'Soft Landing', id:'soft_landing', tip:'A low, cushioned thump dissolving into dust.',
            params:{waveType:1,duration:0.58,attack:0.004,release:0.5,resonance:0.2,echo:0,
                pitch:[0.25,0.02,'Ease Out'],tone:[0.6,0.08,'Ease Out'],waveTo:7,morph:[0.3,0.6],level:[1,0]}},
        {name:'Clockwork Bird', id:'clockwork_bird', tip:'A tiny brass bird trying out its voice.',
            params:{waveType:1,duration:0.44,attack:0.012,release:0.12,resonance:0.3,echo:0.32,
                pitch:[0.62,0.85,'Triangle'],tone:[0.7,1],vibrato:[0.05,0.8,'Ease In'],level:[0.8,0.55]}},
        {name:'Ghost Signal', id:'ghost_signal', tip:'A distant transmission losing its shape.',
            params:{duration:1.45,attack:0.22,release:0.55,resonance:0.65,echo:0.65,
                pitch:[0.62,0.35,'Smooth'],tone:[0.75,0.3],waveTo:7,morph:[0,0.4,'Ease In'],
                vibrato:[0.9,0.05,'Ease Out'],level:[0.75,0.12]}},
        {name:'Airlock', id:'airlock', tip:'A resonant rush of air settling into silence.',
            params:{waveType:2,duration:1.15,attack:0.12,release:0.5,resonance:0.75,echo:0.12,
                pitch:[0.1,0.04],tone:[0.12,0.85,'Triangle'],waveTo:7,morph:[0.95,1],level:[0.7,0.95,'Pulse']}}
    ];

    // Game-verb presets recreated from the reference catalogue (docs/research/retro-sound-references.md).
    // Each verb holds several archetypes; a press draws one and shifts its pitch a little.
    // Waveforms: 0 sin, 1 triangle, 2 saw, 3 square, 7 white noise, 9 bitnoise, 11 FM.
    static verbRecipes = {
        jump: [
            {id:'jump_sweep', params:{waveType:3,duration:0.2,attack:0,release:0.07,echo:0,pitch:[0.42,0.68,'Ease Out'],tone:[0.95,0.9],level:[1,0.55]}},
            {id:'jump_boing', params:{waveType:3,duration:0.3,attack:0,release:0.1,echo:0,pitch:[0.36,0.56,'Triangle'],tone:[0.9,0.8],level:[1,0.5]}},
            {id:'jump_hop', params:{waveType:3,duration:0.18,attack:0,release:0.04,echo:0,pitch:[0.46,0.6,'Steps'],tone:[0.9,0.9],level:[0.9,0.8]}},
            {id:'jump_puff', params:{waveType:7,duration:0.16,attack:0.005,release:0.1,echo:0,pitch:[0.5,0.5],tone:[0.65,0.3,'Ease Out'],level:[1,0.15],resonance:0.1}},
            {id:'jump_flutter', params:{waveType:3,duration:0.36,attack:0,release:0.08,echo:0,pitch:[0.5,0.62],vibrato:[0.9,0.9],tone:[0.9,0.9],level:[0.9,0.6]}},
            {id:'jump_chirp', params:{waveType:3,duration:0.13,attack:0,release:0.05,echo:0,pitch:[0.6,0.73,'Ease Out'],vibrato:[0,0.6,'Ease In'],tone:[1,0.95],level:[1,0.6]}}],
        land: [
            {id:'land_tick', params:{waveType:7,duration:0.06,attack:0,release:0.04,echo:0,pitch:[0.5,0.5],tone:[0.8,0.4,'Ease Out'],level:[1,0]}},
            {id:'land_thud', params:{waveType:1,duration:0.14,attack:0,release:0.1,echo:0,pitch:[0.27,0.1,'Ease Out'],tone:[0.7,0.3],waveTo:7,morph:[0.35,0.3],level:[1,0]}},
            {id:'land_heavy', params:{waveType:0,duration:0.45,attack:0.002,release:0.35,echo:0.05,pitch:[0.2,0.04,'Ease Out'],tone:[0.5,0.15,'Ease Out'],waveTo:7,morph:[0.25,0.6],level:[1,0]}},
            {id:'land_clank', params:{waveType:11,duration:0.16,attack:0,release:0.1,echo:0,pitch:[0.62,0.45,'Steps'],tone:[1,0.7],level:[1,0.1],resonance:0.3}}],
        dash: [
            {id:'dash_whoosh', params:{waveType:7,duration:0.38,attack:0.05,release:0.18,echo:0,pitch:[0.5,0.5],tone:[0.3,0.85,'Triangle'],level:[0.5,1,'Triangle'],resonance:0.45}},
            {id:'dash_zip', params:{waveType:2,duration:0.26,attack:0.01,release:0.1,echo:0,pitch:[0.42,0.76,'Ease In'],tone:[0.7,1],waveTo:7,morph:[0.15,0.7,'Ease In'],level:[0.9,0.5]}},
            {id:'dash_rev', params:{waveType:3,duration:0.5,attack:0.02,release:0.12,echo:0,pitch:[0.3,0.56],vibrato:[0.8,0.8],tone:[0.6,0.95],level:[0.5,1]}},
            {id:'dash_skid', params:{waveType:7,duration:0.4,attack:0.01,release:0.2,echo:0,pitch:[0.5,0.5],tone:[0.9,0.35,'Ease Out'],level:[1,0.15],resonance:0.75}},
            {id:'dash_boost', params:{waveType:2,duration:0.7,attack:0.08,release:0.25,echo:0.2,pitch:[0.32,0.7,'Ease In'],tone:[0.4,0.95,'Ease In'],level:[0.5,1]}}],
        splash: [
            {id:'splash_glug', params:{waveType:3,duration:0.4,attack:0.01,release:0.15,echo:0,pitch:[0.46,0.24,'Ease Out'],vibrato:[0.6,0.6],tone:[0.6,0.4],waveTo:7,morph:[0,0.5],level:[0.9,0.4]}},
            {id:'splash_bubble', params:{waveType:0,duration:0.16,attack:0.003,release:0.08,echo:0.1,pitch:[0.45,0.72,'Ease In'],tone:[0.9,0.9],level:[1,0.3]}},
            {id:'splash_burst', params:{waveType:7,duration:0.32,attack:0.003,release:0.2,echo:0,pitch:[0.5,0.5],tone:[0.9,0.2,'Ease Out'],level:[1,0.1],resonance:0.3}}],
        shoot: [
            {id:'shoot_pew', params:{waveType:3,duration:0.13,attack:0,release:0.05,echo:0,pitch:[0.76,0.36,'Ease Out'],tone:[1,0.8],level:[1,0.3]}},
            {id:'shoot_pip', params:{waveType:3,duration:0.06,attack:0,release:0.03,echo:0,pitch:[0.66,0.56],tone:[1,1],level:[1,0.5]}},
            {id:'shoot_chirp', params:{waveType:3,duration:0.15,attack:0,release:0.05,echo:0,pitch:[0.55,0.76,'Triangle'],tone:[1,0.9],level:[1,0.4]}},
            {id:'shoot_crack', params:{waveType:7,duration:0.2,attack:0,release:0.15,echo:0.05,pitch:[0.5,0.5],tone:[1,0.3,'Ease Out'],level:[1,0],resonance:0.2}},
            {id:'shoot_laser', params:{waveType:3,duration:0.3,attack:0.005,release:0.08,echo:0,pitch:[0.8,0.77],vibrato:[0.45,0.45],tone:[1,0.9],level:[1,0.4]}},
            {id:'shoot_pistol', params:{waveType:7,duration:0.35,attack:0,release:0.28,echo:0.08,pitch:[0.5,0.5],tone:[0.9,0.1,'Ease Out'],waveTo:0,morph:[0.2,0.6,'Ease In'],level:[1,0],resonance:0.25}},
            {id:'shoot_charge', params:{waveType:2,duration:0.4,attack:0.03,release:0.08,echo:0.05,pitch:[0.35,0.72,'Ease In'],tone:[0.5,1],waveTo:7,morph:[0,0.5,'Ease In'],level:[0.4,1,'Ease In']}}],
        swing: [
            {id:'swing_whoosh', params:{waveType:7,duration:0.3,attack:0.03,release:0.14,echo:0,pitch:[0.5,0.5],tone:[0.25,0.8,'Triangle'],level:[0.4,1,'Triangle'],resonance:0.5}},
            {id:'swing_crack', params:{waveType:7,duration:0.09,attack:0,release:0.06,echo:0.05,pitch:[0.5,0.5],tone:[1,0.5,'Ease Out'],level:[1,0]}},
            {id:'swing_shing', params:{waveType:2,duration:0.16,attack:0,release:0.08,echo:0.1,pitch:[0.76,0.56,'Ease Out'],vibrato:[0,0.5,'Ease In'],tone:[1,0.6],level:[1,0.3]}},
            {id:'swing_whir', params:{waveType:3,duration:0.4,attack:0.02,release:0.12,echo:0,pitch:[0.5,0.7,'Triangle'],vibrato:[0.5,0.5],waveTo:7,morph:[0.3,0.3],tone:[0.8,0.8],level:[0.8,0.6]}},
            {id:'swing_hum', params:{waveType:2,duration:0.32,attack:0.02,release:0.1,echo:0.05,pitch:[0.4,0.43],vibrato:[0.3,0.3],waveTo:7,morph:[0.1,0.6,'Triangle'],tone:[0.6,0.9,'Triangle'],level:[0.6,1,'Triangle'],resonance:0.5}}],
        hit: [
            {id:'hit_boink', params:{waveType:3,duration:0.15,attack:0,release:0.05,echo:0,pitch:[0.45,0.63,'Triangle'],tone:[0.9,0.9],level:[1,0.5]}},
            {id:'hit_thunk', params:{waveType:3,duration:0.1,attack:0,release:0.05,echo:0,pitch:[0.4,0.24,'Ease Out'],waveTo:7,morph:[0.2,0.6],tone:[0.8,0.4],level:[1,0.2]}},
            {id:'hit_tick', params:{waveType:7,duration:0.045,attack:0,release:0.03,echo:0,pitch:[0.5,0.5],tone:[0.9,0.5],level:[1,0]}},
            {id:'hit_ting', params:{waveType:11,duration:0.3,attack:0,release:0.26,echo:0.1,pitch:[0.8,0.79],tone:[1,0.8],level:[1,0]}},
            {id:'hit_thud', params:{waveType:0,duration:0.2,attack:0,release:0.15,echo:0,pitch:[0.23,0.1,'Ease Out'],waveTo:7,morph:[0.4,0.1],tone:[0.6,0.3],level:[1,0]}},
            {id:'hit_pok', params:{waveType:3,duration:0.05,attack:0,release:0.02,echo:0,pitch:[0.5,0.5],tone:[0.9,0.9],level:[1,0.8]}}],
        hurt: [
            {id:'hurt_warble', params:{waveType:3,duration:0.4,attack:0,release:0.1,echo:0,pitch:[0.56,0.3],vibrato:[0.85,0.85],tone:[0.9,0.7],level:[1,0.4]}},
            {id:'hurt_buzz', params:{waveType:2,duration:0.3,attack:0,release:0.1,echo:0,pitch:[0.5,0.3,'Ease Out'],vibrato:[0.5,0.9],waveTo:7,morph:[0,0.4],tone:[0.9,0.5],level:[1,0.3]}},
            {id:'hurt_twovoice', params:{waveType:3,duration:0.3,attack:0,release:0.08,echo:0.3,pitch:[0.66,0.3,'Ease In'],tone:[1,0.7],level:[1,0.3]}},
            {id:'hurt_stutter', params:{waveType:3,duration:0.36,attack:0,release:0.05,echo:0,pitch:[0.6,0.4,'Steps'],vibrato:[1,1],level:[1,0.6,'Pulse'],tone:[0.9,0.9]}},
            {id:'hurt_grunt', params:{waveType:8,duration:0.6,attack:0.02,release:0.3,echo:0,pitch:[0.36,0.22,'Ease Out'],vibrato:[0.3,0.6],waveTo:10,morph:[0.2,0.6],tone:[0.6,0.3],level:[1,0.2],resonance:0.3}},
            {id:'hurt_zzt', params:{waveType:9,duration:0.2,attack:0,release:0.1,echo:0,pitch:[0.6,0.3],tone:[0.9,0.4],level:[1,0.2]}}],
        explode: [
            {id:'explode_burst', params:{waveType:7,duration:0.4,attack:0,release:0.3,echo:0,pitch:[0.5,0.5],tone:[0.8,0.15,'Ease Out'],level:[1,0],resonance:0.2}},
            {id:'explode_thump', params:{waveType:1,duration:0.6,attack:0,release:0.45,echo:0,pitch:[0.2,0.05,'Ease Out'],waveTo:7,morph:[0.5,0.9],tone:[0.7,0.1,'Ease Out'],level:[1,0]}},
            {id:'explode_warble', params:{waveType:3,duration:0.8,attack:0,release:0.2,echo:0,pitch:[0.4,0.7,'Pulse'],vibrato:[1,1],waveTo:7,morph:[0,0.6,'Ease In'],tone:[0.9,0.5],level:[1,0.3]}},
            {id:'explode_boom', params:{waveType:7,duration:1.6,attack:0.005,release:1.2,echo:0.3,pitch:[0.5,0.5],tone:[0.5,0.05,'Ease Out'],level:[1,0],resonance:0.3}},
            {id:'explode_crack', params:{waveType:7,duration:0.9,attack:0,release:0.7,echo:0.5,pitch:[0.5,0.5],tone:[1,0.1,'Ease Out'],level:[1,0.05],resonance:0.1}},
            {id:'explode_foomp', params:{waveType:7,duration:0.35,attack:0.03,release:0.25,echo:0,pitch:[0.5,0.5],tone:[0.35,0.12,'Ease Out'],level:[1,0],resonance:0.3}}],
        coin: [
            {id:'coin_twonote', params:{waveType:3,duration:0.3,attack:0,release:0.16,echo:0,pitch:[0.735,0.785,'Steps'],tone:[0.95,0.9],level:[0.9,0.3]}},
            {id:'coin_bell', params:{waveType:11,duration:0.3,attack:0,release:0.26,echo:0,pitch:[0.82,0.82],tone:[1,0.9],level:[1,0]}},
            {id:'coin_pip', params:{waveType:3,duration:0.08,attack:0,release:0.04,echo:0,pitch:[0.75,0.78],tone:[1,1],level:[1,0.5]}},
            {id:'coin_arp', params:{waveType:3,duration:0.22,attack:0,release:0.08,echo:0,pitch:[0.6,0.78,'Steps'],tone:[0.95,0.95],level:[0.9,0.5]}},
            {id:'coin_waka', params:{waveType:3,duration:0.18,attack:0,release:0.03,echo:0,pitch:[0.5,0.62,'Triangle'],tone:[0.8,0.8],level:[0.9,0.9]}}],
        powerup: [
            {id:'powerup_ladder', params:{waveType:3,duration:0.65,attack:0,release:0.12,echo:0.1,pitch:[0.42,0.72,'Steps'],tone:[0.8,1],level:[0.8,0.9]}},
            {id:'powerup_slide', params:{waveType:3,duration:0.5,attack:0,release:0.15,echo:0.1,pitch:[0.4,0.75,'Ease In'],tone:[0.8,1],level:[0.9,0.7]}},
            {id:'powerup_swell', params:{waveType:2,duration:1,attack:0.2,release:0.4,echo:0.35,pitch:[0.5,0.64,'Smooth'],vibrato:[0,0.3,'Ease In'],tone:[0.5,1,'Ease In'],level:[0.4,1,'Ease In'],resonance:0.3}},
            {id:'powerup_threenote', params:{waveType:3,duration:0.36,attack:0,release:0.1,echo:0.05,pitch:[0.55,0.7,'Steps'],tone:[0.9,0.95],level:[0.9,0.7]}},
            {id:'powerup_whoom', params:{waveType:0,duration:0.9,attack:0.1,release:0.3,echo:0.2,pitch:[0.2,0.5,'Ease In'],waveTo:2,morph:[0,0.7,'Ease In'],tone:[0.4,0.95,'Ease In'],level:[0.5,1]}}],
        unlock: [
            {id:'unlock_clunk', params:{waveType:3,duration:0.3,attack:0,release:0.1,echo:0.1,pitch:[0.3,0.62,'Steps'],waveTo:7,morph:[0.5,0],tone:[0.7,1],level:[1,0.6]}},
            {id:'unlock_shimmer', params:{waveType:11,duration:0.9,attack:0.02,release:0.5,echo:0.4,pitch:[0.6,0.85,'Ease Out'],vibrato:[0,0.4,'Ease In'],tone:[0.9,1],level:[1,0.3]}},
            {id:'unlock_shutter', params:{waveType:3,duration:0.7,attack:0,release:0.05,echo:0,pitch:[0.55,0.35,'Steps'],level:[1,0.8,'Pulse'],waveTo:7,morph:[0.4,0.4],tone:[0.8,0.6]}},
            {id:'unlock_click', params:{waveType:7,duration:0.2,attack:0,release:0.12,echo:0.05,pitch:[0.5,0.5],tone:[0.9,0.5,'Ease Out'],waveTo:11,morph:[0.3,0.8,'Steps'],level:[1,0.2],resonance:0.4}},
            {id:'unlock_beep', params:{waveType:3,duration:0.3,attack:0,release:0.05,echo:0,pitch:[0.68,0.78,'Steps'],tone:[1,1],level:[0.9,0.9]}}],
        win: [
            {id:'win_sting', params:{waveType:2,duration:1.2,attack:0.01,release:0.7,echo:0.4,pitch:[0.6,0.6],vibrato:[0,0.4,'Ease In'],tone:[1,0.6],level:[1,0.2],resonance:0.2}},
            {id:'win_rise', params:{waveType:3,duration:1.4,attack:0,release:0.6,echo:0.3,pitch:[0.5,0.72,'Steps'],tone:[0.9,1],level:[0.9,0.5]}},
            {id:'win_bell', params:{waveType:11,duration:1.3,attack:0,release:0.9,echo:0.45,pitch:[0.7,0.85,'Steps'],tone:[1,0.9],level:[1,0.1]}}],
        lose: [
            {id:'lose_spiral', params:{waveType:3,duration:1.4,attack:0,release:0.3,echo:0,pitch:[0.65,0.25,'Ease In'],vibrato:[0.8,1],tone:[0.9,0.5],level:[1,0.4]}},
            {id:'lose_sting', params:{waveType:2,duration:0.8,attack:0,release:0.4,echo:0.2,pitch:[0.5,0.38,'Steps'],tone:[0.8,0.4],level:[1,0.3]}},
            {id:'lose_crash', params:{waveType:3,duration:1,attack:0,release:0.6,echo:0.1,pitch:[0.6,0.2,'Ease Out'],waveTo:7,morph:[0,1,'Ease In'],tone:[0.9,0.2],level:[1,0.1]}},
            {id:'lose_slide', params:{waveType:3,duration:0.9,attack:0,release:0.2,echo:0.1,pitch:[0.6,0.28,'Linear'],vibrato:[0.2,0.2],tone:[0.9,0.6],level:[1,0.5]}}],
        break: [
            {id:'break_crunch', params:{waveType:7,duration:0.35,attack:0,release:0.2,echo:0,pitch:[0.5,0.5],tone:[0.9,0.4,'Ease Out'],level:[1,0.3,'Steps'],resonance:0.2}},
            {id:'break_shatter', params:{waveType:11,duration:0.5,attack:0,release:0.4,echo:0.15,pitch:[0.85,0.7,'Ease Out'],waveTo:7,morph:[0.6,0.2],tone:[1,0.7],level:[1,0]}},
            {id:'break_pop', params:{waveType:0,duration:0.09,attack:0,release:0.06,echo:0,pitch:[0.6,0.4,'Ease Out'],waveTo:7,morph:[0.5,0.2],tone:[1,0.6],level:[1,0]}}],
        door: [
            {id:'door_shwip', params:{waveType:3,duration:0.3,attack:0,release:0.1,echo:0,pitch:[0.4,0.66,'Ease Out'],waveTo:7,morph:[0.2,0.6],tone:[0.7,0.9],level:[1,0.4]}},
            {id:'door_hiss_clank', params:{waveType:7,duration:0.6,attack:0.02,release:0.1,echo:0.05,pitch:[0.5,0.5],tone:[0.9,0.3,'Ease Out'],waveTo:1,morph:[0,1,'Steps'],level:[0.8,1,'Steps'],resonance:0.3}},
            {id:'door_motor', params:{waveType:2,duration:1,attack:0.1,release:0.1,echo:0,pitch:[0.2,0.3,'Ease Out'],vibrato:[0.2,0.2],waveTo:7,morph:[0.3,0.8,'Steps'],tone:[0.4,0.6],level:[0.7,1,'Steps'],resonance:0.4}},
            {id:'door_shutter', params:{waveType:3,duration:0.8,attack:0,release:0.05,echo:0,pitch:[0.5,0.3,'Steps'],level:[1,0.8,'Pulse'],waveTo:7,morph:[0.3,0.3],tone:[0.8,0.5]}},
            {id:'door_pipe', params:{waveType:3,duration:0.55,attack:0,release:0.1,echo:0,pitch:[0.55,0.3,'Ease In'],vibrato:[0.5,0.5],tone:[0.9,0.7],level:[1,0.6]}}],
        blip: [
            {id:'blip_tick', params:{waveType:3,duration:0.04,attack:0,release:0.02,echo:0,pitch:[0.7,0.7],tone:[1,1],level:[1,0.7]}},
            {id:'blip_pip', params:{waveType:3,duration:0.07,attack:0,release:0.03,echo:0,pitch:[0.75,0.8],tone:[1,1],level:[1,0.5]}},
            {id:'blip_pok', params:{waveType:3,duration:0.05,attack:0,release:0.03,echo:0,pitch:[0.5,0.5],tone:[0.8,0.8],level:[1,0.6]}},
            {id:'blip_dink', params:{waveType:11,duration:0.12,attack:0,release:0.1,echo:0,pitch:[0.85,0.85],tone:[1,0.9],level:[1,0]}}],
        confirm: [
            {id:'confirm_twonote', params:{waveType:3,duration:0.24,attack:0,release:0.1,echo:0,pitch:[0.62,0.7,'Steps'],tone:[1,0.95],level:[0.9,0.5]}},
            {id:'confirm_ding', params:{waveType:11,duration:0.5,attack:0,release:0.45,echo:0.15,pitch:[0.78,0.78],tone:[1,0.9],level:[1,0]}},
            {id:'confirm_pwip', params:{waveType:3,duration:0.14,attack:0,release:0.05,echo:0,pitch:[0.55,0.78,'Ease Out'],tone:[1,1],level:[1,0.5]}},
            {id:'confirm_octave', params:{waveType:3,duration:0.4,attack:0,release:0.2,echo:0.1,pitch:[0.64,0.78,'Steps'],tone:[0.95,0.95],level:[0.9,0.4]}},
            {id:'confirm_brrp', params:{waveType:9,duration:0.18,attack:0,release:0.05,echo:0,pitch:[0.6,0.7,'Steps'],tone:[0.9,0.9],level:[1,0.7]}}],
        alert: [
            {id:'alert_beep', params:{waveType:3,duration:0.9,attack:0,release:0.02,echo:0,pitch:[0.78,0.78],level:[1,1,'Pulse'],tone:[1,1]}},
            {id:'alert_siren', params:{waveType:2,duration:1.2,attack:0.02,release:0.1,echo:0,pitch:[0.5,0.68,'Triangle'],tone:[0.9,0.9],level:[0.9,0.9],resonance:0.2}},
            {id:'alert_stab', params:{waveType:2,duration:0.3,attack:0,release:0.1,echo:0.2,pitch:[0.6,0.7,'Steps'],tone:[1,0.9],level:[1,0.4]}},
            {id:'alert_buzz', params:{waveType:2,duration:0.3,attack:0,release:0.08,echo:0,pitch:[0.26,0.24],tone:[0.6,0.5],level:[1,0.7],resonance:0.3}},
            {id:'alert_bonk', params:{waveType:3,duration:0.16,attack:0,release:0.06,echo:0,pitch:[0.3,0.26,'Ease Out'],tone:[0.6,0.4],level:[1,0.5]}},
            {id:'alert_countdown', params:{waveType:0,duration:1.2,attack:0,release:0.05,echo:0.1,pitch:[0.32,0.34],level:[1,0.9,'Pulse'],tone:[0.8,0.8]}}],
        cast: [
            {id:'cast_arp', params:{waveType:3,duration:0.7,attack:0,release:0.25,echo:0.25,pitch:[0.5,0.78,'Steps'],vibrato:[0.3,0.6],tone:[0.9,1],level:[0.9,0.5]}},
            {id:'cast_shimmer', params:{waveType:11,duration:1.1,attack:0.05,release:0.6,echo:0.45,pitch:[0.62,0.85,'Ease Out'],vibrato:[0.2,0.5],tone:[0.9,1],level:[0.9,0.2]}},
            {id:'cast_crack', params:{waveType:9,duration:0.5,attack:0,release:0.4,echo:0.3,pitch:[0.7,0.4,'Ease Out'],tone:[1,0.4,'Ease Out'],level:[1,0]}},
            {id:'cast_swirl', params:{waveType:2,duration:1,attack:0.15,release:0.4,echo:0.3,pitch:[0.4,0.66,'Pulse'],vibrato:[0.6,0.6],waveTo:7,morph:[0.3,0.7,'Pulse'],tone:[0.5,0.95,'Pulse'],level:[0.6,0.9],resonance:0.6}}],
        warp: [
            {id:'warp_bwip', params:{waveType:3,duration:0.3,attack:0,release:0.08,echo:0.1,pitch:[0.3,0.8,'Ease In'],tone:[0.9,1],level:[1,0.5]}},
            {id:'warp_spiral', params:{waveType:3,duration:1,attack:0.02,release:0.3,echo:0.3,pitch:[0.35,0.8,'Ease In'],vibrato:[0.5,1],tone:[0.8,1],level:[0.9,0.5]}},
            {id:'warp_shimmer', params:{waveType:2,duration:1.3,attack:0.3,release:0.5,echo:0.45,pitch:[0.45,0.7,'Smooth'],vibrato:[0.1,0.5],tone:[0.2,1,'Ease In'],level:[0.4,1],resonance:0.7}},
            {id:'warp_whoomp', params:{waveType:0,duration:0.9,attack:0.4,release:0.3,echo:0.2,pitch:[0.3,0.12,'Ease In'],waveTo:7,morph:[0.2,0.6,'Triangle'],tone:[0.3,0.8,'Triangle'],level:[0.3,1,'Ease In'],resonance:0.5}},
            {id:'warp_drone', params:{waveType:2,duration:1.5,attack:0.1,release:0.5,echo:0.2,pitch:[0.45,0.25,'Linear'],vibrato:[0.6,0.6],tone:[0.6,0.4],level:[0.8,0.5],resonance:0.4}}],
        roar: [
            {id:'roar_growl', params:{waveType:2,duration:0.9,attack:0.05,release:0.3,echo:0.1,pitch:[0.2,0.12,'Ease Out'],vibrato:[0.9,0.9],waveTo:10,morph:[0.3,0.7],tone:[0.6,0.4],level:[0.9,0.5],resonance:0.4}},
            {id:'roar_screech', params:{waveType:2,duration:0.7,attack:0.03,release:0.2,echo:0.1,pitch:[0.6,0.75,'Triangle'],vibrato:[0.7,1],waveTo:10,morph:[0.2,0.6],tone:[0.9,0.8],level:[0.9,0.5],resonance:0.5}},
            {id:'roar_pulses', params:{waveType:3,duration:1,attack:0,release:0.1,echo:0,pitch:[0.18,0.14],vibrato:[1,1],level:[1,0.8,'Pulse'],tone:[0.5,0.5]}},
            {id:'roar_cry', params:{waveType:3,duration:0.6,attack:0,release:0.1,echo:0,pitch:[0.55,0.3,'Ease Out'],vibrato:[0.6,0.9],tone:[0.9,0.6],level:[1,0.5]}},
            {id:'roar_moan', params:{waveType:0,duration:1.4,attack:0.2,release:0.5,echo:0.2,pitch:[0.2,0.32,'Pulse'],vibrato:[0.2,0.4],waveTo:8,morph:[0.4,0.6],tone:[0.6,0.6],level:[0.5,0.9,'Pulse']}}],
        whirr: [
            {id:'whirr_motor', params:{waveType:2,duration:1.2,attack:0.15,release:0.3,echo:0,pitch:[0.2,0.3,'Ease Out'],vibrato:[0.15,0.15],waveTo:7,morph:[0.2,0.3],tone:[0.4,0.55],level:[0.7,0.9],resonance:0.4}},
            {id:'whirr_servo', params:{waveType:2,duration:0.6,attack:0.02,release:0.1,echo:0,pitch:[0.55,0.7,'Ease Out'],vibrato:[0.2,0.2],tone:[0.7,0.7],level:[0.9,0.7],resonance:0.5}},
            {id:'whirr_tick', params:{waveType:3,duration:1,attack:0,release:0.05,echo:0,pitch:[0.45,0.45],level:[1,1,'Pulse'],vibrato:[1,1],tone:[0.7,0.7]}},
            {id:'whirr_rev', params:{waveType:3,duration:1.1,attack:0.05,release:0.2,echo:0,pitch:[0.18,0.36,'Ease In'],vibrato:[0.3,0.3],tone:[0.5,0.7],level:[0.8,1]}},
            {id:'whirr_rotor', params:{waveType:7,duration:1.2,attack:0.05,release:0.2,echo:0,pitch:[0.5,0.5],vibrato:[1,1],tone:[0.35,0.45],level:[0.6,1,'Pulse'],waveTo:0,morph:[0.4,0.4],resonance:0.5}}],
        heal: [
            {id:'heal_arp', params:{waveType:3,duration:0.8,attack:0,release:0.3,echo:0.3,pitch:[0.55,0.78,'Steps'],tone:[0.7,0.9],level:[0.8,0.4]}},
            {id:'heal_shimmer', params:{waveType:11,duration:1.2,attack:0.05,release:0.7,echo:0.45,pitch:[0.6,0.84,'Ease Out'],vibrato:[0,0.3,'Ease In'],tone:[0.9,1],level:[0.9,0.2]}},
            {id:'heal_ladder', params:{waveType:3,duration:0.9,attack:0,release:0.05,echo:0.05,pitch:[0.6,0.76,'Linear'],level:[1,0.9,'Pulse'],vibrato:[1,1],tone:[0.9,0.9]}},
            {id:'heal_swell', params:{waveType:0,duration:1.4,attack:0.4,release:0.6,echo:0.4,pitch:[0.6,0.66,'Smooth'],waveTo:11,morph:[0,0.6,'Ease In'],vibrato:[0,0.3],tone:[0.6,0.95],level:[0.3,1,'Ease In']}}]
    };
    static verbExamples = Object.entries(Transfxr.verbRecipes).flatMap(([verb, archetypes]) => archetypes.map(a => ({...a, verb})));

    templates = [
        ...Object.keys(Transfxr.verbRecipes).map(verb => {
            const entry = typeof game_verb === 'function' ? game_verb(verb) : null;
            return [entry ? entry.name : verb, (entry ? entry.tip : verb) + ' One of ' + Transfxr.verbRecipes[verb].length + ' retro archetypes.', 'generate_verb_' + verb, entry ? entry.name : verb];
        }),
        ...(Transfxr.preset_families.length ? Transfxr.preset_families.map(p =>
            [p.name,p.tip,'generate_family_'+p.id,p.name.replace(/ /g,'')]) :
            Transfxr.examples.map(p => [p.name,p.tip,'generate_'+p.id,p.name.replace(/ /g,'')])),
        ['Timbral Morph','Generate a journey between two waveform characters.','generate_morph','Morph'],
        ['Randomize','Find a new journey; locked controls stay put.','randomize_params','Random'],
        ['Mutate','Nudge both endpoints of unlocked controls.','mutate_params','Mutant']
    ];

    constructor() {
        super();
        this.post_initialize();
        for (const example of Transfxr.examples) this['generate_'+example.id] = () => this.generate_example(example.id);
        for (const verb of Object.keys(Transfxr.verbRecipes)) this['generate_verb_'+verb] = () => this.generate_verb(verb);
        for (const family of Transfxr.preset_families) this['generate_family_'+family.id] = () => this.generate_family(family.id);
    }

    apply_params(params, check_locked = false) {
        if(!params||typeof params!=='object')return;
        if(params.noise && typeof params.noise==='object' &&
            (params.waveTo===undefined || params.waveTo===-1) &&
            (params.noise.start>0 || params.noise.end>0)) {
            // Saved sounds from before waveform morphing used a separate white-noise blend.
            params={...params,waveTo:7,morph:params.noise};
        }
        if(['waveType','duration','pitch','tone','vibrato','level'].every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            const defaults=this.default_params();
            for(const key of ['waveTo','morph'])if(!Object.prototype.hasOwnProperty.call(params,key))this.set_param(key,defaults[key],check_locked);
        }
        // File/link input is data, not a guarantee of finite, in-range controls.
        for (const info of this.param_info) {
            const name = this.get_param_normalized(info).name;
            if (Object.prototype.hasOwnProperty.call(params, name)) this.set_param(name, params[name], check_locked);
        }
    }

    verb_generator(verb) { return Transfxr.verbRecipes[verb] ? 'generate_verb_' + verb : null; }
    verbs() { return Object.keys(Transfxr.verbRecipes); }
    generate_verb(verb) {
        const archetypes = Transfxr.verbRecipes[verb];
        if (!archetypes) return;
        const archetype = archetypes[Math.floor(Math.random() * archetypes.length)];
        this.generate_example(archetype.id, true);
        // Archetypes vary a little more than examples: timing as well as pitch.
        this.set_param('duration', this.params.duration * (0.9 + Math.random() * 0.2), true);
        this.verb_archetype = archetype.id;
    }

    generate_example(id, vary = true) {
        const example = Transfxr.examples.find(p => p.id === id) || Transfxr.verbExamples.find(p => p.id === id);
        this.reset_params(true);
        const shift = vary ? (Math.random() - 0.5) * 0.045 : 0;
        for (const [key, value] of Object.entries(example.params)) {
            if (Array.isArray(value)) {
                this.set_param(key, {start:value[0] + (key==='pitch'?shift:0),
                    end:value[1] + (key==='pitch'?shift:0),curve:value[2] || 'Linear'}, true);
            } else this.set_param(key, value, true);
        }
    }

    create_editor(tab,parent) { return new MorphEditor(tab,parent); }

    generate_morph() {
        this.create_random_template();
        this.set_param('waveTo',(this.params.waveType+1+Math.floor(Math.random()*11))%12,true);
        this.set_param('morph',{start:0,end:1,curve:['Smooth','Ease In','Ease Out','Pulse'][Math.floor(Math.random()*4)]},true);
        this.set_param('tone',{start:.8,end:.75+Math.random()*.25,curve:'Smooth'},true);
        this.set_param('duration',.5+Math.random()*1.2,true);
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

class MorphEditor {
    constructor(tab,parent) {
        this.tab=tab;
        const row=document.createElement('label');row.className='morph-target';row.textContent='Morph to';
        this.select=document.createElement('select');this.select.setAttribute('aria-label','Morph to');
        for(const [label,tip,value] of tab.synth.get_param_info('waveTo').values){
            const option=document.createElement('option');option.value=value;option.textContent=label;option.title=tip;this.select.appendChild(option);
        }
        this.select.addEventListener('change',()=>{tab.synth.set_param('waveTo',+this.select.value);tab.parameter_changed();});
        this.select.addEventListener('keydown',event=>event.stopPropagation());
        row.appendChild(this.select);parent.appendChild(row);
        // Keep the curve with its destination, without changing the saved parameter schema.
        this.curveRow=document.getElementById(tab.name+'_graph_morph').closest('tr');
        const table=document.createElement('table');table.className='morph-curve';
        table.appendChild(this.curveRow);parent.appendChild(table);
        this.update();
    }
    update(){
        this.select.value=this.tab.synth.params.waveTo;
        this.curveRow.hidden=this.tab.synth.params.waveTo===-1;
    }
}
