// Seeded leader arcs split into shorter branches over an unstable mains field.
class Zappr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.2,0.12,5),frames=Math.round(duration*rate),out=new Float32Array(frames);
        const arcs=Math.round(value('arcs',7,1,24)),voltage=value('voltage',0.55),branching=value('branching',0.4);
        const crackle=value('crackle',0.45),hum=value('hum',0.2),spark=value('spark',0.65),spread=value('spread',0.7),decay=value('decay',0.4);
        const random=SoundDSP.rng(value('seed',0.5)),sin=Math.sin,exp=Math.exp,pow=Math.pow,min=Math.min,max=Math.max;
        const tau=2*Math.PI,humFrequency=42+voltage*65,events=[];
        for(let arc=0;arc<arcs;arc++) {
            const position=arc===0?0.004:(arc+random()*0.65)/arcs*duration*(0.03+spread*0.86);
            const life=0.008+decay*0.1,frequency=400+voltage*4800*(0.6+random()*0.8);
            events.push([position,life,frequency,0.55+random()*0.4]);
            const branches=Math.round(branching*(2+random()*5));
            for(let branch=0;branch<branches;branch++)events.push([position+life*(0.3+random()*2),life*(0.18+random()*0.55),frequency*(0.5+random()*1.2),branching*(0.15+random()*0.25)]);
        }
        let phase=0,crackleEnv=0,noiseLow=0;
        const crackleFall=exp(-1/(rate*(0.001+decay*0.014)));
        for(let i=0;i<frames;i++) {
            const t=i/rate,noise=random()*2-1;noiseLow+=0.075*(noise-noiseLow);
            phase+=tau*humFrequency/rate;if(phase>tau)phase-=tau;
            if(random()<crackle*(12+voltage*130)/rate)crackleEnv=0.15+random()*0.55;
            crackleEnv*=crackleFall;
            const field=hum*(sin(phase)+0.28*sin(phase*3)+0.15*sin(phase*7))*0.27;
            out[i]=(field+crackleEnv*(noise-noiseLow)*crackle)*min(1,t/0.006)*pow(max(0,1-t/duration),0.2+decay*0.6);
        }
        for(const [time,life,frequency,gain] of events) {
            const start=Math.round(time*rate),length=min(frames-start,Math.ceil(life*rate*6));
            let phase=random()*tau,low=0;
            for(let j=0;j<length;j++) {
                const age=j/rate,noise=random()*2-1;
                phase+=tau*frequency*(0.3+0.7*exp(-age/life))/rate;if(phase>tau)phase-=tau;
                low+=0.2*(noise-low);
                const discharge=(0.4+spark*0.5)*(noise-low)+sin(phase+sin(phase*0.47)*voltage*2)*(1-spark*0.65);
                const restrike=0.65+0.35*max(0,sin(tau*age*(75+voltage*290)));
                out[start+j]+=discharge*gain*exp(-age/life)*restrike*min(1,j/12);
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
