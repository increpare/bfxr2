// Two contacts excite a small damped detent and the lower modes of its housing.
class Tappr_DSP {
    static materials = [
        {pitch:0.7,ring:0.42,noise:0.15,ratios:[1,1.91,3.07]},
        {pitch:1,ring:0.75,noise:0.3,ratios:[1,2.18,3.73]},
        {pitch:0.82,ring:0.95,noise:0.22,ratios:[1,1.63,2.91]},
        {pitch:1.25,ring:1.7,noise:0.12,ratios:[1,2.37,4.13]},
        {pitch:1.55,ring:1.35,noise:0.08,ratios:[1,1.48,2.71]},
        {pitch:0.67,ring:0.58,noise:0.4,ratios:[1,2.07,3.41]}
    ];

    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate, duration=value('duration',0.18,0.04,2);
        const frames=Math.round(duration*rate), out=new Float32Array(frames);
        const force=new Float32Array(frames), random=SoundDSP.rng(value('seed',0.5));
        const material=this.materials[Math.round(value('material',1,0,5))];
        const size=value('size',0.5), hardness=value('hardness',0.4), body=value('body',0.4);
        const release=value('release',0.35), gap=value('gap',0.4), electronic=value('electronic',0.08);
        const damping=value('damping',0.7), sin=Math.sin, cos=Math.cos, exp=Math.exp;
        const pow=Math.pow, min=Math.min, max=Math.max, round=Math.round, tau=Math.PI*2;
        const base=1750*pow(2,-3.3*size)*material.pitch*(0.97+random()*0.06);
        const decay=(0.003+duration*0.16*material.ring)*(1-0.91*damping);
        const onset=round(0.0055*rate);
        const contacts=[{start:onset,strength:1,polarity:1},
            {start:round((0.0055+duration*(0.1+gap*0.58))*rate),strength:release,polarity:-1}];
        // Both contacts consume the same random stream even when release is zero.
        // Changing release strength therefore preserves the first contact's detail.
        for(const contact of contacts) {
            const width=max(2,round((0.00015+(1-hardness)*0.0017)*(0.8+random()*0.4)*rate));
            for(let j=0;j<width && contact.start+j<frames;j++) {
                const impulse=sin(Math.PI*(j+0.5)/width)*Math.PI/(2*width);
                force[contact.start+j]+=impulse*contact.strength*contact.polarity;
            }
            const scrapeLength=round((0.0015+(1-hardness)*0.004)*rate);
            let smooth=0;
            for(let j=0;j<scrapeLength && contact.start+j<frames;j++) {
                smooth+=(random()*2-1-smooth)*(0.1+hardness*0.6);
                out[contact.start+j]+=smooth*exp(-j/(scrapeLength*0.22))*material.noise
                    *(0.22+hardness*0.5)*contact.strength;
            }
        }
        const modes=material.ratios.map((ratio,index)=>{
            const angle=tau*min(rate*0.4,base*ratio)/rate;
            const radius=exp(-1/(max(0.0007,decay/(1+index*0.7))*rate));
            return {c:cos(angle)*radius,s:sin(angle)*radius,re:0,im:0,
                gain:(index===0?0.68:0.27*pow(hardness+0.05,index))};
        });
        // The housing has its own low modes rather than merely darkening the detent.
        for(let index=0;index<2;index++) {
            const angle=tau*(130+620*pow(1-size,2))*(index===0?1:1.57)/rate;
            const radius=exp(-1/((0.004+duration*0.07)*(1-0.8*damping)*(index===0?1:0.65)*rate));
            modes.push({c:cos(angle)*radius,s:sin(angle)*radius,re:0,im:0,gain:body*(index===0?0.8:0.24)});
        }
        for(let i=onset;i<frames;i++) {
            let sample=0;
            for(const mode of modes) {
                const re=mode.re*mode.c-mode.im*mode.s+force[i];
                mode.im=mode.re*mode.s+mode.im*mode.c;
                mode.re=re;
                sample+=re*mode.gain;
            }
            out[i]+=sample;
        }
        const electronicLength=min(round(duration*rate*0.3),round(rate*0.08));
        const electronicPitch=850*pow(2,(1-size)*1.5);
        for(const contact of contacts) {
            let phase=0;
            for(let j=0;j<electronicLength && contact.start+j<frames;j++) {
                const age=j/electronicLength;
                phase+=tau*electronicPitch*(1+contact.polarity*0.18*(1-age))/rate;
                out[contact.start+j]+=sin(phase)*sin(Math.PI*age)*exp(-age*4)
                    *electronic*0.25*contact.strength;
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
