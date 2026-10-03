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
        {id:'haunted',name:'Haunted Portal',pair:[['Choirr','ghost_chord'],['Riftr','portal_tear']],balance:[0.38,0.52]},
        {id:'crystal_prize',name:'Crystal Prize',pair:[['Jinglr','discovery'],['Clonkr','glass_ping']],balance:[0.2,0.38]},
        {id:'spell_hit',name:'Ice Blade',pair:[['Whooshr','sword_swing'],['Fractr','ice_wall']],balance:[0.55,0.72]},
        {id:'spark_impact',name:'Charged Steel',pair:[['Clonkr','metal_clang'],['Zappr','static_spark']],balance:[0.35,0.55]},
        {id:'heavy_magic',name:'Thunder Spell',pair:[['Boomr','grenade'],['Zappr','lightning_arc']],balance:[0.3,0.48]},
        {id:'monster',name:'Sleeping Monster',pair:[['Crittr','cave_beast'],['Breathr','sleeping_beast']],balance:[0.35,0.55]},
        {id:'goo_machine',name:'Goo Machine',pair:[['Squishr','wet_splat'],['Machinr','servo']],balance:[0.35,0.6]},
        {id:'shockwave',name:'Shockwave',pair:[['Boomr','grenade'],['Whooshr','heavy_swing']],balance:[0.25,0.42]},
        {id:'sacred_treasure',name:'Sacred Treasure',pair:[['Jinglr','discovery'],['Choirr','angelic']],balance:[0.55,0.7]},
        {id:'enchanted_string',name:'Enchanted String',pair:[['Pluckr','metal_string'],['Riftr','teleport_arrive']],balance:[0.3,0.5]},
        {id:'phase_step',name:'Phase Step',pair:[['Whooshr','dodge'],['Riftr','phase_dash']],balance:[0.58,0.75]},
        {id:'clockwork_familiar',name:'Clockwork Familiar',pair:[['Machinr','windup_toy'],['Birdr','chirp']],balance:[0.35,0.55]},
        {id:'hatchling',name:'Hatchling',pair:[['Fractr','bone_scatter'],['Crittr','tiny_dragon']],balance:[0.38,0.6]},
        {id:'charged_swarm',name:'Charged Swarm',pair:[['Swarmr','locusts'],['Zappr','power_short']],balance:[0.3,0.48]},
        {id:'liquid_reward',name:'Liquid Reward',pair:[['Jinglr','confirm'],['Squishr','suction_cup']],balance:[0.2,0.4]},
        {id:'alien_beacon',name:'Alien Beacon',pair:[['Signlr','radar_blip'],['Choirr','robot_choir']],balance:[0.45,0.65]}
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
    static generated_source(name,generator) {
        const synth=Stackr.source(name);
        const template=this.templates_for(synth).find(t=>t[2]===generator);
        if(!template)return null;
        synth[generator]();
        return {synth:synth.name,name:template[0],generator,params:synth.params,renderSeed:Math.random()};
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
            if(Mixr.templates_for(synth).some(t=>t[2]===source.generator))entry.generator=source.generator;
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
        const next=Mixr.generated_source(name,generator);
        if(!next)return false;
        const sources=this.get_sources();
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
            ? Mixr.generated_source(current.synth,current.generator) || current : current);
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
        const sources=recipe.pair.map(([name,id])=>{
            const source=Mixr.generated_source(name,'generate_'+id);
            if(!source)throw new Error('Unknown Mixr preset: '+name+' / '+id);
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
