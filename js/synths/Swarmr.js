class Swarmr extends PresetSynth {
    name='Swarmr';
    canvas_bg_logo = 'img/logo_swarmr.png';
    tooltip='Flocks, clouds and coordinated little machines.';
    static DSP=Swarmr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'kind',display_name:'Agents',tooltip:'The individual sound inside the swarm.',default_value:0,columns:3,header:true,
            values:[['Wings','Independent wing strokes and rushing air.',0],['Chirps','Brief calls.',1],['Rotors','Small motors with rough blade wakes.',2],
                ['Ticks','Paired skittering feet and joint clicks.',3],['Wisps','Soft hovering tones.',4],['Jets','Tiny rushing exhausts.',5]]},
        ['Duration','Seconds.','duration',1.8,0.25,5],
        ['Population','Number of independent emitters.','count',14,3,32],
        ['Speed','Wingbeats, chirps and repeated activity.','speed',0.5,0,1],
        ['Cohesion','Synchronize the individual calls and movement.','cohesion',0.3,0,1],
        ['Agitation','Unsteady flight and pitch.','agitation',0.25,0,1],
        ['Size','Larger agents have lower voices.','size',0.45,0,1],
        ['Flyby','Approach and recede, changing pitch and level.','movement',0.5,0,1],
        ['Scatter','Spread the agents’ arrivals over time.','scatter',0.2,0,1]
    ];
    recipes=[
        {name:'Nanobots',id:'nanobots',tip:'A cloud of busy microscopic machines.',values:{kind:3,duration:[0.6,1.6],count:[16,32],speed:[0.65,1],cohesion:[0.1,0.4],agitation:[0.5,1],size:[0,0.25],movement:[0.1,0.5],scatter:[0.1,0.5]}},
        {name:'Cave Bats',id:'cave_bats',tip:'A startled flock leaving its roost.',values:{kind:0,duration:[1.2,2.6],count:[8,19],speed:[0.3,0.65],cohesion:[0.05,0.3],agitation:[0.55,0.95],size:[0.5,0.8],movement:[0.6,1],scatter:[0.25,0.8]}},
        {name:'Fireflies',id:'fireflies',tip:'Little overlapping points of sound.',values:{kind:1,duration:[1.3,3],count:[4,12],speed:[0.05,0.28],cohesion:[0.05,0.3],agitation:[0,0.2],size:[0.05,0.3],movement:[0.05,0.3],scatter:[0.1,0.65]}},
        {name:'Scarabs',id:'scarabs',tip:'A shifting carpet of hard little feet.',values:{kind:3,duration:[1,2.5],count:[15,32],speed:[0.15,0.55],cohesion:[0,0.2],agitation:[0.2,0.6],size:[0.65,1],movement:[0.05,0.4],scatter:[0.15,0.6]}},
        {name:'Drone Patrol',id:'drone_patrol',tip:'A formation of small flying machines.',values:{kind:2,duration:[1.6,3.8],count:[3,8],speed:[0.15,0.55],cohesion:[0.55,0.95],agitation:[0.02,0.25],size:[0.5,0.95],movement:[0.7,1],scatter:[0,0.3]}},
        {name:'Fairy Flock',id:'fairy_flock',tip:'A small migrating cloud of shimmering voices.',values:{kind:4,duration:[1.4,3.3],count:[6,17],speed:[0.1,0.35],cohesion:[0.4,0.85],agitation:[0.1,0.4],size:[0.1,0.5],movement:[0.15,0.65],scatter:[0.1,0.6]}},
        {name:'Locusts',id:'locusts',tip:'A dense, restless wing cloud.',values:{kind:0,duration:[1.5,3.3],count:[22,32],speed:[0.65,1],cohesion:[0,0.22],agitation:[0.65,1],size:[0.05,0.3],movement:[0.1,0.55],scatter:[0,0.3]}},
        {name:'Seeking Missiles',id:'seeking_missiles',tip:'Several tiny rockets rush past.',values:{kind:5,duration:[0.7,1.8],count:[3,7],speed:[0.6,1],cohesion:[0.2,0.65],agitation:[0.4,0.9],size:[0.2,0.7],movement:[0.8,1],scatter:[0.2,0.9]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        if(name==='count'&&Number.isFinite(value))value=Math.round(value);
        super.set_param(name,value,checkLocked);
    }
}
