class Glitchr extends PresetSynth {
    name='Glitchr';
    tooltip='Lost buffers, codec warble, tape scrubbing and torn digital audio.';
    static DSP=Glitchr_DSP;
    param_info=[...PresetSynth.common_params,
        ['Duration','Length in seconds.','duration',0.7,0.08,4],
        ['Pitch','Pitch of the captured sound or data carrier.','pitch',0.5,0,1],
        ['Fragment','Length of the damaged buffer, packet or grain.','fragment',0.3,0,1],
        ['Repeat','Hold the same captured fragment before taking fresh audio.','repeat',0.4,0,1],
        ['Chaos','Read-head jumps, packet damage and unstable playback speed.','chaos',0.5,0,1],
        ['Dropout','Lose complete packets of audio.','dropout',0.2,0,1],
        ['Crush','Quantize amplitude with fewer usable bits.','crush',0.3,0,1],
        ['Sample Hold','Lower the damaged output sample rate.','rate',0.3,0,1],
        {type:'BUTTONSELECT',name:'mode',display_name:'Failure',tooltip:'Each failure uses a different processing mechanism.',default_value:0,columns:2,header:true,values:[['Underrun','A stalled read buffer repeats, then jumps ahead.',0],['Codec Warble','Coarsely coded frequency bands flutter and smear.',1],['Tape Scrub','An unstable read head scrubs backward and forward.',2],['Bit Rot','Decimated samples lose resolution and flip bits.',3],['Data Squeal','Binary data leaks into the audio carrier.',4],['Granular Tear','Overlapping fragments scatter and reverse.',5],['Stutter','A captured phrase is retriggered in short bursts.',6],['Spectral Freeze','Captured partials hang and change in blocks.',7]]}
    ];
    recipes=[
        {name:'Lose',id:'lose',verb:'lose',tip:'Data decaying into noise.',values:{mode:[3,5],duration:[0.6,1.4],pitch:[0.2,0.6],fragment:[0.1,0.5],repeat:[0.2,0.6],chaos:[0.5,1],dropout:[0.1,0.4],crush:[0.4,0.9],rate:[0.2,0.7]}},
        {name:'Blip',id:'blip',verb:'blip',tip:'One stuttered grain.',values:{mode:[6,0],duration:[0.08,0.18],pitch:[0.4,0.8],fragment:[0.05,0.3],repeat:[0.6,1],chaos:[0,0.3],dropout:0,crush:[0,0.3],rate:[0,0.2]}},
        {name:'Warp',id:'warp',verb:'warp',tip:'A read head scrubbing through time.',values:{mode:[2,1],duration:[0.5,1.3],pitch:[0.3,0.65],fragment:[0.1,0.5],repeat:[0.2,0.7],chaos:[0.5,1],dropout:[0,0.2],crush:[0,0.3],rate:[0,0.15]}},
        {name:'Hurt',id:'hurt',verb:'hurt',tip:'A short squeal of damaged data.',values:{mode:4,duration:[0.15,0.4],pitch:[0.4,0.85],fragment:[0.05,0.3],repeat:[0.3,0.7],chaos:[0.5,1],dropout:[0,0.2],crush:[0.3,0.7],rate:[0,0.2]}},
        {name:'Alert',id:'alert',verb:'alert',tip:'A repeating stutter demanding attention.',values:{mode:6,duration:[0.3,0.8],pitch:[0.4,0.75],fragment:[0.1,0.4],repeat:[0.8,1],chaos:[0,0.3],dropout:[0,0.2],crush:[0,0.3],rate:[0,0.2]}},
        {name:'Buffer Underrun',id:'save_corruption',values:{mode:0,duration:[0.5,1.4],pitch:[0.25,0.65],fragment:[0.03,0.3],repeat:[0.6,0.95],chaos:[0.25,0.65],dropout:[0.2,0.55],crush:[0.1,0.4],rate:[0,0.2]}},
        {name:'Codec Warble',id:'teleport_error',values:{mode:1,duration:[0.7,1.7],pitch:[0.3,0.6],fragment:[0.1,0.45],repeat:[0.3,0.7],chaos:[0.5,1],dropout:[0.05,0.3],crush:[0.4,0.8],rate:[0,0.2]}},
        {name:'Bit Rot',id:'bit_rot',values:{mode:3,duration:[0.6,1.6],pitch:[0.15,0.5],fragment:[0.15,0.6],repeat:[0.15,0.6],chaos:[0.2,0.7],dropout:[0.1,0.45],crush:[0.65,1],rate:[0.55,1]}},
        {name:'Phrase Stutter',id:'buffer_skip',values:{mode:6,duration:[0.4,1.2],pitch:[0.35,0.7],fragment:[0.1,0.5],repeat:[0.75,1],chaos:[0.05,0.4],dropout:[0.05,0.3],crush:[0,0.35],rate:[0,0.2]}},
        {name:'Data Squeal',id:'corrupt_pickup',values:{mode:4,duration:[0.2,0.8],pitch:[0.4,0.85],fragment:[0.05,0.4],repeat:[0.25,0.7],chaos:[0.45,0.95],dropout:[0.05,0.3],crush:[0.25,0.7],rate:[0,0.2]}},
        {name:'Spectral Freeze',id:'broken_terminal',values:{mode:7,duration:[0.8,2.2],pitch:[0.25,0.65],fragment:[0.3,0.85],repeat:[0.5,0.9],chaos:[0.3,0.8],dropout:[0.05,0.3],crush:[0.1,0.5],rate:[0,0.15]}},
        {name:'Tape Scrub',id:'rewind_burst',values:{mode:2,duration:[0.5,1.5],pitch:[0.3,0.65],fragment:[0.05,0.6],repeat:[0.25,0.75],chaos:[0.4,1],dropout:[0,0.15],crush:[0,0.2],rate:[0,0.1]}},
        {name:'Granular Tear',id:'digital_death',values:{mode:5,duration:[0.6,1.8],pitch:[0.2,0.65],fragment:[0.08,0.55],repeat:[0.2,0.7],chaos:[0.65,1],dropout:[0.05,0.3],crush:[0.2,0.6],rate:[0.05,0.35]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        const oldKeys=['masterVolume','seed','duration','pitch','fragment','repeat','chaos','dropout','crush','rate'];
        if(params && oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key)) && !Object.prototype.hasOwnProperty.call(params,'mode'))this.set_param('mode',this.param_default('mode'),checkLocked);
        super.apply_params(params,checkLocked);
    }
}
