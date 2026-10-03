class Pluckr extends PresetSynth {
    name='Pluckr';
    tooltip='Plucked strings, sympathetic bridges and small magical instruments.';
    static DSP=Pluckr_DSP;
    param_info=[...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'material',display_name:'String',tooltip:'String material changes the excitation, loss and wave dispersion.',default_value:0,columns:3,
            values:[['Nylon','A smooth, flexible string with a rounded ring.',0],['Steel','Bright wire with stiff, persistent upper partials.',1],['Gut','A soft fibre string with warm, uneven loss.',2],
                ['Rubber','A thick elastic string that rapidly absorbs vibration.',3],['Glass','An impossible rigid filament with dispersing partials.',4]]},
        ['Duration','Total string ring, in seconds.','duration',1.8,0.15,5],
        ['Pitch','Root string tuning.','pitch',0.5,0,1],
        ['Strings','Strings in the open chord.','strings',3,1,8],
        ['Damping','How quickly vibration is absorbed.','damping',0.25,0,1],
        ['Brightness','Excitation and feedback-loop high frequencies.','brightness',0.6,0,1],
        ['Pluck Point','Where along the string the finger pulls.','pluck',0.3,0,1],
        ['Coupling','Energy exchanged through a common bridge.','coupling',0.15,0,1],
        ['Strum','Delay between successive string releases.','strum',0.2,0,1],
        ['Tremolo Volume','Depth of the pulsing string volume; does not change pitch.','tremolo',0,0,1],
        ['Vibrato Pitch','Depth of the gentle pitch wobble, up to about three quarters of a semitone.','vibrato',0,0,1],
        ['Motion Speed','Pulses per second for both tremolo and vibrato.','tremoloRate',4,0.2,12],
        ['Loose Tuning','Independent imperfections in string tuning.','inharmonic',0.05,0,1]
    ];
    recipes=[
        {name:'Coin',id:'coin',verb:'coin',tip:'A bright little tine.',values:{material:[1,4],duration:[0.3,0.7],pitch:[0.6,0.9],strings:[1,2],damping:[0.3,0.6],brightness:[0.6,1],pluck:[0.1,0.4],coupling:[0,0.2],strum:[0.05,0.2],inharmonic:[0,0.1]}},
        {name:'Confirm',id:'confirm',verb:'confirm',tip:'A compact upward strum.',values:{material:[0,1,4],duration:[0.3,0.7],pitch:[0.45,0.75],strings:[2,3],damping:[0.3,0.55],brightness:[0.45,0.8],pluck:[0.2,0.55],coupling:[0.1,0.4],strum:[0.3,0.6],inharmonic:[0,0.1]}},
        {name:'Unlock',id:'unlock',verb:'unlock',tip:'A cascade of sympathetic glass strings.',values:{material:4,duration:[0.8,1.8],pitch:[0.5,0.8],strings:[4,7],damping:[0.1,0.3],brightness:[0.35,0.65],pluck:[0.2,0.6],coupling:[0.5,1],strum:[0.5,0.9],inharmonic:[0.05,0.25]}},
        {name:'Heal',id:'heal',verb:'heal',tip:'A soft open chord.',values:{material:[0,2],duration:[0.8,1.8],pitch:[0.4,0.7],strings:[3,5],damping:[0.1,0.3],brightness:[0.2,0.5],pluck:[0.2,0.6],coupling:[0.1,0.4],strum:[0.3,0.6],inharmonic:[0,0.08]}},
        {name:'Jump',id:'jump',verb:'jump',tip:'One short muted bass note.',values:{material:[0,3],duration:[0.15,0.4],pitch:[0.1,0.35],strings:1,damping:[0.5,0.85],brightness:[0.2,0.5],pluck:[0.3,0.6],coupling:0,strum:0,inharmonic:[0,0.1]}},
        {name:'Lose',id:'lose',verb:'lose',tip:'A loose, mismatched chord dying unevenly.',values:{material:[2,3],duration:[0.7,1.4],pitch:[0.1,0.4],strings:[2,4],damping:[0.15,0.4],brightness:[0.4,0.8],pluck:[0.1,0.8],coupling:[0.4,0.9],strum:[0.3,0.7],inharmonic:[0.7,1]}},
        {name:'Blip',id:'blip',verb:'blip',tip:'A tiny damped pluck.',values:{material:[0,1],duration:[0.08,0.18],pitch:[0.5,0.85],strings:1,damping:[0.7,0.95],brightness:[0.4,0.8],pluck:[0.2,0.5],coupling:0,strum:0,inharmonic:[0,0.05]}},
        {name:'Harp',id:'harp',tip:'A clear open chord with a long ring.',values:{material:[0,2],duration:[2,4],pitch:[0.35,0.65],strings:[3,6],damping:[0.05,0.25],brightness:[0.25,0.55],pluck:[0.2,0.6],coupling:[0.1,0.35],strum:[0.3,0.65],inharmonic:[0.01,0.08]}},
        {name:'Kalimba',id:'kalimba',tip:'A small bright thumb-piano tine.',values:{material:[1,4],duration:[0.7,1.6],pitch:[0.5,0.8],strings:[1,2],damping:[0.25,0.5],brightness:[0.55,0.9],pluck:[0.1,0.4],coupling:[0.05,0.2],strum:[0.05,0.2],inharmonic:[0.02,0.14]}},
        {name:'Muted Guitar',id:'muted_guitar',tip:'A short palm-muted chord.',values:{material:[0,2,3],duration:[0.4,0.9],pitch:[0.2,0.48],strings:[3,6],damping:[0.7,0.94],brightness:[0.12,0.38],pluck:[0.25,0.65],coupling:[0.15,0.45],strum:[0.08,0.22],inharmonic:[0.03,0.15]}},
        {name:'Metal String',id:'metal_string',tip:'A hard, bright wire with a persistent ring.',values:{material:1,duration:[1.4,3.5],pitch:[0.3,0.7],strings:[1,3],damping:[0.02,0.18],brightness:[0.8,1],pluck:[0.02,0.2],coupling:[0.1,0.4],strum:[0.04,0.2],inharmonic:[0.1,0.3]}},
        {name:'Magic Harp',id:'magic_harp',tip:'A cascade of high sympathetic strings.',values:{material:4,duration:[2,4.5],pitch:[0.5,0.8],strings:[5,8],damping:[0.02,0.16],brightness:[0.35,0.65],pluck:[0.2,0.65],coupling:[0.6,1],strum:[0.65,1],inharmonic:[0.1,0.3]}},
        {name:'Bass Pluck',id:'bass_pluck',tip:'One thick string with a round body.',values:{material:[0,2,3],duration:[0.8,2.4],pitch:[0.02,0.2],strings:1,damping:[0.15,0.4],brightness:[0.08,0.3],pluck:[0.3,0.6],coupling:[0.05,0.25],strum:0,inharmonic:[0.01,0.12]}},
        {name:'Broken String',id:'broken_string',tip:'A loose, mismatched chord dying unevenly.',values:{material:[2,3],duration:[0.6,1.5],pitch:[0.12,0.5],strings:[2,5],damping:[0.45,0.8],brightness:[0.5,0.95],pluck:[0.02,0.9],coupling:[0.4,0.9],strum:[0.2,0.7],inharmonic:[0.8,1]}},
        {name:'Quest Pluck',id:'quest_pluck',tip:'A compact upward chord for a discovered clue.',values:{material:[0,1,4],duration:[0.8,1.8],pitch:[0.45,0.7],strings:[3,5],damping:[0.15,0.35],brightness:[0.45,0.8],pluck:[0.2,0.55],coupling:[0.2,0.5],strum:[0.4,0.7],inharmonic:[0.02,0.12]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        if(!params||typeof params!=='object')return;
        const defaults=this.default_params();
        const complete=['duration','pitch','strings','damping','brightness','pluck','coupling','strum','inharmonic','seed','masterVolume'].every(key=>Object.prototype.hasOwnProperty.call(params,key));
        if(complete)for(const key of ['material','tremolo','tremoloRate','vibrato']) {
            if(!Object.prototype.hasOwnProperty.call(params,key))this.set_param(key,defaults[key],checkLocked);
        }
        // Retired Gravity snapshots become glass strings with explicit modulation.
        const migrated=params.material===5 ? {...params,material:4,tremolo:params.tremolo??0.35,tremoloRate:params.tremoloRate??1.7} : params;
        super.apply_params(migrated,checkLocked);
    }

    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='strings'&&!(checkLocked&&this.locked_params[name]))this.params.strings=Math.round(this.params.strings);}
}
