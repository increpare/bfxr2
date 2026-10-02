class Rollr extends PresetSynth {
    name='Rollr';
    tooltip='Rolling wheels, gritty surfaces and rumbling bodies.';
    static DSP=Rollr_DSP;
    param_info=[...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'material',display_name:'Body',tooltip:'The material resonating above the rolling surface.',default_value:0,columns:2,header:true,values:[['Wood','Dry wheel knocks.',0],['Stone','Dense rumbling.',1],['Metal','Rattling resonances.',2],['Soft','Muffled contact.',3]]},
        ['Duration','Seconds.','duration',2,0.2,5],
        ['Wheels','Independent rolling contact points.','wheels',2,1,6],
        ['Speed','Wheel rotation and contact rate.','speed',0.5,0,1],
        ['Roughness','Grit and irregular bumps in the surface.','roughness',0.45,0,1],
        ['Size','Larger bodies resonate lower.','size',0.5,0,1],
        ['Hardness','Brighter wheel contacts.','hardness',0.6,0,1],
        ['Slowdown','Lose speed over the sound.','slowing',0.35,0,1]
    ];
    recipes=[
        {name:'Wooden Wheels',id:'wooden_wheels',values:{material:0,duration:[1.1,2.5],wheels:[2,4],speed:[0.15,0.45],roughness:[0.3,0.7],size:[0.5,0.85],hardness:[0.4,0.7],slowing:[0.05,0.4]}},
        {name:'Stone Roll',id:'stone_roll',values:{material:1,duration:[1.4,3],wheels:1,speed:[0.1,0.4],roughness:[0.65,1],size:[0.8,1],hardness:[0.4,0.7],slowing:[0.2,0.7]}},
        {name:'Skateboard',id:'skateboard',values:{material:0,duration:[0.9,2.2],wheels:4,speed:[0.65,1],roughness:[0.35,0.65],size:[0.2,0.45],hardness:[0.75,1],slowing:[0.1,0.4]}},
        {name:'Minecart',id:'minecart',values:{material:2,duration:[1.8,3.5],wheels:4,speed:[0.3,0.65],roughness:[0.6,1],size:[0.7,1],hardness:[0.7,1],slowing:[0,0.25]}},
        {name:'Shopping Cart',id:'shopping_cart',values:{material:2,duration:[1.2,2.6],wheels:4,speed:[0.2,0.55],roughness:[0.5,0.85],size:[0.35,0.65],hardness:[0.5,0.85],slowing:[0.1,0.5]}},
        {name:'Suitcase',id:'suitcase',values:{material:3,duration:[0.9,2.4],wheels:2,speed:[0.3,0.65],roughness:[0.3,0.7],size:[0.3,0.6],hardness:[0.5,0.8],slowing:[0.15,0.55]}},
        {name:'Metal Roller',id:'metal_roller',values:{material:2,duration:[1.3,2.8],wheels:1,speed:[0.25,0.6],roughness:[0.1,0.45],size:[0.5,0.85],hardness:[0.7,1],slowing:[0.2,0.6]}},
        {name:'Snowball',id:'snowball',values:{material:3,duration:[1.3,2.7],wheels:1,speed:[0.1,0.45],roughness:[0.65,1],size:[0.7,1],hardness:[0,0.2],slowing:[0.4,0.9]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){if(name==='wheels'&&Number.isFinite(value))value=Math.round(value);super.set_param(name,value,checkLocked);}
}
