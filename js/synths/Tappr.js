class Tappr extends PresetSynth {
    name='Tappr';
    tooltip='Tactile buttons, toggles and small interface contacts.';
    static DSP=Tappr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'material',display_name:'Contact',tooltip:'The surface and spring under the control.',default_value:1,columns:3,
            values:[['Rubber','A soft, damped pad.',0],['Plastic','A light plastic detent.',1],['Keycap','A little keyboard spring.',2],
                ['Metal','A crisp metal catch.',3],['Glass','A fine glass contact.',4],['Wood','A dry wooden stop.',5]]},
        ['Duration','Complete sound length in seconds, including the decay.','duration',0.18,0.04,2],
        ['Size','Larger contacts and housings resonate lower.','size',0.5,0,1],
        ['Hardness','From a padded press to a crisp contact.','hardness',0.4,0,1],
        ['Body','The lower resonance of the control housing.','body',0.4,0,1],
        ['Release','Strength of the independent second contact.','release',0.35,0,1],
        ['Contact Gap','Delay between the press and release.','gap',0.4,0,1],
        ['Electronic','A little rounded electronic confirmation.','electronic',0.08,0,1],
        ['Damping','Absorb the spring and housing resonance.','damping',0.7,0,1]
    ];
    recipes=[
        {name:'Focus',id:'focus',tip:'A soft touch when focus moves.',values:{material:[0,1],duration:[0.055,0.1],size:[0.45,0.7],hardness:[0.08,0.3],body:[0.08,0.28],release:[0,0.08],gap:[0.1,0.25],electronic:[0.01,0.1],damping:[0.8,1]}},
        {name:'Select',id:'select',tip:'A compact, positive button press.',values:{material:[1,2],duration:[0.09,0.17],size:[0.3,0.55],hardness:[0.32,0.62],body:[0.25,0.55],release:[0.18,0.42],gap:[0.15,0.4],electronic:[0.04,0.18],damping:[0.62,0.9]}},
        {name:'Back',id:'back',tip:'A lower, softer return contact.',values:{material:[0,5],duration:[0.1,0.2],size:[0.6,0.85],hardness:[0.2,0.45],body:[0.35,0.65],release:[0.1,0.32],gap:[0.25,0.55],electronic:[0.02,0.15],damping:[0.68,0.94]}},
        {name:'Toggle On',id:'toggle_on',tip:'A spring catches into position.',values:{material:[2,3],duration:[0.13,0.25],size:[0.3,0.56],hardness:[0.45,0.78],body:[0.32,0.62],release:[0.5,0.85],gap:[0.18,0.45],electronic:[0.06,0.25],damping:[0.5,0.8]}},
        {name:'Toggle Off',id:'toggle_off',tip:'A lower detent settles back.',values:{material:[1,2],duration:[0.12,0.23],size:[0.6,0.88],hardness:[0.28,0.58],body:[0.42,0.74],release:[0.25,0.55],gap:[0.2,0.5],electronic:[0,0.09],damping:[0.68,0.92]}},
        {name:'Disabled',id:'disabled',tip:'A padded contact with no satisfying catch.',values:{material:0,duration:[0.065,0.12],size:[0.7,0.95],hardness:[0.03,0.2],body:[0.15,0.4],release:[0,0.06],gap:[0.1,0.3],electronic:[0,0.04],damping:[0.88,1]}},
        {name:'Panel Open',id:'panel_open',tip:'A little latch followed by its open stop.',values:{material:[1,3,4],duration:[0.22,0.42],size:[0.34,0.6],hardness:[0.3,0.6],body:[0.4,0.72],release:[0.38,0.65],gap:[0.55,0.88],electronic:[0.12,0.35],damping:[0.46,0.74]}},
        {name:'Panel Close',id:'panel_close',tip:'A deeper catch settling into its frame.',values:{material:[1,5],duration:[0.19,0.36],size:[0.62,0.88],hardness:[0.3,0.57],body:[0.6,0.9],release:[0.52,0.86],gap:[0.46,0.76],electronic:[0,0.1],damping:[0.6,0.84]}}
    ];
    constructor(){super();this.initialize_presets();}
}
