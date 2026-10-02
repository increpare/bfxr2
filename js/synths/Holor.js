class Holor extends PresetSynth {
    name='Holor';
    tooltip='Precise holographic interface gestures with moving digital overtones.';
    static DSP=Holor_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'gesture',display_name:'Gesture',tooltip:'The motion and envelope of the interaction.',
            default_value:0,columns:4,values:[['Sweep','A smooth hand or panel movement.',0],['Ping','A focused, decaying point.',1],
                ['Lock','Accelerating pulses converging on a target.',2],['Reveal','Overlapping scans assembling a shape.',3]]},
        ['Duration','Complete gesture length, in seconds.','duration',0.45,0.08,3],
        ['Pitch','The central oscillator frequency.','pitch',0.5,0,1],
        ['Sweep','The direction and extent of the spectral motion.','sweep',0.4,-1,1],
        ['Bandwidth','Width and brightness of the scanned resonant band.','bandwidth',0.4,0,1],
        ['Sidebands','Adds metallic FM overtones around the carrier.','sidebands',0.45,0,1],
        ['Scan','Scans resonances and shifts frequencies around the carrier.','scan',0.25,0,1],
        ['Grain','Tiny filtered digital flecks along the gesture.','grain',0.12,0,1],
        ['Comb','A short moving delay colors the gesture with spectral notches.','comb',0.35,0,1]
    ];
    recipes=[
        {id:'cursor_trail',name:'Cursor Trail',tip:'A fine shimmering trace following the cursor.',values:{gesture:0,duration:[0.1,0.23],pitch:[0.64,0.85],sweep:[-0.28,0.3],bandwidth:[0.15,0.4],sidebands:[0.25,0.5],scan:[0.35,0.62],grain:[0.04,0.18],comb:[0.4,0.75]}},
        {id:'radial_menu',name:'Radial Menu',tip:'A circular spread of bright moving spectral teeth.',values:{gesture:0,duration:[0.2,0.46],pitch:[0.4,0.61],sweep:[0.35,0.7],bandwidth:[0.4,0.65],sidebands:[0.45,0.72],scan:[0.32,0.58],grain:[0.06,0.22],comb:[0.65,1]}},
        {id:'map_ping',name:'Map Ping',tip:'A precise map marker with a metallic halo.',values:{gesture:1,duration:[0.3,0.7],pitch:[0.57,0.77],sweep:[-0.16,0.08],bandwidth:[0.08,0.28],sidebands:[0.18,0.42],scan:[0.03,0.15],grain:[0,0.04],comb:[0.15,0.42]}},
        {id:'target_lock',name:'Target Lock',tip:'Rapid focused scans settle on a target.',values:{gesture:2,duration:[0.35,0.85],pitch:[0.48,0.72],sweep:[0.25,0.75],bandwidth:[0.12,0.32],sidebands:[0.3,0.62],scan:[0.6,0.95],grain:[0.02,0.12],comb:[0.2,0.5]}},
        {id:'drag_drop',name:'Drag / Drop',tip:'A downward digital flick snapping into place.',values:{gesture:1,duration:[0.12,0.28],pitch:[0.35,0.58],sweep:[-0.85,-0.4],bandwidth:[0.45,0.72],sidebands:[0.55,0.85],scan:[0.1,0.3],grain:[0.08,0.25],comb:[0.45,0.75]}},
        {id:'panel_swipe',name:'Panel Swipe',tip:'A short broad scan for a moving panel.',values:{gesture:0,duration:[0.2,0.48],pitch:[0.28,0.48],sweep:[-0.95,-0.5],bandwidth:[0.7,1],sidebands:[0.65,0.95],scan:[0.25,0.55],grain:[0.4,0.75],comb:[0.5,0.85]}},
        {id:'tooltip',name:'Tooltip',tip:'A small airy electronic point.',values:{gesture:1,duration:[0.09,0.19],pitch:[0.7,0.9],sweep:[0.02,0.2],bandwidth:[0.12,0.3],sidebands:[0.08,0.3],scan:[0.04,0.16],grain:[0,0.08],comb:[0.08,0.3]}},
        {id:'data_reveal',name:'Data Reveal',tip:'Layered scans assemble a holographic readout.',values:{gesture:3,duration:[0.4,0.95],pitch:[0.35,0.6],sweep:[0.4,0.85],bandwidth:[0.45,0.8],sidebands:[0.6,1],scan:[0.5,0.9],grain:[0.25,0.55],comb:[0.55,0.95]}}
    ];
    constructor(){super();this.initialize_presets();}
}
