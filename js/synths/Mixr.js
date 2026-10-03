class Mixr extends PresetSynth {
    name = 'Mixr';
    tooltip = 'Two sounds together.';
    static DSP = Mixr_DSP;
    hide_params = ['masterVolume', 'seed', 'sources'];
    param_info = [
        ...PresetSynth.common_params,
        ['A ↔ B', 'Balance between the two sounds.', 'balance', 0.5, 0, 1],
        {type:'TEXT', name:'sources', default_value:'[]', max_length:60000}
    ];
    static retired = ['Chattr','Weathr','Tappr','Notifr','Tickr','Holor','Pewpr','Rollr','Pulser','Rumblr'];
    recipes = [
        {id:'haunted',name:'Otherworld',pair:['Choirr','Riftr'],balance:[0.5,0.68],tip:'Choirr × Riftr.'},
        {id:'crystal_prize',name:'Treasure Box',pair:['Jinglr','Clonkr'],balance:[0.5,0.68],tip:'Jinglr × Clonkr.'},
        {id:'spell_hit',name:'Shatterstorm',pair:['Whooshr','Fractr'],balance:[0.57,0.75],tip:'Whooshr × Fractr.'},
        {id:'spark_impact',name:'Live Wire',pair:['Clonkr','Zappr'],balance:[0.52,0.7],tip:'Clonkr × Zappr.'},
        {id:'heavy_magic',name:'Thunderworks',pair:['Boomr','Zappr'],balance:[0.26,0.44],tip:'Boomr × Zappr.'},
        {id:'monster',name:'Beast Within',pair:['Crittr','Breathr'],balance:[0.3,0.48],tip:'Crittr × Breathr.'},
        {id:'goo_machine',name:'Wetware',pair:['Squishr','Machinr'],balance:[0.44,0.62],tip:'Squishr × Machinr.'},
        {id:'shockwave',name:'Shockwaves',pair:['Boomr','Whooshr'],balance:[0.38,0.56],tip:'Boomr × Whooshr.'},
        {id:'sacred_treasure',name:'Arcane Reward',pair:['Jinglr','Choirr'],balance:[0.43,0.61],tip:'Jinglr × Choirr.'},
        {id:'enchanted_string',name:'Strange Strings',pair:['Pluckr','Riftr'],balance:[0.11,0.29],tip:'Pluckr × Riftr.'},
        {id:'phase_step',name:'Phase Shift',pair:['Whooshr','Riftr'],balance:[0.38,0.56],tip:'Whooshr × Riftr.'},
        {id:'clockwork_familiar',name:'Clockwork Aviary',pair:['Machinr','Birdr'],balance:[0.31,0.49],tip:'Machinr × Birdr.'},
        {id:'hatchling',name:'Monster Hatchery',pair:['Fractr','Crittr'],balance:[0.21,0.39],tip:'Fractr × Crittr.'},
        {id:'charged_swarm',name:'Electric Hive',pair:['Swarmr','Zappr'],balance:[0.37,0.55],tip:'Swarmr × Zappr.'},
        {id:'liquid_reward',name:'Jelly Beans',pair:['Jinglr','Squishr'],balance:[0.64,0.8],tip:'Jinglr × Squishr.'},
        {id:'alien_beacon',name:'Alien Broadcast',pair:['Signlr','Choirr'],balance:[0.44,0.62],tip:'Signlr × Choirr.'},
        {id:'pocket_rattle',name:'Pocket Rattle',pair:['Rustlr','Clonkr'],balance:[0.12,0.3],tip:'Rustlr × Clonkr.'},
        {id:'soft_landing',name:'Goo Collision',pair:['Bouncr','Squishr'],balance:[0.33,0.51],tip:'Impactr × Squishr.'},
        {id:'reality_error',name:'Reality Error',pair:['Transfxr','Glitchr'],balance:[0.37,0.55],tip:'Transfxr × Glitchr.'},
        {id:'arcade_rush',name:'Arcade Rush',pair:['Bfxr','Whooshr'],balance:[0.54,0.72],tip:'Bfxr × Whooshr.'},
        {id:'underbrush',name:'Underbrush',pair:['Swarmr','Rustlr'],balance:[0.45,0.63],tip:'Swarmr × Rustlr.'},
        {id:'song_garden',name:'Song Garden',pair:['Pluckr','Birdr'],balance:[0.11,0.29],tip:'Pluckr × Birdr.'},
        {id:'demolition',name:'Demolition',pair:['Fractr','Boomr'],balance:[0.37,0.55],tip:'Fractr × Boomr.'},
        {id:'haunted_hardware',name:'Scrap Brain',pair:['Clonkr','Glitchr'],balance:[0.5,0.68],tip:'Clonkr × Glitchr.'}
    ].map(recipe => ({...recipe, values:{balance:recipe.balance}}));
    constructor() { super(); this.initialize_presets(); }
    create_editor(tab,parent) { return new MixEditor(tab,parent); }
    create_random_template() { return super.create_random_template(); }
    get_sources() { return JSON.parse(this.params.sources); }

    static templates_for(synth) {
        if (!synth || this.retired.includes(synth.name)) return [];
        return synth.templates.filter(t => typeof synth[t[2]] === 'function' &&
            (t[2].startsWith('generate_') || (synth.name === 'Footsteppr' && t[2] === 'randomize_params')));
    }
    static generators() {
        return Stackr.sources().flatMap(Constructor => {
            const synth=new Constructor();
            return this.templates_for(synth).map(([name,tip,generator]) =>
                ({synth:synth.name, family:synth.display_name || synth.name, name, tip, generator}));
        });
    }
    static generated_source(name,generator,previousGenerator) {
        const synth=Stackr.source(name);
        const templates=this.templates_for(synth);
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
            const templates=Mixr.templates_for(synth);
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
        if (synth && (synth.name === 'Mixr' || synth.name === 'Stackr')) return false;
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
        const next=Mixr.generated_source(name,generator,previous);
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
            ? Mixr.generated_source(current.synth,current.generator,current.selectedGenerator) || current : current);
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
            const source=Mixr.generated_source(name,'*');
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
