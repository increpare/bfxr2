// A moving air source: turbulent bands and a tonal edge sweep past the listener.
class Whooshr_DSP {
    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',0.6,0.1,5),length=Math.round(rate*duration);
        const out=new Float32Array(length),random=SoundDSP.rng(value('seed',0.5));
        const size=value('size',0.4),air=value('air',0.8),whistle=value('whistle',0.25);
        const movement=value('movement',0.7),focus=value('focus',0.6),flutter=value('flutter',0.1);
        const sin=Math.sin,pow=Math.pow,exp=Math.exp,min=Math.min,pi=Math.PI,tau=2*pi;
        const base=190*pow(2,(1-size)*3.1),offset=random()*tau,beat=8+random()*10;
        let low=0,broad=0,phase=offset;
        for(let i=0;i<length;i++) {
            const u=i/(length-1),t=i/rate,position=(u-0.5)*2;
            const approach=1-movement*0.7*position;
            const envelope=pow(sin(pi*u),0.6+focus*5)/(1+focus*position*position*7);
            const gust=1-flutter*0.65+flutter*0.65*sin(tau*beat*t+offset)*sin(tau*beat*t+offset);
            const cutoff=min(12000,(350+5500*(1-size))*approach);
            const noise=random()*2-1;
            low+=(1-exp(-tau*cutoff/rate))*(noise-low);
            broad+=(1-exp(-tau*cutoff*0.14/rate))*(noise-broad);
            phase+=tau*base*approach*(1+flutter*0.025*sin(tau*beat*t))/rate;
            if(phase>tau)phase-=tau;
            out[i]=((low-broad)*air*2.7+(sin(phase)+0.12*sin(phase*2))*whistle*0.45)*envelope*gust;
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
