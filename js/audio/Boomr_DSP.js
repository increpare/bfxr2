// A pressure front, turbulent fireball and separately arriving fragments.
class Boomr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.5,0.12,5),frames=Math.round(rate*duration);
        const out=new Float32Array(frames),size=value('size',0.5),pressure=value('pressure',0.7),blast=value('blast',0.65);
        const debris=value('debris',0.35),spread=value('spread',0.5),tail=value('tail',0.45),muffle=value('muffle',0.15);
        const random=SoundDSP.rng(value('seed',0.5)),sin=Math.sin,exp=Math.exp,min=Math.min,max=Math.max,pow=Math.pow;
        const tau=2*Math.PI,base=35+180*pow(1-size,2),blastDecay=0.025+duration*(0.05+tail*0.3);
        const filter=0.006+0.76*pow(1-muffle,3),rumbleFilter=0.004+(1-size)*0.014;
        let phase=0,low=0,rumble=0,filtered=0;
        for(let i=0;i<frames;i++) {
            const t=i/rate,noise=random()*2-1;
            phase+=tau*base*(1+1.8*exp(-t/(0.008+size*0.055)))/rate;
            if(phase>tau)phase-=tau;
            low+=filter*(noise-low);rumble+=rumbleFilter*(noise-rumble);
            const front=sin(phase)*exp(-t/(0.025+size*0.22));
            const fire=low*exp(-t/blastDecay)*(1+0.22*sin(tau*19*t));
            const rolling=rumble*6*exp(-t/(0.08+duration*(0.12+tail*0.36)))*(1-exp(-t/0.018));
            const signal=pressure*front*1.5+blast*fire*1.3+tail*rolling;
            filtered+=filter*(signal-filtered);
            out[i]=filtered*min(1,t/0.0015);
        }
        const pieces=Math.round(4+debris*48);
        for(let piece=0;piece<pieces;piece++) {
            const start=Math.floor((0.006+random()*duration*(0.04+spread*0.8))*rate);
            const life=(0.008+random()*0.075)*(0.4+size),length=min(frames-start,Math.ceil(life*rate*5));
            const frequency=(180+random()*1900)*(1.2-size*0.8),gain=debris*(0.12+random()*0.38);
            const damping=exp(-1/(life*rate)),coefficient=2*Math.cos(tau*frequency/rate)*damping;
            let y1=0,y2=0,noiseLow=0;
            for(let j=0;j<length;j++) {
                const hit=j<20?(random()*2-1)*(1-j/20):0;
                const ring=hit+coefficient*y1-damping*damping*y2;y2=y1;y1=ring;
                noiseLow+=filter*(ring-noiseLow);
                out[start+j]+=noiseLow*gain*0.07*max(0,1-j/length);
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
