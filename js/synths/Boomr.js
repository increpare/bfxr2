class Boomr extends PresetSynth {
    name='Boomr';
    tooltip='Pressure waves, fireballs and falling fragments.';
    static DSP=Boomr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        ['Duration','Seconds.','duration',1.5,0.12,5],
        ['Size','Larger blasts have a deeper pressure body and slower, darker fireballs.','size',0.5,0,1],
        ['Pressure','The low shock front of the explosion.','pressure',0.7,0,1],
        ['Blast','The initial turbulent fireball.','blast',0.65,0,1],
        ['Debris','Sharp grit and dull rubble contacts after the blast.','debris',0.35,0,1],
        ['Gas','Sustained escaping gas, rising after the initial rupture.','gas',0.25,0,1],
        ['Aftershock','Delayed ground pulses and secondary pressure fronts.','aftershock',0.25,0,1],
        ['Rubble Size','Fine shrapnel at the left; heavy, low chunks at the right.','rubbleSize',0.5,0,1],
        ['Scatter','Spread the fragments through the tail.','spread',0.5,0,1],
        ['Aftermath','Length and weight of the rolling decay.','tail',0.45,0,1],
        ['Muffle','Lose sharp detail behind walls or underwater.','muffle',0.15,0,1],
        {type:'BUTTONSELECT',name:'mechanism',display_name:'Explosion',tooltip:'How the stored energy is released.',default_value:0,columns:3,
            values:[['Detonation','A sudden pressure front with turbulent air.',0],['Fuel','A swelling fire bloom and hollow shell.',1],['Underwater','Deep pressure and rebounding cavitation bubbles.',2],['Impact','Ground transmission and an ejecta cone.',3],['Collapse','Successive structural failures.',4],['Pop','A tiny, dry rupture.',5],['Gas Rupture','A pressure vessel opens into a turbulent jet.',6],['Implosion','Inward suction gives way to a dense collapse.',7]]},
        ['Space','Diffuse pressure reflections and a spacious rolling tail.','space',0.25,0,1]
    ];
    recipes=[
        {name:'Explode',id:'explode',verb:'explode',tip:'A blast with a fireball and loose debris.',values:{mechanism:[0,1,3],duration:[0.6,1.8],size:[0.3,0.8],pressure:[0.6,1],blast:[0.5,1],debris:[0.3,0.9],gas:[0.05,0.5],aftershock:[0.05,0.5],rubbleSize:[0.1,0.6],spread:[0.2,0.7],tail:[0.3,0.7],muffle:[0,0.3],space:[0.1,0.5]}},
        {name:'Hit',id:'hit',verb:'hit',tip:'A dry little pressure pop.',values:{mechanism:5,duration:[0.1,0.3],size:[0,0.3],pressure:[0.6,1],blast:[0.1,0.4],debris:[0,0.15],gas:0,aftershock:0,rubbleSize:[0,0.3],spread:[0,0.2],tail:[0,0.15],muffle:[0,0.1],space:[0,0.1]}},
        {name:'Land',id:'land',verb:'land',tip:'A ground thud with a little dust.',values:{mechanism:3,duration:[0.2,0.45],size:[0.4,0.8],pressure:[0.6,0.9],blast:[0,0.1],debris:[0.05,0.25],gas:0,aftershock:[0,0.2],rubbleSize:[0.6,1],spread:[0.1,0.4],tail:[0.1,0.35],muffle:[0.3,0.7],space:[0,0.2]}},
        {name:'Shoot',id:'shoot',verb:'shoot',tip:'A short gunpowder report.',values:{mechanism:[0,5],duration:[0.15,0.45],size:[0.1,0.4],pressure:[0.7,1],blast:[0.3,0.7],debris:[0,0.2],gas:[0,0.1],aftershock:0,rubbleSize:[0,0.3],spread:[0,0.2],tail:[0.05,0.25],muffle:[0,0.2],space:[0,0.2]}},
        {name:'Grenade',id:'grenade',tip:'A sharp pressure thump and loose shrapnel.',values:{gas:[0.03,0.15],aftershock:[0.05,0.22],rubbleSize:[0.05,0.35],mechanism:0,space:[0.08,0.35],duration:[0.65,1.5],size:[0.25,0.55],pressure:[0.65,1],blast:[0.45,0.8],debris:[0.55,0.95],spread:[0.3,0.7],tail:[0.2,0.5],muffle:[0.03,0.25]}},
        {name:'Barrel',id:'barrel',tip:'A hollow fuel drum erupting.',values:{gas:[0.65,1],aftershock:[0.1,0.3],rubbleSize:[0.25,0.55],mechanism:1,space:[0.25,0.55],duration:[1,2],size:[0.4,0.7],pressure:[0.5,0.85],blast:[0.7,1],debris:[0.65,1],spread:[0.15,0.55],tail:[0.45,0.8],muffle:[0.1,0.35]}},
        {name:'Rocket',id:'rocket',tip:'A hard detonation with a tearing fireball.',values:{gas:[0.25,0.6],aftershock:[0.25,0.6],rubbleSize:[0.05,0.3],mechanism:0,space:[0.2,0.5],duration:[0.7,1.6],size:[0.3,0.65],pressure:[0.8,1],blast:[0.8,1],debris:[0.2,0.5],spread:[0.05,0.3],tail:[0.3,0.65],muffle:[0,0.18]}},
        {name:'Depth Charge',id:'depth_charge',tip:'An immense muffled underwater pressure wave.',values:{gas:[0,0.04],aftershock:[0.7,1],rubbleSize:[0.7,1],mechanism:2,space:[0.4,0.85],duration:[1.8,3.6],size:[0.8,1],pressure:[0.85,1],blast:[0.4,0.8],debris:[0,0.15],spread:[0.4,0.8],tail:[0.65,1],muffle:[0.75,1]}},
        {name:'Fireball',id:'fireball',tip:'A bloom of flame with a rolling hot tail.',values:{gas:[0.7,1],aftershock:[0.02,0.15],rubbleSize:[0.1,0.3],mechanism:1,space:[0.35,0.75],duration:[1.3,2.8],size:[0.45,0.8],pressure:[0.3,0.6],blast:[0.85,1],debris:[0.02,0.22],spread:[0.2,0.55],tail:[0.7,1],muffle:[0.2,0.5]}},
        {name:'Meteor',id:'meteor',tip:'A massive impact and scattered incandescent rubble.',values:{gas:[0.1,0.4],aftershock:[0.8,1],rubbleSize:[0.8,1],mechanism:3,space:[0.6,1],duration:[2.2,4.5],size:[0.85,1],pressure:[0.85,1],blast:[0.65,0.95],debris:[0.75,1],spread:[0.65,1],tail:[0.7,1],muffle:[0.3,0.6]}},
        {name:'Demolition',id:'demolition',tip:'A heavy charge followed by falling structure.',values:{gas:[0.08,0.22],aftershock:[0.5,0.9],rubbleSize:[0.6,1],mechanism:4,space:[0.5,0.9],duration:[1.6,3.8],size:[0.65,0.95],pressure:[0.65,0.9],blast:[0.4,0.7],debris:[0.85,1],spread:[0.7,1],tail:[0.45,0.85],muffle:[0.15,0.4]}},
        {name:'Tiny Pop',id:'tiny_pop',tip:'A miniature comic detonation.',values:{gas:0,aftershock:0,rubbleSize:[0,0.2],mechanism:5,space:[0,0.08],duration:[0.12,0.35],size:[0,0.2],pressure:[0.55,0.85],blast:[0.1,0.4],debris:[0,0.12],spread:[0,0.25],tail:[0,0.18],muffle:[0,0.12]}},
        {name:'Gas Tank',id:'gas_tank',tip:'A vessel ruptures, then vents a long rough jet.',values:{mechanism:6,duration:[1.3,3.4],size:[0.25,0.7],pressure:[0.3,0.65],blast:[0.2,0.5],gas:[0.8,1],aftershock:[0,0.08],debris:[0.02,0.2],rubbleSize:[0.15,0.4],spread:[0.3,0.6],tail:[0.4,0.8],muffle:[0,0.2],space:[0.05,0.25]}},
        {name:'Implosion',id:'implosion',tip:'A short inward rush and deep, crumpling structural failure.',values:{mechanism:7,duration:[0.8,2.1],size:[0.6,1],pressure:[0.8,1],blast:[0.2,0.45],gas:[0.03,0.12],aftershock:[0.15,0.4],debris:[0.6,1],rubbleSize:[0.7,1],spread:[0.15,0.45],tail:[0.15,0.4],muffle:[0.25,0.5],space:[0.1,0.35]}},
        {name:'Distant Charge',id:'distant_charge',tip:'A deep distant thud with separated ground shocks and settling rubble.',values:{mechanism:0,duration:[2,4.5],size:[0.85,1],pressure:[0.65,1],blast:[0.03,0.15],gas:[0,0.1],aftershock:[0.7,1],debris:[0.1,0.35],rubbleSize:[0.8,1],spread:[0.6,1],tail:[0.7,1],muffle:[0.65,0.9],space:[0.7,1]}}
    ];
    randomize_params() {
        this.generate_recipe(this.recipes[Math.floor(Math.random()*this.recipes.length)].id);
    }
    apply_params(params,checkLocked=false) {
        if(!params||typeof params!=='object')return;
        // Complete older snapshots need defaults for controls they never stored.
        // A partial edit must leave unrelated current controls untouched.
        const oldKeys=['masterVolume','seed','duration','size','pressure','blast','debris','spread','tail','muffle'];
        if(oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['mechanism','space','gas','aftershock','rubbleSize']) if(!Object.prototype.hasOwnProperty.call(params,key)) {
                this.set_param(key,this.param_default(key),checkLocked);
            }
        }
        super.apply_params(params,checkLocked);
    }
    constructor(){super();this.initialize_presets();}
}
