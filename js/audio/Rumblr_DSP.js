// A controlled sub body carries slower pressure changes, structural modes and debris.
class Rumblr_DSP {
    static render(p) {
        const {sin,exp,pow,round,min,max,PI}=Math,tau=PI*2;
        const v=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=v('duration',2,0.2,5),out=new Float32Array(round(duration*rate));
        const random=SoundDSP.rng(v('seed',0.5)),size=v('size',0.6),weight=v('weight',0.6);
        const rough=v('roughness',0.4),tremor=v('tremor',0.3),dust=v('dust',0.15);
        const attack=v('attack',0.3),sweep=v('sweep',0,-1,1),depth=v('depth',0.75),harmonics=v('harmonics',0.35);
        const base=32*pow(2,(1-size)*2.6-depth*0.85),modes=[];
        for(let n=0;n<6;n++)modes.push({phase:random()*tau,frequency:base*(1.7+n*0.83)*(0.97+random()*0.06),gain:1/(1+n*0.7)});
        let phase=random()*tau,nearPhase=random()*tau,low=0,pressure=0,drift=0,grit=0,dc=0;
        const nearRatio=1.008+random()*0.025,motionPhase=random()*tau;
        const lowCoefficient=1-exp(-tau*(45+rough*150)/rate),pressureCoefficient=1-exp(-tau*(20+rough*32)/rate);
        const dcCoefficient=1-exp(-tau*7/rate);
        for(let i=0;i<out.length;i++) {
            const t=i/rate,u=i/(out.length-1),noise=random()*2-1;
            low+=(noise-low)*lowCoefficient;pressure+=(low-pressure)*pressureCoefficient;
            drift+=(noise-drift)*0.00015;
            grit=grit*0.992+(random()<dust*0.0011?(0.08+random()*0.32):0);
            const bend=pow(2,sweep*(u-0.5)*0.7),wander=1+rough*drift*1.6;
            // Keep fundamental motion audible and above DC even at the largest falling settings.
            const frequency=max(16,base*bend*wander);
            phase+=tau*frequency/rate;nearPhase+=tau*frequency*nearRatio/rate;
            const sub=sin(phase)*(0.22+weight*0.29+depth*0.17)+sin(nearPhase)*depth*0.14;
            // Selected upper harmonics convey the same fundamental on speakers without deep bass.
            const overtones=harmonics*(sin(phase*2)*0.12+sin(phase*3)*0.16+sin(phase*4)*0.11+sin(phase*5)*0.07);
            let structure=0;
            for(const mode of modes) {
                mode.phase+=tau*mode.frequency*bend*(1+rough*drift*2.5)/rate;
                structure+=sin(mode.phase)*mode.gain;
            }
            const shudder=0.62+0.23*sin(tau*(0.8+tremor*6.5)*t+motionPhase)+0.15*sin(tau*0.71*t+rough*9*drift);
            const swell=0.88+0.12*sin(tau*(0.19+rough*0.25)*t+motionPhase);
            const envelope=min(1,u/max(0.01,attack*0.5),(1-u)/0.18);
            const body=sub+overtones+structure*(0.12-depth*0.065)*(0.7+weight*0.3);
            const turbulence=pressure*rough*(2.2+weight*2)+low*rough*0.75;
            const value=(body+turbulence+noise*grit*dust*0.5)*swell*(1-tremor+tremor*shudder);
            dc+=(value-dc)*dcCoefficient;
            out[i]=(value-dc)*envelope;
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}
