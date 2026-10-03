class Mixr extends PresetSynth {
    name = 'Mixr';
    tooltip = 'Two sounds together.';
    canvas_bg_logo = "img/logo_mixr.png";
    static DSP = Mixr_DSP;
    hide_params = ['masterVolume', 'seed', 'sources'];
    param_info = [
        ...PresetSynth.common_params,
        ['Balance', 'Balance between the two sounds.', 'balance', 0.5, 0, 1],
        {type:'BUTTONSELECT', name:'align', display_name:'Align', tooltip:'Where B sits in time relative to A.', default_value:0, columns:3,
            values:[['Start','Both sounds begin together.',0],['Peak','The loudest moments of A and B coincide.',1],['Tail','B begins as A has mostly decayed.',2]]},
        ['Offset', 'Extra delay for B, in seconds. Negative values move B earlier.', 'offset', 0, -1, 1],
        {type:'TEXT', name:'sources', default_value:'[]', max_length:60000}
    ];
    static retired = ['Chattr','Weathr','Tappr','Notifr','Tickr','Holor','Pewpr','Rollr','Pulser','Rumblr'];
    // Subclasses that may use retired engines as hidden ingredients set this to true.
    static includeRetired = false;
    recipes = [

        //GOOD
        {id:'clockwork_familiar',name:'Clockwork Aviary',pair:['Machinr','Birdr'],balance:[0.31,0.49],tip:'Machinr × Birdr.'},

        //OK
        {id:'crystal_prize',name:'Treasure Box',pair:['Jinglr','Clonkr'],balance:[0.5,0.68],tip:'Jinglr × Clonkr.'},
        {id:'cyber_bird',name:'Cyber Bird',pair:['Birdr','Bfxr'],balance:[0.37,0.55],tip:'Birdr × Bfxr.'},
        {id:'goo_machine',name:'Wetware',pair:['Squishr','Machinr'],balance:[0.44,0.62],tip:'Squishr × Machinr.'},
        {id:'alien_beacon',name:'Alien Broadcast',pair:['Signlr','Choirr'],balance:[0.44,0.62],tip:'Signlr × Choirr.'},

        {id:'garden_lute',name:'Garden Lute',pair:['Pluckr','Crittr'],balance:[0.11,0.29],tip:'Pluckr × Crittr.'},
        {id:'reality_error',name:'Reality Error',pair:['Riftr','Glitchr'],balance:[0.37,0.55],tip:'Sonar × Glitches.'},
        {id:'soft_landing',name:'Goo Collision',pair:['Bouncr','Squishr'],balance:[0.33,0.51],tip:'Bonks × Squishy.'},

        {id:'spark_impact',name:'Live Wire',pair:['Clonkr','Zappr'],balance:[0.52,0.7],tip:'Clonkr × Zappr.'},
        {id:'shockwave',name:'Shockwaves',pair:['Boomr','Breathr'],balance:[0.2,0.5],tip:'Boomr × Breathr.'},
        {id:'haunted_hardware',name:'Brain Zaps',pair:['Clonkr','Glitchr'],balance:[0.5,0.68],tip:'Clonkr × Glitchr.'},


        //BAD

        {id:'haunted',name:'Otherworld',pair:['Choirr','Riftr'],balance:[0.5,0.68],tip:'Choirr × Riftr.'},
        {id:'spell_hit',name:'Shatterstorm',pair:['Whooshr','Fractr'],balance:[0.57,0.75],tip:'Whooshr × Fractr.'},
        {id:'heavy_magic',name:'Thunderworks',pair:['Boomr','Zappr'],balance:[0.26,0.44],tip:'Boomr × Zappr.'},
        {id:'phase_step',name:'Phase Shift',pair:['Whooshr','Riftr'],balance:[0.38,0.56],tip:'Whooshr × Riftr.'},
        {id:'hatchling',name:'Monster Hatchery',pair:['Fractr','Crittr'],balance:[0.21,0.39],tip:'Fractr × Crittr.'},
        {id:'sacred_treasure',name:'Arcane Reward',pair:['Jinglr','Choirr'],balance:[0.43,0.61],tip:'Jinglr × Choirr.'},
        {id:'pocket_rattle',name:'Pocket Rattle',pair:['Rustlr','Clonkr'],balance:[0.12,0.3],tip:'Rustlr × Clonkr.'},
        {id:'demolition',name:'Demolition',pair:['Fractr','Boomr'],balance:[0.37,0.55],tip:'Fractr × Boomr.'}
    ].map(recipe => ({...recipe, tip:recipe.pair.map(synth_display_name).join(' × ')+'.', values:{balance:recipe.balance}}));
    constructor() { super(); this.initialize_presets(); }
    create_editor(tab,parent) { return new MixEditor(tab,parent); }
    create_random_template() { return super.create_random_template(); }
    get_sources() { return JSON.parse(this.params.sources); }

    static templates_for(synth, includeRetired = this.includeRetired) {
        if (!synth || (!includeRetired && Mixr.retired.includes(synth.name))) return [];
        // Hidden generators are ingredients without a button, such as Bfxr's reference templates.
        const hidden = (synth.hidden_generators || []).map(name => [name.replace(/^generate_/, ''), 'A reference recreation.', name, name.replace(/^generate_/, '')]);
        return [...synth.templates, ...hidden].filter(t => typeof synth[t[2]] === 'function' &&
            (t[2].startsWith('generate_') || (synth.name === 'Footsteppr' && t[2] === 'randomize_params')));
    }
    // 'Synth:verb' or 'Synth:generate_x' names one generator. Verbs resolve through the engine's verb presets.
    static resolve_reference(reference) {
        const [name, what] = String(reference).split(':');
        const synth = Stackr.source(name);
        if (!synth || !what) return null;
        const generator = what.startsWith('generate_') || what === 'randomize_params' ? what
            : typeof synth.verb_generator === 'function' ? synth.verb_generator(what) : null;
        return generator ? {synth:name, generator} : null;
    }
    static verb_source(reference) {
        const resolved = this.resolve_reference(reference);
        return resolved ? this.generated_source(resolved.synth, resolved.generator) : null;
    }
    static generators() {
        return Stackr.sources().flatMap(Constructor => {
            const synth=new Constructor();
            return this.templates_for(synth).map(([name,tip,generator]) =>
                ({synth:synth.name, family:synth_display_name(synth.name), name, tip, generator}));
        });
    }
    static generated_source(name,generator,previousGenerator) {
        const synth=Stackr.source(name);
        const templates=this.templates_for(synth, this.includeRetired);
        let template;
        if(generator==='*'){
            const candidates=templates.length>1 ? templates.filter(t=>t[2]!==previousGenerator) : templates;
            template=candidates[Math.floor(Math.random()*candidates.length)];
        } else template=templates.find(t=>t[2]===generator);
        if(!template)return null;
        synth[template[2]]();
        const source={synth:synth.name,name:template[0],generator,params:synth.params,renderSeed:Math.random()};
        if(generator==='*')source.selectedGenerator=template[2];
        return source;
    }
    set_param(name,value,checkLocked=false) {
        if (name !== 'sources') return super.set_param(name,value,checkLocked);
        if (checkLocked && this.locked_param(name)) return;
        let sources;
        try { sources = typeof value === 'string' ? JSON.parse(value.slice(0,60000)) : value; } catch { sources = []; }
        const clean = (Array.isArray(sources) ? sources : []).slice(0,2).map(source => {
            const synth = source && Stackr.source(source.synth);
            if (!synth) return null;
            const entry={synth:synth.name, name:typeof source.name === 'string' ? source.name.slice(0,60) : synth.name,
                params:Stackr.sanitize_source(synth,source.params)};
            const templates=this.constructor.templates_for(synth);
            if(source.generator==='*' && templates.length){
                entry.generator='*';
                if(templates.some(t=>t[2]===source.selectedGenerator))entry.selectedGenerator=source.selectedGenerator;
            } else if(templates.some(t=>t[2]===source.generator))entry.generator=source.generator;
            if(Number.isFinite(source.renderSeed))entry.renderSeed=SoundDSP.clamp(source.renderSeed,0,1);
            return entry;
        });
        this.params.sources = JSON.stringify(clean);
        this.sound_params = null;
    }
    set_source(slot,synth,name) {
        if (slot!==0 && slot!==1) return false;
        if (synth && ['Mixr','Stackr','Soundboard'].includes(synth.name)) return false;
        const sources=this.get_sources();
        while(sources.length<=slot)sources.push(null);
        sources[slot]=synth ? {synth:synth.name,name:name||synth.name,params:synth.params} : null;
        this.set_param('sources',sources);
        return true;
    }
    set_generator(slot,name,generator) {
        if(slot!==0 && slot!==1)return false;
        const sources=this.get_sources();
        const current=sources[slot];
        const previous=current && current.synth===name ? current.selectedGenerator || current.generator : undefined;
        const next=this.constructor.generated_source(name,generator,previous);
        if(!next)return false;
        while(sources.length<=slot)sources.push(null);
        sources[slot]=next;
        this.set_param('sources',sources);
        return true;
    }
    regenerate_source(slot) {
        if(this.locked_param('sources'))return false;
        const current=this.get_sources()[slot];
        return current && current.generator ? this.set_generator(slot,current.synth,current.generator) : false;
    }
    regenerate_both() {
        if(this.locked_param('sources'))return;
        const sources=this.get_sources().map(current=>current && current.generator
            ? this.constructor.generated_source(current.synth,current.generator,current.selectedGenerator) || current : current);
        this.set_param('sources',sources);
    }
    // Older integrations can still reseed a copied character snapshot.
    reseed_source(slot) {
        const current=this.get_sources()[slot];
        if(!current)return;
        if(current.generator)return this.regenerate_source(slot);
        if(current.synth==='Chattr') {
            const source=Stackr.source(current.synth);source.apply_params(current.params);
            const family=source.constructor.characters.find(c=>source.params.voiceMode===0?c.id==='clear_speaker':c.params.character===source.params.character);
            if(family){source.generate_character(family.id);this.set_source(slot,source,family.name);}
        }
    }
    after_recipe(recipe) {
        if(this.locked_param('sources'))return;
        const sources=recipe.pair.map(name=>{
            const source=this.constructor.generated_source(name,'*');
            if(!source)throw new Error('Unknown Mixr instrument: '+name);
            return source;
        });
        this.set_param('sources',sources);
    }
    randomize_params() { this.generate_recipe(this.recipes[Math.floor(Math.random()*this.recipes.length)].id); }
    mutate_params() {
        this.set_param('balance',this.params.balance+(Math.random()-.5)*.15,true);
        if(this.locked_param('sources'))return;
        const sources=this.get_sources().map(current=>{
            if(!current)return null;
            const source=Stackr.source(current.synth);
            source.apply_params(current.params);source.mutate_params();
            return {...current,params:source.params};
        });
        this.set_param('sources',sources);
    }
}
