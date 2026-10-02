// Two pressure chambers per beat, with a separate turbulent flow between them.
class Pulser_DSP {
    static render(p){
        const {sin,exp,pow,round,min,max,PI}=Math;
        const v=(k,d,a=0,b=1)=>Number.isFinite(p[k])?SoundDSP.clamp(p[k],a,b):d;
        const rate=SoundDSP.rate,duration=v('duration',1.5,0.2,5),out=new Float32Array(round(duration*rate));
        const random=SoundDSP.rng(v('seed',0.5)),beats=round(v('beats',3,1,12)),slot=duration*0.85/beats;
        const size=v('size',0.5),pitch=45*pow(2,v('pitch',0.35)*2.3),separation=v('separation',0.35);
        const secondary=v('secondary',0.6),murmur=v('murmur',0.1),tension=v('tension',0.2),irregular=v('irregular',0.05);
        const tau=PI*2,gain=0.85/Math.sqrt(max(1,beats*(0.02+size*0.07)/duration*3));
        for(let beat=0;beat<beats;beat++){
            const start=0.008+beat*slot+(beat?((random()-0.5)*slot*irregular*0.35):0);
            for(let chamber=0;chamber<2;chamber++){
                const onset=round((start+chamber*slot*(0.22+separation*0.25))*rate);
                const decay=0.013+size*0.08,frequency=pitch*(chamber?1.35:1)*(0.96+random()*0.08);
                const length=min(out.length-onset,round(decay*7*rate));
                let phase=random()*tau,low=0;
                for(let i=0;i<length;i++){
                    const t=i/rate,env=exp(-t/decay)*min(1,t/0.002);
                    phase+=tau*frequency*(1+0.8*exp(-t/0.008))/rate;
                    low+=(random()*2-1-low)*0.08;
                    out[onset+i]+=(sin(phase)+tension*0.25*sin(phase*3)+low*murmur)*env*gain*(chamber?secondary:1);
                }
            }
        }
        let flow=0;
        for(let i=0;i<out.length;i++){
            flow+=(random()*2-1-flow)*0.025;
            out[i]+=flow*murmur*0.35*sin(PI*i/out.length);
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}
