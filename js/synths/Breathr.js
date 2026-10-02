class Breathr extends PresetSynth {
    name='Breathr';
    tooltip='Breathing, exertion and air moving through impossible lungs.';
    static DSP=Breathr_DSP;
    param_info=[...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'source',display_name:'Airway',tooltip:'Airflow texture and airway motion.',default_value:0,columns:3,
            values:[['Airflow','Directional turbulent air through a changing mouth and throat.',0],['Retro','Stepped breath envelopes and coarse game noise.',1],['Snore','An obstructed airway fluttering under pressure.',2]]},
        ['Duration','Complete breathing sequence, in seconds.','duration',2.7,0.15,5],
        ['Breaths','Number of inhale and exhale cycles.','cycles',1,1,10],
        ['Exertion','Force and turbulence of the airflow.','effort',0.55,0,1],
        ['Inhale Share','Portion of moving air spent inhaling.','inhale',0.42,0.1,0.9],
        ['Hold','Pause between inhaling and exhaling.','hold',0.04,0,0.7],
        ['Throat Size','From narrow high airways to a deep chest.','throat',0.5,0,1],
        ['Rasp','Airway roughness; in Snore mode, vibrating soft tissue.','rasp',0.1,0,1],
        ['Tremble','Uneven, shivering airflow.','flutter',0.15,0,1],
        ['Enclosure','Short reflections around a mask, helmet or cave.','space',0.1,0,1]
    ];
    recipes=[
        {name:'Snore',id:'snore',tip:'A soft snuffle, a rattling inhale, a sleepy release.',values:{source:2,duration:[2.1,3.8],cycles:1,effort:[0.18,0.48],inhale:[0.45,0.65],hold:[0.08,0.22],throat:[0.4,0.78],rasp:[0.55,0.95],flutter:[0.28,0.65],space:[0,0.16]}},
        {name:'Tired Runner',id:'tired_runner',tip:'Fast, uneven breaths after a sprint.',values:{source:[0,1],duration:[1.5,2.8],cycles:[3,6],effort:[0.65,1],inhale:[0.3,0.46],hold:[0,0.08],throat:[0.25,0.55],rasp:[0.2,0.5],flutter:[0.25,0.6],space:[0,0.12]}},
        {name:'Deep Breath',id:'deep_breath',tip:'One full, deliberate breath.',values:{source:0,duration:[2.5,4.8],cycles:1,effort:[0.2,0.5],inhale:[0.42,0.58],hold:[0.02,0.12],throat:[0.4,0.75],rasp:[0,0.12],flutter:[0,0.1],space:[0,0.1]}},
        {name:'Held Breath',id:'held_breath',tip:'Air drawn in, held, then slowly released.',values:{source:0,duration:[2.4,4.8],cycles:1,effort:[0.2,0.45],inhale:[0.23,0.45],hold:[0.42,0.68],throat:[0.25,0.6],rasp:[0.05,0.2],flutter:[0.05,0.3],space:[0,0.08]}},
        {name:'Gasp',id:'gasp',tip:'A sharp intake and shaky release.',values:{source:[0,1],duration:[0.25,0.7],cycles:1,effort:[0.8,1],inhale:[0.16,0.3],hold:[0.1,0.28],throat:[0.04,0.3],rasp:[0.25,0.6],flutter:[0.25,0.65],space:[0,0.18]}},
        {name:'Sleeping Beast',id:'sleeping_beast',tip:'Huge sleepy lungs with a rough throat.',values:{source:2,duration:[2.8,4.9],cycles:[1,2],effort:[0.2,0.5],inhale:[0.3,0.43],hold:[0.06,0.2],throat:[0.8,1],rasp:[0.65,1],flutter:[0.1,0.4],space:[0.15,0.4]}},
        {name:'Diver',id:'diver',tip:'Measured breathing through a resonant regulator.',values:{source:[0,1],duration:[1.5,3.3],cycles:[2,3],effort:[0.55,0.85],inhale:[0.35,0.5],hold:[0.08,0.2],throat:[0.15,0.4],rasp:[0,0.12],flutter:[0.05,0.2],space:[0.4,0.7]}},
        {name:'Helmet',id:'helmet',tip:'Close, enclosed respirator airflow.',values:{source:[0,1],duration:[1.5,3.5],cycles:[2,4],effort:[0.4,0.75],inhale:[0.36,0.5],hold:[0.06,0.18],throat:[0.45,0.75],rasp:[0.25,0.55],flutter:[0.03,0.16],space:[0.65,1]}},
        {name:'Ghost Breath',id:'ghost_breath',tip:'A cold, trembling exhalation in a hollow space.',values:{source:[1,2],duration:[2.2,4.5],cycles:[1,2],effort:[0.12,0.4],inhale:[0.1,0.25],hold:[0.02,0.12],throat:[0.6,0.9],rasp:[0.4,0.8],flutter:[0.6,1],space:[0.55,0.95]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        if(!params||typeof params!=='object')return;
        const defaults=this.default_params();
        const legacy=!Object.prototype.hasOwnProperty.call(params,'source')&&
            Object.keys(defaults).filter(key=>key!=='source').every(key=>Object.prototype.hasOwnProperty.call(params,key));
        super.apply_params(params,checkLocked);
        // Complete old saves predate the selector; partial edits retain the current choice.
        if(legacy)this.set_param('source',defaults.source,checkLocked);
    }
    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='cycles'&&!(checkLocked&&this.locked_params[name]))this.params.cycles=Math.round(this.params.cycles);}
}
