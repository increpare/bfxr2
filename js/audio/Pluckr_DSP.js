// Karplus–Strong string loops share a damped bridge; each starts with a shaped pluck.
class Pluckr_DSP {
    static render(p) {
        const {sin,exp,pow,round,floor,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.8,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        const random=SoundDSP.rng(value('seed',0.5)),count=round(value('strings',3,1,8));
        const pitch=55*pow(2,value('pitch',0.5)*4),damping=value('damping',0.25),brightness=value('brightness',0.6);
        const coupling=value('coupling',0.15),strum=value('strum',0.2),pluck=value('pluck',0.3),inharmonic=value('inharmonic',0.05);
        const notes=[0,7,12,16,19,24,28,31],strings=[],gain=0.65/Math.sqrt(count);
        for(let s=0;s<count;s++) {
            const frequency=pitch*pow(2,notes[s]/12+(random()-0.5)*inharmonic*0.07);
            const period=rate/frequency,delay=max(2,floor(period-0.5));
            const buffer=new Float32Array(delay);let low=0,mean=0;
            const location=0.05+pluck*0.9;
            for(let i=0;i<delay;i++) {
                low+=(random()*2-1-low)*(0.05+brightness*0.9);
                const x=i/delay,triangle=x<location?x/location:(1-x)/(1-location);
                buffer[i]=low*0.75+(triangle-0.5)*(1-brightness)*0.75;mean+=buffer[i];
            }
            mean/=delay;for(let i=0;i<delay;i++)buffer[i]-=mean;
            strings.push({buffer,index:0,previous:0,low:0,allpass:0,allpassInput:0,
                // Fractional allpass compensates the loop filter's half-sample delay.
                fraction:(1-(period-0.5-delay))/(1+(period-0.5-delay)),
                feedback:exp(-3/(frequency*(0.07+pow(1-damping,2)*4))),
                start:round(s*strum*min(rate*0.11,out.length/max(1,count)*0.65))});
        }
        let bridge=0;
        for(let i=0;i<out.length;i++) {
            let sum=0,bridgeNext=0;
            for(let s=0;s<count;s++) {
                const string=strings[s];if(i<string.start)continue;
                const current=string.buffer[string.index];
                const averaged=0.5*(current+string.previous);string.previous=current;
                string.low+=(averaged-string.low)*(0.18+brightness*0.8);
                const input=string.low;
                const dispersed=string.fraction*input+string.allpassInput-string.fraction*string.allpass;
                string.allpassInput=input;string.allpass=dispersed;
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
