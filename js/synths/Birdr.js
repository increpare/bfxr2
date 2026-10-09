class Birdr extends PresetSynth {
    name = 'Birdr';
    canvas_bg_logo = 'img/logo_birdr.png';
    tooltip = 'Birdsong, chirps, trills and wild calls in short phrases.';
    static DSP = Birdr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'voice',display_name:'Voice',tooltip:'The way the syrinx and beak shape the call.',default_value:0,columns:3,
            values:[['Whistle','A clear, single-voiced song.',0],['Twin','Two interacting sides of the syrinx.',1],
                ['Reed','A bright, nasal squawk.',2],['Rasp','A rough, throaty caw.',3],['Hoot','A rounded, hollow hoot.',4]]},
        ['Duration','Seconds for the complete phrase.','duration',0.8,0.15,5],
        ['Pitch','The pitch of the bird, from low hoots to tiny chirps.','pitch',0.58,0,1],
        ['Syllables','Number of separate calls in the phrase.','syllables',3,1,16],
        ['Gap','Breathing space between syllables.','gap',0.3,0,0.85],
        ['Sweep','A falling or rising pitch sweep within each syllable.','sweep',-0.3,-1,1],
        ['Arch','An upward or downward curve through each syllable.','arch',0.45,-1,1],
        ['Trill','Depth of rapid pitch and breath pulses.','trill',0.15,0,1],
        ['Trill Rate','Speed of the trill inside each syllable.','trill_rate',0.4,0,1],
        ['Duet','Amount of the second voice; Twin makes it interact with the first.','duet',0.1,0,1],
        ['Rasp','Uneven vocal fold vibration and rough overtones.','rasp',0.04,0,1],
        ['Breath','Air flowing past the beak.','breath',0.03,0,1],
        ['Rhythm','Uneven timing of the syllables.','rhythm',0.12,0,1],
        ['Phrase','Pitch and articulation changes across the phrase.','variation',0.25,0,1]
    ];
    recipes = [
        {name:'Chirp',id:'chirp',tip:'One quick, bright call.',values:{voice:0,duration:[0.15,0.32],pitch:[0.57,0.78],syllables:1,gap:[0.08,0.2],sweep:[-0.75,0.65],arch:[0.25,0.9],trill:[0,0.1],duet:[0,0.08],rasp:[0,0.05],breath:[0.01,0.06]}},
        {name:'Sparrow',id:'sparrow',tip:'A handful of short, chattering chirps.',values:{voice:1,duration:[0.45,1],pitch:[0.6,0.77],syllables:[3,6],gap:[0.35,0.58],sweep:[-0.6,-0.1],arch:[0.3,0.8],trill:[0.05,0.2],duet:[0.1,0.3],rasp:[0.08,0.25],rhythm:[0.25,0.6],variation:[0.1,0.35]}},
        {name:'Songbird',id:'songbird',tip:'A lilting phrase with a repeated contour.',values:{voice:0,duration:[0.7,1.5],pitch:[0.45,0.67],syllables:[3,6],gap:[0.2,0.4],sweep:[-0.2,0.45],arch:[0.35,0.8],trill:[0.1,0.35],trill_rate:[0.15,0.5],duet:[0.02,0.17],variation:[0.4,0.8],rhythm:[0.15,0.45]}},
        {name:'Canary',id:'canary',tip:'A bright, fast rolled whistle.',values:{voice:0,duration:[0.45,1.1],pitch:[0.58,0.76],syllables:[1,3],gap:[0.1,0.22],sweep:[-0.15,0.25],arch:[0.1,0.4],trill:[0.55,0.9],trill_rate:[0.65,1],breath:[0,0.04],rasp:[0,0.03],variation:[0.1,0.4]}},
        {name:'Warbler',id:'warbler',tip:'Two syringeal voices weave a bubbling phrase.',values:{voice:1,duration:[0.65,1.4],pitch:[0.4,0.64],syllables:[3,7],gap:[0.08,0.3],sweep:[-0.4,0.4],arch:[-0.5,0.7],trill:[0.3,0.65],trill_rate:[0.2,0.65],duet:[0.45,0.85],variation:[0.35,0.85],rhythm:[0.2,0.6]}},
        {name:'Parrot',id:'parrot',tip:'A nasal, raspy squawk.',values:{voice:2,duration:[0.3,0.8],pitch:[0.27,0.48],syllables:[1,2],gap:[0.15,0.35],sweep:[-0.6,0.2],arch:[0.3,0.8],trill:[0.15,0.4],duet:[0.15,0.45],rasp:[0.35,0.65],breath:[0.1,0.25]}},
        {name:'Crow',id:'crow',tip:'A hoarse caw with a falling throat.',values:{voice:3,duration:[0.4,1.25],pitch:[0.12,0.3],syllables:[1,3],gap:[0.28,0.48],sweep:[-0.5,-0.15],arch:[0.15,0.45],trill:[0.12,0.32],duet:[0.05,0.2],rasp:[0.55,0.9],breath:[0.08,0.2],variation:[0.05,0.2]}},
        {name:'Owl',id:'owl',tip:'A mellow, hollow hoot.',values:{voice:4,duration:[0.55,1.4],pitch:[0.06,0.23],syllables:[1,3],gap:[0.2,0.4],sweep:[-0.18,0.04],arch:[0.05,0.2],trill:[0.01,0.1],duet:[0,0.06],rasp:[0,0.03],breath:[0.03,0.09],variation:[0.05,0.18]}},
        {name:'Cuckoo',id:'cuckoo',tip:'A paired hollow call with a lower answer.',values:{voice:4,duration:[0.45,0.9],pitch:[0.22,0.35],syllables:2,gap:[0.28,0.4],sweep:[-0.05,0.04],arch:[0.01,0.08],trill:[0,0.035],duet:[0,0.04],rasp:[0,0.02],breath:[0.015,0.045],variation:[0.35,0.5],rhythm:[0,0.08]}},
        {name:'Loon',id:'loon',tip:'A short, rising lake call with a second voice.',values:{voice:1,duration:[0.7,1.7],pitch:[0.25,0.41],syllables:[1,2],gap:[0.08,0.22],sweep:[0.3,0.7],arch:[0.1,0.4],trill:[0.08,0.25],trill_rate:[0.1,0.3],duet:[0.2,0.5],rasp:[0.01,0.08],breath:[0.02,0.08],variation:[0.1,0.3]}}
    ];
    constructor() { super(); this.initialize_presets(); }
    randomize_params() { this.create_random_template(); }
    set_param(name,value,checkLocked=false) {
        super.set_param(name,value,checkLocked);
        if (name==='syllables' && !(checkLocked && this.locked_params[name])) this.params.syllables=Math.round(this.params.syllables);
    }
}
