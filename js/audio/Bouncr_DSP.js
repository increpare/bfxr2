// A single body's flights get shorter after every collision; material modes ring at contact.
class Bouncr_DSP {
    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',2,0.2,5),length=Math.round(rate*duration);
        const out=new Float32Array(length),random=SoundDSP.rng(value('seed',0.5));
        const material=Math.round(value('material',0,0,4)),count=Math.round(value('count',7,2,20));
        const bounce=value('bounce',0.65),gravity=value('gravity',0.5),size=value('size',0.5);
        const hardness=value('hardness',0.6),spin=value('spin',0);
        const sin=Math.sin,exp=Math.exp,pow=Math.pow,min=Math.min,max=Math.max,tau=Math.PI*2;
        const pitches=[0.55,1,2.8,3.5,0.7],rings=[0.05,0.018,0.16,0.09,0.026];
        const ratios=[[1,2,3.1],[1,2.43,4.13],[1,1.47,2.71],[1,2.76,5.4],[1,1.91,3.47]][material];
        const base=(110+900*pow(1-size,2))*pitches[material];
        let time=0.012,gap=min(duration*0.42,0.18+0.45*(1-gravity));
        for(let hit=0;hit<count;hit++) {
            const start=Math.round(time*rate);if(start>=length)break;
            const strength=pow(0.53+bounce*0.43,hit)*(0.9+random()*0.1);
            const detune=1+(random()-0.5)*0.06*spin;
            const decay=(rings[material]+size*0.035)*(0.55+hardness*0.8);
            const end=min(length,start+Math.ceil(max(0.1,decay*7)*rate));
            const contact=0.0015+(1-hardness)*0.008;
            for(let i=start;i<end;i++) {
                const t=(i-start)/rate,attack=min(1,t/(0.0004+(1-hardness)*0.002));
                const bend=material===0 ? 1+0.65*exp(-t*35) : 1;
                const phase=tau*base*detune*t;
                const modes=sin(phase*bend)+0.3*sin(phase*ratios[1])*exp(-t/decay)+0.15*hardness*sin(phase*ratios[2]);
                const noise=(random()*2-1)*exp(-t/contact)*(0.18+hardness*0.42);
                out[i]+=(modes*exp(-t/decay)*0.65+noise)*strength*attack;
            }
            // Restitution governs the shrinking flight, while spin adds a faster settling rattle.
            time+=gap;gap*=0.4+bounce*0.54;
            gap=max(0.006,gap*(1-spin*0.12));
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
