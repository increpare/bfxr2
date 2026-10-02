class Boomr extends PresetSynth {
    name='Boomr';
    tooltip='Pressure waves, fireballs and falling fragments.';
    static DSP=Boomr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        ['Duration','Seconds.','duration',1.5,0.12,5],
        ['Size','Large blasts have lower pressure waves.','size',0.5,0,1],
        ['Pressure','The low shock front of the explosion.','pressure',0.7,0,1],
        ['Blast','Turbulent fire and rushing air.','blast',0.65,0,1],
        ['Debris','Separate ringing fragments after the blast.','debris',0.35,0,1],
        ['Scatter','Spread the fragments through the tail.','spread',0.5,0,1],
        ['Aftermath','Length and weight of the rolling decay.','tail',0.45,0,1],
        ['Muffle','Lose sharp detail behind walls or underwater.','muffle',0.15,0,1]
    ];
    recipes=[
        {name:'Grenade',id:'grenade',tip:'A sharp pressure thump and loose shrapnel.',values:{duration:[0.65,1.5],size:[0.25,0.55],pressure:[0.65,1],blast:[0.45,0.8],debris:[0.55,0.95],spread:[0.3,0.7],tail:[0.2,0.5],muffle:[0.03,0.25]}},
        {name:'Barrel',id:'barrel',tip:'A hollow fuel drum erupting.',values:{duration:[1,2],size:[0.4,0.7],pressure:[0.5,0.85],blast:[0.7,1],debris:[0.65,1],spread:[0.15,0.55],tail:[0.45,0.8],muffle:[0.1,0.35]}},
        {name:'Rocket',id:'rocket',tip:'A hard detonation with a tearing fireball.',values:{duration:[0.7,1.6],size:[0.3,0.65],pressure:[0.8,1],blast:[0.8,1],debris:[0.2,0.5],spread:[0.05,0.3],tail:[0.3,0.65],muffle:[0,0.18]}},
        {name:'Depth Charge',id:'depth_charge',tip:'An immense muffled underwater pressure wave.',values:{duration:[1.8,3.6],size:[0.8,1],pressure:[0.85,1],blast:[0.4,0.8],debris:[0,0.15],spread:[0.4,0.8],tail:[0.65,1],muffle:[0.75,1]}},
        {name:'Fireball',id:'fireball',tip:'A bloom of flame with a rolling hot tail.',values:{duration:[1.3,2.8],size:[0.45,0.8],pressure:[0.3,0.6],blast:[0.85,1],debris:[0.02,0.22],spread:[0.2,0.55],tail:[0.7,1],muffle:[0.2,0.5]}},
        {name:'Meteor',id:'meteor',tip:'A massive impact and scattered incandescent rubble.',values:{duration:[2.2,4.5],size:[0.85,1],pressure:[0.85,1],blast:[0.65,0.95],debris:[0.75,1],spread:[0.65,1],tail:[0.7,1],muffle:[0.3,0.6]}},
        {name:'Demolition',id:'demolition',tip:'A heavy charge followed by falling structure.',values:{duration:[1.6,3.8],size:[0.65,0.95],pressure:[0.65,0.9],blast:[0.4,0.7],debris:[0.85,1],spread:[0.7,1],tail:[0.45,0.85],muffle:[0.15,0.4]}},
        {name:'Tiny Pop',id:'tiny_pop',tip:'A miniature comic detonation.',values:{duration:[0.12,0.35],size:[0,0.2],pressure:[0.55,0.85],blast:[0.1,0.4],debris:[0,0.12],spread:[0,0.25],tail:[0,0.18],muffle:[0,0.12]}}
    ];
    constructor(){super();this.initialize_presets();}
}
