class Riftr extends PresetSynth {
    name = 'Riftr';
    tooltip = 'Warped spaces, force fields and reversals through a moving resonant field.';
    static DSP = Riftr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'excitation', display_name:'Excitation', tooltip:'What enters the resonant field.',
            default_value:0, columns:5, values:[['Pulse','A short tonal impulse.',0],['Arc','A swelling electrical arc.',1],
                ['Drone','A sustained, pulsing field.',2],['Tear','A noisy rupture with a low body.',3],['Quanta','Separated packets of phase-shifted tone.',4]]},
        ['Duration','Length of the complete effect, in seconds.','duration',1.8,0.15,6],
        ['Pitch','Pitch of the signal entering the field.','pitch',0.45,0,1],
        ['Bend','Pitch travel from falling to rising.','bend',-0.2,-1,1],
        ['Space','Propagation distance inside the field; larger spaces echo more slowly.','space',0.5,0,1],
        ['Feedback','How much energy returns through the field.','feedback',0.65,0,1],
        ['Dispersion','Allpass delays scatter the field into a smeared, metallic tail.','dispersion',0.55,0,1],
        ['Motion','Moving delay taps bend the field’s phase and pitch.','motion',0.3,0,1],
        ['Field Mix','Blend between the source and its resonant field.','field',0.7,0,1],
        ['Reverse','Blend the finished field with time running backwards.','reverse',0,0,1]
    ];
    recipes = [
        {name:'Warp',id:'warp',verb:'warp',tip:'A field tearing open or snapping shut.',values:{excitation:[0,3],duration:[0.5,1.6],pitch:[0.4,0.85],bend:[-0.7,0.9],space:[0.2,0.6],feedback:[0.6,0.9],dispersion:[0.3,0.8],motion:[0.2,0.7],field:[0.5,0.85],reverse:[0,0.6]}},
        {name:'Cast',id:'cast',verb:'cast',tip:'A rising arc of energy leaving the hand.',values:{excitation:[1,4],duration:[0.5,1.5],pitch:[0.4,0.9],bend:[0.2,0.9],space:[0.1,0.5],feedback:[0.4,0.8],dispersion:[0.3,0.8],motion:[0.3,0.9],field:[0.5,0.9],reverse:[0,0.3]}},
        {name:'Lose',id:'lose',verb:'lose',tip:'A tone sinking into a tightening field.',values:{excitation:0,duration:[0.8,1.8],pitch:[0.3,0.6],bend:[-0.9,-0.4],space:[0.3,0.7],feedback:[0.6,0.9],dispersion:[0.5,0.9],motion:[0.1,0.4],field:[0.6,0.9],reverse:[0,0.3]}},
        {name:'Gravity Well',id:'gravity_well',tip:'A descending tone trapped in a tightening field.',values:{excitation:1,duration:[1.5,3],pitch:[0.35,0.6],bend:[-1,-0.55],space:[0.45,0.8],feedback:[0.65,0.9],dispersion:[0.4,0.8],motion:[0.15,0.5],field:[0.6,0.9],reverse:[0,0.12]}},
        {name:'Time Rewind',id:'time_rewind',tip:'A dispersed impact pulling itself back together.',values:{excitation:0,duration:[1,2.6],pitch:[0.45,0.8],bend:[-0.65,0.3],space:[0.35,0.75],feedback:[0.72,0.95],dispersion:[0.6,1],motion:[0.1,0.5],field:[0.7,1],reverse:[0.93,1]}},
        {name:'Phase Dash',id:'phase_dash',verb:'dash',tip:'A short upward arc slipping through a small space.',values:{excitation:1,duration:[0.18,0.5],pitch:[0.25,0.65],bend:[0.35,0.95],space:[0.03,0.25],feedback:[0.15,0.5],dispersion:[0.15,0.5],motion:[0.55,1],field:[0.35,0.7],reverse:[0,0.15]}},
        {name:'Force Field',id:'force_field',tip:'An energized barrier humming through its resonant geometry.',values:{excitation:2,duration:[1.5,3.8],pitch:[0.18,0.5],bend:[-0.12,0.12],space:[0.04,0.35],feedback:[0.72,0.98],dispersion:[0.15,0.55],motion:[0.2,0.55],field:[0.55,0.85],reverse:[0,0.2]}},
        {name:'Portal Tear',id:'portal_tear',tip:'A ragged opening scattering sound through a large space.',values:{excitation:3,duration:[1,2.8],pitch:[0.25,0.55],bend:[0.3,0.9],space:[0.5,0.95],feedback:[0.55,0.9],dispersion:[0.7,1],motion:[0.5,1],field:[0.5,0.9],reverse:[0.15,0.4]}},
        {name:'Teleport Arrive',id:'teleport_arrive',tip:'A reversed field gathering into a bright arrival.',values:{excitation:0,duration:[0.45,1.2],pitch:[0.6,0.95],bend:[-0.7,-0.1],space:[0.15,0.5],feedback:[0.55,0.85],dispersion:[0.3,0.8],motion:[0.1,0.6],field:[0.45,0.8],reverse:[0.78,1]}},
        {name:'Black Hole',id:'black_hole',tip:'A low drone falling into a deep resonant cavity.',values:{excitation:2,duration:[2.5,5],pitch:[0.05,0.25],bend:[-1,-0.45],space:[0.65,1],feedback:[0.85,1],dispersion:[0.65,1],motion:[0.05,0.3],field:[0.55,0.9],reverse:[0,0.18]}},
        {name:'Reality Glitch',id:'reality_glitch',tip:'Phase packets echoing forwards and backwards.',values:{excitation:4,duration:[0.65,1.9],pitch:[0.45,0.95],bend:[-0.8,0.9],space:[0.08,0.55],feedback:[0.45,0.85],dispersion:[0.25,0.9],motion:[0.7,1],field:[0.4,0.8],reverse:[0.25,0.75]}}
    ];
    constructor() { super(); this.initialize_presets(); }
}
