class Fractr extends PresetSynth {
    name = 'Fractr';
    tooltip = 'Falling shards, collapsing walls and glittering disintegration. Every click breaks something new.';
    static DSP = Fractr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'material', display_name:'Material', tooltip:'The resonances carried by each fragment.',
            default_value:0, columns:4, values:[['Glass','Bright, inharmonic shards.',0],['Ice','Hollow crystalline cracks.',1],
                ['Crystal','Long, almost harmonic ringing.',2],['Stone','Low, dusty rubble.',3],
                ['Pixel','Tuned fragments snapped to a time grid.',4],['Armor','Brittle metallic plates.',5],['Bone','Dry, small clattering pieces.',6]]},
        ['Duration','Length of the entire break and its tail, in seconds.','duration',1.8,0.15,6],
        ['Fragments','Number of separately falling pieces.','fragments',32,3,96],
        ['Fragment Size','Larger pieces resonate lower.','fragmentSize',0.4,0,1],
        ['Spread','Time between the first and last fractures.','spread',0.6,0,1],
        ['Decay','How long each fragment rings after contact.','decay',0.4,0,1],
        ['Gravity','Stronger gravity speeds the cascade and shortens bounce flights.','gravity',0.5,0,1],
        ['Bounce','Number and strength of each fragment’s returning contacts.','bounce',0.4,0,1]
    ];
    recipes = [
        {name:'Glass Cascade',id:'glass_cascade',tip:'A fresh shower of bright glass shards.',values:{material:0,duration:[1.1,2.6],fragments:[30,72],fragmentSize:[0.18,0.46],spread:[0.45,0.85],decay:[0.2,0.5],gravity:[0.35,0.7],bounce:[0.45,0.8]}},
        {name:'Ice Wall',id:'ice_wall',tip:'A wall splitting into cold, hollow chunks.',values:{material:1,duration:[1.6,3.1],fragments:[20,50],fragmentSize:[0.5,0.85],spread:[0.55,0.95],decay:[0.3,0.6],gravity:[0.2,0.6],bounce:[0.2,0.5]}},
        {name:'Crystal Break',id:'crystal_break',tip:'A magical crystal scattering ringing fragments.',values:{material:2,duration:[1.2,3.2],fragments:[8,28],fragmentSize:[0.1,0.45],spread:[0.12,0.4],decay:[0.65,1],gravity:[0.1,0.4],bounce:[0.25,0.6]}},
        {name:'Stone Collapse',id:'stone_collapse',tip:'Heavy rubble falling through a collapsing structure.',values:{material:3,duration:[2.2,4.6],fragments:[40,96],fragmentSize:[0.55,1],spread:[0.7,1],decay:[0.25,0.7],gravity:[0.5,0.9],bounce:[0.35,0.75]}},
        {name:'Pixel Disintegrate',id:'pixel_disintegrate',tip:'An object breaking into tuned digital particles.',values:{material:4,duration:[0.45,1.5],fragments:[18,60],fragmentSize:[0.05,0.55],spread:[0.4,0.95],decay:[0.15,0.4],gravity:[0,0.4],bounce:[0,0.25]}},
        {name:'Brittle Armor',id:'brittle_armor',tip:'A sharp armor break followed by scattered plates.',values:{material:5,duration:[0.55,1.5],fragments:[7,24],fragmentSize:[0.35,0.75],spread:[0.08,0.35],decay:[0.18,0.48],gravity:[0.55,1],bounce:[0.5,0.9]}},
        {name:'Bone Scatter',id:'bone_scatter',tip:'A dry jumble of small pieces tumbling away.',values:{material:6,duration:[0.7,1.7],fragments:[10,34],fragmentSize:[0.18,0.6],spread:[0.25,0.6],decay:[0.12,0.4],gravity:[0.35,0.7],bounce:[0.65,1]}},
        {name:'Shatter Freeze',id:'shatter_freeze',tip:'A suspended fracture that slowly sheds chiming shards.',values:{material:[0,2],duration:[3,5.5],fragments:[18,46],fragmentSize:[0.15,0.5],spread:[0.8,1],decay:[0.65,1],gravity:[0,0.1],bounce:[0.08,0.3]}}
    ];
    constructor() { super(); this.initialize_presets(); }
    set_param(name, value, checkLocked = false) {
        super.set_param(name, value, checkLocked);
        if (name === 'fragments' && !(checkLocked && this.locked_params[name])) {
            this.params.fragments = Math.round(this.params.fragments);
        }
    }
}
