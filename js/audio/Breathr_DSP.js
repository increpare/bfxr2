// Lung cycles drive turbulent airflow through a changing throat and chest.
class Breathr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,round,floor,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,tau=PI*2,duration=value('duration',2,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        const random=SoundDSP.rng(value('seed',0.5)),cycles=round(value('cycles',3,1,10));
        const effort=value('effort',0.6),inhale=value('inhale',0.4,0.1,0.9),hold=value('hold',0.1,0,0.7);
        const throat=value('throat',0.5),rasp=value('rasp',0.2),flutter=value('flutter',0.2),space=value('space',0.1);
        const slot=out.length/cycles,inEnd=(1-hold)*inhale,outStart=inEnd+hold;
        const radius=exp(-PI*(95+effort*170)/rate),r2=radius*radius,bandGain=(1-radius)*2;
        const delay=round(rate*(0.04+space*0.13)),gain=0.8+effort*0.8;
        const variations=Array.from({length:cycles},()=>0.85+random()*0.3);
        let low=0,chest=0,y1=0,y2=0,previous=0,previous2=0,phase=random()*tau,coefficient=0;
        for(let i=0;i<out.length;i++) {
            const position=(i%slot)/slot,cycle=min(cycles-1,floor(i/slot));
            const inhaling=position<inEnd,exhaling=position>outStart;
            const local=inhaling?position/inEnd:exhaling?(position-outStart)/(1-outStart):0;
            const airflow=pow(max(0,sin(PI*local)),0.55+effort*0.8)*variations[cycle];
            const noise=random()*2-1;
            low+=(noise-low)*(inhaling?0.18+effort*0.25:0.045+effort*0.18);
            chest+=(noise-chest)*0.012;
            const opening=0.75+0.5*airflow;
            if((i&31)===0)coefficient=2*radius*cos(tau*(180+pow(1-throat,2)*1700)*opening*(inhaling?1.2:0.82)/rate);
            phase+=tau*(38+(1-throat)*95)*(1+flutter*0.14*sin(tau*6.7*i/rate))/rate;
            const turbulent=low-chest*0.65;
            const excitation=turbulent+(exhaling?rasp*(sin(phase)+0.3*sin(phase*1.5))*0.28:0);
            const resonant=bandGain*(excitation-previous2)+coefficient*y1-r2*y2;
            y2=y1;y1=resonant;previous2=previous;previous=excitation;
            const tremor=1-flutter*0.25+flutter*0.25*sin(tau*(9+effort*13)*i/rate);
            out[i]=(turbulent*0.65+resonant*2.2+chest*throat*1.5)*airflow*tremor*gain;
            if(i>=delay)out[i]+=out[i-delay]*space*0.42;
        }
        return SoundDSP.finish(out,volume);
    }
}
