// Coupled object and surface modes are excited by the same finite contact pulse.
class Bouncr_DSP {
    static render(p) {
        const v=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const {sin,exp,pow,min,max,sqrt,round,PI}=Math,tau=PI*2,rate=SoundDSP.rate;
        const duration=v('duration',2,0.2,5),out=new Float32Array(round(rate*duration));
        const random=SoundDSP.rng(v('seed',0.5)),material=round(v('material',0,0,4)),surface=round(v('surface',0,0,5));
        const count=round(v('count',1,1,20)),bounce=v('bounce',0.65),gravity=v('gravity',0.5);
        const size=v('size',0.5),hardness=v('hardness',0.6),spin=v('spin',0),force=v('force',0.65),tail=v('tail',0.4);
        // Frequency, decay, stiffness and inharmonic partials describe each body.
        const objects=[
            {pitch:0.55,decay:0.041,hard:0.22,ratios:[1,1.97,3.17,4.8]},
            {pitch:1,decay:0.030,hard:0.64,ratios:[1,2.43,4.13,6.27]},
            {pitch:2.5,decay:0.16,hard:1,ratios:[1,1.47,2.71,4.09]},
            {pitch:3.3,decay:0.10,hard:0.95,ratios:[1,2.76,5.4,8.13]},
            {pitch:0.72,decay:0.025,hard:0.86,ratios:[1,1.91,3.47,5.31]}
        ];
        const surfaces=[
            {pitch:260,decay:0.022,hard:0.95,ring:0.30,ratios:[1,1.61,2.83,4.41]},
            {pitch:135,decay:0.075,hard:0.6,ring:0.72,ratios:[1,2.18,3.72,5.41]},
            {pitch:330,decay:0.26,hard:0.93,ring:0.85,ratios:[1,1.59,2.32,3.79]},
            {pitch:710,decay:0.18,hard:1,ring:0.70,ratios:[1,1.71,3.04,4.93]},
            {pitch:78,decay:0.017,hard:0.16,ring:0.18,ratios:[1,1.83,2.81,4.18]},
            {pitch:90,decay:0.016,hard:0.035,ring:0.15,ratios:[1,2.11,3.43,4.72]}
        ];
        const object=objects[material],target=surfaces[surface];
        const stiffness=sqrt(object.hard*target.hard)*(0.18+hardness*0.82);
        const transfer=0.15+target.hard*0.85,decayScale=(0.3+tail*2.7)*(0.75+force*0.5);
        const base=(95+790*pow(1-size,2))*object.pitch;
        let time=0.012,gap=min(duration*0.42,0.18+0.45*(1-gravity));
        for(let hit=0;hit<count;hit++) {
            const start=round(time*rate);if(start>=out.length)break;
            const strength=(0.18+force*0.82)*pow(0.53+bounce*0.43,hit)*(0.94+random()*0.06);
            const contact=(0.0008+(1-stiffness)*0.013)/(0.65+force*0.8);
            const objectDecay=object.decay*decayScale*(0.3+transfer*0.7)*(0.75+bounce*0.35);
            const surfaceDecay=target.decay*decayScale*(0.8+size*0.5);
            const detune=1+(random()-0.5)*(0.025+spin*0.07);
            const modes=[];
            for(let mode=0;mode<4;mode++) {
                modes.push({frequency:min(rate*0.42,base*object.ratios[mode]*detune),phase:0,
                    decay:objectDecay/(1+mode*(0.2+(1-hardness)*0.4)),gain:transfer*0.72*pow(stiffness+0.18,mode*0.48)/(1+mode*0.8)});
                modes.push({frequency:min(rate*0.42,target.pitch*(1.6-size)*target.ratios[mode]*(0.97+random()*0.06)),phase:0,
                    decay:surfaceDecay/(1+mode*0.48),gain:target.ring*0.72*pow(stiffness+0.12,mode*0.6)/(1+mode)});
            }
            // A broad soft contact cannot excite modes faster than its pressure pulse.
            for(const mode of modes)mode.gain/=1+pow(mode.frequency*contact*0.4,2);
            const end=min(out.length,start+Math.ceil(max(contact*10,max(objectDecay,surfaceDecay)*7)*rate));
            let low=0,rub=0,absorbed=0;
            const tone=1-exp(-tau*(100+stiffness*11000)/rate);
            const absorption=1-exp(-tau*(100+pow(target.hard,2)*14000)/rate);
            for(let i=start;i<end;i++) {
                const t=(i-start)/rate,attack=min(1,t/(0.00025+contact*0.3));
                const noise=random()*2-1;low+=(noise-low)*tone;rub+=(noise-rub)*0.08;
                let body=0;
                for(const mode of modes) {
                    // Integrating instantaneous frequency gives a smooth compressed-rubber release.
                    const bend=material===0?1+(0.2+force*0.65)*exp(-t/(contact*2.5)):1;
                    mode.phase+=tau*mode.frequency*bend/rate;
                    body+=sin(mode.phase)*mode.gain*exp(-t/mode.decay);
                }
                const contactNoise=low*(0.18+stiffness*0.6)*exp(-t/contact);
                const scatter=(surface===4?0.6:surface===0?0.16:0.04)*low*exp(-t/(0.014+tail*0.035));
                const scrape=rub*spin*0.6*exp(-t/(0.025+spin*0.08))*(0.65+0.35*sin(tau*(110+random()*30)*t));
                absorbed+=(body+contactNoise+scatter+scrape-absorbed)*absorption;
                out[i]+=absorbed*strength*attack;
            }
            time+=gap;gap=max(0.006,gap*(0.4+bounce*0.54)*(1-spin*0.12));
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}
