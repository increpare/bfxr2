class Squishr extends PresetSynth {
    name = 'Squishr';
    tooltip = 'Slime, bubbles, suction, and springy goo: tactile sounds from soft and liquid things.';
    static DSP = Squishr_DSP;
    header_properties = ['texture'];

    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'texture', display_name:'Texture', tooltip:'The liquid or soft-body gesture.',
            default_value:0, columns:3, header:true, values:[
                ['Slime','Sticky noise with scattered little squelches.',0], ['Bubbles','Rounded rising bubble resonances.',1],
                ['Suction','Pulling pressure followed by a release pop.',2], ['Splat','A noisy impact and scattered droplets.',3],
                ['Gulp','Repeated pairs of descending liquid resonances.',4], ['Spring','Stretchy, bouncing jelly oscillations.',5]]},
        ['Viscosity','Thin, bright liquid to thick, muffled goo.','viscosity',0.6,0,1],
        ['Stretch','Length and wobble of the soft-body deformation.','stretch',0.4,0,1],
        ['Pressure','Force, bubble activity, and pitch movement.','pressure',0.6,0,1],
        ['Wetness','Dry soft-body motion to prominent wet bubbles.','wetness',0.75,0,1],
        ['Bubble Size','Tiny high droplets to large, low liquid cavities.','bubbleSize',0.55,0,1],
        ['Duration','Length of the gesture in seconds.','duration',0.65,0.1,3]
    ];

    recipes = [
        {name:'Slime Step', id:'slime_step', tip:'A sticky footstep through a puddle of goo.',
            values:{texture:0,viscosity:[0.65,0.95],stretch:[0.25,0.6],pressure:[0.5,0.85],wetness:[0.65,1],bubbleSize:[0.55,0.85],duration:[0.28,0.55]}},
        {name:'Bubble Pop', id:'bubble_pop', tip:'A small rounded bubble bursting.',
            values:{texture:1,viscosity:[0.25,0.55],stretch:[0.02,0.25],pressure:[0.5,0.9],wetness:[0.8,1],bubbleSize:[0.15,0.4],duration:[0.1,0.2]}},
        {name:'Suction Cup', id:'suction_cup', tip:'Stretch the seal, then pop it free.',
            values:{texture:2,viscosity:[0.55,0.9],stretch:[0.55,0.95],pressure:[0.55,0.9],wetness:[0.4,0.8],bubbleSize:[0.45,0.7],duration:[0.35,0.8]}},
        {name:'Wet Splat', id:'wet_splat', tip:'A wet impact spraying small droplets.',
            values:{texture:3,viscosity:[0.1,0.4],stretch:[0.02,0.25],pressure:[0.75,1],wetness:[0.75,1],bubbleSize:[0.3,0.65],duration:[0.18,0.4]}},
        {name:'Gulp', id:'gulp', tip:'A low, hollow swallow of liquid.',
            values:{texture:4,viscosity:[0.3,0.6],stretch:[0.2,0.55],pressure:[0.35,0.65],wetness:[0.8,1],bubbleSize:[0.55,0.85],duration:[0.2,0.45]}},
        {name:'Springy Goo', id:'springy_goo', tip:'Elastic slime springing back into shape.',
            values:{texture:5,viscosity:[0.5,0.85],stretch:[0.75,1],pressure:[0.45,0.85],wetness:[0.25,0.6],bubbleSize:[0.4,0.7],duration:[0.45,0.95]}},
        {name:'Bubbling Potion', id:'bubbling_potion', tip:'An active cauldron of uneven rounded bubbles.',
            values:{texture:1,viscosity:[0.5,0.85],stretch:[0.2,0.65],pressure:[0.65,1],wetness:[0.8,1],bubbleSize:[0.35,0.8],duration:[1.4,2.7]}},
        {name:'Mud Pull', id:'mud_pull', tip:'Slowly pull something out of thick, sticky mud.',
            values:{texture:2,viscosity:[0.85,1],stretch:[0.7,1],pressure:[0.3,0.65],wetness:[0.35,0.7],bubbleSize:[0.75,1],duration:[0.9,1.8]}},
        {name:'Water Drop', id:'water_drop', tip:'A light high droplet falling into water.',
            values:{texture:1,viscosity:[0.02,0.25],stretch:[0.02,0.15],pressure:[0.15,0.45],wetness:[0.85,1],bubbleSize:[0.02,0.25],duration:[0.1,0.18]}},
        {name:'Jelly Wobble', id:'jelly_wobble', tip:'A large soft jelly shaking from side to side.',
            values:{texture:5,viscosity:[0.75,1],stretch:[0.6,0.95],pressure:[0.2,0.5],wetness:[0.05,0.3],bubbleSize:[0.7,1],duration:[0.8,1.5]}}
    ];

    constructor() { super(); this.initialize_presets(); }
}
