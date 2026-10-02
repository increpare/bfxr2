// Continuous surface rumble is punctuated by wheel contacts that excite a body's resonances.
class Rollr_DSP {
    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',2,0.2,5),length=Math.round(rate*duration);
        const out=new Float32Array(length),random=SoundDSP.rng(value('seed',0.5));
        const material=Math.round(value('material',0,0,3)),wheels=Math.round(value('wheels',2,1,6));
        const speed=value('speed',0.5),roughness=value('roughness',0.45),size=value('size',0.5);
        const hardness=value('hardness',0.6),slowing=value('slowing',0.35);
        const sin=Math.sin,cos=Math.cos,exp=Math.exp,pow=Math.pow,min=Math.min,max=Math.max,tau=Math.PI*2;
        const base=(100+750*pow(1-size,2))*[1,0.6,1.8,0.3][material];
        const ring=[0.022,0.035,0.075,0.012][material]*(0.7+hardness*0.7);
        const radius=exp(-1/(ring*rate)),angle=tau*base/rate,realCoeff=cos(angle)*radius,imagCoeff=sin(angle)*radius;
        const wheelPhases=Array.from({length:wheels},(_,i)=>i/wheels+random()*roughness*0.1);
        const wheelWeights=Array.from({length:wheels},()=>0.8+random()*0.2);
        const contactRate=2+speed*22,noiseCoeff=0.015+hardness*0.13;
        // Begin with a contact even when a slow wheel cannot complete a revolution.
        wheelPhases[0]=1-contactRate*0.012;
        const gain=1/max(1,Math.sqrt(wheels)*0.8);
        let low=0,grain=0,real=0,imaginary=0,contactNoise=0;
        for(let i=0;i<length;i++) {
            const u=i/(length-1),velocity=1-slowing*u*0.94;
            const drift=1+roughness*0.18*sin(tau*i/rate*1.7);
            let force=0;
            for(let wheel=0;wheel<wheels;wheel++) {
                wheelPhases[wheel]+=contactRate*velocity*drift/rate;
                if(wheelPhases[wheel]>=1){wheelPhases[wheel]-=1;force+=wheelWeights[wheel]*(1-roughness*0.4+random()*roughness*0.8);}
            }
            if(random()<roughness*(0.00015+speed*0.0015)*velocity)force+=roughness*random()*0.45;
            const noise=random()*2-1;
            low+=noiseCoeff*(noise-low);
            grain+=0.003*(noise-grain);
            contactNoise=contactNoise*0.9+force;
            const previous=real;
            real=real*realCoeff-imaginary*imagCoeff+force;
            imaginary=previous*imagCoeff+imaginary*realCoeff;
            const window=min(1,i/(rate*0.018),(length-1-i)/(rate*0.04));
            const rumble=(low-grain)*(0.02+roughness*0.7)*(0.35+hardness*0.65);
            out[i]=(real*0.6+noise*contactNoise*hardness*0.16+rumble)*window*pow(velocity,0.4)*gain;
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
