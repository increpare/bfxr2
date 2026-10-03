class Crittr extends PresetSynth {
    name = 'Crittr';
    tooltip = 'Nonverbal beasts, tiny companions and impossible wildlife.';
    static DSP = Crittr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'voice',display_name:'Anatomy',tooltip:'The source and throat shape of the creature.',
            default_value:0,columns:3,values:[['Throat','A warm, pulsing throat.',0],['Beak','A sharp, ringing chirp.',1],
                ['Gills','A hollow, bubbling voice.',2],['Chitin','A thin, buzzing stridulation.',3],
                ['Spirit','A soft, airy singing call.',4],['Clockwork','A metallic artificial throat.',5],['Dog','A chesty bark with a fast breath attack.',6],
                ['Cat','A voiced meow with a closing mouth.',7]]},
        ['Duration','Length of the complete call, in seconds.','duration',1.2,0.15,5],
        ['Pitch','The vibration rate of the creature\'s voice.','pitch',0.45,0,1],
        ['Throat Size','Small throats ring high; large throats resonate deeply.','size',0.45,0,1],
        ['Evolution','How far the throat opens and changes during each call.','morph',0.45,0,1],
        ['Calls','Number of separate vocal gestures.','calls',2,1,12],
        ['Call Gap','The portion of each gesture left for a pause.','gap',0.2,0,0.85],
        ['Pitch Bend','Falling grunts to rising yelps within each gesture.','contour',0.25,-1,1],
        ['Growl','Adds slower vocal folds below the main pitch.','growl',0.2,0,1],
        ['Breath','Air and rasp passing through the throat.','breath',0.15,0,1],
        ['Flutter','From a steady voice to rapid trills and trembling.','flutter',0.2,0,1]
    ];
    recipes = [
        {name:'Hurt',id:'hurt',verb:'hurt',tip:'A short yelp from a creature.',values:{voice:[0,6,7],duration:[0.2,0.5],pitch:[0.3,0.6],size:[0.3,0.7],morph:[0.5,1],calls:1,gap:[0.05,0.2],contour:[-0.8,-0.3],growl:[0.1,0.5],breath:[0.2,0.5],flutter:[0.05,0.3]}},
        {name:'Roar',id:'roar',verb:'roar',tip:'A big creature announcing itself: growl, screech, pulsed bellow, layered roar or a monster cry.',values:{},variants:[
            {voice:[0,6],duration:[0.6,1.8],pitch:[0.05,0.3],size:[0.65,1],morph:[0.5,1],calls:1,gap:[0.03,0.15],contour:[-0.5,0.2],growl:[0.6,1],breath:[0.2,0.5],flutter:[0.05,0.3]},
            {voice:[1,3],duration:[0.5,1.3],pitch:[0.55,0.85],size:[0.1,0.4],morph:[0.6,1],calls:[1,2],gap:[0.05,0.2],contour:[0.2,0.9],growl:[0.3,0.7],breath:[0.3,0.7],flutter:[0.3,0.8]},
            {voice:[0,2],duration:[0.8,2],pitch:[0.02,0.2],size:[0.8,1],morph:[0.2,0.6],calls:[3,6],gap:[0.15,0.4],contour:[-0.3,0.1],growl:[0.8,1],breath:[0.1,0.3],flutter:[0.4,0.9]},
            {voice:[0,6,2],duration:[1,2.4],pitch:[0.1,0.4],size:[0.6,1],morph:[0.8,1],calls:1,gap:[0.02,0.1],contour:[0.4,1],growl:[0.5,1],breath:[0.3,0.7],flutter:[0.1,0.5]},
            {voice:[7,4,5],duration:[0.4,1],pitch:[0.3,0.6],size:[0.3,0.7],morph:[0.5,1],calls:[1,2],gap:[0.05,0.25],contour:[-0.9,-0.4],growl:[0.2,0.6],breath:[0.1,0.4],flutter:[0.4,0.9]}]},
        {name:'Confirm',id:'confirm',verb:'confirm',tip:'A small friendly rising chirrup.',values:{voice:[5,4],duration:[0.2,0.4],pitch:[0.45,0.65],size:[0.15,0.4],morph:[0.3,0.6],calls:1,gap:[0.1,0.3],contour:[0.3,0.7],growl:0,breath:[0,0.05],flutter:[0,0.15]}},
        {name:'Lose',id:'lose',verb:'lose',tip:'A drooping whimper.',values:{voice:[0,7],duration:[0.5,1.2],pitch:[0.35,0.6],size:[0.25,0.55],morph:[0.4,0.8],calls:[1,2],gap:[0.1,0.3],contour:[-0.9,-0.5],growl:[0,0.15],breath:[0.1,0.3],flutter:[0.2,0.5]}},
        {name:'Woof',id:'woof',tip:'A short bark, from a small yap to a chesty woof.',values:{voice:6,duration:[0.23,0.65],pitch:[0.18,0.43],size:[0.4,0.85],morph:[0.45,0.85],calls:1,gap:[0.06,0.18],contour:[-0.7,-0.25],growl:[0.18,0.5],breath:[0.14,0.35],flutter:[0.01,0.13]}},
        {name:'Meow',id:'meow',tip:'A rising, nasal meow relaxing into a rounded vowel.',values:{voice:7,duration:[0.35,0.95],pitch:[0.48,0.66],size:[0.24,0.52],morph:[0.65,1],calls:1,gap:[0.03,0.14],contour:[-0.35,0.1],growl:[0.01,0.12],breath:[0.01,0.09],flutter:[0.02,0.13]}},
        {name:'Tiny Dragon',id:'tiny_dragon',tip:'A little chirrup with a smoky throat.',values:{voice:1,duration:[0.45,1.2],pitch:[0.53,0.76],size:[0.1,0.35],morph:[0.45,0.95],calls:[1,3],gap:[0.16,0.36],contour:[-0.75,0.5],growl:[0.1,0.35],breath:[0.08,0.3],flutter:[0.04,0.2]}},
        {name:'Cave Beast',id:'cave_beast',tip:'A huge, uneven rumble from the dark.',values:{voice:0,duration:[1.1,2.9],pitch:[0.04,0.26],size:[0.7,1],morph:[0.5,1],calls:[1,2],gap:[0.05,0.25],contour:[-0.55,0.1],growl:[0.65,1],breath:[0.18,0.5],flutter:[0.08,0.3]}},
        {name:'Alien Purr',id:'alien_purr',tip:'A small contented creature with too many vocal folds.',values:{voice:2,duration:[1,2.4],pitch:[0.26,0.49],size:[0.25,0.65],morph:[0.2,0.55],calls:[1,3],gap:[0.02,0.16],contour:[-0.15,0.15],growl:[0.4,0.8],breath:[0.02,0.16],flutter:[0.65,0.95]}},
        {name:'Insect Call',id:'insect_call',tip:'A bright wing rasp in short phrases.',values:{voice:3,duration:[0.6,1.9],pitch:[0.7,0.94],size:[0.02,0.26],morph:[0.05,0.4],calls:[3,8],gap:[0.25,0.65],contour:[-0.12,0.17],growl:[0,0.05],breath:[0.1,0.3],flutter:[0.6,1]}},
        {name:'Ghost Whale',id:'ghost_whale',tip:'A long, hollow voice rising out of the deep.',values:{voice:4,duration:[2.3,4.5],pitch:[0.22,0.43],size:[0.68,1],morph:[0.65,1],calls:[1,2],gap:[0.02,0.15],contour:[0.45,0.95],growl:[0.12,0.4],breath:[0.12,0.32],flutter:[0.03,0.2]}},
        {name:'Clockwork Pet',id:'clockwork_pet',tip:'An eager little mechanical companion.',values:{voice:5,duration:[0.4,1.25],pitch:[0.45,0.72],size:[0.12,0.45],morph:[0.2,0.7],calls:[2,5],gap:[0.15,0.4],contour:[0.2,0.8],growl:[0.03,0.18],breath:[0,0.09],flutter:[0.12,0.45]}},
        {name:'Forest Spirit',id:'forest_spirit',tip:'A breathy, flickering woodland call.',values:{voice:4,duration:[0.9,2.3],pitch:[0.48,0.77],size:[0.2,0.5],morph:[0.4,0.85],calls:[2,4],gap:[0.16,0.4],contour:[-0.3,0.5],growl:[0.02,0.18],breath:[0.35,0.7],flutter:[0.25,0.6]}},
        {name:'Angry Blob',id:'angry_blob',tip:'An indignant, rubbery bubbling protest.',values:{voice:2,duration:[0.45,1.4],pitch:[0.14,0.38],size:[0.45,0.85],morph:[0.65,1],calls:[2,5],gap:[0.15,0.35],contour:[-0.85,-0.3],growl:[0.5,0.9],breath:[0.03,0.18],flutter:[0.15,0.5]}}
    ];
    constructor() { super(); this.initialize_presets(); }
    randomize_params() {
        this.create_random_template();
        // Randomize is a one-shot explorer; longer recipe buttons and manual edits remain available.
        if (this.params.duration>1.5) this.set_param('duration',0.55+Math.random()*0.85,true);
    }
    set_param(name,value,checkLocked=false) {
        super.set_param(name,value,checkLocked);
        if (name==='calls' && !(checkLocked && this.locked_params[name])) {
            this.params.calls=Math.round(this.params.calls);
        }
    }
}
