class Whooshr extends PresetSynth {
    name='Whooshr';
    canvas_bg_logo = 'img/logo_whooshr.png';
    tooltip='Swings, flybys and rushing air.';
    static DSP=Whooshr_DSP;
    param_info=[...PresetSynth.common_params,
        ['Duration','Seconds.','duration',0.6,0.1,5],
        ['Size','Large objects push deeper air.','size',0.4,0,1],
        ['Air','Filtered rushing turbulence.','air',0.8,0,1],
        ['Whistle','The pitched edge of a fast object.','whistle',0.25,0,1],
        ['Flyby','Pitch falls as the object passes.','movement',0.7,0,1],
        ['Focus','Concentrate the rush around its closest approach.','focus',0.6,0,1],
        ['Flutter','Uneven folds, feathers and trailing edges.','flutter',0.1,0,1]
    ];
    recipes=[
        {name:'Sword Swing',id:'sword_swing',values:{duration:[0.18,0.42],size:[0.25,0.5],air:[0.6,0.9],whistle:[0.25,0.55],movement:[0.65,1],focus:[0.5,0.85],flutter:[0,0.1]}},
        {name:'Dodge',id:'dodge',values:{duration:[0.25,0.55],size:[0.5,0.8],air:[0.75,1],whistle:[0,0.1],movement:[0.2,0.6],focus:[0.3,0.65],flutter:[0.1,0.3]}},
        {name:'Arrow Pass',id:'arrow_pass',values:{duration:[0.16,0.4],size:[0.05,0.3],air:[0.3,0.65],whistle:[0.5,0.9],movement:[0.8,1],focus:[0.65,1],flutter:[0,0.1]}},
        {name:'Heavy Swing',id:'heavy_swing',values:{duration:[0.4,0.9],size:[0.8,1],air:[0.8,1],whistle:[0.05,0.2],movement:[0.5,0.85],focus:[0.3,0.6],flutter:[0.05,0.25]}},
        {name:'Fast Projectile',id:'fast_projectile',values:{duration:[0.1,0.25],size:[0,0.2],air:[0.65,1],whistle:[0.3,0.7],movement:[0.9,1],focus:[0.7,1],flutter:[0,0.08]}},
        {name:'Wingbeat',id:'wingbeat',values:{duration:[0.35,0.85],size:[0.55,0.9],air:[0.6,0.9],whistle:[0,0.08],movement:[0.1,0.4],focus:[0.15,0.45],flutter:[0.65,1]}},
        {name:'Cloth Swipe',id:'cloth_swipe',values:{duration:[0.25,0.7],size:[0.4,0.75],air:[0.65,1],whistle:[0,0.04],movement:[0.1,0.4],focus:[0.25,0.55],flutter:[0.4,0.8]}},
        {name:'Air Dash',id:'air_dash',values:{duration:[0.35,0.85],size:[0.3,0.65],air:[0.75,1],whistle:[0.15,0.4],movement:[0.65,1],focus:[0.1,0.35],flutter:[0.05,0.2]}}
    ];
    constructor(){super();this.initialize_presets();}
}
