// Two syringeal oscillators, beak resonances and a syllable-level breath schedule.
class Birdr_DSP {
    static render(p) {
        const {sin,cos,exp,PI,min,max,round} = Math;
        const value = (name,fallback,low=0,high=1) => Number.isFinite(p[name]) ? min(high,max(low,p[name])) : fallback;
        const rate=SoundDSP.rate,tau=2*PI,duration=value('duration',0.8,0.15,5);
        const output=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if (volume===0) return SoundDSP.finish(output,0);
        const random=SoundDSP.rng(value('seed',0.5)),voice=round(value('voice',0,0,4));
        const count=round(value('syllables',3,1,16)),gap=value('gap',0.3,0,0.85);
        const pitch=180*2**(value('pitch',0.58)*4.8),sweep=value('sweep',-0.3,-1,1),arch=value('arch',0.45,-1,1);
        const trill=value('trill',0.15),trillRate=5+value('trill_rate',0.4)*65;
        const duet=value('duet',0.1),rasp=value('rasp',0.04),breath=value('breath',0.03);
        const rhythm=value('rhythm',0.12),variation=value('variation',0.25);
        // Repeat a contour with alternating answers and seeded drift, rather than choosing unrelated notes.
        const weights=Array.from({length:count},()=>1+rhythm*(random()-0.5)*1.1);
        const total=weights.reduce((a,b)=>a+b,0);
        let offset=0;
        const syllables=weights.map((weight,index)=>{
            const length=weight/total*output.length;
            const result={start:offset,active:max(1,length*(1-gap)),
                shift:variation*((index%2?-0.6:0.15)+(random()-0.5)*0.2),
                curvature:1+variation*(random()-0.5)*0.5,phase:random()*tau};
            offset+=length; return result;
        });
        let phase=random()*tau,second=random()*tau,noiseLow=0,call=0;
        const radii=[exp(-PI*260/rate),exp(-PI*480/rate)],y1=[0,0],y2=[0,0];
        const centers=voice===3?[850,1850]:[1550,3200];
        const coeff=centers.map((f,i)=>2*radii[i]*cos(tau*f/rate));
        for(let i=0;i<output.length;i++) {
            while(call<count-1 && i>=syllables[call+1].start) call++;
            const syllable=syllables[call],local=i-syllable.start,u=min(1,local/syllable.active);
            const attack=max(35,syllable.active*(voice===4?0.18:0.065));
            const release=max(70,syllable.active*(voice===3?0.4:0.2));
            let envelope=max(0,min(1,local/attack,(syllable.active-local)/release));
            envelope*=voice===4?sin(PI*u)**0.6:0.88+0.12*sin(PI*u);
            const tremor=sin(tau*trillRate*local/rate+syllable.phase);
            const contour=sweep*(u-0.5)*1.8+arch*sin(PI*u)*syllable.curvature+syllable.shift;
            const irregular=rasp*(0.035*sin(phase*0.47)+0.022*sin(second*0.31));
            const frequency=min(10500,pitch*2**(contour+trill*0.2*tremor+irregular));
            phase+=tau*frequency/rate;
            second+=tau*min(11500,frequency*(1.12+0.15*sin(PI*u)+duet*0.35))/rate;
            const noise=random()*2-1;
            noiseLow+=(noise-noiseLow)*0.13;
            const modulation=voice===1?duet*1.15*sin(second):0;
            let source=sin(phase+modulation);
            if(voice===2) source=0.7*sin(phase+0.8*sin(phase))+0.23*sin(phase*2)+0.12*sin(phase*3);
            if(voice===3) source=0.55*sin(phase+1.3*sin(phase))+0.3*sin(phase*0.5)+rasp*noiseLow;
            if(voice===4) source=0.88*sin(phase)+0.1*sin(phase*2);
            source+=duet*0.28*sin(second)+rasp*0.2*sin(phase*0.5)*(0.65+0.35*sin(phase*0.19));
            let resonant=0;
            for(let band=0;band<2;band++) {
                const sample=(1-radii[band])*source+coeff[band]*y1[band]-radii[band]**2*y2[band];
                y2[band]=y1[band];y1[band]=sample;resonant+=sample;
            }
            if(voice===2 || voice===3) source=source*0.62+resonant*0.85;
            source=source*(1-breath*0.45)+breath*(noise-noiseLow)*0.25;
            const pulse=1-trill*0.35+trill*0.35*tremor;
            output[i]=source*envelope*pulse*0.65;
        }
        return SoundDSP.finish(output,volume);
    }
}
