// A weapon gesture: capacitor rise, firing transient, energy body and recoil.
class Pewpr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',0.7,0.12,5),frames=Math.round(duration*rate),out=new Float32Array(frames);
        const kind=Math.round(value('kind',0,0,3)),shots=Math.round(value('shots',1,1,8));
        const pitch=value('pitch',0.55),sweep=value('sweep',-0.65,-1,1),charge=value('charge',0),punch=value('punch',0.65);
        const body=value('body',0.45),recoil=value('recoil',0.2),grit=value('grit',0.1);
        const random=SoundDSP.rng(value('seed',0.5)),sin=Math.sin,exp=Math.exp,pow=Math.pow,min=Math.min,max=Math.max;
        const tau=2*Math.PI,base=90*pow(2,pitch*5),chargeTime=duration*charge*0.58;
        const spacing=(duration-chargeTime)*0.58/max(1,shots-1),gain=0.8/Math.sqrt(1+0.22*(shots-1));
        for(let shot=0;shot<shots;shot++) {
            const firing=chargeTime+shot*spacing,start=shot===0?0:Math.floor(firing*rate);
            const bodyTime=max(0.008,(duration-chargeTime)*(0.07+body*0.3)/Math.sqrt(shots));
            const tailTime=bodyTime*(0.25+recoil),detune=1+(random()-0.5)*0.035;
            let phase=random()*tau,subPhase=0,noiseLow=0;
            for(let i=start;i<frames;i++) {
                const t=i/rate,age=t-firing,noise=random()*2-1;noiseLow+=0.12*(noise-noiseLow);
                if(age<0) {
                    const u=t/max(chargeTime,0.0001);
                    phase+=tau*base*(0.25+u*u*1.4)/rate;if(phase>tau)phase-=tau;
                    out[i]+=0.14*charge*u*u*(sin(phase)+0.3*sin(phase*2.01))*min(1,t/0.008);
                    continue;
                }
                const sweepProgress=1-exp(-age/(0.008+bodyTime*0.9));
                const frequency=min(10000,base*detune*pow(2,sweep*sweepProgress*3));
                phase+=tau*frequency/rate;if(phase>tau)phase-=tau;
                subPhase+=tau*(35+70*(1-pitch))*exp(-age/(0.08+bodyTime))/rate;
                const envelope=exp(-age/bodyTime),attack=min(1,age/0.0008);
                let tone;
                if(kind===1) tone=sin(phase+2.5*sin(phase*0.502))+0.25*sin(phase*1.99);
                else if(kind===2) tone=0.3*sin(phase)+noiseLow*3;
                else if(kind===3) tone=sin(phase+0.7*sin(phase*1.414))+0.4*sin(phase*2.76);
                else tone=sin(phase)+0.22*sin(phase*2)+0.08*sin(phase*3);
                const snap=(noise*(0.2+grit*0.8)+sin(phase*1.73)*0.35)*punch*exp(-age/0.008);
                const energy=(tone*(0.22+body*0.85)+grit*noise*0.7)*envelope;
                const recoilAge=age-bodyTime*0.8;
                const kick=recoilAge>0?recoil*sin(subPhase)*exp(-recoilAge/max(tailTime,0.005))*min(1,recoilAge/0.005):0;
                out[i]+=gain*(snap+energy+kick)*attack;
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
