class Weathr extends PresetSynth {
    name = 'Weathr';
    tooltip = 'Wind, rain, fire and water. Every sound exports as a seamless loop.';
    loop_preview = true;
    static DSP = Weathr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'environment',display_name:'Environment',tooltip:'The source of the texture.',
            default_value:0,columns:5,values:[['Wind','Air rushing and whistling.',0],['Rain','Droplets over a bed of rainfall.',1],
                ['Fire','Low flame and snapping embers.',2],['Water','Bubbling water and currents.',3],['Electric','A live hum and scattered arcs.',4]]},
        ['Duration','Loop length in seconds. The exported sound repeats seamlessly.','duration',6,4,10],
        ['Density','Amount of rain, flame, wind, bubbles or electrical activity.','density',0.5,0,1],
        ['Turbulence','Depth of gusts, surges and irregular changes in the texture.','turbulence',0.5,0,1],
        ['Brightness','Open the texture from a distant rumble to sharp close detail.','brightness',0.55,0,1],
        ['Scale','Small, quick detail to slow, broad swells and large droplets.','scale',0.5,0,1],
        ['Detail','Strength of individual drops, pops, bubbles and electrical arcs.','detail',0.5,0,1]
    ];
    recipes = [
        {name:'Soft Wind',id:'wind',tip:'A fresh breeze with slowly shifting gusts.',values:{environment:0,duration:[5,9],density:[0.2,0.5],turbulence:[0.2,0.55],brightness:[0.25,0.55],scale:[0.5,0.85],detail:[0.05,0.2]}},
        {name:'Rainfall',id:'rain',tip:'A new scattering of raindrops over steady rain.',values:{environment:1,duration:[5,9],density:[0.4,0.8],turbulence:[0.1,0.35],brightness:[0.5,0.8],scale:[0.15,0.45],detail:[0.4,0.75]}},
        {name:'Campfire',id:'campfire',tip:'Warm flame and a different set of snapping embers.',values:{environment:2,duration:[5,9],density:[0.3,0.65],turbulence:[0.3,0.65],brightness:[0.35,0.65],scale:[0.4,0.75],detail:[0.6,0.95]}},
        {name:'Bubbling Stream',id:'stream',tip:'Small water bubbles among irregular ripples.',values:{environment:3,duration:[5,9],density:[0.25,0.55],turbulence:[0.2,0.55],brightness:[0.4,0.7],scale:[0.05,0.35],detail:[0.6,1]}},
        {name:'Electric Crackle',id:'electric',tip:'A low electrical hum with scattered sizzling arcs.',values:{environment:4,duration:[4,7],density:[0.15,0.55],turbulence:[0.25,0.65],brightness:[0.65,0.95],scale:[0.05,0.3],detail:[0.65,1]}},
        {name:'Storm Front',id:'storm',tip:'Heavy rain building and receding in broad gusts.',values:{environment:1,duration:[7,10],density:[0.85,1],turbulence:[0.7,1],brightness:[0.2,0.5],scale:[0.75,1],detail:[0.3,0.6]}},
        {name:'Ocean Surf',id:'ocean',tip:'Broad waves rolling into a wash of foam.',values:{environment:3,duration:[7,10],density:[0.65,0.95],turbulence:[0.8,1],brightness:[0.2,0.45],scale:[0.85,1],detail:[0.05,0.2]}},
        {name:'Blizzard',id:'blizzard',tip:'Sharp, dense wind with a thin icy whistle.',values:{environment:0,duration:[6,10],density:[0.75,1],turbulence:[0.6,0.95],brightness:[0.7,1],scale:[0.3,0.6],detail:[0.65,1]}},
        {name:'Waterfall',id:'waterfall',tip:'A dense rush of water with deep churning detail.',values:{environment:3,duration:[5,9],density:[0.85,1],turbulence:[0.05,0.25],brightness:[0.6,0.85],scale:[0.6,0.85],detail:[0.15,0.4]}}
    ];
    constructor() { super(); this.initialize_presets(); }
}
