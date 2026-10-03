class Pulser extends PresetSynth {
    name='Pulser';
    tooltip='Paired heart thuds, low-health warnings and uneasy living machinery.';
    static DSP=Pulser_DSP;
    param_info=[...PresetSynth.common_params,
        ['Duration','Complete pulse sequence, in seconds.','duration',1.5,0.2,5],
        ['Beats','Number of paired pressure pulses.','beats',3,1,12],
        ['Pitch','From a low chest thud to a small, hard pump.','pitch',0.35,0,1],
        ['Size','How long the pressure contact resonates.','size',0.5,0,1],
        ['Second Beat','Strength of the second chamber in each pair.','secondary',0.6,0,1],
        ['Separation','Time between the two contacts in each beat.','separation',0.35,0,1],
        ['Murmur','Turbulent flow swelling between contacts.','murmur',0.1,0,1],
        ['Tension','Harder valve contacts and rough mechanical overtones.','tension',0.2,0,1],
        ['Irregularity','Uneven spacing between successive beats.','irregular',0.05,0,1]
    ];
    recipes=[
        {name:'Heartbeat',id:'heartbeat',tip:'A close, rounded double heartbeat.',values:{duration:[1.5,2.8],beats:[2,4],pitch:[0.11,0.29],size:[0.41,0.59],secondary:[0.56,0.74],separation:[0.26,0.44],murmur:[0.03,0.21],tension:[0.01,0.19],irregular:[0,0.13]}},
        {name:'Panic',id:'panic',tip:'Urgent, hard pulses for danger or low health.',values:{duration:[1.1,1.8],beats:[4,6],pitch:[0.3,0.48],size:[0.21,0.39],secondary:[0.71,0.89],separation:[0.12,0.28],murmur:[0.16,0.34],tension:[0.51,0.69],irregular:[0.11,0.29]}},
        {name:'Giant Heart',id:'giant_heart',tip:'Slow, heavy chambers inside a huge creature.',values:{duration:[2.5,4],beats:[2,3],pitch:[0,0.14],size:[0.81,0.99],secondary:[0.61,0.79],separation:[0.46,0.64],murmur:[0.11,0.29],tension:[0.11,0.29],irregular:[0,0.14]}},
        {name:'Android Core',id:'android_core',tip:'A small, sharp mechanical pressure pump.',values:{duration:[0.7,1.6],beats:[3,6],pitch:[0.66,0.84],size:[0.16,0.34],secondary:[0.41,0.59],separation:[0.06,0.24],murmur:[0,0.12],tension:[0.71,0.89],irregular:[0,0.11]}},
        {name:'Poison',id:'poison',tip:'An uneven throb through rough, rushing fluid.',values:{duration:[1.5,3],beats:[3,5],pitch:[0.21,0.39],size:[0.51,0.69],secondary:[0.31,0.49],separation:[0.41,0.59],murmur:[0.56,0.74],tension:[0.41,0.59],irregular:[0.66,0.84]}},
        {name:'Underwater',id:'underwater',tip:'A muffled internal pulse with liquid flow.',values:{duration:[1.8,3.2],beats:[2,4],pitch:[0.01,0.19],size:[0.66,0.84],secondary:[0.56,0.74],separation:[0.56,0.74],murmur:[0.36,0.54],tension:[0,0.17],irregular:[0.03,0.21]}},
        {name:'Energy Core',id:'energy_core',tip:'A tense reactor shudder with a strong return pulse.',values:{duration:[0.8,2],beats:[3,6],pitch:[0.51,0.69],size:[0.46,0.64],secondary:[0.76,0.94],separation:[0.26,0.44],murmur:[0.06,0.24],tension:[0.76,0.94],irregular:[0,0.14]}},
        {name:'Last Life',id:'last_life',tip:'A faltering warning, with a weak second beat.',values:{duration:[1.8,3.4],beats:[2,4],pitch:[0.06,0.24],size:[0.71,0.89],secondary:[0.21,0.39],separation:[0.56,0.74],murmur:[0.26,0.44],tension:[0.26,0.44],irregular:[0.76,0.94]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='beats'&&!(checkLocked&&this.locked_param(name)))this.params.beats=Math.round(this.params.beats);}
}
