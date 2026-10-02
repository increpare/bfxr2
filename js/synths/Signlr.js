class Signlr extends PresetSynth {
    name = 'Signlr';
    tooltip = 'Coded transmissions, derelict beacons and mysterious receivers.';
    static DSP = Signlr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'encoding',display_name:'Encoding',tooltip:'How each symbol changes the carrier.',
            default_value:0,columns:4,values:[['FSK','Bits switch between two frequencies.',0],['Phase','Bits turn the phase of a carrier.',1],
                ['Chirp','Each symbol is a swept sonar pulse.',2],['Radio','A fluttering, filtered receiver.',3]]},
        ['Duration','Length of the transmission, in seconds.','duration',1.4,0.15,5],
        ['Carrier','The central transmission frequency.','carrier',0.55,0,1],
        ['Deviation','Frequency spread or depth of phase coding.','deviation',0.35,0,1],
        ['Symbol Rate','From slow beacon characters to rapid data.','symbols',0.4,0,1],
        ['Packets','Number of separately keyed transmission bursts.','packets',3,1,12],
        ['Packet Gap','The portion of each packet left for silence.','gap',0.25,0,0.85],
        ['Drift','A carrier falling or climbing over the transmission.','drift',0,-1,1],
        ['Corruption','Lost symbols and unstable tuning.','corruption',0.08,0,1],
        ['Interference','Receiver static and a nearby unwanted carrier.','interference',0.08,0,1],
        ['Echo','Delayed copies bouncing back from the channel.','echo',0.15,0,1]
    ];
    recipes = [
        {name:'Derelict Beacon',id:'derelict_beacon',tip:'A tired navigation beacon still repeating its code.',values:{encoding:0,duration:[1.4,3.2],carrier:[0.22,0.45],deviation:[0.06,0.2],symbols:[0.02,0.15],packets:[2,4],gap:[0.4,0.7],drift:[-0.22,-0.04],corruption:[0.05,0.18],interference:[0.04,0.2],echo:[0.35,0.65]}},
        {name:'Alien Handshake',id:'alien_handshake',tip:'An unfamiliar exchange of shifting coded phrases.',values:{encoding:0,duration:[0.65,1.7],carrier:[0.48,0.75],deviation:[0.5,0.95],symbols:[0.25,0.58],packets:[2,5],gap:[0.1,0.35],drift:[-0.3,0.4],corruption:[0,0.1],interference:[0,0.08],echo:[0.08,0.35]}},
        {name:'Distress Burst',id:'distress_burst',tip:'Urgent short packets through a damaged channel.',values:{encoding:0,duration:[0.6,1.5],carrier:[0.45,0.66],deviation:[0.1,0.28],symbols:[0.05,0.22],packets:[3,6],gap:[0.3,0.56],drift:[-0.08,0.08],corruption:[0,0.08],interference:[0.08,0.25],echo:[0.05,0.25]}},
        {name:'Broken Radio',id:'broken_radio',tip:'Fragments of a wavering receiver amid static.',values:{encoding:3,duration:[1,2.5],carrier:[0.25,0.65],deviation:[0.4,0.95],symbols:[0.25,0.6],packets:[2,5],gap:[0.05,0.3],drift:[-0.8,0.65],corruption:[0.4,0.85],interference:[0.5,0.9],echo:[0,0.15]}},
        {name:'Sonar Map',id:'sonar_map',tip:'Swept pings and returning echoes from unseen shapes.',values:{encoding:2,duration:[1.4,3.5],carrier:[0.43,0.65],deviation:[0.05,0.25],symbols:[0,0.08],packets:[2,4],gap:[0.28,0.58],drift:[-0.12,0.12],corruption:[0,0.02],interference:[0,0.03],echo:[0.65,1]}},
        {name:'Encrypted Packet',id:'encrypted_packet',tip:'Dense, clipped phase-coded data.',values:{encoding:1,duration:[0.25,0.85],carrier:[0.55,0.82],deviation:[0.65,1],symbols:[0.65,1],packets:[1,3],gap:[0.08,0.3],drift:[-0.05,0.05],corruption:[0,0.1],interference:[0.01,0.08],echo:[0,0.12]}},
        {name:'Lost Satellite',id:'lost_satellite',tip:'A fading orbital signal sweeping out of tune.',values:{encoding:2,duration:[1.5,3.6],carrier:[0.5,0.8],deviation:[0.25,0.7],symbols:[0.12,0.3],packets:[2,5],gap:[0.2,0.5],drift:[-0.95,-0.35],corruption:[0.15,0.45],interference:[0.06,0.25],echo:[0.4,0.85]}},
        {name:'Save Terminal',id:'save_terminal',tip:'A friendly terminal chirping its data into storage.',values:{encoding:0,duration:[0.3,0.85],carrier:[0.45,0.65],deviation:[0.15,0.4],symbols:[0.18,0.38],packets:[2,4],gap:[0.12,0.28],drift:[0.15,0.45],corruption:0,interference:0,echo:[0.03,0.2]}}
    ];
    constructor() { super(); this.initialize_presets(); }
    set_param(name,value,checkLocked=false) {
        super.set_param(name,value,checkLocked);
        if (name==='packets' && !(checkLocked && this.locked_params[name])) {
            this.params.packets=Math.round(this.params.packets);
        }
    }
}
