class Zappr extends PresetSynth {
    name='Zappr';
    tooltip='Branching arcs, charged fields and electrical failures.';
    static DSP=Zappr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        ['Duration','Seconds.','duration',1.2,0.12,5],
        ['Voltage','Raises the frequency and agitation of the current.','voltage',0.55,0,1],
        ['Arcs','Number of primary discharges.','arcs',7,1,24],
        ['Branching','Smaller discharges split from each main arc.','branching',0.4,0,1],
        ['Crackle','Irregular tiny contacts between the main arcs.','crackle',0.45,0,1],
        ['Hum','Low electrical field beneath the discharge.','hum',0.2,0,1],
        ['Sparks','Move from ringing arcs to noisy sparks.','spark',0.65,0,1],
        ['Spread','Spread the discharges over the duration.','spread',0.7,0,1],
        ['Decay','Length of each electrical discharge.','decay',0.4,0,1]
    ];
    recipes=[
        {name:'Static Spark',id:'static_spark',tip:'A little sharp discharge from a fingertip.',values:{duration:[0.12,0.3],voltage:[0.55,0.9],arcs:[1,3],branching:[0,0.15],crackle:[0,0.2],hum:[0,0.02],spark:[0.8,1],spread:[0,0.2],decay:[0,0.12]}},
        {name:'Tesla Coil',id:'tesla_coil',tip:'A buzzing field throws branching arcs.',values:{duration:[1.3,2.8],voltage:[0.7,1],arcs:[14,24],branching:[0.65,1],crackle:[0.45,0.8],hum:[0.45,0.8],spark:[0.25,0.6],spread:[0.7,1],decay:[0.25,0.6]}},
        {name:'Power Short',id:'power_short',tip:'A failing connection spits and buzzes.',values:{duration:[0.5,1.5],voltage:[0.25,0.6],arcs:[5,12],branching:[0.2,0.6],crackle:[0.8,1],hum:[0.3,0.65],spark:[0.65,1],spread:[0.35,0.8],decay:[0.05,0.3]}},
        {name:'Lightning Arc',id:'lightning_arc',tip:'A single great fork of electrical energy.',values:{duration:[0.5,1.3],voltage:[0.8,1],arcs:[1,3],branching:[0.85,1],crackle:[0.05,0.25],hum:[0,0.12],spark:[0.45,0.8],spread:[0.02,0.18],decay:[0.65,1]}},
        {name:'Stun Baton',id:'stun_baton',tip:'A close, rapidly sparking electric weapon.',values:{duration:[0.4,1.1],voltage:[0.5,0.8],arcs:[9,20],branching:[0.25,0.6],crackle:[0.7,1],hum:[0.15,0.4],spark:[0.55,0.9],spread:[0.75,1],decay:[0.05,0.25]}},
        {name:'Reactor',id:'reactor',tip:'A heavy field with unstable internal discharges.',values:{duration:[2,4.5],voltage:[0.1,0.35],arcs:[8,18],branching:[0.3,0.75],crackle:[0.3,0.7],hum:[0.8,1],spark:[0.1,0.4],spread:[0.75,1],decay:[0.55,0.95]}},
        {name:'Magic Spark',id:'magic_spark',tip:'A bright ringing cluster of impossible energy.',values:{duration:[0.4,1.2],voltage:[0.6,0.95],arcs:[3,8],branching:[0.6,1],crackle:[0,0.15],hum:[0,0.08],spark:[0,0.2],spread:[0.4,0.8],decay:[0.45,0.8]}},
        {name:'Fuse Blow',id:'fuse_blow',tip:'A brief, harsh electrical failure.',values:{duration:[0.15,0.5],voltage:[0.4,0.75],arcs:[2,5],branching:[0.4,0.8],crackle:[0.4,0.75],hum:[0.1,0.4],spark:[0.8,1],spread:[0,0.18],decay:[0.1,0.35]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='arcs'&&!(checkLocked&&this.locked_params[name]))this.params.arcs=Math.round(this.params.arcs);
    }
}
