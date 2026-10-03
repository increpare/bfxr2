class Bouncr extends PresetSynth {
    // Keep the saved engine identity while showing its friendly name.
    name='Bouncr';
    display_name='Bonks';
    hide_params=['masterVolume','count','bounce','gravity','spin'];
    tooltip='An object of one material striking a surface of another.';
    static DSP=Bouncr_DSP;
    param_info=[PresetSynth.common_params[0],
        {type:'BUTTONSELECT',name:'material',display_name:'Object',tooltip:'The material of the object arriving at the surface.',default_value:0,columns:3,header:true,values:[['Rubber','Soft elastic body.',0],['Wood','Dry, hollow knock.',1],['Metal','Dense ringing body.',2],['Glass','Bright, brittle resonances.',3],['Stone','Heavy, granular body.',4]]},
        {type:'BUTTONSELECT',name:'surface',display_name:'Surface',tooltip:'The receiving surface has its own resonance and absorbs the object differently.',default_value:0,columns:3,header:true,values:[['Concrete','Dense, short clack.',0],['Wood','Hollow board resonance.',1],['Metal','Long ringing panel.',2],['Glass','Thin bright pane.',3],['Earth','Loose, grainy absorption.',4],['Fabric','Soft, muffled landing.',5]]},
        ['Force','Strike velocity changes contact compression and transferred energy.','force',0.65,0,1],
        ['Duration','Length of the rendered sound in seconds.','duration',2,0.2,5],
        ['Mass / Size','Larger, heavier objects excite lower body and surface modes.','size',0.5,0,1],
        ['Hardness','Contact stiffness: a soft thud through to a sharp strike.','hardness',0.6,0,1],
        ['Tail','Damping and resonant decay after the impact.','tail',0.4,0,1],
        PresetSynth.common_params[1],
        ['Contacts','One impact, or optional diminishing rebounds.','count',1,1,20],
        ['Elasticity','Body resilience and energy retained by optional rebounds.','bounce',0.65,0,1],
        ['Gravity','Stronger gravity shortens the gap between optional rebounds.','gravity',0.5,0,1],
        ['Spin','An angled collision adds rubbing and a settling rattle.','spin',0,0,1]
    ];
    recipes=[
        {name:'Rubber on Wood',id:'rubber_ball',values:{material:0,surface:1,duration:[0.5,1.2],count:1,size:[0.35,0.75],hardness:[0.15,0.45],bounce:[0.5,0.9],force:[0.35,0.8],tail:[0.2,0.55]}},
        {name:'Steel on Concrete',id:'metal_ball',values:{material:2,surface:0,duration:[0.5,1.4],count:1,size:[0.4,0.8],hardness:[0.7,1],force:[0.5,1],tail:[0.2,0.6],spin:[0,0.25]}},
        {name:'Wood on Metal',id:'wooden_dice',values:{material:1,surface:2,duration:[0.8,1.8],count:1,size:[0.2,0.6],hardness:[0.45,0.85],force:[0.4,0.85],tail:[0.4,0.85],spin:[0,0.25]}},
        {name:'Heavy Soft Landing',id:'basketball',values:{material:[0,4],surface:5,duration:[0.4,1.1],count:1,size:[0.7,1],hardness:[0.15,0.45],force:[0.65,1],tail:[0.1,0.45]}},
        {name:'Glass on Stone',id:'marble',values:{material:3,surface:0,duration:[0.5,1.3],count:1,size:[0.05,0.35],hardness:[0.7,1],force:[0.3,0.65],tail:[0.3,0.7]}},
        {name:'Coin on Glass',id:'coin_spin',values:{material:2,surface:3,duration:[0.7,1.8],count:1,size:[0.03,0.3],hardness:[0.65,1],force:[0.2,0.6],tail:[0.45,0.9],spin:[0.3,0.8]}},
        {name:'Wood on Concrete',id:'cartoon_bounce',values:{material:1,surface:0,duration:[0.4,1.1],count:1,size:[0.25,0.65],hardness:[0.45,0.8],force:[0.4,0.85],tail:[0.15,0.5]}},
        {name:'Stone into Earth',id:'heavy_tumble',values:{material:4,surface:4,duration:[0.5,1.5],count:1,size:[0.75,1],hardness:[0.35,0.75],force:[0.55,1],tail:[0.2,0.6],spin:[0.25,0.8]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        const oldKeys=['masterVolume','seed','material','duration','count','bounce','gravity','size','hardness','spin'];
        if(params && oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['surface','force','tail'])if(!Object.prototype.hasOwnProperty.call(params,key))this.set_param(key,this.param_default(key),checkLocked);
        }
        super.apply_params(params,checkLocked);
    }
    set_param(name,value,checkLocked=false){if(name==='count'&&Number.isFinite(value))value=Math.round(value);super.set_param(name,value,checkLocked);}
}
