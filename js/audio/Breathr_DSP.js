// Turbulent air changes colour with direction; obstructed airways flutter into a snore.
class Breathr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,round,floor,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,tau=PI*2,duration=value('duration',2.7,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        // Missing mode retains the original cycle for saved/raw parameter objects.
        const single=round(value('mode',1,0,1))===0,inward=(1-value('direction',1,-1,1))/2;
        const random=SoundDSP.rng(value('seed',0.5)),cycles=single?1:round(value('cycles',1,1,10)),source=round(value('source',0,0,2));
        const effort=value('effort',0.55),inhale=value('inhale',0.42,0.1,0.9),hold=value('hold',0.04,0,0.7);
        const throat=value('throat',0.5),rasp=value('rasp',0.1),flutter=value('flutter',0.15),space=value('space',0.1);
        const slot=out.length/cycles,inEnd=(1-hold)*inhale*0.9,outStart=inEnd+hold*0.9+0.025,outEnd=0.965;
        const delay=round(rate*(0.022+space*0.075)),gain=1.5+effort*1.5;
        const variations=Array.from({length:cycles},()=>0.88+random()*0.24);
        const radius=exp(-PI*550/rate),r2=radius*radius,bandGain=(1-radius)*1.6;
        let low=0,highpass=0,y1=0,y2=0,previous=0,previous2=0,wander=0,phase=random()*tau;
        let coefficient=0,cutoff=0,heldNoise=0;
        for(let i=0;i<out.length;i++) {
            const position=(i%slot)/slot,cycle=min(cycles-1,floor(i/slot));
            const inhaling=position<inEnd,exhaling=position>outStart&&position<outEnd;
            const blend=single?inward:inhaling?1:0;
            const local=single?i/max(1,out.length-1):inhaling?position/inEnd:exhaling?(position-outStart)/(outEnd-outStart):0;
            const arch=pow(max(0,sin(PI*local)),single?0.7+0.1*blend:inhaling?0.8:0.7);
            const shape=single?(1-0.36*local)*(1-blend)+(0.8+0.2*local)*blend:inhaling?0.8+0.2*local:1-0.36*local;
            const airflow=arch*shape*variations[cycle];
            const noise=random()*2-1;
            wander+=(noise-wander)*0.0025;
            if(source===1&&i%round(5+throat*22)===0)heldNoise=noise>0?0.8:-0.8;
            const excitation=source===1?heldNoise:noise;
            if((i&31)===0) {
                // Inhale jets are brighter; the mouth and chest soften the released air.
                const airHz=single?(750+effort*1600)*(1-blend)+(2400+effort*2700)*blend:inhaling?2400+effort*2700:750+effort*1600;
                const hz=airHz*(1-throat*0.38)*(0.75+airflow*0.25);
                cutoff=1-exp(-tau*hz/rate);
                coefficient=2*radius*cos(tau*(single?510+490*blend:inhaling?1000:510)*(1.35-throat*0.6)/rate);
            }
            low+=(excitation-low)*cutoff;
            highpass+=(low-highpass)*(1-exp(-tau*(single?110+120*blend:inhaling?230:110)/rate));
            const turbulent=low-highpass;
            const resonant=bandGain*(turbulent-previous2)+coefficient*y1-r2*y2;
            y2=y1;y1=resonant;previous2=previous;previous=turbulent;
            phase+=tau*(24+(1-throat)*44)*(1+flutter*0.3*sin(tau*2.3*i/rate)+wander*0.9)/rate;
            const obstruction=source===2?0.72+rasp*0.27:rasp*0.22;
            const flap=pow(max(0,sin(phase)),3);
            const airway=1-obstruction+obstruction*flap;
            const tremor=max(0.2,1+wander*flutter*6+flutter*0.07*sin(tau*7.3*i/rate));
            let envelope=airflow*tremor;
            if(source===1)envelope=round(envelope*12)/12;
            // Snore pressure pulses are driven by turbulent flow, not a sustained vocal note.
            const tissue=source===2?(flap-0.212)*rasp*0.3*arch:0;
            out[i]=((turbulent*0.85+resonant*0.8)*airway+tissue)*envelope*gain;
            if(i>=delay)out[i]+=out[i-delay]*space*0.38;
        }
        return SoundDSP.finish(out,volume);
    }
}
