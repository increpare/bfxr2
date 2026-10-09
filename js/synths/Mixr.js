class Mixr extends PresetSynth {
    name = 'Mixr';
    tooltip = 'Two sounds together.';
    canvas_bg_logo = "img/logo_mixr.png";
    static DSP = Mixr_DSP;
    hide_params = ['masterVolume', 'seed', 'sources'];
    param_info = [
        ...PresetSynth.common_params,
        ['Balance', 'Balance between the two sounds.', 'balance', 0.5, 0, 1],
        {type:'TEXT', name:'sources', default_value:'[]', max_length:60000}
    ];
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

    static sources() {
        return [typeof Bfxr === 'undefined' ? null : Bfxr,
            typeof Footsteppr === 'undefined' ? null : Footsteppr,
            typeof Transfxr === 'undefined' ? null : Transfxr,
            typeof Clonkr === 'undefined' ? null : Clonkr,
            typeof Machinr === 'undefined' ? null : Machinr,
            typeof Jinglr === 'undefined' ? null : Jinglr,
            typeof Squishr === 'undefined' ? null : Squishr,
            typeof Crittr === 'undefined' ? null : Crittr,
            typeof Birdr === 'undefined' ? null : Birdr,
            typeof Signlr === 'undefined' ? null : Signlr,
            typeof Fractr === 'undefined' ? null : Fractr,
            typeof Riftr === 'undefined' ? null : Riftr,
            typeof Swarmr === 'undefined' ? null : Swarmr,
            typeof Rustlr === 'undefined' ? null : Rustlr,
            typeof Boomr === 'undefined' ? null : Boomr,
            typeof Zappr === 'undefined' ? null : Zappr,
            typeof Whooshr === 'undefined' ? null : Whooshr,
            typeof Bouncr === 'undefined' ? null : Bouncr,
            typeof Breathr === 'undefined' ? null : Breathr,
            typeof Choirr === 'undefined' ? null : Choirr,
            typeof Pluckr === 'undefined' ? null : Pluckr,
            typeof Glitchr === 'undefined' ? null : Glitchr].filter(Boolean);
    }
    static source(name) { const Constructor = this.sources().find(c => c.name === name); return Constructor ? new Constructor() : null; }

    static sanitize_source(synth, params) {
        // Older synths' apply_params accepts arbitrary keys; validate each known control here.
        // Apply editable scores last: generator controls can otherwise replace saved notes.
        const controls = synth.param_info.map(info => synth.get_param_normalized(info));
        controls.sort((a,b) => Number(a.type === 'TEXT') - Number(b.type === 'TEXT'));
        const known={};
        for(const info of controls)if(params&&Object.prototype.hasOwnProperty.call(params,info.name))known[info.name]=params[info.name];
        // Specialized engines filter their own input, and migrations may need former controls.
        // The legacy base setter accepts arbitrary keys, so only give it known controls.
        synth.apply_params(synth.apply_params === SynthBase.prototype.apply_params ? known : params);
        const migrated={...synth.params};
        synth.params=synth.default_params();
        for(const info of controls)synth.set_param(info.name,migrated[info.name]);
        return JSON.parse(JSON.stringify(synth.params));
    }

    static render_source(source, seed = 0.5) {
        const synth = this.source(source.synth);
        if (!synth) return new Float32Array(1);
        this.sanitize_source(synth,source.params);
        const originalRandom = Math.random;
        Math.random = SoundDSP.rng(seed);
        try {
            return synth.render();
        } finally { Math.random = originalRandom; }
    }

    static templates_for(synth) {
        if (!synth) return [];
        return synth.templates.filter(t => typeof synth[t[2]] === 'function' &&
            (t[2].startsWith('generate_') || (synth.name === 'Footsteppr' && t[2] === 'randomize_params')));
    }
    static generators() {
        return Mixr.sources().flatMap(Constructor => {
            const synth=new Constructor();
            return this.templates_for(synth).map(([name,tip,generator]) =>
                ({synth:synth.name, family:synth_display_name(synth.name), name, tip, generator}));
        });
    }
    static generated_source(name,generator,previousGenerator) {
        const synth=Mixr.source(name);
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
            const synth = source && Mixr.source(source.synth);
            if (!synth) return null;
            const entry={synth:synth.name, name:typeof source.name === 'string' ? source.name.slice(0,60) : synth.name,
                params:Mixr.sanitize_source(synth,source.params)};
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
        if (synth && synth.name === 'Mixr') return false;
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
            const source=Mixr.source(current.synth);
            source.apply_params(current.params);source.mutate_params();
            return {...current,params:source.params};
        });
        this.set_param('sources',sources);
    }
}
