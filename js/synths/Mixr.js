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
    recipes = [
        {id:'heavy_magic',name:'Heavy Magic',pair:[['Rumblr','deep_pressure'],['Zappr','lightning_arc']]},
        {id:'spark_impact',name:'Spark Impact',pair:[['Clonkr','metal_clang'],['Zappr','static_spark']]},
        {id:'spell_hit',name:'Spell Hit',pair:[['Whooshr','sword_swing'],['Fractr','ice_wall']]},
        {id:'monster',name:'Monster',pair:[['Crittr','cave_beast'],['Breathr','sleeping_beast']]},
        {id:'goo_machine',name:'Goo Machine',pair:[['Squishr','wet_splat'],['Machinr','servo']]},
        {id:'crystal_prize',name:'Crystal Prize',pair:[['Jinglr','discovery'],['Clonkr','glass_ping']]},
        {id:'shockwave',name:'Shockwave',pair:[['Boomr','grenade'],['Whooshr','heavy_swing']]},
        {id:'haunted',name:'Haunted',pair:[['Choirr','ghost_chord'],['Riftr','portal_tear']]}
    ].map(recipe => ({...recipe, values:{balance:[0.35,0.65]}}));
    constructor() { super(); this.initialize_presets(); }
    create_editor(tab,parent) { return new MixEditor(tab,parent); }
    create_random_template() { this.set_param('sources',[]); return ['Mix',this.params]; }
    get_sources() { return JSON.parse(this.params.sources); }
    set_param(name,value,checkLocked=false) {
        if (name !== 'sources') return super.set_param(name,value,checkLocked);
        if (checkLocked && this.locked_param(name)) return;
        let sources;
        try { sources = typeof value === 'string' ? JSON.parse(value.slice(0,60000)) : value; } catch { sources = []; }
        const clean = (Array.isArray(sources) ? sources : []).slice(0,2).map(source => {
            const synth = source && Stackr.source(source.synth);
            if (!synth) return null;
            return {synth:synth.name, name:typeof source.name === 'string' ? source.name.slice(0,60) : synth.name,
                params:Stackr.sanitize_source(synth,source.params)};
        });
        this.params.sources = JSON.stringify(clean);
        this.sound_params = null;
    }
    set_source(slot,synth,name) {
        if (synth && (synth.name === 'Mixr' || synth.name === 'Stackr')) return;
        const sources=this.get_sources();
        while(sources.length<=slot)sources.push(null);
        sources[slot]=synth ? {synth:synth.name,name:name||synth.name,params:synth.params} : null;
        this.set_param('sources',sources);
    }
    reseed_source(slot) {
        const current=this.get_sources()[slot];
        if(!current)return;
        const source=Stackr.source(current.synth);
        source.apply_params(current.params);
        let name;
        if(source.name==='Chattr') {
            const family=source.constructor.characters.find(c=>source.params.voiceMode===0?c.id==='clear_speaker':c.params.character===source.params.character);
            if(family){source.generate_character(family.id);name=family.name;}
            else {source.randomize_params();name=current.name;}
        } else { [name]=source.create_random_template(); }
        this.set_source(slot,source,name);
    }
    after_recipe(recipe) {
        if(this.locked_param('sources'))return;
        const sources=recipe.pair.map(([name,id])=>{
            const source=Stackr.source(name);
            if(!source)return null;
            const recipe=source.recipes && source.recipes.find(r=>r.id===id);
            let label;
            if(recipe){source.generate_recipe(id);label=recipe.name;}
            else { [label]=source.create_random_template(); }
            return {synth:source.name,name:label,params:source.params};
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
