class Breathr extends PresetSynth {
    name='Breathr';
    tooltip='Breathing, exertion and air moving through impossible lungs.';
    static DSP=Breathr_DSP;
    param_info=[...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'source',display_name:'Airway',tooltip:'Airflow texture and airway motion.',default_value:0,columns:3,
            values:[['Airflow','Directional turbulent air through a changing mouth and throat.',0],['Retro','Stepped breath envelopes and coarse game noise.',1],['Snore','An obstructed airway fluttering under pressure.',2]]},
        {type:'BUTTONSELECT',name:'mode',display_name:'Breath',tooltip:'One intake or release, or a complete breathing cycle.',default_value:0,columns:2,
            values:[['Single','One breath; Direction blends its inward and outward character.',0],['Cycle','Inhale, hold and exhale, with optional repeated breaths.',1]]},
        ['Duration','Length of the breath or complete sequence, in seconds.','duration',0.65,0.15,5],
        ['Direction','From bright inward air (−1) to a soft outward release (+1).','direction',1,-1,1],
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
        {name:'Hurt',id:'hurt',verb:'hurt',tip:'A sharp, shaky intake of pain.',values:{mode:0,source:[0,1],direction:[-1,-0.7],duration:[0.15,0.4],cycles:1,effort:[0.7,1],inhale:[0.16,0.3],hold:[0.1,0.28],throat:[0.05,0.4],rasp:[0.2,0.6],flutter:[0.2,0.6],space:[0,0.15]}},
        {name:'Dash',id:'dash',verb:'dash',tip:'A short, forceful exhale of effort.',values:{mode:0,source:0,direction:[0.6,1],duration:[0.15,0.32],effort:[0.8,1],throat:[0.3,0.7],rasp:[0.05,0.3],flutter:[0.05,0.3],space:[0,0.1]}},
        {name:'Lose',id:'lose',verb:'lose',tip:'A weary, fading sigh.',values:{mode:0,source:0,direction:[0.8,1],duration:[0.6,1.4],effort:[0.25,0.5],throat:[0.45,0.8],rasp:[0.08,0.3],flutter:[0.12,0.4],space:[0,0.15]}},
        {name:'Roar',id:'roar',verb:'roar',tip:'A huge rough throat pushing air.',values:{mode:0,source:[0,2],direction:[0.5,1],duration:[0.5,1.4],effort:[0.7,1],throat:[0.8,1],rasp:[0.5,1],flutter:[0.1,0.4],space:[0.1,0.4]}},
        {name:'Inhale',id:'inhale',tip:'One short intake of air.',values:{mode:0,source:0,direction:[-1,-0.7],duration:[0.3,0.8],effort:[0.25,0.65],throat:[0.25,0.65],rasp:[0,0.16],flutter:[0.03,0.2],space:[0,0.12]}},
        {name:'Exhale',id:'exhale',tip:'One soft outward breath.',values:{mode:0,source:0,direction:[0.7,1],duration:[0.35,0.95],effort:[0.2,0.6],throat:[0.35,0.75],rasp:[0,0.15],flutter:[0.02,0.18],space:[0,0.12]}},
        {name:'Sigh',id:'sigh',tip:'A weary, gently fading release.',values:{mode:0,source:0,direction:[0.8,1],duration:[0.65,1.6],effort:[0.25,0.5],throat:[0.45,0.8],rasp:[0.08,0.3],flutter:[0.12,0.4],space:[0,0.15]}},
        {name:'Snore',id:'snore',tip:'One short rattling intake through a sleepy airway.',values:{mode:0,source:2,direction:[-1,-0.55],duration:[0.55,1.3],cycles:1,effort:[0.18,0.48],inhale:[0.45,0.65],hold:[0.08,0.22],throat:[0.4,0.78],rasp:[0.55,0.95],flutter:[0.28,0.65],space:[0,0.16]}},
        {name:'Tired Runner',id:'tired_runner',tip:'Fast, uneven breaths after a sprint.',values:{mode:1,source:[0,1],duration:[1.5,2.8],cycles:[3,6],effort:[0.65,1],inhale:[0.3,0.46],hold:[0,0.08],throat:[0.25,0.55],rasp:[0.2,0.5],flutter:[0.25,0.6],space:[0,0.12]}},
        {name:'Deep Breath',id:'deep_breath',tip:'One full, deliberate breath.',values:{mode:1,source:0,duration:[2.5,4.8],cycles:1,effort:[0.2,0.5],inhale:[0.42,0.58],hold:[0.02,0.12],throat:[0.4,0.75],rasp:[0,0.12],flutter:[0,0.1],space:[0,0.1]}},
        {name:'Held Breath',id:'held_breath',tip:'Air drawn in, held, then slowly released.',values:{mode:1,source:0,duration:[2.4,4.8],cycles:1,effort:[0.2,0.45],inhale:[0.23,0.45],hold:[0.42,0.68],throat:[0.25,0.6],rasp:[0.05,0.2],flutter:[0.05,0.3],space:[0,0.08]}},
        {name:'Gasp',id:'gasp',tip:'A single sharp, shaky intake.',values:{mode:0,source:[0,1],direction:[-1,-0.8],duration:[0.15,0.4],cycles:1,effort:[0.8,1],inhale:[0.16,0.3],hold:[0.1,0.28],throat:[0.04,0.3],rasp:[0.25,0.6],flutter:[0.25,0.65],space:[0,0.18]}},
        {name:'Sleeping Beast',id:'sleeping_beast',tip:'Huge sleepy lungs with a rough throat.',values:{mode:1,source:2,duration:[2.8,4.9],cycles:[1,2],effort:[0.2,0.5],inhale:[0.3,0.43],hold:[0.06,0.2],throat:[0.8,1],rasp:[0.65,1],flutter:[0.1,0.4],space:[0.15,0.4]}},
        {name:'Diver',id:'diver',tip:'Measured breathing through a resonant regulator.',values:{mode:1,source:[0,1],duration:[1.5,3.3],cycles:[2,3],effort:[0.55,0.85],inhale:[0.35,0.5],hold:[0.08,0.2],throat:[0.15,0.4],rasp:[0,0.12],flutter:[0.05,0.2],space:[0.4,0.7]}},
        {name:'Helmet',id:'helmet',tip:'Close, enclosed respirator airflow.',values:{mode:1,source:[0,1],duration:[1.5,3.5],cycles:[2,4],effort:[0.4,0.75],inhale:[0.36,0.5],hold:[0.06,0.18],throat:[0.45,0.75],rasp:[0.25,0.55],flutter:[0.03,0.16],space:[0.65,1]}},
        {name:'Ghost Breath',id:'ghost_breath',tip:'A cold, trembling exhalation in a hollow space.',values:{mode:1,source:[1,2],duration:[2.2,4.5],cycles:[1,2],effort:[0.12,0.4],inhale:[0.1,0.25],hold:[0.02,0.12],throat:[0.6,0.9],rasp:[0.4,0.8],flutter:[0.6,1],space:[0.55,0.95]}}
    ];
    constructor(){super();this.initialize_presets();}
    param_is_hidden(name){
        return this.params.mode===0?['cycles','inhale','hold'].includes(name):name==='direction';
    }
    create_random_template(){
        const singles=this.recipes.filter(recipe=>recipe.values.mode===0);
        const recipe=singles[Math.floor(Math.random()*singles.length)];
        this.generate_recipe(recipe.id);
        return [recipe.name.replace(/[^a-zA-Z0-9]/g,''),this.params];
    }
    apply_params(params,checkLocked=false){
        if(!params||typeof params!=='object')return;
        const defaults=this.default_params();
        const complete=['duration','cycles','effort','inhale','hold','throat','rasp','flutter','space','seed','masterVolume'].every(key=>Object.prototype.hasOwnProperty.call(params,key));
        super.apply_params(params,checkLocked);
        // Complete old saves predate the selector; partial edits retain the current choice.
        if(complete){
            if(!Object.prototype.hasOwnProperty.call(params,'source'))this.set_param('source',defaults.source,checkLocked);
            if(!Object.prototype.hasOwnProperty.call(params,'mode'))this.set_param('mode',1,checkLocked);
            if(!Object.prototype.hasOwnProperty.call(params,'direction'))this.set_param('direction',defaults.direction,checkLocked);
        }
    }
    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='cycles'&&!(checkLocked&&this.locked_params[name]))this.params.cycles=Math.round(this.params.cycles);}
}
