class Chattr extends SynthBase {
    name = 'Chattr';
    version = '2.0.0';
    tooltip = 'Little voices for imaginary friends.';
    header_properties = ['text', 'texture'];
    permalocked = ['masterVolume', 'text'];
    hide_params = ['masterVolume'];
    param_info = [
        ['Sound Volume', 'Overall volume of this voice.', 'masterVolume', 0.5, 0, 1],
        {type:'TEXT', name:'text', display_name:'Something to say', default_value:'Oh! A tiny visitor. Hello there!', max_length:Chattr_DSP.maxLength, header:true},
        {type:'BUTTONSELECT', name:'texture', display_name:'Voice', tooltip:'Three source colors, all shaped by the same speaking mouth.',
            default_value:0, columns:3, header:true, values:[
                ['Babble','A warm, buzzy little voice.',0],
                ['Squeak','A softer, rounder voice.',1], ['Bleep','Bright, electronic speech.',2]]},
        ['Articulation', 'Loose vowel chatter on the left; full English consonants and connected speech on the right. The words keep their pronunciation.', 'articulation', 0.8, 0, 1],
        ['Pitch', 'Low and cuddly to tiny and squeaky.', 'pitch', 0.58, 0, 1],
        ['Mouth size', 'Small bright vowels to a big, hollow voice. Independent of pitch.', 'mouth', 0.42, 0, 1],
        ['Chatter speed', 'Unhurried mumbling to a breathless stream of chatter.', 'speed', 0.5, 0, 1],
        ['Expression', 'Steady delivery to lively, melodic syllables. Questions rise; exclamations perk up.', 'expression', 0.7, 0, 1],
        ['Inflection', 'Syllables swoop down on the left and curl up on the right.', 'inflection', 0.1, -1, 1],
        ['Wobble', 'A little quiver, or a very wobbly creature.', 'wobble', 0.18, 0, 1],
        ['Breath', 'Airy, hushed edges to the voice.', 'breath', 0.12, 0, 1],
        ['Grit', 'A fuzzy growl for grumpy creatures and old radios.', 'grit', 0.12, 0, 1],
        ['Word spacing', 'Run words together, or leave thoughtful pauses.', 'spacing', 0.28, 0, 1],
        ['Personality', 'Change the repeatable melody and timing while keeping the same pronunciation.', 'seed', 0.37, 0, 1]
    ];

    static characters = [
        {id:'clear_speaker',name:'Clear Speaker',tip:'A neutral voice for hearing the words before making them strange.',params:{articulation:1,pitch:0.35,mouth:0.5,speed:0.42,expression:0.25,inflection:0,wobble:0,breath:0,grit:0,spacing:0.3}},
        {id:'village_mouse',name:'Village Mouse',tip:'A bright little neighbour with a lot to tell you.',params:{pitch:0.65,mouth:0.27,speed:0.62,expression:0.75}},
        {id:'sleepy_bear',name:'Sleepy Bear',tip:'Warm, low, and in no particular hurry.',params:{pitch:0.12,mouth:0.9,speed:0.12,expression:0.3,grit:0.4,spacing:0.65}},
        {id:'pocket_robot',name:'Pocket Robot',tip:'A helpful box of beeps.',params:{texture:2,pitch:0.4,mouth:0.5,speed:0.6,expression:0.18,inflection:0,wobble:0,breath:0,spacing:0.48}},
        {id:'moon_frog',name:'Moon Frog',tip:'A rubbery croak from the lily pond on the moon.',params:{pitch:0.26,mouth:0.76,speed:0.34,expression:0.8,inflection:-0.72,wobble:0.8,grit:0.55}},
        {id:'dust_sprite',name:'Dust Sprite',tip:'A shy, airy squeak from under the sofa.',params:{texture:1,pitch:0.86,mouth:0.12,speed:0.48,expression:0.8,breath:0.52,wobble:0.32,grit:0}},
        {id:'busy_duck',name:'Busy Duck',tip:'Nasal, excitable, and late for something.',params:{pitch:0.53,mouth:0.6,speed:0.88,expression:1,inflection:0.5,grit:0.48,spacing:0.1}},
        {id:'tiny_alien',name:'Tiny Alien',tip:'Curious bubbles from a faraway place.',params:{texture:1,pitch:0.52,mouth:0.8,speed:0.32,expression:0.9,inflection:0.85,wobble:0.65,spacing:0.48}},
        {id:'old_radio',name:'Old Radio',tip:'A fuzzy little transmission with something to announce.',params:{texture:2,pitch:0.25,mouth:0.25,speed:0.55,expression:0.4,breath:0.65,grit:0.88,wobble:0.1}}
    ];
    static phrases = [
        'Oh! A tiny visitor. Hello there!', 'I found a very good stick. It is for you.',
        'One mushroom, two mushrooms... soup!', 'Psst. The moon is made of pudding.',
        'Welcome back! I saved you a seat.', 'Beep boop. Friendship detected!',
        'Is that a hat, or a very small boat?', 'Hmm... yes. An excellent pebble.'
    ];
    templates = [
        ...Chattr.characters.map(c=>[c.name,c.tip,'generate_'+c.id,c.name.replace(/ /g,'')]),
        ['Randomize','Meet someone new. Your words and locked controls stay put.','randomize_params','NewFriend'],
        ['Mutate','A slightly different mood for this voice.','mutate_params','NewMood']
    ];

    constructor() {
        super();
        this.post_initialize();
        for (const character of Chattr.characters) this['generate_'+character.id] = () => this.generate_character(character.id);
    }

    apply_params(params, check_locked = false) {
        if (!params || typeof params !== 'object') return;
        // Complete voices saved before articulation existed always get the same default,
        // independent of whichever voice happens to be selected when they are opened.
        if (!Object.prototype.hasOwnProperty.call(params,'articulation') &&
            ['text','texture','pitch','mouth','speed','expression','inflection','wobble','breath','grit','spacing','seed','masterVolume']
                .every(name => Object.prototype.hasOwnProperty.call(params,name))) this.set_param('articulation',0.8,check_locked);
        for (const info of this.param_info) {
            const name = this.get_param_normalized(info).name;
            if (Object.prototype.hasOwnProperty.call(params,name)) this.set_param(name,params[name],check_locked);
        }
    }

    generate_character(id, vary = true) {
        const character = Chattr.characters.find(c=>c.id===id);
        if (!character) return;
        const words = this.params.text;
        this.reset_params(true);
        this.apply_params(character.params,true);
        if (vary) this.set_param('seed',Math.random(),true);
        this.set_param('text',words);
    }

    create_random_template() {
        // A welcoming first voice, rather than a random mode on first opening.
        this.generate_character('village_mouse',false);
        return ['VillageMouse',this.params];
    }

    randomize_params() {
        const words = this.params.text;
        super.randomize_params();
        this.set_param('text',words);
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.score = Chattr_DSP.schedule(this.params);
        this.sound = RealizedSound.from_buffer(Chattr_DSP.render(this.params,this.score));
        this.sound_params = JSON.stringify(this.params);
    }
}
