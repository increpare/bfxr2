class Rumblr extends PresetSynth {
    name='Rumblr';
    tooltip='Deep sub pressure, moving structural modes and audible low overtones.';
    static DSP=Rumblr_DSP;
    param_info=[...PresetSynth.common_params,
        ['Duration','Length in seconds.','duration',2,0.2,5],
        ['Size','Larger spaces and structures resonate lower.','size',0.6,0,1],
        ['Weight','Transfer more energy into the low body.','weight',0.6,0,1],
        ['Roughness','Turbulent pressure and uneven structural motion.','roughness',0.4,0,1],
        ['Tremor','Slow shuddering motion and irregular pulses.','tremor',0.3,0,1],
        ['Dust','Scattered fine debris above the bass.','dust',0.15,0,1],
        ['Attack','How slowly the pressure builds.','attack',0.3,0,1],
        ['Sweep','Rising or falling structural tension.','sweep',0,-1,1],
        ['Depth','Shift the body into the sub bass and reduce upper structural modes.','depth',0.75,0,1],
        ['Overtones','Harmonics that make deep pressure audible on smaller speakers.','harmonics',0.35,0,1]
    ];
    recipes=[
        {name:'Earthquake',id:'earthquake',values:{duration:[1.5,3.5],size:[0.75,1],weight:[0.75,1],roughness:[0.55,0.85],tremor:[0.5,0.85],dust:[0.35,0.7],attack:[0.1,0.3],sweep:[-0.15,0.1],depth:[0.7,1],harmonics:[0.35,0.6]}},
        {name:'Boss Approach',id:'boss_approach',values:{duration:[2,4],size:[0.75,1],weight:[0.8,1],roughness:[0.2,0.45],tremor:[0.35,0.7],dust:[0.02,0.2],attack:[0.6,0.85],sweep:[0.05,0.25],depth:[0.65,0.95],harmonics:[0.3,0.6]}},
        {name:'Stone Door',id:'stone_door',values:{duration:[0.8,2],size:[0.55,0.8],weight:[0.65,0.95],roughness:[0.6,0.85],tremor:[0.4,0.7],dust:[0.6,0.9],attack:[0.1,0.3],sweep:[-0.4,-0.15],depth:[0.5,0.8],harmonics:[0.35,0.7]}},
        {name:'Engine Room',id:'engine_room',values:{duration:[1.5,3.5],size:[0.45,0.7],weight:[0.55,0.85],roughness:[0.1,0.35],tremor:[0.7,1],dust:[0,0.12],attack:[0.25,0.5],sweep:[-0.08,0.08],depth:[0.4,0.7],harmonics:[0.4,0.75]}},
        {name:'Space Hull',id:'space_hull',values:{duration:[1.6,3.6],size:[0.8,1],weight:[0.65,0.9],roughness:[0.15,0.4],tremor:[0.1,0.35],dust:[0.05,0.25],attack:[0.3,0.65],sweep:[-0.4,-0.15],depth:[0.8,1],harmonics:[0.25,0.55]}},
        {name:'Landslide',id:'landslide',values:{duration:[1.2,3],size:[0.6,0.9],weight:[0.7,1],roughness:[0.8,1],tremor:[0.25,0.65],dust:[0.75,1],attack:[0.15,0.45],sweep:[0.1,0.35],depth:[0.6,0.9],harmonics:[0.3,0.65]}},
        {name:'Deep Pressure',id:'deep_pressure',values:{duration:[2,4.5],size:[0.9,1],weight:[0.8,1],roughness:[0.03,0.2],tremor:[0.03,0.2],dust:[0,0.1],attack:[0.65,0.95],sweep:[-0.25,-0.05],depth:[0.9,1],harmonics:[0.15,0.4]}},
        {name:'Volcano',id:'volcano',values:{duration:[1.5,3.5],size:[0.75,1],weight:[0.85,1],roughness:[0.7,1],tremor:[0.55,0.9],dust:[0.5,0.85],attack:[0.25,0.55],sweep:[-0.05,0.2],depth:[0.75,1],harmonics:[0.4,0.7]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        const oldKeys=['masterVolume','seed','duration','size','weight','roughness','tremor','dust','attack','sweep'];
        if(params && oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['depth','harmonics'])if(!Object.prototype.hasOwnProperty.call(params,key))this.set_param(key,this.param_default(key),checkLocked);
        }
        super.apply_params(params,checkLocked);
    }
}
