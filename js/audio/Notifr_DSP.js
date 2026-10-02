// Short overlapping tone groups: interval carries direction, tension adds urgency.
class Notifr_DSP {
    static render(p) {
        const {sin,exp,pow,min,max,round,floor,PI}=Math;
        const value=(name,fallback,low=0,high=1)=>Number.isFinite(p[name])?min(high,max(low,p[name])):fallback;
        const rate=SoundDSP.rate,tau=2*PI,duration=value('duration',0.55,0.08,3);
        const output=new Float32Array(round(duration*rate));
        const volume=value('masterVolume',0.5);
        if(volume===0) return SoundDSP.finish(output,0);
        const random=SoundDSP.rng(value('seed',0.5));
        const tone=round(value('tone',0,0,3)),pitch=110*2**(4*value('pitch',0.55));
        const interval=value('interval',5,-12,12),tension=value('tension',0.08);
        const pulses=round(value('pulses',2,1,8)),spacing=value('spacing',0.3,0,0.85);
        const urgency=value('urgency',0.15),softness=value('softness',0.65);
        const ring=value('ring',0.3),echo=value('echo',0.1);
        // Reserve the end for ringing and echoes without extending the requested length.
        const phrase=output.length*(0.97-echo*0.2),slot=phrase/pulses;
        const brightness=1-softness,groupGain=0.49/(1+0.28*ring*pulses);
        for(let group=0;group<pulses;group++) {
            // An accelerating clock bunches urgent repetitions toward the end.
            const position=group/pulses,next=(group+1)/pulses;
            const start=round(phrase*(1-pow(1-position,1+urgency*0.7)));
            const nextStart=phrase*(1-pow(1-next,1+urgency*0.7));
            const groupSlot=max(1,nextStart-start);
            const active=max(12,groupSlot*(1-spacing)+slot*ring*0.9);
            const end=min(output.length,start+round(active));
            const attack=min(active*0.22,rate*(0.0015+softness*0.015));
            const release=max(1,min(active*0.2,rate*(0.008+ring*0.04)));
            const direction=pulses===1?0:interval*group/(pulses-1);
            const fundamental=min(9500,pitch*2**(direction/12));
            const second=min(12000,fundamental*2**((interval+tension*0.8)/12));
            const clash=min(13000,fundamental*2**((1+5*tension)/12));
            const step=tau*fundamental/rate,secondStep=tau*second/rate,clashStep=tau*clash/rate;
            let phase=random()*tau,answerPhase=random()*tau,clashPhase=random()*tau;
            const gain=groupGain*(0.96+random()*0.08),decay=2.8-ring*2.4;
            for(let i=start;i<end;i++) {
                const local=i-start,unit=local/active;
                const envelope=min(1,local/attack,(active-local)/release)*exp(-unit*decay);
                phase+=step; answerPhase+=secondStep; clashPhase+=clashStep;
                let body=sin(phase),answer=sin(answerPhase);
                if(tone===1) {
                    body+=brightness*(0.42*sin(phase*2.756)*exp(-unit*4)+0.22*sin(phase*5.404)*exp(-unit*7));
                    answer+=brightness*0.22*sin(answerPhase*2.756)*exp(-unit*5);
                } else if(tone===2) {
                    body+=brightness*(0.34*sin(phase*2)*exp(-unit*3)+0.19*sin(phase*4)*exp(-unit*6));
                    answer+=brightness*0.18*sin(answerPhase*2);
                } else if(tone===3) {
                    body+=brightness*(0.32*sin(phase*3)+0.18*sin(phase*5));
                    answer+=brightness*0.25*sin(answerPhase*3);
                }
                const tremolo=1-urgency*0.22*(0.5+0.5*sin(tau*(12+urgency*19)*local/rate));
                output[i]+=gain*envelope*tremolo*(body+answer*0.45+sin(clashPhase)*tension*0.35);
            }
        }
        if(echo>0) {
            const delay=max(1,round(min(duration*0.19,0.074)*rate));
            // A short decaying repeat keeps the attack intelligible, without a room tail.
            for(let i=delay;i<output.length;i++) output[i]+=output[i-delay]*echo*0.43;
        }
        return SoundDSP.finish(output,volume);
    }
}
