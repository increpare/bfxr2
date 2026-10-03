class Fractr extends PresetSynth {
    name = 'Fractr';
    tooltip = 'Structural snaps, brittle crunches, cracking ice and falling rubble.';
    static DSP = Fractr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'material', display_name:'Material', tooltip:'The crack, grit and short body of each fragment.',
            default_value:0, columns:4, values:[['Glass','Bright, inharmonic shards.',0],['Ice','Hollow crystalline cracks.',1],
                ['Crystal','Long, almost harmonic ringing.',2],['Stone','Low, dusty rubble.',3],
                ['Armor','Brittle metallic plates.',5],['Bone','A solid, visceral snap and splintering after-cracks.',6],['Biscuit','Porous, dry crunches and crumbling crumbs.',7]]},
        ['Duration','Length of the entire break and its tail, in seconds.','duration',1.8,0.15,6],
        ['Fragments','Number of separately falling pieces.','fragments',32,3,96],
        ['Fragment Size','Larger pieces make deeper, longer contacts; small shards spit and crackle.','fragmentSize',0.4,0,1],
        ['Spread','Time between the first and last fractures.','spread',0.6,0,1],
        ['Decay','Length of the grit after each crack; Crystal also sustains its ringing.','decay',0.4,0,1],
        ['Gravity','Stronger gravity speeds the cascade and shortens bounce flights.','gravity',0.5,0,1],
        ['Bounce','Number and strength of each fragment’s returning contacts.','bounce',0.4,0,1],
        ['Stress','Straining, creaking microfractures before the material lets go.','stress',0.4,0,1],
        ['Shards','Loose fragment and contact level, independent of the main structural snap.','shards',0.35,0,1],
        ['Fracture','Strength of the initial structural split and its branching cracks.','fracture',0.75,0,1]
    ];
    recipes = [
        {name:'Break',id:'break',verb:'break',tip:'An object snapping into a handful of pieces.',values:{material:[0,1,3,5,7],duration:[0.3,1.2],fragments:[6,30],fragmentSize:[0.2,0.7],spread:[0.05,0.4],decay:[0.1,0.4],gravity:[0.5,1],bounce:[0.1,0.5],stress:[0.05,0.5],shards:[0.2,0.7],fracture:[0.8,1]}},
        {name:'Hit',id:'hit',verb:'hit',tip:'A close, forceful snap.',values:{material:[0,5,6,7],duration:[0.15,0.4],fragments:[3,8],fragmentSize:[0.3,0.8],spread:[0.01,0.08],decay:[0.02,0.12],gravity:[0.8,1],bounce:[0,0.12],stress:[0.05,0.3],shards:[0.03,0.15],fracture:[0.85,1]}},
        {name:'Step',id:'step',verb:'step',tip:'A crunching step on gravel or dry crust.',values:{material:[7,3],duration:[0.12,0.3],fragments:[6,18],fragmentSize:[0.2,0.5],spread:[0.02,0.12],decay:[0.02,0.1],gravity:[0.7,1],bounce:[0,0.1],stress:[0.05,0.3],shards:[0.1,0.3],fracture:[0.5,0.9]}},
        {name:'Cast',id:'cast',verb:'cast',tip:'Ringing crystal splinters of magic.',values:{material:2,duration:[0.5,1.4],fragments:[5,16],fragmentSize:[0.1,0.4],spread:[0.1,0.4],decay:[0.6,1],gravity:[0.1,0.4],bounce:[0.2,0.5],stress:[0.05,0.25],shards:[0.6,1],fracture:[0.4,0.8]}},
        {name:'Glass Cascade',id:'glass_cascade',tip:'A fresh shower of bright glass shards.',values:{stress:[0.05,0.25],fracture:[0.65,1],shards:[0.5,0.9],material:0,duration:[1.1,2.6],fragments:[30,72],fragmentSize:[0.18,0.46],spread:[0.45,0.85],decay:[0.2,0.5],gravity:[0.35,0.7],bounce:[0.45,0.8]}},
        {name:'Ice Wall',id:'ice_wall',tip:'A wall splitting into cold, hollow chunks.',values:{stress:[0.65,1],fracture:[0.7,1],material:1,duration:[1.6,3.1],fragments:[20,50],fragmentSize:[0.5,0.85],spread:[0.55,0.95],decay:[0.3,0.6],gravity:[0.2,0.6],bounce:[0.2,0.5]}},
        {name:'Crystal Break',id:'crystal_break',tip:'A magical crystal scattering ringing fragments.',values:{stress:[0.1,0.3],fracture:[0.45,0.85],shards:[0.65,1],material:2,duration:[1.2,3.2],fragments:[8,28],fragmentSize:[0.1,0.45],spread:[0.12,0.4],decay:[0.65,1],gravity:[0.1,0.4],bounce:[0.25,0.6]}},
        {name:'Stone Collapse',id:'stone_collapse',tip:'Heavy rubble falling through a collapsing structure.',values:{stress:[0.5,0.9],fracture:[0.7,1],shards:[0.6,1],material:3,duration:[2.2,4.6],fragments:[40,96],fragmentSize:[0.55,1],spread:[0.7,1],decay:[0.25,0.7],gravity:[0.5,0.9],bounce:[0.35,0.75]}},
        {name:'Brittle Armor',id:'brittle_armor',tip:'A sharp armor break followed by scattered plates.',values:{stress:[0.3,0.65],fracture:[0.85,1],material:5,duration:[0.55,1.5],fragments:[7,24],fragmentSize:[0.35,0.75],spread:[0.08,0.35],decay:[0.18,0.48],gravity:[0.55,1],bounce:[0.5,0.9]}},
        {name:'Bone Snap',id:'bone_scatter',tip:'A forceful close snap, splinters and a brief fleshy body.',values:{stress:[0.1,0.5],fracture:[0.85,1],shards:[0.04,0.16],material:6,duration:[0.22,0.48],fragments:[3,8],fragmentSize:[0.55,0.9],spread:[0.01,0.09],decay:[0.03,0.14],gravity:[0.8,1],bounce:[0,0.12]}},
        {name:'Shatter Freeze',id:'shatter_freeze',tip:'A suspended fracture that slowly sheds chiming shards.',values:{stress:[0.7,1],fracture:[0.35,0.65],material:[0,2],duration:[3,5.5],fragments:[18,46],fragmentSize:[0.15,0.5],spread:[0.8,1],decay:[0.65,1],gravity:[0,0.1],bounce:[0.08,0.3]}},
        {name:'Glass Snap',id:'glass_snap',tip:'A thin pane cleaves with a sharp snap and a few tiny chips.',values:{material:0,duration:[0.18,0.4],stress:[0.05,0.25],fracture:[0.8,1],shards:[0.03,0.12],fragments:[3,9],fragmentSize:[0.1,0.35],spread:[0.01,0.06],decay:[0.02,0.12],gravity:[0.7,1],bounce:[0,0.15]}},
        {name:'Ice Crack',id:'ice_crack',tip:'A thick sheet of ice splits in branching, hollow cracks.',values:{material:1,duration:[0.3,0.65],stress:[0.3,0.7],fracture:[0.8,1],shards:[0.04,0.18],fragments:[3,10],fragmentSize:[0.55,0.9],spread:[0.03,0.15],decay:[0.08,0.2],gravity:[0.6,0.9],bounce:[0,0.1]}},
        {name:'Biscuit Crunch',id:'biscuit_crunch',tip:'A dry bite crushes a brittle crust into irregular crumbs.',values:{material:7,duration:[0.22,0.5],stress:[0.15,0.45],fracture:[0.8,1],shards:[0.03,0.12],fragments:[8,24],fragmentSize:[0.25,0.6],spread:[0.03,0.13],decay:[0.02,0.12],gravity:[0.7,1],bounce:[0,0.12]}}
    ];
    randomize_params() {
        this.generate_recipe(this.recipes[Math.floor(Math.random()*this.recipes.length)].id);
    }
    // Old saves and external callers can retain the original ID without a Pixel button.
    generate_pixel_disintegrate() {
        this.generate_recipe('crystal_break');
        this.set_param('material',4,true);
    }
    generate_recipe(id) {
        if(id==='pixel_disintegrate') return this.generate_pixel_disintegrate();
        super.generate_recipe(id);
    }
    apply_params(params,checkLocked=false) {
        if(!params||typeof params!=='object')return;
        // Complete older snapshots need defaults for controls they never stored.
        // A partial edit must leave unrelated current controls untouched.
        const oldKeys=['masterVolume','seed','material','duration','fragments','fragmentSize','spread','decay','gravity','bounce'];
        if(oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['stress','fracture','shards']) if(!Object.prototype.hasOwnProperty.call(params,key)) {
                this.set_param(key,this.param_default(key),checkLocked);
            }
        }
        super.apply_params(params,checkLocked);
    }
    constructor() { super(); this.initialize_presets(); }
    set_param(name, value, checkLocked = false) {
        if(name==='material' && value===4) {
            if(!(checkLocked && this.locked_params[name])) { this.params.material=4; this.sound_params=null; }
            return;
        }
        super.set_param(name, value, checkLocked);
        if (name === 'fragments' && !(checkLocked && this.locked_params[name])) {
            this.params.fragments = Math.round(this.params.fragments);
        }
    }
}
