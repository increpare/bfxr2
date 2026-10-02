// Low structural modes drift beneath turbulent pressure and scattered grit.
class Rumblr_DSP {
    static render(p){
        const {sin,exp,pow,round,min,max,PI}=Math;
        const v=(k,d,a=0,b=1)=>Number.isFinite(p[k])?SoundDSP.clamp(p[k],a,b):d;
        const rate=SoundDSP.rate,duration=v('duration',2,0.2,5),out=new Float32Array(round(duration*rate));
        const random=SoundDSP.rng(v('seed',0.5)),size=v('size',0.6),weight=v('weight',0.6);
        const rough=v('roughness',0.4),tremor=v('tremor',0.3),dust=v('dust',0.15),attack=v('attack',0.3),sweep=v('sweep',0,-1,1);
        const tau=PI*2,base=28*pow(2,(1-size)*2.8),modes=[];
        for(let n=0;n<7;n++)modes.push({phase:random()*tau,frequency:base*(1+n*0.347)*(0.97+random()*0.06),gain:1/(1+n*0.6)});
        let low=0,deep=0,grit=0;
        for(let i=0;i<out.length;i++){
            const t=i/rate,u=i/(out.length-1),noise=random()*2-1;
            low+=(noise-low)*(0.008+rough*0.055);deep+=(noise-deep)*0.004;
            grit=grit*0.991+(random()<dust*0.0009?(0.1+random()*0.3):0);
            const bend=pow(2,sweep*(u-0.5)),shudder=0.75+0.25*sin(tau*(2+tremor*23)*t);
            let body=0;
            for(const mode of modes){mode.phase+=tau*mode.frequency*bend*(1+rough*deep*0.5)/rate;body+=sin(mode.phase)*mode.gain;}
            const envelope=min(1,u/max(0.01,attack*0.5),(1-u)/0.16);
            out[i]=(body*(0.14+weight*0.14)+low*rough*2+noise*grit*dust)*envelope*(1-tremor+tremor*shudder);
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}
