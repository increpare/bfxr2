// Independent moving emitters synchronize into a flock, or scatter into a cloud.
class Swarmr_DSP {
    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate, duration=value('duration',1.8,0.25,5);
        const frames=Math.round(duration*rate), out=new Float32Array(frames);
        const count=Math.round(value('count',14,3,32)), kind=Math.round(value('kind',0,0,5));
        const speed=value('speed',0.5), cohesion=value('cohesion',0.3), agitation=value('agitation',0.25);
        const size=value('size',0.45), movement=value('movement',0.5), scatter=value('scatter',0.2);
        const random=SoundDSP.rng(value('seed',0.5)), sin=Math.sin, pow=Math.pow, min=Math.min, max=Math.max, pi=Math.PI;
        const base=90*pow(2,(1-size)*3.8), pulseRate=2+speed*17;
        const gain=0.44/Math.sqrt(count), tau=Math.PI*2;
        for(let agent=0;agent<count;agent++) {
            const start=Math.floor(random()*scatter*frames*0.42);
            const pulseOffset=random()*(1-cohesion), initialPhase=random()*tau;
            const spread=(random()-0.5)*(0.08+0.8*(1-cohesion));
            const detune=pow(2,spread), driftPhase=random()*tau;
            const driftRate=0.4+random()*2, center=0.4+random()*0.2;
            const voiceGain=gain*(0.8+random()*0.4);
            const pulseSpeed=pulseRate*(1+(random()-0.5)*(1-cohesion)*0.3);
            let phase=initialPhase, filteredNoise=0;
            for(let i=start;i<frames;i++) {
                const t=i/rate, age=(i-start)/(frames-start);
                const travel=1+movement*0.55*(1-2*age);
                const jitter=1+agitation*0.12*sin(tau*driftRate*t+driftPhase);
                const beat=(t*pulseSpeed+pulseOffset)%1;
                const wing=sin(tau*beat), positive=max(0,wing);
                let frequency=base*detune*travel*jitter, envelope=1, signal;
                if(kind===1) { frequency*=1.3+2.2*(1-beat);envelope=pow(positive,6); }
                else if(kind===2) frequency*=0.32;
                else if(kind===3) {
                    frequency*=2.3;
                    // Each arrival contributes a tick even when the shared clock's
                    // first pulse passed before this emitter entered a short sound.
                    const arrivalBeat=(i-start)*pulseSpeed/rate;
                    envelope=max(beat<0.2?pow(1-beat/0.2,5):0,
                        arrivalBeat<0.2?pow(1-arrivalBeat/0.2,5):0);
                }
                else if(kind===4) frequency*=0.75;
                else if(kind===5) frequency*=0.28;
                phase+=tau*frequency/rate;
                // Keep accumulated phase small without a modulo in the oscillator loop.
                if(phase>tau)phase-=tau;
                const noise=random()*2-1;
                filteredNoise+=0.08*(noise-filteredNoise);
                switch(kind) {
                    case 0: signal=(sin(phase)+0.3*sin(phase*2))*(0.2+0.8*positive*positive)+filteredNoise*0.2;break;
                    case 1: signal=(sin(phase)+0.2*sin(phase*2))*envelope;break;
                    case 2: signal=(sin(phase)+0.35*sin(phase*3))*(0.7+0.3*wing)+noise*0.03;break;
                    case 3: signal=(noise*0.65+sin(phase)*0.5)*envelope;break;
                    case 4: signal=sin(phase)*(0.75+0.25*wing)+0.12*sin(phase*2);break;
                    default: signal=(filteredNoise*2.5+sin(phase)*0.25+noise*0.07)*(0.7+0.3*wing);
                }
                const distance=(age-center)*3;
                const flyby=1/(1+movement*distance*distance*4);
                const window=kind===3 ? min(1,(i-start)/(rate*0.002),(frames-1-i)/(rate*0.005))
                    : pow(max(0,sin(pi*age)),0.7);
                out[i]+=signal*window*flyby*voiceGain;
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
