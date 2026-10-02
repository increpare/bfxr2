class Rustlr extends PresetSynth {
    name='Rustlr';
    tooltip='Paper, fabric and small inventory-handling gestures.';
    static DSP=Rustlr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'material',display_name:'Material',tooltip:'The surface being handled.',default_value:0,columns:3,
            values:[['Paper','Dry fibers and crisp creases.',0],['Cloth','Soft fabric friction.',1],['Leather','A low, leathery rub.',2],
                ['Plastic','Light, crackly film.',3],['Foil','Bright metallic wrinkles.',4],['Zip','Closely spaced zipper teeth.',5]]},
        {type:'BUTTONSELECT',name:'gesture',display_name:'Gesture',tooltip:'How the movement develops.',default_value:1,columns:4,
            values:[['Flick','A quick movement that falls away.',0],['Turn','A broad bending movement.',1],
                ['Slide','Sustained contact along a surface.',2],['Crumple','Repeated pinches and releases.',3]]},
        ['Duration','Complete movement length in seconds.','duration',0.65,0.08,3],
        ['Grain','From tiny surface grains to broad rubbing contacts.','grain',0.45,0,1],
        ['Density','The number and overlap of surface microcontacts.','density',0.5,0,1],
        ['Motion','Emphasize the start or the arrival of the movement.','motion',0,-1,1],
        ['Pressure','Contact force, elastic loading and friction releases.','pressure',0.5,0,1],
        ['Folds','Number of distinct bends or creases.','folds',3,1,12],
        ['Brightness','Detail in the upper friction frequencies.','brightness',0.5,0,1]
    ];
    recipes=[
        {name:'Card Flick',id:'card_flick',tip:'A small card or inventory tile flicks into place.',values:{material:0,gesture:0,duration:[0.12,0.24],grain:[0.12,0.36],density:[0.4,0.7],motion:[-0.4,0.2],pressure:[0.35,0.65],folds:[1,2],brightness:[0.52,0.85]}},
        {name:'Page Turn',id:'page_turn',tip:'A paper page bends and settles.',values:{material:0,gesture:1,duration:[0.45,0.85],grain:[0.35,0.68],density:[0.5,0.83],motion:[-0.25,0.45],pressure:[0.3,0.6],folds:[2,4],brightness:[0.38,0.7]}},
        {name:'Bag Open',id:'bag_open',tip:'A soft pouch pulls open.',values:{material:[1,2],gesture:1,duration:[0.38,0.8],grain:[0.55,0.88],density:[0.55,0.9],motion:[0.1,0.7],pressure:[0.45,0.8],folds:[2,5],brightness:[0.22,0.55]}},
        {name:'Equip Gear',id:'equip_gear',tip:'Leather and fabric settle around an equipped item.',values:{material:2,gesture:[1,3],duration:[0.3,0.65],grain:[0.35,0.68],density:[0.48,0.8],motion:[-0.25,0.35],pressure:[0.62,0.9],folds:[3,6],brightness:[0.4,0.7]}},
        {name:'Item Slide',id:'item_slide',tip:'An item slides across a surface.',values:{material:[0,2,3],gesture:2,duration:[0.2,0.46],grain:[0.18,0.45],density:[0.65,0.93],motion:[-0.65,0.3],pressure:[0.35,0.64],folds:[1,3],brightness:[0.35,0.7]}},
        {name:'Cloth Fold',id:'cloth_fold',tip:'A soft inventory bundle folds into place.',values:{material:1,gesture:1,duration:[0.32,0.72],grain:[0.65,0.95],density:[0.65,1],motion:[-0.2,0.55],pressure:[0.62,0.95],folds:[2,4],brightness:[0.25,0.6]}},
        {name:'Wrapper',id:'wrapper',tip:'A thin wrapper wrinkles and unfolds.',values:{material:[3,4],gesture:3,duration:[0.38,0.85],grain:[0.18,0.48],density:[0.4,0.75],motion:[-0.25,0.4],pressure:[0.42,0.72],folds:[4,9],brightness:[0.6,0.93]}},
        {name:'Zip Pouch',id:'zip_pouch',tip:'A short zipper pulls through its teeth.',values:{material:5,gesture:2,duration:[0.25,0.62],grain:[0.06,0.27],density:[0.24,0.58],motion:[-0.45,0.65],pressure:[0.48,0.8],folds:[1,3],brightness:[0.45,0.8]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='folds' && !(checkLocked && this.locked_params[name])) this.params.folds=Math.round(this.params.folds);
    }
}
