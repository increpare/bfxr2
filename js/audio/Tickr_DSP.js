// A progress clock schedules individual contacts, then a separate completion cue.
class Tickr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,min,max,round,PI}=Math;
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate, duration=value('duration',1.2,0.15,5);
        const out=new Float32Array(round(duration*rate)), random=SoundDSP.rng(value('seed',0.5));
        const count=round(value('count',12,1,48)), kind=round(value('kind',2,0,4));
        const acceleration=value('acceleration',0.4,-1,1), rise=value('rise',0.5,-1,1);
        const pitch=130*pow(2,value('pitch',0.45)*4.3), decay=value('decay',0.3);
        const brightness=value('brightness',0.5), jitter=value('jitter',0.05), finish=value('finish',0.5);
        const tau=PI*2, exponent=pow(2,-acceleration*1.4), span=duration*0.73;
        const first=min(0.015,duration*0.06), starts=[];
        for(let n=0;n<count;n++)starts.push(first+span*pow(n/max(1,count-1),exponent));
        // Fit jitter inside neighbouring gaps so progress never runs backwards.
        for(let n=0;n<count;n++){
            const gap=min(n?starts[n]-starts[n-1]:span/max(1,count),
                n+1<count?starts[n+1]-starts[n]:duration*0.07);
            starts[n]+=jitter*(random()-0.5)*max(0,gap)*0.45;
        }
        const ringTime=0.003+decay*0.065;
        const densityGain=1/Math.sqrt(max(1,count*ringTime/max(0.01,span)*1.7));
        const addTick=(time,frequency,strength,ending=false)=>{
            const start=max(0,round(time*rate));
            const sustain=ending?0.025+decay*0.09:ringTime;
            const length=min(out.length-start,round(sustain*7*rate));
            const radius=exp(-1/(rate*sustain)), attack=1-exp(-1/(rate*0.0006));
            const gain=strength*(0.9+0.2*random()), phase=random()*tau;
            const step=tau*min(10000,max(40,frequency))/rate;
            let envelope=1, onset=0, noiseLow=0, angle=phase;
            for(let i=0;i<length;i++){
                const noise=random()*2-1;
                noiseLow+=(noise-noiseLow)*(0.05+brightness*0.75);
                angle+=step; onset+=(1-onset)*attack;
                let tone;
                if(ending)tone=sin(angle)*0.6+sin(angle*1.5)*0.3+sin(angle*2)*0.12;
                else switch(kind){
                    case 0: tone=noiseLow*0.7+sin(angle)*0.5;break;
                    case 1: tone=sin(angle+brightness*exp(-i/(rate*0.009))*2*sin(angle*2.73))*0.8+sin(angle*1.501)*0.2;break;
                    case 2: tone=sin(angle)+brightness*0.15*sin(angle*2);break;
                    case 3: tone=(noiseLow*0.85+sin(angle)*0.35)*(0.25+0.75*max(0,cos(i*tau*650/rate)));break;
                    default: tone=sin(angle)*(0.7+0.3*cos(angle*0.5))+brightness*sin(angle*3)*0.2;
                }
                out[start+i]+=tone*envelope*onset*gain;
                envelope*=radius;
            }
        };
        for(let n=0;n<count;n++){
            const progress=n/max(1,count-1), detune=pow(2,(random()-0.5)*0.05);
            addTick(starts[n],pitch*pow(2,rise*2.3*progress)*detune,0.72*densityGain);
        }
        if(finish>0)addTick(first+duration*0.81,pitch*pow(2,rise*2.3)*1.25,finish*0.65,true);
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
