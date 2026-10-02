class Bouncr extends PresetSynth {
    name='Bouncr';
    tooltip='Bouncing bodies, tumbling dice and settling coins.';
    static DSP=Bouncr_DSP;
    param_info=[...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'material',display_name:'Material',tooltip:'The body that strikes the ground.',default_value:0,columns:3,header:true,values:[['Rubber','Elastic thuds.',0],['Wood','Dry knocks.',1],['Metal','Ringing collisions.',2],['Glass','Bright little clinks.',3],['Stone','Dense dull impacts.',4]]},
        ['Duration','Seconds.','duration',2,0.2,5],
        ['Bounces','Maximum number of contacts.','count',7,2,20],
        ['Elasticity','Retain energy and flight time after impact.','bounce',0.65,0,1],
        ['Gravity','Stronger gravity shortens the flights.','gravity',0.5,0,1],
        ['Size','Larger bodies resonate lower.','size',0.5,0,1],
        ['Hardness','Sharp contact and brighter resonances.','hardness',0.6,0,1],
        ['Spin','Accelerate the settling rattle and vary its pitch.','spin',0,0,1]
    ];
    recipes=[
        {name:'Rubber Ball',id:'rubber_ball',values:{material:0,duration:[1.5,2.6],count:[5,9],bounce:[0.7,0.95],gravity:[0.2,0.55],size:[0.3,0.6],hardness:[0.2,0.5],spin:[0,0.15]}},
        {name:'Metal Ball',id:'metal_ball',values:{material:2,duration:[1,2.1],count:[5,10],bounce:[0.55,0.8],gravity:[0.4,0.75],size:[0.3,0.65],hardness:[0.65,1],spin:[0,0.2]}},
        {name:'Wooden Dice',id:'wooden_dice',values:{material:1,duration:[0.6,1.4],count:[6,12],bounce:[0.25,0.55],gravity:[0.6,1],size:[0.15,0.4],hardness:[0.55,0.85],spin:[0.5,1]}},
        {name:'Basketball',id:'basketball',values:{material:0,duration:[2,3.5],count:[4,7],bounce:[0.8,1],gravity:[0,0.3],size:[0.75,1],hardness:[0.55,0.8],spin:[0,0.1]}},
        {name:'Marble',id:'marble',values:{material:3,duration:[0.8,1.7],count:[6,12],bounce:[0.55,0.8],gravity:[0.4,0.8],size:[0.05,0.3],hardness:[0.7,1],spin:[0.2,0.5]}},
        {name:'Coin Spin',id:'coin_spin',values:{material:2,duration:[1,2.2],count:[14,20],bounce:[0.7,0.9],gravity:[0.4,0.75],size:[0.05,0.25],hardness:[0.8,1],spin:[0.85,1]}},
        {name:'Cartoon Bounce',id:'cartoon_bounce',values:{material:0,duration:[1.2,2.5],count:[4,8],bounce:[0.7,0.95],gravity:[0.1,0.5],size:[0,0.3],hardness:[0.05,0.3],spin:[0.1,0.35]}},
        {name:'Heavy Tumble',id:'heavy_tumble',values:{material:4,duration:[0.9,2],count:[3,7],bounce:[0.2,0.5],gravity:[0.4,0.8],size:[0.8,1],hardness:[0.3,0.65],spin:[0.3,0.7]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){if(name==='count'&&Number.isFinite(value))value=Math.round(value);super.set_param(name,value,checkLocked);}
}
