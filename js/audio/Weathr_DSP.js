// All stochastic material lives on a circle: there are no start/end envelopes.
class Weathr_DSP {
    static circularLowpass(input, cutoff) {
        const q = Math.exp(-2*Math.PI*cutoff/SoundDSP.rate);
        const gain = 1-q;
        let state=0;
        for(let i=0;i<input.length;i++) state=q*state+gain*input[i];
        // Solve the filter's periodic initial condition, including very low cutoffs.
        state /= 1-Math.pow(q,input.length);
        const result = new Float32Array(input.length);
        for(let i=0;i<input.length;i++) result[i]=state=q*state+gain*input[i];
        return result;
    }

    static render(p) {
        const rate=SoundDSP.rate;
        const count=Math.round(p.duration*rate);
        const output=new Float32Array(count);
        const white=new Float32Array(count);
        const random=SoundDSP.rng(p.seed);
        const {sin, cos, exp, floor, max, min, PI}=Math;
        const tau=2*PI;
        for(let i=0;i<count;i++) white[i]=random()*2-1;
        const rumble=this.circularLowpass(white,100+120*(1-p.scale));
        const air=this.circularLowpass(white,1800+3000*p.brightness);
        const phaseA=random()*tau, phaseB=random()*tau;
        const swells=max(1,Math.round(p.duration*(0.16+(1-p.scale)*0.65)));
        const whistleCycles=Math.round((170+600*(1-p.scale))*p.duration);
        const humCycles=Math.round((48+12*(1-p.scale))*p.duration);
        const activity=0.12+0.88*p.density;
        for(let i=0;i<count;i++) {
            const angle=tau*i/count;
            const wave=0.5+0.34*sin(angle*swells+phaseA)+0.16*sin(angle*(swells+2)+phaseB);
            const surge=1-p.turbulence*0.8+p.turbulence*wave*1.6;
            let value;
            switch(p.environment) {
                case 1:
                    value=air[i]*(0.055+0.48*p.density)+rumble[i]*0.7*p.scale;
                    break;
                case 2:
                    value=rumble[i]*(1.2+1.8*p.density)+air[i]*0.07*p.density;
                    break;
                case 3:
                    value=air[i]*(0.08+0.52*p.density)*(.3+p.scale*0.7)
                        +rumble[i]*(0.6+p.scale*1.7)*activity;
                    break;
                case 4:
                    value=0.04*activity*(sin(angle*humCycles)+0.3*sin(angle*humCycles*3))
                        +air[i]*0.02*p.density;
                    break;
                default:
                    value=(rumble[i]*3.1+air[i]*0.16)*activity
                        +0.08*p.detail*activity*sin(angle*whistleCycles+1.5*sin(angle*swells+phaseB));
            }
            output[i]=value*surge;
        }
        // Smooth events are written modulo the length. A late drop or ember's
        // tail is therefore already present at the beginning of the exported loop.
        if(p.environment!==0) {
            const rates=[0,8+125*p.density*p.density,3+40*p.density,4+45*p.density,2+38*p.density];
            const events=Math.round(p.duration*rates[p.environment]);
            for(let event=0;event<events;event++) {
                const onset=floor(random()*count);
                const eventSize=0.35+random()*0.65;
                let seconds,frequency,amplitude;
                switch(p.environment) {
                    case 1:
                        seconds=0.009+0.055*p.scale*eventSize;
                        frequency=(900+random()*2600)/(0.7+p.scale*1.3);
                        amplitude=(0.08+0.16*eventSize)*p.detail;
                        break;
                    case 2:
                        seconds=0.008+random()*0.026+0.016*p.scale;
                        frequency=700+random()*2200;
                        amplitude=(0.18+0.35*eventSize)*p.detail;
                        break;
                    case 3:
                        seconds=0.035+0.09*eventSize+0.04*p.scale;
                        frequency=(350+random()*1100)/(0.7+p.scale*1.8);
                        amplitude=(0.1+0.22*eventSize)*p.detail;
                        break;
                    default:
                        seconds=0.006+random()*0.06;
                        frequency=1300+random()*3200;
                        amplitude=(0.13+0.4*eventSize)*p.detail;
                }
                const length=max(8,floor(seconds*rate));
                const eventPhase=random()*tau;
                for(let j=0;j<length;j++) {
                    const u=j/(length-1), t=j/rate;
                    // Zero value and slope at both ends prevents event-edge clicks.
                    const window=sin(PI*u)**2*exp(-u*4.5);
                    const noise=random()*2-1;
                    let source;
                    if(p.environment===3) source=sin(tau*frequency*(t+1.5*t*t/seconds)+eventPhase);
                    else if(p.environment===1) source=noise*0.8+sin(tau*frequency*t)*0.35;
                    else if(p.environment===2) source=noise+sin(tau*frequency*t)*0.5;
                    else source=noise*0.7+sin(tau*frequency*t+3*sin(tau*90*t));
                    output[(onset+j)%count]+=source*window*amplitude*3;
                }
            }
        }
        // The final colour filter also starts in its exact circular steady state.
        const colored=this.circularLowpass(output,180*Math.pow(70,p.brightness));
        return SoundDSP.finish(colored,p.masterVolume,{loop:true});
    }
}
