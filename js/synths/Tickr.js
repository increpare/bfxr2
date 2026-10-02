class Tickr extends PresetSynth {
    name='Tickr';
    tooltip='Counters, progress, ratchets and a final little payoff.';
    static DSP=Tickr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'kind',display_name:'Tick',tooltip:'The individual contact in the sequence.',default_value:2,columns:3,header:true,
            values:[['Click','A dry contact.',0],['Coin','A small metallic ring.',1],['Bleep','A clean electronic tick.',2],['Ratchet','A rough mechanical tooth.',3],['Pulse','A soft rounded pulse.',4]]},
        ['Duration','Seconds, including the finish.','duration',1.2,0.15,5],
        ['Count','Number of individual ticks.','count',12,1,48],
        ['Acceleration','Negative slows down; positive speeds up.','acceleration',0.4,-1,1],
        ['Pitch','Starting pitch.','pitch',0.45,0,1],
        ['Pitch Rise','How far the ticks climb or fall.','rise',0.5,-1,1],
        ['Decay','How long each tick rings.','decay',0.3,0,1],
        ['Brightness','Upper harmonics and sharper contacts.','brightness',0.5,0,1],
        ['Jitter','Small irregularities in the timing.','jitter',0.05,0,1],
        ['Finish','Level of the separate completion cue.','finish',0.5,0,1]
    ];
    recipes=[
        {name:'Count Coins',id:'count_coins',tip:'A pocketful of rewards adds up.',values:{kind:1,duration:[0.7,1.8],count:[8,24],acceleration:[0.35,0.85],pitch:[0.48,0.7],rise:[0.2,0.6],decay:[0.12,0.3],brightness:[0.35,0.75],jitter:[0,0.15],finish:[0.3,0.65]}},
        {name:'Level Fill',id:'level_fill',tip:'A bar fills and lands on its new level.',values:{kind:2,duration:[1,2.4],count:[15,35],acceleration:[0.35,0.8],pitch:[0.25,0.45],rise:[0.6,1],decay:[0.1,0.28],brightness:[0.15,0.45],jitter:[0,0.04],finish:[0.55,0.85]}},
        {name:'Combo Build',id:'combo_build',tip:'A run of actions gains momentum.',values:{kind:4,duration:[0.4,1.1],count:[5,12],acceleration:[0.4,1],pitch:[0.3,0.6],rise:[0.3,0.75],decay:[0.12,0.3],brightness:[0.35,0.75],jitter:[0,0.07],finish:[0.15,0.5]}},
        {name:'Countdown',id:'countdown',tip:'Spaced pulses tighten toward a cue.',values:{kind:2,duration:[1.7,3.5],count:[3,7],acceleration:[0,0.25],pitch:[0.25,0.5],rise:[-0.15,0.15],decay:[0.25,0.55],brightness:[0.05,0.3],jitter:[0,0.015],finish:[0.6,1]}},
        {name:'Research',id:'research',tip:'Quiet calculation followed by a small result.',values:{kind:4,duration:[1.2,2.7],count:[12,30],acceleration:[-0.1,0.3],pitch:[0.38,0.6],rise:[0.1,0.45],decay:[0.05,0.2],brightness:[0,0.3],jitter:[0.1,0.35],finish:[0.2,0.5]}},
        {name:'Scan',id:'scan',tip:'A scanner races across its target.',values:{kind:0,duration:[0.4,1.1],count:[18,40],acceleration:[0.4,0.95],pitch:[0.45,0.8],rise:[-0.6,-0.2],decay:[0,0.1],brightness:[0.35,0.8],jitter:[0,0.1],finish:[0.1,0.35]}},
        {name:'Lockpick',id:'lockpick',tip:'Teeth pass through a lock and catch.',values:{kind:3,duration:[0.7,1.7],count:[7,19],acceleration:[-0.65,0.35],pitch:[0.15,0.4],rise:[-0.25,0.2],decay:[0,0.15],brightness:[0.25,0.65],jitter:[0.25,0.85],finish:[0.05,0.25]}},
        {name:'Download',id:'download',tip:'A tight data counter resolving into a ping.',values:{kind:2,duration:[0.6,1.8],count:[22,48],acceleration:[0.45,1],pitch:[0.4,0.65],rise:[0.2,0.65],decay:[0.02,0.12],brightness:[0.4,0.85],jitter:[0.03,0.18],finish:[0.4,0.75]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='count'&&!(checkLocked&&this.locked_param(name)))this.params.count=Math.round(this.params.count);
    }
}
