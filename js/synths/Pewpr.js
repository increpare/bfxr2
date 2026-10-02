class Pewpr extends PresetSynth {
    name='Pewpr';
    tooltip='Charged weapons, energy bolts and mechanical recoil.';
    static DSP=Pewpr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'kind',display_name:'Core',tooltip:'The firing body of the weapon.',default_value:0,columns:4,
            values:[['Laser','Clean harmonic energy.',0],['Plasma','Unstable modulated energy.',1],['Slug','A noisy physical projectile.',2],['Crystal','Cold, inharmonic energy.',3]]},
        ['Duration','Seconds for the complete firing sequence.','duration',0.7,0.12,5],
        ['Pitch','The carrier frequency of each shot.','pitch',0.55,0,1],
        ['Sweep','Falling bolts to rising ricochets.','sweep',-0.65,-1,1],
        ['Charge','Build up energy before the first shot.','charge',0,0,1],
        ['Punch','The sharp initial firing transient.','punch',0.65,0,1],
        ['Body','Energy and sustain after firing.','body',0.45,0,1],
        ['Recoil','A low kick after the main firing body.','recoil',0.2,0,1],
        ['Grit','Add rough exhaust and projectile noise.','grit',0.1,0,1],
        ['Shots','Number of shots in a burst.','shots',1,1,8]
    ];
    recipes=[
        {name:'Laser Pistol',id:'laser_pistol',tip:'A short, clean falling bolt.',values:{kind:0,duration:[0.2,0.55],pitch:[0.55,0.8],sweep:[-0.95,-0.55],charge:[0,0.06],punch:[0.55,0.9],body:[0.15,0.4],recoil:[0.05,0.3],grit:[0,0.08],shots:1}},
        {name:'Plasma Rifle',id:'plasma_rifle',tip:'A burst of unstable energy packets.',values:{kind:1,duration:[0.55,1.3],pitch:[0.3,0.6],sweep:[-0.7,-0.2],charge:[0,0.12],punch:[0.4,0.75],body:[0.4,0.75],recoil:[0.15,0.5],grit:[0.12,0.35],shots:[2,5]}},
        {name:'Railgun',id:'railgun',tip:'A brief capacitor whine and powerful discharge.',values:{kind:0,duration:[0.8,1.8],pitch:[0.55,0.85],sweep:[-1,-0.7],charge:[0.3,0.65],punch:[0.85,1],body:[0.1,0.35],recoil:[0.65,1],grit:[0.3,0.7],shots:1}},
        {name:'Blaster',id:'blaster',tip:'A chunky, low energy projectile.',values:{kind:1,duration:[0.3,0.75],pitch:[0.25,0.55],sweep:[-0.9,-0.4],charge:[0,0.08],punch:[0.65,1],body:[0.5,0.8],recoil:[0.4,0.8],grit:[0.1,0.3],shots:1}},
        {name:'Shotgun',id:'shotgun',tip:'A noisy projectile blast and heavy recoil.',values:{kind:2,duration:[0.35,0.8],pitch:[0.15,0.4],sweep:[-0.8,-0.3],charge:[0,0.02],punch:[0.85,1],body:[0.2,0.45],recoil:[0.75,1],grit:[0.7,1],shots:1}},
        {name:'Ricochet',id:'ricochet',tip:'A bright projectile singing away.',values:{kind:3,duration:[0.35,0.95],pitch:[0.5,0.8],sweep:[0.5,1],charge:[0,0.05],punch:[0.45,0.8],body:[0.25,0.6],recoil:[0,0.12],grit:[0.05,0.2],shots:[1,2]}},
        {name:'Charge Shot',id:'charge_shot',tip:'A long rising charge followed by a heavy bolt.',values:{kind:1,duration:[1.3,2.8],pitch:[0.3,0.65],sweep:[-1,-0.45],charge:[0.75,1],punch:[0.75,1],body:[0.55,0.9],recoil:[0.6,1],grit:[0.1,0.35],shots:1}},
        {name:'Freeze Ray',id:'freeze_ray',tip:'A cold, crystalline stream of pulses.',values:{kind:3,duration:[0.8,1.8],pitch:[0.55,0.85],sweep:[-0.1,0.35],charge:[0.05,0.25],punch:[0.1,0.3],body:[0.7,1],recoil:[0,0.15],grit:[0.05,0.2],shots:[3,7]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='shots'&&!(checkLocked&&this.locked_params[name]))this.params.shots=Math.round(this.params.shots);
    }
}
