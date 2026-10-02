// Nonperiodic pressure shock, cooling turbulent gas, and short rubble contacts.
class Boomr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.5,0.12,5),frames=Math.round(rate*duration);
        const out=new Float32Array(frames),size=value('size',0.5),pressure=value('pressure',0.7),blast=value('blast',0.65);
        const debris=value('debris',0.35),spread=value('spread',0.5),tail=value('tail',0.45),muffle=value('muffle',0.15);
        const random=SoundDSP.rng(value('seed',0.5)),exp=Math.exp,min=Math.min,pow=Math.pow,abs=Math.abs;
        const tau=2*Math.PI,blastDecay=0.025+duration*(0.05+tail*0.3);
        const coefficient=hz=>1-exp(-tau*hz/rate);
        const pressureFilter=coefficient(80+420*pow(1-size,2)),pressureDC=coefficient(18);
        const rumbleFilter=coefficient(28+90*(1-size)),driftFilter=coefficient(8);
        const finalFilter=coefficient(85+15000*pow(1-muffle,3));
        const shockTime=0.0015+size*0.013,pressureDecay=0.022+size*0.21;
        const startFrame=Math.round(0.006*rate);
        let fire=0,pressureLow=0,pressureSlow=0,rumble=0,drift=0,turbulence=0;
        for(let i=startFrame;i<frames;i++) {
            const t=(i-startFrame)/rate,noise=random()*2-1,bodyNoise=random()*2-1;
            pressureLow+=pressureFilter*(bodyNoise-pressureLow);
            pressureSlow+=pressureDC*(pressureLow-pressureSlow);
            rumble+=rumbleFilter*(bodyNoise-rumble);
            drift+=driftFilter*(rumble-drift);
            turbulence+=0.0018*(noise-turbulence);
            // A single compression/rarefaction pulse has no oscillator period.
            const shock=(1-t/shockTime)*exp(-t/shockTime);
            const pressureBody=(pressureLow-pressureSlow)*4.5*exp(-t/pressureDecay);
            const snap=noise*exp(-t/(0.0007+size*0.0025));
            // Expanding gas loses high frequencies quickly, leaving uneven low pressure.
            const fireFilter=coefficient(160+6500*(1-size*0.7)*exp(-t/(blastDecay*0.32)));
            fire+=fireFilter*(noise-fire);
            const plume=fire*exp(-t/blastDecay)*(0.75+abs(turbulence)*9);
            const rolling=(rumble-drift)*7*exp(-t/(0.08+duration*(0.12+tail*0.36)))*(1-exp(-t/0.014));
            out[i]=pressure*(shock*1.6+pressureBody+snap*0.6)+blast*plume*2.2+tail*rolling;
        }
        const pieces=Math.round(4+debris*48);
        for(let piece=0;piece<pieces;piece++) {
            const start=Math.floor((0.009+random()*duration*(0.04+spread*0.8))*rate);
            const chunk=random(),life=(0.0015+chunk*0.018)*(0.45+size);
            const length=min(frames-start,Math.ceil(life*rate*7));
            const gain=debris*(0.16+random()*0.42),damping=exp(-1/(life*rate));
            const dustFilter=coefficient((700+random()*6500)*(1-size*0.72));
            const bodyFilter=coefficient(100+random()*450*(1-size*0.6));
            let dust=0,body=0,envelope=1,crack=1;
            const crackDecay=exp(-1/(rate*(0.0003+chunk*0.001)));
            for(let j=0;j<length;j++) {
                const noise=random()*2-1;
                dust+=dustFilter*(noise-dust);
                body+=bodyFilter*(noise-body);
                // Rough scattering and a dull contact body cannot settle into a note.
                out[start+j]+=(dust*envelope+body*envelope*2+noise*crack*0.3)*gain;
                envelope*=damping;crack*=crackDecay;
            }
        }
        let filtered=0;
        for(let i=0;i<frames;i++) {
            filtered+=finalFilter*(out[i]-filtered);
            out[i]=filtered;
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
