// Material-dependent waveguide strings share a damped bridge and shaped pluck.
class Pluckr_DSP {
    static render(p) {
        const {sin,atan2,exp,pow,round,floor,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.8,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        const random=SoundDSP.rng(value('seed',0.5)),count=round(value('strings',3,1,8)),material=round(value('material',0,0,5));
        const pitch=55*pow(2,value('pitch',0.5)*4),damping=value('damping',0.25),brightness=value('brightness',0.6);
        const coupling=value('coupling',0.15),strum=value('strum',0.2),pluck=value('pluck',0.3),inharmonic=value('inharmonic',0.05);
        // Flexible fibres lose high frequencies; rigid filaments disperse travelling waves.
        const matter=[
            {life:1,average:0.5,filter:0.18,bright:0.8,excite:1,dispersion:0,stages:0},
            {life:1.45,average:0.14,filter:0.65,bright:0.35,excite:1.5,dispersion:0.2,stages:1},
            {life:0.62,average:0.55,filter:0.12,bright:0.5,excite:0.6,dispersion:0.6,stages:1},
            {life:0.075,average:0.65,filter:0.1,bright:0.28,excite:0.35,dispersion:0.4,stages:1},
            {life:1.3,average:0.06,filter:0.85,bright:0.15,excite:1.8,dispersion:-0.72,stages:2},
            {life:0.95,average:0.25,filter:0.4,bright:0.5,excite:1.1,dispersion:-0.45,stages:2}
        ][material];
        const notes=[0,7,12,16,19,24,28,31],strings=[],gain=0.65/Math.sqrt(count);
        for(let s=0;s<count;s++) {
            const frequency=pitch*pow(2,notes[s]/12+(random()-0.5)*inharmonic*0.07);
            const period=rate/frequency,omega=2*PI/period,a=matter.dispersion;
            const dispersionDelay=matter.stages*2*atan2((1-a)*sin(omega/2),(1+a)*Math.cos(omega/2))/omega;
            const desired=max(2,period-matter.average-dispersionDelay),delay=max(2,floor(desired));
            const buffer=new Float32Array(delay);let low=0,mean=0;
            const location=0.05+pluck*0.9;
            for(let i=0;i<delay;i++) {
                low+=(random()*2-1-low)*min(1,(0.05+brightness*0.9)*matter.excite);
                const x=i/delay,triangle=x<location?x/location:(1-x)/(1-location);
                buffer[i]=low*0.75+(triangle-0.5)*(1-brightness)*0.75;mean+=buffer[i];
            }
            mean/=delay;for(let i=0;i<delay;i++)buffer[i]-=mean;
            strings.push({buffer,index:0,previous:0,low:0,allpass:0,allpassInput:0,
                waveInputs:new Float32Array(matter.stages),waveOutputs:new Float32Array(matter.stages),
                // Clamp the physical loop before deriving its fractional-delay coefficient.
                fraction:(1-(desired-delay))/(1+(desired-delay)),
                feedback:exp(-3/(frequency*(0.07+pow(1-damping,2)*4)*matter.life)),
                start:round(s*strum*min(rate*0.11,out.length/max(1,count)*0.65))});
        }
        let bridge=0;
        for(let i=0;i<out.length;i++) {
            let sum=0,bridgeNext=0;
            const dispersion=matter.dispersion+(material===5?0.22*sin(2*PI*1.7*i/rate):0);
            for(let s=0;s<count;s++) {
                const string=strings[s];if(i<string.start)continue;
                const current=string.buffer[string.index];
                const averaged=current*(1-matter.average)+string.previous*matter.average;string.previous=current;
                string.low+=(averaged-string.low)*(matter.filter+brightness*matter.bright);
                const input=string.low;
                let dispersed=string.fraction*input+string.allpassInput-string.fraction*string.allpass;
                string.allpassInput=input;string.allpass=dispersed;
                for(let stage=0;stage<matter.stages;stage++) {
                    const next=dispersion*dispersed+string.waveInputs[stage]-dispersion*string.waveOutputs[stage];
                    string.waveInputs[stage]=dispersed;string.waveOutputs[stage]=next;dispersed=next;
                }
                string.buffer[string.index]=string.feedback*(dispersed*(1-coupling*0.025)+bridge*coupling*0.025);
                string.index++;if(string.index===string.buffer.length)string.index=0;
                sum+=current;bridgeNext+=current;
            }
            bridge=bridgeNext/count;
            out[i]=sum*gain;
        }
        return SoundDSP.finish(out,volume);
    }
}
