class Notifr extends PresetSynth {
    name='Notifr';
    tooltip='Compact messages, achievements, warnings and other semantic alerts.';
    static DSP=Notifr_DSP;
    hide_params=['masterVolume','tone'];
    param_info=[
        ...PresetSynth.common_params,
        ['Instrument Seed','The construction of the voice, independent of the alert pattern.','instrumentSeed',0.5,0,1],
        {type:'BUTTONSELECT',name:'tone',display_name:'Tone',tooltip:'The voice shared by the overlapping alert tones.',
            default_value:0,columns:4,values:[['Soft','Rounded electronic tones.',0],['Bell','Inharmonic bell partials.',1],
                ['Chime','Bright harmonic chimes.',2],['Buzz','Firm, buzzy alert tones.',3]]},
        ['Duration','Complete alert length, including its ring and echo, in seconds.','duration',0.55,0.08,3],
        ['Pitch','The root pitch of the alert.','pitch',0.55,0,1],
        ['Interval','The answering tone and overall rise or fall, in semitones.','interval',5,-12,12],
        ['Tension','Adds a close, unsettled interval to the tone group.','tension',0.08,0,1],
        ['Pulses','Number of compact tone groups.','pulses',2,1,8],
        ['Spacing','How much space is left between the groups.','spacing',0.3,0,0.85],
        ['Urgency','Accelerates repeated groups and adds an insistent tremble.','urgency',0.15,0,1],
        ['Softness','Rounds the attack and softens the upper partials.','softness',0.65,0,1],
        ['Ring','Lets the tones linger and overlap.','ring',0.3,0,1],
        ['Echo','Adds a small repeat inside the alert length.','echo',0.1,0,1]
    ];
    recipes=[
        {id:'message',name:'Message',tip:'A gentle pair of notes for a new message.',values:{tone:0,duration:[0.18,0.4],pitch:[0.48,0.64],interval:[3,5],tension:[0,0.04],pulses:2,spacing:[0.25,0.5],urgency:[0,0.12],softness:[0.7,1],ring:[0.15,0.4],echo:[0,0.12]}},
        {id:'quest_update',name:'Quest Update',tip:'A small ascending acknowledgment.',values:{tone:[0,2],duration:[0.35,0.7],pitch:[0.38,0.56],interval:[4,7],tension:[0,0.06],pulses:[2,3],spacing:[0.18,0.35],urgency:[0.08,0.22],softness:[0.45,0.75],ring:[0.2,0.48],echo:[0.03,0.18]}},
        {id:'objective_done',name:'Objective Done',tip:'A clear rising confirmation.',values:{tone:2,duration:[0.3,0.68],pitch:[0.46,0.68],interval:[7,12],tension:[0,0.03],pulses:2,spacing:[0.18,0.4],urgency:[0,0.18],softness:[0.35,0.65],ring:[0.35,0.65],echo:[0.08,0.25]}},
        {id:'achievement',name:'Achievement',tip:'A brief bright celebration of overlapping chimes.',values:{tone:[1,2],duration:[0.65,1.3],pitch:[0.4,0.6],interval:[7,12],tension:[0,0.05],pulses:[3,4],spacing:[0.05,0.2],urgency:[0.08,0.28],softness:[0.12,0.4],ring:[0.65,1],echo:[0.18,0.42]}},
        {id:'low_health',name:'Low Health',tip:'An insistent low pulse with a tense edge.',values:{tone:3,duration:[0.45,0.95],pitch:[0.18,0.32],interval:[-2,1],tension:[0.65,0.95],pulses:[3,5],spacing:[0.48,0.7],urgency:[0.65,1],softness:[0.3,0.6],ring:[0,0.1],echo:[0,0.08]}},
        {id:'warning',name:'Warning',tip:'A sharp repeated warning with unsettled intervals.',values:{tone:[2,3],duration:[0.35,0.75],pitch:[0.48,0.7],interval:[-1,2],tension:[0.5,0.85],pulses:[2,4],spacing:[0.4,0.65],urgency:[0.55,0.9],softness:[0.08,0.3],ring:[0.02,0.15],echo:[0,0.12]}},
        {id:'denied',name:'Denied',tip:'A blunt falling answer for an unavailable action.',values:{tone:3,duration:[0.15,0.38],pitch:[0.32,0.5],interval:[-9,-4],tension:[0.35,0.7],pulses:2,spacing:[0.15,0.35],urgency:[0.1,0.35],softness:[0.25,0.55],ring:[0,0.12],echo:[0,0.08]}},
        {id:'connected',name:'Connected',tip:'Two soft upward tones settling into place.',values:{tone:0,duration:[0.22,0.48],pitch:[0.4,0.59],interval:[5,9],tension:[0,0.04],pulses:2,spacing:[0.1,0.32],urgency:[0,0.1],softness:[0.72,1],ring:[0.35,0.6],echo:[0.02,0.14]}}
    ];
    constructor(){super();this.initialize_presets();}
    reseed_instrument(tone=this.params.tone) {
        this.set_param('tone',tone,true);
        this.set_param('instrumentSeed',Math.random(),true);
    }
    after_recipe() { this.reseed_instrument(); }
    create_editor(tab,parent) { return new NotifrInstrumentEditor(tab,parent); }
    apply_params(params,checkLocked=false) {
        if(params && !Object.prototype.hasOwnProperty.call(params,'instrumentSeed') &&
            ['tone','duration','pitch','pulses','seed'].every(key=>Object.prototype.hasOwnProperty.call(params,key)))
            this.set_param('instrumentSeed',0.5,checkLocked);
        super.apply_params(params,checkLocked);
    }
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='pulses'&&!(checkLocked&&this.locked_params[name])) this.params.pulses=Math.round(this.params.pulses);
    }
}

class NotifrInstrumentEditor {
    constructor(tab,parent) {
        this.tab=tab;this.buttons=[];
        const root=document.createElement('div');root.className='phrase-editor';
        const heading=document.createElement('div');heading.className='phrase-section-label';
        heading.textContent='Reseed instrument';
        heading.appendChild(tab.generate_lock_button('tone'));root.appendChild(heading);
        const row=document.createElement('div');row.className='phrase-instruments';root.appendChild(row);
        for(const [name,tip,tone] of tab.synth.get_param_info('tone').values) {
            const button=document.createElement('button');button.textContent=name;button.title=tip;
            button.addEventListener('click',()=>{tab.synth.reseed_instrument(tone);tab.parameter_changed();tab.update_ui_params();this.update();});
            row.appendChild(button);this.buttons.push({button,tone});
        }
        parent.appendChild(root);this.update();
    }
    update() {
        const s=this.tab.synth;
        for(const {button,tone} of this.buttons){
            button.setAttribute('aria-pressed',String(s.params.tone===tone));
            button.disabled=s.locked_param('instrumentSeed')&&(s.locked_param('tone')||s.params.tone===tone);
        }
    }
}
