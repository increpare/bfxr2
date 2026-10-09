class Jinglr extends PresetSynth {
    name = 'Jinglr';
    canvas_bg_logo = 'img/logo_jinglr.png';
    tooltip = 'Little musical gestures for discoveries, victories, warnings and quiet moments.';
    static DSP = Jinglr_DSP;
    hide_params = ['masterVolume','phrase','instrument','instrumentSeed','seed'];
    header_properties = [];
    batching = false;

    param_info = [
        PresetSynth.common_params[0],
        ['Variation','A repeatable melody variation. Changing it makes a new unlocked phrase.','seed',50000/99999,0,1],
        ['Instrument seed','The five-digit character within this instrument family.','instrumentSeed',42731,0,99999],
        {type:'TEXT',name:'phrase',display_name:'Phrase',default_value:Jinglr_DSP.defaultPhrase,max_length:4096},
        {type:'BUTTONSELECT',name:'instrument',display_name:'Instrument',tooltip:'The voice playing each note.',
            default_value:0,columns:4,header:true,values:[['Pluck','A small string instrument.',0],['Bell','Sparkling, inharmonic chimes.',1],
                ['Chip','A bright arcade pulse.',2],['Flute','A soft breathy pipe.',3],
                ['Keys','Hammered, tine and electric keyboard tones.',4],['Reed','Woody and buzzy wind instruments.',5],
                ['FM','Glassy, metallic and rubbery digital voices.',6],['Strings','Soft bowed and shimmering ensemble tones.',7]]},
        {type:'BUTTONSELECT',name:'key',display_name:'Key',tooltip:'The root note of the phrase.',default_value:0,columns:6,
            values:['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'].map((name,index)=>[name,'Root note '+name,index])},
        {type:'BUTTONSELECT',name:'scale',display_name:'Scale',tooltip:'Notes stay within this scale when you change key.',default_value:0,columns:4,
            values:[['Major','Bright and settled.',0],['Minor','Somber and mysterious.',1],['Pentatonic','Five easygoing notes.',2],['Dorian','A gently hopeful minor scale.',3]]},
        {type:'BUTTONSELECT',name:'contour',display_name:'Contour',tooltip:'Choose a new shape for the unlocked phrase.',default_value:0,columns:5,
            values:[['Rise','Climb towards the last note.',0],['Fall','Settle downwards.',1],['Arch','Rise and return.',2],['Wander','A little melodic ramble.',3],['Call','Repeat a short call.',4]]},
        {type:'BUTTONSELECT',name:'rhythm',display_name:'Rhythm',tooltip:'Choose new note lengths for the unlocked phrase.',default_value:0,columns:4,
            values:[['Even','A steady sequence.',0],['Dotted','Long-short pairs.',1],['Skipping','Quick notes and pauses.',2],['Held','Room for each note to ring.',3]]},
        ['Notes','Number of notes in a newly generated phrase. Changing it makes a new unlocked phrase.','noteCount',4,2,12],
        ['Octave','The register of the root note.','octave',4,3,6],
        ['Tempo','Quarter-note beats per minute.','tempo',140,60,220],
        ['Swing','Delay every second note while preserving the length of each pair.','swing',0,0,0.6],
        ['Brightness','How much sparkle the instrument has.','brightness',0.55,0,1],
        ['Decay','How long each note holds and rings.','decay',0.45,0,1],
        ['Echo','Three soft musical repeats.','echo',0.12,0,0.8]
    ];

    recipes = [
        {name:'Confirm',id:'confirm',tip:'A quick, bright yes.',values:{instrument:[0,1,4,6],scale:0,contour:0,rhythm:0,noteCount:2,tempo:[200,220],octave:[4,5],brightness:[0.35,0.8],decay:[0.04,0.2],echo:0}},
        {name:'Message',id:'message',tip:'A small, soft arrival.',values:{instrument:[0,1,3,4],scale:2,contour:[0,4],rhythm:1,noteCount:2,tempo:[180,220],octave:[4,5],brightness:[0.15,0.55],decay:[0.06,0.24],echo:0}},
        {name:'Dismiss',id:'dismiss',tip:'A short downward reply.',values:{instrument:[0,2,4],scale:[0,2],contour:1,rhythm:0,noteCount:2,tempo:[195,220],octave:[3,4],brightness:[0.15,0.6],decay:[0.02,0.14],echo:0}},
        {name:'Denied',id:'denied',tip:'A compact, low refusal.',values:{instrument:[2,5,6],scale:1,contour:1,rhythm:1,noteCount:2,tempo:[200,220],octave:3,brightness:[0.2,0.6],decay:[0.01,0.12],echo:0}},
        {name:'Discovery',id:'discovery',tip:'An inquisitive rising sparkle.',values:{instrument:[0,1,4],scale:[0,2],key:[0,2,5,7,9],contour:0,rhythm:[0,1],noteCount:[4,7],tempo:[130,185],octave:[4,5],brightness:[0.5,0.9],decay:[0.3,0.65],echo:[0.1,0.3]}},
        {name:'Victory',id:'victory',tip:'A brisk, bright upward fanfare.',values:{instrument:[1,2,5],scale:0,key:[0,2,4,5,7],contour:0,rhythm:[0,1],noteCount:[5,9],tempo:[155,215],octave:[4,5],brightness:[0.7,1],decay:[0.35,0.6],echo:[0.1,0.3]}},
        {name:'Failure',id:'failure',tip:'A drooping little minor-key defeat.',values:{instrument:[0,2,7],scale:1,key:[0,2,5,7,9],contour:1,rhythm:[0,3],noteCount:[3,5],tempo:[80,120],octave:[3,4],brightness:[0.15,0.5],decay:[0.15,0.4],echo:[0,0.12]}},
        {name:'Secret',id:'secret',tip:'An elusive chime from somewhere nearby.',values:{instrument:[1,6],scale:[1,3],key:[1,3,6,8,10],contour:[2,3],rhythm:[1,2],noteCount:[4,7],tempo:[95,145],octave:[4,5],brightness:[0.4,0.85],decay:[0.55,0.85],echo:[0.3,0.55]}},
        {name:'Warning',id:'warning',tip:'An urgent repeated arcade call.',values:{instrument:[2,5],scale:1,key:[0,1,3,6,8],contour:4,rhythm:[0,2],noteCount:[4,8],tempo:[160,220],octave:[4,5],brightness:[0.7,1],decay:[0.05,0.25],echo:[0,0.08]}},
        {name:'Checkpoint',id:'checkpoint',tip:'A small reassuring arrival.',values:{instrument:[0,3,4],scale:[0,2],key:[0,2,5,7,9],contour:2,rhythm:0,noteCount:[3,5],tempo:[120,160],octave:[4,5],brightness:[0.3,0.65],decay:[0.35,0.65],echo:[0.05,0.2]}},
        {name:'Puzzle Solved',id:'puzzle_solved',tip:'A curious idea resolving into a bright finish.',values:{instrument:[0,1,6],scale:[0,2],key:[0,2,4,5,7,9],contour:0,rhythm:[1,2],noteCount:[6,10],tempo:[115,165],octave:[4,5],brightness:[0.45,0.8],decay:[0.45,0.7],echo:[0.18,0.35]}},
        {name:'Lullaby',id:'lullaby',tip:'A soft wandering tune with time to breathe.',values:{instrument:[0,3,7],scale:[0,2,3],key:[0,2,5,7,9],contour:[2,3],rhythm:3,noteCount:[4,7],tempo:[65,100],octave:[4,5],brightness:[0.05,0.35],decay:[0.65,0.95],echo:[0.12,0.3]}}
    ];

    constructor() { super(); this.initialize_presets(); }

    create_editor(tab,parent) { return new PhraseEditor(tab,parent); }

    static melody_seed(value) {
        return Math.round((Number.isFinite(value) ? SoundDSP.clamp(value,0,1) : 50000/99999)*99999)/99999;
    }

    set_param(name,value,checkLocked=false) {
        if (checkLocked && this.locked_param(name)) return;
        if (name==='phrase') value=JSON.stringify(Jinglr_DSP.phrase(value));
        if (name==='seed') value=Jinglr.melody_seed(value);
        if (['noteCount','octave','instrumentSeed'].includes(name)) value=Number.isFinite(value) ? Math.round(value) : value;
        super.set_param(name,value,checkLocked);
        if (!this.batching && ['noteCount','contour','rhythm','seed'].includes(name)) this.generate_phrase();
    }

    apply_params(params,checkLocked=false) {
        const previous=this.batching;
        this.batching=true;
        try {
            // Full snapshots from before instrument codes always start at the same voice.
            if (params && typeof params==='object' && ['phrase','seed','instrument'].every(name=>
                Object.prototype.hasOwnProperty.call(params,name)) &&
                !Object.prototype.hasOwnProperty.call(params,'instrumentSeed')) {
                this.set_param('instrumentSeed',42731,checkLocked);
            }
            super.apply_params(params,checkLocked);
        }
        finally { this.batching=previous; }
    }

    generate_recipe(id) {
        if (!this.recipes.some(recipe=>recipe.id===id)) return;
        this.reseed_sound(()=>super.generate_recipe(id));
    }

    reseed_sound(generate) {
        const locks=this.locked_params, batching=this.batching;
        const melody=this.params.seed, voice=this.params.instrumentSeed, phrase=this.params.phrase;
        // Presets replace the whole cue, including seeds held by the retired lock buttons.
        this.locked_params={...locks,phrase:false,seed:false,instrument:false,instrumentSeed:false};
        this.batching=true;
        try {
            generate();
            if (this.params.seed===melody) this.set_param('seed',((Math.round(melody*99999)+1)%100000)/99999);
            if (this.params.instrumentSeed===voice) this.set_param('instrumentSeed',(voice+1)%100000);
            this.generate_phrase();
            // Short two-note cues have few shapes; avoid immediately repeating one.
            for(let attempt=0;this.params.phrase===phrase && attempt<32;attempt++) {
                this.set_param('seed',((Math.round(this.params.seed*99999)+1)%100000)/99999);
                this.generate_phrase();
            }
        } finally {
            this.locked_params=locks;
            this.batching=batching;
        }
    }

    after_recipe() { this.generate_phrase(); this.generate_instrument(this.params.instrument); }

    generate_instrument(type) {
        this.set_param('instrument',type,true);
        // A repeat press always makes a different character, including under a fixed RNG.
        const step=1+Math.floor(Math.random()*99999);
        this.set_param('instrumentSeed',(this.params.instrumentSeed+step)%100000,true);
    }

    generate_phrase(freshSeed=false) {
        if (this.locked_param('phrase')) return;
        if (freshSeed) {
            const code=Math.round(this.params.seed*99999);
            const step=1+Math.floor(Math.random()*99999);
            super.set_param('seed',((code+step)%100000)/99999,true);
        }
        this.set_param('phrase',this.compose_phrase(),true);
    }

    melody_matches_seed() { return this.params.phrase===this.compose_phrase(); }

    compose_phrase(params=this.params) {
        const p=params, random=SoundDSP.rng(Jinglr.melody_seed(p.seed)), count=Math.round(p.noteCount);
        const span=4+Math.floor(random()*5), offset=Math.floor(random()*3)-1;
        const rhythms=[[0.5],[0.75,0.25],[0.25,0.5,0.25,0.75],[1,0.5,1,1.5]];
        let wander=offset;
        const notes=Array.from({length:count},(_,index)=>{
            const position=index/Math.max(1,count-1);
            const jitter=index===0 || index===count-1 ? 0 : Math.floor(random()*3)-1;
            let degree;
            switch (p.contour) {
                case 1: degree=offset+Math.round(span*(1-position))+jitter; break;
                case 2: degree=offset+Math.round(span*Math.sin(position*Math.PI))+jitter; break;
                case 3: wander+=Math.floor(random()*5)-2; degree=wander; break;
                case 4: degree=offset+(index%2 ? 3+Math.floor(random()*3) : 0); break;
                default: degree=offset+Math.round(span*position)+jitter;
            }
            let beats=rhythms[p.rhythm][index%rhythms[p.rhythm].length];
            if (index===count-1) beats=p.rhythm===3 ? 2 : 1;
            const rest=p.rhythm===2 && index>0 && index<count-1 && random()<0.18;
            return {degree:rest ? null : degree,beats};
        });
        return JSON.stringify(Jinglr_DSP.phrase(JSON.stringify(notes)));
    }

    randomize_params() {
        this.reseed_sound(()=>super.randomize_params());
    }

    mutate_params() {
        // A mutation gets a new visible code, so the resulting melody can be reconstructed.
        this.batching=true;
        try {
            super.mutate_params();
            const step=1+Math.floor(Math.random()*4999);
            const code=Math.round(this.params.seed*99999);
            const direction=Math.random()<0.5 ? -1 : 1;
            this.set_param('seed',((code+direction*step+100000)%100000)/99999,true);
        }
        finally { this.batching=false; }
        this.generate_phrase();
    }
}
