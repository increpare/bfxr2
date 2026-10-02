class Clonkr extends PresetSynth {
    name = 'Clonkr';
    tooltip = 'Knock, scrape, and rattle imaginary objects made of real-sounding materials.';
    static DSP = Clonkr_DSP;
    header_properties = ['material', 'action'];

    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'material', display_name:'Material', tooltip:'The resonances and decay of the object.',
            default_value:0, columns:5, header:true, values:[
                ['Wood','Dry, uneven wooden modes.',0], ['Glass','Clear, widely spaced ringing modes.',1],
                ['Metal','Dense, long-ringing inharmonic modes.',2], ['Ceramic','Brittle, short bell-like modes.',3],
                ['Rubber','Low, soft, heavily damped modes.',4]]},
        {type:'BUTTONSELECT', name:'action', display_name:'Contact', tooltip:'How the object is excited.',
            default_value:0, columns:3, header:true, values:[
                ['Hit','A single strike.',0], ['Scrape','Continuous rough contact.',1], ['Rattle','Uneven bouncing collisions.',2]]},
        ['Size','Small bright objects to large low objects.','size',0.5,0,1],
        ['Hollowness','Emphasize the hollow body resonance.','hollowness',0.35,0,1],
        ['Strike Hardness','A padded contact to a sharp, brittle strike.','hardness',0.65,0,1],
        ['Damping','How quickly the material absorbs its ringing.','damping',0.35,0,1],
        ['Duration','Resonance scale; also the contact time for scrapes and rattles.','duration',0.7,0.1,2]
    ];

    recipes = [
        {name:'Teacup', id:'teacup', tip:'Tap a small hollow china cup.',
            values:{material:3,action:0,size:[0.18,0.32],hollowness:[0.65,0.95],hardness:[0.55,0.8],damping:[0.1,0.32],duration:[0.45,0.9]}},
        {name:'Glass Ping', id:'glass_ping', tip:'A bright, delicate piece of glass.',
            values:{material:1,action:0,size:[0.05,0.23],hollowness:[0.25,0.65],hardness:[0.7,1],damping:[0.05,0.24],duration:[0.5,1.15]}},
        {name:'Wood Knock', id:'wood_knock', tip:'A dry knock on a wooden block or door.',
            values:{material:0,action:0,size:[0.36,0.68],hollowness:[0.25,0.7],hardness:[0.35,0.7],damping:[0.35,0.72],duration:[0.2,0.6]}},
        {name:'Dungeon Gate', id:'dungeon_gate', tip:'Heavy iron scraping and ringing in a stone passage.',
            values:{material:2,action:[1,2],size:[0.78,1],hollowness:[0.6,0.95],hardness:[0.35,0.65],damping:[0.16,0.38],duration:[1.2,2]}},
        {name:'Metal Clang', id:'metal_clang', tip:'Strike a resonant metal plate.',
            values:{material:2,action:0,size:[0.38,0.68],hollowness:[0.05,0.4],hardness:[0.65,1],damping:[0.05,0.3],duration:[0.7,1.5]}},
        {name:'Ceramic Crack', id:'ceramic_crack', tip:'Brittle pottery cracking into short rattling shards.',
            values:{material:3,action:2,size:[0.08,0.4],hollowness:[0.05,0.3],hardness:[0.8,1],damping:[0.68,0.95],duration:[0.12,0.32]}},
        {name:'Rubber Thud', id:'rubber_thud', tip:'A heavy cushioned bounce.',
            values:{material:4,action:0,size:[0.55,0.95],hollowness:[0.3,0.8],hardness:[0.08,0.35],damping:[0.3,0.7],duration:[0.35,0.8]}},
        {name:'Loose Bolts', id:'loose_bolts', tip:'A handful of small metal parts tumbling together.',
            values:{material:2,action:2,size:[0.18,0.4],hollowness:[0,0.25],hardness:[0.7,1],damping:[0.48,0.8],duration:[0.45,1]}},
        {name:'Dragged Crate', id:'dragged_crate', tip:'Rough wood scraping along the floor.',
            values:{material:0,action:1,size:[0.65,0.95],hollowness:[0.55,0.95],hardness:[0.4,0.8],damping:[0.5,0.85],duration:[0.65,1.6]}},
        {name:'Coin Drop', id:'coin_drop', tip:'A small coin bouncing and settling.',
            values:{material:2,action:2,size:[0.03,0.16],hollowness:[0,0.25],hardness:[0.8,1],damping:[0.3,0.6],duration:[0.22,0.52]}}
    ];

    constructor() { super(); this.initialize_presets(); }
}
