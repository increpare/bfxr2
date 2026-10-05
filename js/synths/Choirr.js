class Choirr extends PresetSynth {
    name='Choirr';
    canvas_bg_logo = 'img/logo_choirr.png';
    tooltip='Sustained vowel ensembles, spectral choirs and wordless chords.';
    static DSP=Choirr_DSP;
    param_info=[PresetSynth.common_params[0],
        ['Ensemble Seed','Changes each singer’s tuning, vocal colour, vibrato timing, entrance and breath noise. Keeps the chord and root pitch.','seed',0.5,0,1],
        {type:'BUTTONSELECT',name:'harmony',display_name:'Harmony',tooltip:'Notes shared across the singers.',default_value:1,columns:3,values:[['Unison','Every singer holds the same note.',0],['Major','A bright major chord.',1],['Minor','A dark minor chord.',2],['Fifths','Open fifths and octaves.',3],['Cluster','Close and dissonant intervals.',4]]},
        ['Duration','Complete ensemble swell, in seconds.','duration',2.5,0.15,5],
        ['Pitch','Root note of the ensemble.','pitch',0.5,0,1],
        ['Singers','Independent vocal sources.','voices',6,1,12],
        ['Vowel','Morphs from oo through ah to ee.','vowel',0.35,0,1],
        ['Detune','Spread individual singers around their notes.','detune',0.4,0,1],
        ['Swell','Rounded attack and release of the held chord.','swell',0.5,0,1],
        ['Breath','Air mixed into every voice.','breath',0.1,0,1],
        ['Living Motion','Independent vibrato and gently shifting levels.','motion',0.4,0,1]
    ];
    recipes=[
        {name:'Angelic',id:'angelic',tip:'A bright, gently breathing major chorus.',values:{harmony:1,duration:[2.5,4.5],pitch:[0.45,0.66],voices:[6,10],vowel:[0.18,0.4],detune:[0.18,0.4],swell:[0.45,0.75],breath:[0.06,0.2],motion:[0.2,0.5]}},
        {name:'Ominous',id:'ominous',tip:'A low minor chord behind the door.',values:{harmony:2,duration:[2.6,4.8],pitch:[0.06,0.27],voices:[5,9],vowel:[0.08,0.32],detune:[0.35,0.7],swell:[0.25,0.6],breath:[0.08,0.24],motion:[0.15,0.45]}},
        {name:'Monks',id:'monks',tip:'Low voices holding an open fifth.',values:{harmony:3,duration:[2,4.5],pitch:[0.12,0.31],voices:[3,7],vowel:[0.28,0.55],detune:[0.1,0.3],swell:[0.1,0.35],breath:[0.01,0.12],motion:[0.08,0.25]}},
        {name:'Fairy Choir',id:'fairy_choir',tip:'Small, high singers in a shimmering chord.',values:{harmony:1,duration:[1.2,2.7],pitch:[0.66,0.9],voices:[5,10],vowel:[0.55,0.87],detune:[0.35,0.7],swell:[0.3,0.65],breath:[0.06,0.2],motion:[0.55,0.9]}},
        {name:'Robot Choir',id:'robot_choir',tip:'Steady synthetic vowel generators in unison.',values:{harmony:0,duration:[0.8,2.3],pitch:[0.32,0.62],voices:[3,8],vowel:[0.4,0.95],detune:[0,0.08],swell:[0.02,0.15],breath:[0,0.025],motion:[0,0.05]}},
        {name:'Ghost Chord',id:'ghost_chord',tip:'An airy minor chorus that fades into view.',values:{harmony:2,duration:[2.4,4.8],pitch:[0.34,0.57],voices:[7,12],vowel:[0.04,0.22],detune:[0.5,0.9],swell:[0.6,1],breath:[0.4,0.75],motion:[0.4,0.8]}},
        {name:'Victory Chord',id:'victory_chord',tip:'A full, open ah announcing success.',values:{harmony:1,duration:[0.8,2],pitch:[0.35,0.57],voices:[8,12],vowel:[0.4,0.58],detune:[0.12,0.32],swell:[0.15,0.4],breath:[0.02,0.1],motion:[0.15,0.4]}},
        {name:'Void Voices',id:'void_voices',tip:'An unsettled cluster of low, wordless voices.',values:{harmony:4,duration:[2.4,4.9],pitch:[0.03,0.25],voices:[6,12],vowel:[0.45,0.8],detune:[0.65,1],swell:[0.3,0.7],breath:[0.15,0.5],motion:[0.6,1]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='voices'&&!(checkLocked&&this.locked_params[name]))this.params.voices=Math.round(this.params.voices);}
}
