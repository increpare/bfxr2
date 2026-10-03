// FM and shifted sidebands, a scanned resonant band, and a short moving comb.
class Holor_DSP {
    static render(p) {
        const {sin,cos,exp,pow,min,max,round,floor,PI}=Math;
        const value=(name,fallback,low=0,high=1)=>Number.isFinite(p[name])?min(high,max(low,p[name])):fallback;
        const rate=SoundDSP.rate,tau=2*PI,duration=value('duration',0.45,0.08,3);
        const output=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0) return SoundDSP.finish(output,0);
        const random=SoundDSP.rng(value('seed',0.5));
        const gesture=round(value('gesture',0,0,3)),base=140*2**(4.6*value('pitch',0.5));
        const sweep=value('sweep',0.4,-1,1),bandwidth=value('bandwidth',0.4);
        const sidebands=value('sidebands',0.45),scan=value('scan',0.25);
        const grain=value('grain',0.12),comb=value('comb',0.35);
        const modStep=tau*(43+base*0.317)/rate,scanStep=tau*(3+scan*scan*85)/rate;
        let phase=random()*tau,modPhase=random()*tau,scanPhase=random()*tau,shiftPhase=random()*tau;
        let x1=0,x2=0,y1=0,y2=0,b0=0,a1=0,a2=0;
        let grainLevel=0,grainTarget=0;
        const grainSamples=max(1,round(rate*(0.004+(1-grain)*0.028)));
        const combBuffer=new Float32Array(1024);
        let cursor=0;
        const attack=min(0.012,duration*0.12)*rate,release=min(0.035,duration*0.2)*rate;
        for(let i=0;i<output.length;i++) {
            const unit=i/(output.length-1),scanWave=sin(scanPhase);
            // Lock converges in discrete steps; Reveal unfolds in four overlapping scans.
            let travel=unit;
            if(gesture===1) travel=1-exp(-unit*5);
            else if(gesture===2) travel=1-pow(1-unit,2.4);
            else if(gesture===3) travel=0.75*unit+0.25*floor(unit*4)/4;
            const frequency=min(9000,max(50,base*2**(sweep*(travel-0.5)*2)));
            phase+=tau*frequency/rate;
            modPhase+=modStep;
            scanPhase+=scanStep;
            shiftPhase+=tau*(17+scan*113)*(0.65+0.35*scanWave)/rate;
            const index=sidebands*(1.6+bandwidth*2.2)*(1+scan*scanWave*0.35);
            const carrier=sin(phase+index*sin(modPhase));
            // Multiplying analytic oscillator pairs makes upper/lower shifted components.
            const shifted=sin(phase)*cos(shiftPhase)+cos(phase)*sin(shiftPhase)*(0.3+0.7*scanWave);
            if((i&31)===0) {
                const center=min(10500,max(110,frequency*(1.5+bandwidth*1.5)*2**(scan*scanWave*0.7)));
                const omega=tau*center/rate,alpha=sin(omega)/(2*(1.2+10*(1-bandwidth)));
                const scale=1/(1+alpha);
                b0=alpha*scale; a1=-2*cos(omega)*scale; a2=(1-alpha)*scale;
            }
            if(i%grainSamples===0) grainTarget=random()*2-1;
            grainLevel+=(grainTarget-grainLevel)*0.035;
            const excitation=random()*2-1;
            const band=b0*(excitation-x2)-a1*y1-a2*y2;
            x2=x1; x1=excitation; y2=y1; y1=band;
            let envelope=min(1,i/attack,(output.length-1-i)/release);
            if(gesture===0) envelope*=0.65+0.35*sin(PI*unit);
            else if(gesture===1) envelope*=exp(-unit*5.5);
            else if(gesture===2) {
                const gate=sin(tau*(2.5*unit+5.5*unit*unit));
                envelope*=(0.27+0.73*max(0,gate))*(0.72+0.28*unit);
            } else envelope*=(0.3+0.7*unit)*(0.74+0.26*sin(tau*unit*4));
            const gate=1-grain*0.42+grain*0.42*grainLevel;
            let sample=envelope*(carrier*(0.47-sidebands*0.09)+shifted*scan*0.17
                +band*(0.22*sidebands+grain*1.1))*gate;
            // Fractional delay keeps the tiny comb moving smoothly, with bounded feedback.
            const delay=rate*(0.0017+0.0045*(0.5+0.5*sin(tau*unit*(1+scan*2))))*(1+bandwidth*0.4);
            let read=cursor-delay;
            if(read<0) read+=combBuffer.length;
            const before=floor(read),fraction=read-before;
            const delayed=combBuffer[before]*(1-fraction)+combBuffer[(before+1)%combBuffer.length]*fraction;
            combBuffer[cursor]=sample+delayed*comb*0.43;
            sample=sample*(1-comb*0.2)-delayed*comb*0.52;
            cursor=(cursor+1)%combBuffer.length;
            output[i]=sample;
        }
        return SoundDSP.finish(output,volume);
    }
}
