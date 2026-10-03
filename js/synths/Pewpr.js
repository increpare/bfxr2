class Pewpr extends PresetSynth {
    name='Pewpr';
    tooltip='An exotic armory: coherent beams, magnetic coils, living weapons and gravity collapse.';
    static DSP=Pewpr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'kind',display_name:'Mechanism',tooltip:'A different synthesis mechanism for each weapon technology.',default_value:0,columns:4,
            values:[['Laser','Coherent chirped light packets.',0],['Plasma','Unstable oscillating plasma packets.',1],['Ballistic','Pressure wave, barrel body and mechanical action.',2],['Crystal','Dispersive, inharmonic crystal splinters.',3],['Magnetic','An accelerating train of electromagnetic coils.',4],['Organic','A living weapon with moving vocal cavities.',5],['Beam','A sustained interfering energy field.',6],['Gravity','A sucking pressure well followed by collapse.',7]]},
        ['Duration','Seconds for the complete firing sequence.','duration',0.7,0.12,5],
        ['Pitch','Energy scale, cavity size or carrier frequency.','pitch',0.55,0,1],
        ['Sweep','Direction and reach of the weapon’s energy motion.','sweep',-0.65,-1,1],
        ['Charge','Build up energy before the first shot.','charge',0,0,1],
        ['Punch','Strength of the discharge, fracture or pressure transient.','punch',0.65,0,1],
        ['Body','Weight and duration of the firing body.','body',0.45,0,1],
        ['Recoil','Mechanical return, cavity echo or gravitational aftershock.','recoil',0.2,0,1],
        ['Grit','Turbulence, tearing or breath mixed into the mechanism.','grit',0.1,0,1],
        ['Shots','Number of shots in a burst.','shots',1,1,8],
        ['Character','Coil spacing, cavity shape, crystal dispersion or beam detuning.','character',0.5,0,1],
        ['Modulation','Instability, pulsation or moving resonances.','modulation',0.45,0,1]
    ];
    recipes=[
        {name:'Laser Pistol',id:'laser_pistol',tip:'Coherent light packets with a sharp optical chirp.',values:{kind:0,duration:[0.2,0.65],pitch:[0.4,0.85],sweep:[-1,-0.3],charge:[0,0.08],punch:[0.55,0.9],body:[0.15,0.45],recoil:[0.05,0.3],grit:[0,0.08],shots:1,character:[0.1,0.9],modulation:[0.05,0.5]}},
        {name:'Plasma Rifle',id:'plasma_rifle',tip:'Burbling, unstable packets of confined plasma.',values:{kind:1,duration:[0.6,1.5],pitch:[0.25,0.6],sweep:[-0.8,0.15],charge:[0,0.15],punch:[0.4,0.75],body:[0.4,0.85],recoil:[0.15,0.55],grit:[0.12,0.45],shots:[2,5],character:[0.15,0.95],modulation:[0.45,1]}},
        {name:'Coil Driver',id:'railgun',tip:'Accelerating magnetic coils discharge into a deep recoil.',values:{kind:4,duration:[0.8,1.8],pitch:[0.25,0.8],sweep:[-1,-0.3],charge:[0.15,0.55],punch:[0.75,1],body:[0.15,0.5],recoil:[0.65,1],grit:[0.02,0.3],shots:1,character:[0.2,1],modulation:[0.2,0.85]}},
        {name:'Spore Cannon',id:'blaster',tip:'A living throat inflates, spits and contracts.',values:{kind:5,duration:[0.45,1.3],pitch:[0.1,0.65],sweep:[-0.9,0.5],charge:[0,0.18],punch:[0.35,0.8],body:[0.5,0.9],recoil:[0.15,0.6],grit:[0.2,0.7],shots:[1,3],character:[0.1,0.95],modulation:[0.25,1]}},
        {name:'Scatter Cannon',id:'shotgun',tip:'A physical pressure blast, short barrel body and a mechanical return.',values:{kind:2,duration:[0.35,0.9],pitch:[0.1,0.6],sweep:[-0.8,-0.1],charge:[0,0.04],punch:[0.8,1],body:[0.2,0.5],recoil:[0.6,1],grit:[0.5,1],shots:1,character:[0.1,0.95],modulation:[0.1,0.75]}},
        {name:'Prism Lance',id:'ricochet',tip:'Splintering dispersive rays fan out in different directions.',values:{kind:3,duration:[0.45,1.4],pitch:[0.3,0.75],sweep:[-0.7,1],charge:[0,0.18],punch:[0.3,0.75],body:[0.35,0.85],recoil:[0.1,0.5],grit:[0.01,0.2],shots:[1,2],character:[0.15,1],modulation:[0.2,0.9]}},
        {name:'Gravity Well',id:'charge_shot',tip:'Space folds inward, collapses, then rolls outward in subsonic aftershocks.',values:{kind:7,duration:[1.3,3],pitch:[0.1,0.6],sweep:[-1,0.5],charge:[0.35,0.85],punch:[0.7,1],body:[0.55,1],recoil:[0.6,1],grit:[0.05,0.3],shots:1,character:[0.2,1],modulation:[0.2,0.95]}},
        {name:'Ion Beam',id:'freeze_ray',tip:'A sustained, beating field that tears into fluttering interference.',values:{kind:6,duration:[0.9,2.4],pitch:[0.25,0.8],sweep:[-0.4,0.4],charge:[0.05,0.3],punch:[0.05,0.3],body:[0.7,1],recoil:[0.05,0.4],grit:[0.01,0.25],shots:1,character:[0.1,1],modulation:[0.15,0.9]}}
    ];
    apply_params(params,checkLocked=false) {
        if(!params||typeof params!=='object')return;
        // Complete older snapshots need defaults for controls they never stored.
        // A partial edit must leave unrelated current controls untouched.
        const oldKeys=['masterVolume','seed','kind','duration','pitch','sweep','charge','punch','body','recoil','grit','shots'];
        if(oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['character','modulation']) if(!Object.prototype.hasOwnProperty.call(params,key)) {
                this.set_param(key,this.param_default(key),checkLocked);
            }
        }
        super.apply_params(params,checkLocked);
    }
    param_is_disabled(name){return name==='sweep' && [2,7].includes(this.params.kind);}
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='shots'&&!(checkLocked&&this.locked_params[name]))this.params.shots=Math.round(this.params.shots);
    }
}
