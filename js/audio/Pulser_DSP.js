// Paired pressure contacts: a short chest thud, valve noise and tension-driven grit.
class Pulser_DSP {
    static render(p){
        const {sin,exp,pow,round,min,max,PI}=Math;
        const v=(k,d,a=0,b=1)=>Number.isFinite(p[k])?SoundDSP.clamp(p[k],a,b):d;
        const rate=SoundDSP.rate,duration=v('duration',1.5,0.2,5),out=new Float32Array(round(duration*rate));
        const volume=v('masterVolume',0.5);if(volume===0)return SoundDSP.finish(out,0);
        const random=SoundDSP.rng(v('seed',0.5)),beats=round(v('beats',3,1,12)),slot=duration*0.85/beats;
        const size=v('size',0.5),pitch=38*pow(2,v('pitch',0.35)*2.7),separation=v('separation',0.35);
        const secondary=v('secondary',0.6),murmur=v('murmur',0.1),tension=v('tension',0.2),irregular=v('irregular',0.05);
        const tau=PI*2,gain=0.95/Math.sqrt(max(1,beats*(0.02+size*0.07)/duration*3));
        for(let beat=0;beat<beats;beat++){
            const start=0.008+beat*slot+(beat?((random()-0.5)*slot*irregular*0.35):0);
            for(let chamber=0;chamber<2;chamber++){
                const onset=round((start+chamber*slot*(0.22+separation*0.25))*rate);
                // Dense panic rhythms keep each chamber short enough to read as a separate hit.
                const decay=min(0.018+size*0.036,slot*0.18),frequency=pitch*(chamber?1.19:1)*(0.96+random()*0.08);
                const length=min(out.length-onset,round(decay*7*rate));
                let phase=0,low=0,body=0;
                for(let i=0;i<length;i++){
                    const t=i/rate,env=exp(-t/decay)*min(1,t/0.002);
                    phase+=tau*frequency*(1+0.5*exp(-t/0.009))/rate;
                    low+=(random()*2-1-low)*(0.07+tension*0.16);
                    body+=(low-body)*0.009;
                    const valve=(low-body)*(1.7+tension*1.8);
                    const pressure=sin(phase)*exp(-t/(decay*0.8))*0.65;
                    const grit=tension*0.35*sin(phase*2.63)*exp(-t/(decay*0.6));
                    out[onset+i]+=(pressure+valve+grit)*env*gain*(chamber?secondary:1);
                }
            }
        }
        let flow=0,body=0;
        for(let i=0;i<out.length;i++){
            flow+=(random()*2-1-flow)*0.045;body+=(flow-body)*0.008;
            const position=(i/rate/slot)%1;
            const squeeze=pow(max(0,sin(PI*position)),3);
            out[i]+=(flow-body)*murmur*(0.3+squeeze)*sin(PI*i/out.length);
        }
        return SoundDSP.finish(out,volume);
    }
}
