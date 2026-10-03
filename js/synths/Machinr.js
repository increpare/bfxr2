class Machinr extends PresetSynth {
    name = 'Machinr';
    tooltip = 'Motors, gears, shutters and stubborn mechanisms. Each category builds a new machine.';
    static DSP = Machinr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'mechanism', display_name:'Mechanism', tooltip:'The moving parts inside the machine.',
            default_value:0, columns:4, values:[['Motor','An electric rotor and bearings.',0],['Gears','Meshing teeth and a strained winch.',1],
                ['Shutter','A fast spring, latch and winding motor.',2],['Clock','An alternating escapement.',3],
                ['Engine','Uneven combustion and exhaust.',4],['Servo','A small motor seeking a position.',5],
                ['Toy','A winding spring and chattering gears.',6],['Door','A heavy hinge, sliding body and closing latch.',7]]},
        ['Duration','Length of the complete movement, in seconds.','duration',1.8,0.12,6],
        ['Speed','Rotation rate or repetition speed of the moving parts.','speed',0.55,0,1],
        ['Load','Resistance against the mechanism: slower, strained and heavier.','load',0.25,0,1],
        ['Roughness','Worn bearings, friction and irregular running.','roughness',0.25,0,1],
        ['Gear Looseness','Loose parts add rattling and uneven tooth contacts.','looseness',0.2,0,1],
        ['Size','From tiny bright parts to a large, deep machine.','size',0.35,0,1],
        ['Start Time','Seconds taken to engage and reach working speed.','startTime',0.08,0,2],
        ['Stop Time','Seconds spent slowing down and stopping.','stopTime',0.16,0,2]
    ];
    recipes = [
        {name:'Door',id:'door',verb:'door',tip:'A door moving and latching: a creaking hinge or a quick latch.',values:{},variants:[
            {mechanism:7,duration:[0.9,1.8],speed:[0.1,0.4],load:[0.6,1],roughness:[0.5,1],looseness:[0.3,0.8],size:[0.6,1],startTime:[0.1,0.4],stopTime:[0.03,0.12]},
            {mechanism:[2,7],duration:[0.3,0.6],speed:[0.6,1],load:[0.1,0.4],roughness:[0.05,0.3],looseness:[0.2,0.6],size:[0.3,0.7],startTime:[0,0.02],stopTime:[0.02,0.08]}]},
        {name:'Whirr',id:'whirr',verb:'whirr',tip:'A machine running for a moment: motor, servo, gears, windup toy or a coughing engine.',values:{},variants:[
            {mechanism:0,duration:[0.5,1.6],speed:[0.4,1],load:[0.05,0.5],roughness:[0.02,0.5],looseness:[0.02,0.4],size:[0.03,0.7],startTime:[0.02,0.3],stopTime:[0.05,0.5]},
            {mechanism:5,duration:[0.3,1],speed:[0.3,1],load:[0.1,0.7],roughness:[0,0.3],looseness:[0,0.3],size:[0.05,0.5],startTime:[0.005,0.08],stopTime:[0.02,0.15]},
            {mechanism:[1,3],duration:[0.6,2],speed:[0.1,0.7],load:[0.1,0.9],roughness:[0.1,0.9],looseness:[0.2,1],size:[0.1,0.9],startTime:[0,0.3],stopTime:[0.03,0.3]},
            {mechanism:6,duration:[0.6,2],speed:[0.4,1],load:[0.1,0.5],roughness:[0.1,0.6],looseness:[0.4,1],size:[0.02,0.4],startTime:[0.01,0.1],stopTime:[0.2,0.9]},
            {mechanism:4,duration:[0.8,2.2],speed:[0.15,0.7],load:[0.3,1],roughness:[0.4,1],looseness:[0.2,0.9],size:[0.4,1],startTime:[0.1,0.5],stopTime:[0.1,0.6]}]},
        {name:'Unlock',id:'unlock',verb:'unlock',tip:'A quick latch and clockwork release.',values:{mechanism:[2,3],duration:[0.3,0.9],speed:[0.5,1],load:[0.05,0.35],roughness:[0,0.2],looseness:[0.1,0.5],size:[0.1,0.45],startTime:[0,0.01],stopTime:[0.02,0.1]}},
        {name:'Confirm',id:'confirm',verb:'confirm',tip:'A crisp shutter click.',values:{mechanism:2,duration:[0.12,0.3],speed:[0.7,1],load:[0.05,0.3],roughness:[0,0.1],looseness:[0.05,0.3],size:[0.1,0.35],startTime:[0,0.004],stopTime:[0.02,0.06]}},
        {name:'Tiny Motor',id:'tiny_motor',tip:'A fresh little electric motor spinning up.',values:{mechanism:0,duration:[0.6,1.8],speed:[0.65,0.95],load:[0.05,0.3],roughness:[0.02,0.2],looseness:[0.02,0.2],size:[0.03,0.25],startTime:[0.03,0.2],stopTime:[0.08,0.35]}},
        {name:'Rusty Winch',id:'rusty_winch',tip:'Slow, strained gears with a different creak each time.',values:{mechanism:1,duration:[1.4,3.7],speed:[0.12,0.4],load:[0.65,1],roughness:[0.6,0.95],looseness:[0.55,0.95],size:[0.55,0.9],startTime:[0.12,0.4],stopTime:[0.1,0.4]}},
        {name:'Camera Shutter',id:'camera_shutter',tip:'A quick spring release, double click and winding tail.',values:{mechanism:2,duration:[0.16,0.42],speed:[0.65,1],load:[0.05,0.35],roughness:[0.02,0.15],looseness:[0.1,0.4],size:[0.12,0.4],startTime:[0,0.004],stopTime:[0.02,0.07]}},
        {name:'Clockwork',id:'clockwork',tip:'A new tiny escapement, ticking against its gears.',values:{mechanism:3,duration:[1,2.8],speed:[0.1,0.48],load:[0.1,0.35],roughness:[0.02,0.18],looseness:[0.1,0.45],size:[0.08,0.45],startTime:[0,0.012],stopTime:[0.03,0.15]}},
        {name:'Engine Trouble',id:'engine_trouble',tip:'An engine coughing under uneven load.',values:{mechanism:4,duration:[1.5,3.5],speed:[0.18,0.55],load:[0.6,1],roughness:[0.7,1],looseness:[0.4,0.85],size:[0.6,1],startTime:[0.15,0.65],stopTime:[0.2,0.75]}},
        {name:'Servo',id:'servo',tip:'A high motor whine seeking a new position.',values:{mechanism:5,duration:[0.35,1.3],speed:[0.45,0.95],load:[0.1,0.55],roughness:[0.01,0.15],looseness:[0.01,0.2],size:[0.1,0.4],startTime:[0.008,0.06],stopTime:[0.025,0.12]}},
        {name:'Windup Toy',id:'windup_toy',tip:'A loose little spring-powered mechanism winding down.',values:{mechanism:6,duration:[1.2,3.2],speed:[0.55,0.95],load:[0.15,0.45],roughness:[0.2,0.55],looseness:[0.5,1],size:[0.02,0.32],startTime:[0.01,0.08],stopTime:[0.3,0.9]}},
        {name:'Heavy Door',id:'heavy_door',tip:'A deep hinge creak with a weighty closing latch.',values:{mechanism:7,duration:[1.1,3.2],speed:[0.1,0.45],load:[0.65,1],roughness:[0.5,0.95],looseness:[0.3,0.85],size:[0.75,1],startTime:[0.1,0.45],stopTime:[0.04,0.2]}}
    ];
    constructor() { super(); this.initialize_presets(); }
}
