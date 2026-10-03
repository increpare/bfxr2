// Rotating parts, friction and resonant contacts; no recordings or browser state.
class Machinr_DSP {
    static render(p) {
        const rate = SoundDSP.rate;
        const count = Math.max(2, Math.round(p.duration * rate));
        const output = new Float32Array(count);
        const random = SoundDSP.rng(p.seed);
        const {sin, cos, exp, abs, min, max, PI} = Math;
        const tau = 2 * PI;
        const scale = Math.pow(2, (0.5 - p.size) * 2.6);
        const base = (35 + 230 * p.speed * p.speed) * scale * (1 - 0.32 * p.load);
        const toothRate = (5 + p.speed * 48) * (1 - p.load * 0.28);
        const attack = max(0.003, p.startTime) * rate;
        const release = max(0.006, p.stopTime) * rate;
        // Contact resonances share a material size, but alternate on an escapement.
        const ringFrequency = min(8500, (650 + 1100 * (1 - p.size)) * scale);
        const decay = exp(-1 / (rate * (0.007 + 0.035 * p.looseness)));
        const ringA = 2 * decay * cos(tau * ringFrequency / rate);
        const ringB = 2 * decay * cos(tau * ringFrequency * 0.63 / rate);
        let a1=0, a2=0, b1=0, b2=0, phase=0, teeth=0, slowNoise=0, friction=0;
        let previousTooth=-1, turn=0, contact=0, eventStrength=1;
        const rotorOffset = random() * tau;
        for (let i=0; i<count; i++) {
            const t=i/rate, progress=i/(count-1);
            const engage=min(1,i/attack), stop=min(1,(count-1-i)/release);
            const envelope=engage*stop;
            const noise=random()*2-1;
            slowNoise += (noise-slowNoise)*0.0015;
            friction += (noise-friction)*(0.09+0.5*p.roughness);
            let spin=(0.18+0.82*engage)*(0.2+0.8*stop);
            if(p.mechanism===6) spin*=1-0.7*progress;
            const wobble=1+p.roughness*(0.085*sin(tau*7.3*t+rotorOffset)+slowNoise*1.2);
            phase += tau*base*spin*wobble/rate;
            let contactRate=toothRate;
            if(p.mechanism===3) contactRate=1.3+p.speed*8;
            if(p.mechanism===4) contactRate=7+p.speed*30;
            if(p.mechanism===7) contactRate=4+p.speed*17;
            teeth += contactRate*spin*wobble/rate;
            const tooth=Math.floor(teeth);
            let kick=0;
            if(tooth!==previousTooth) {
                previousTooth=tooth;
                turn++;
                eventStrength=0.45+random()*0.55;
                kick=(0.15+p.looseness*0.7)*eventStrength;
                if(p.mechanism===3) kick=0.75;
                if(p.mechanism===4) kick*=random()>p.roughness*0.22?1:0.1;
                contact=eventStrength;
            }
            contact *= exp(-1/(rate*(0.007+0.025*p.load)));
            // Shutters use two explicit latch contacts; the door strikes at closure.
            if(p.mechanism===2) {
                kick=(i===Math.floor(rate*0.008)||i===Math.floor(count*(0.19+0.12*p.load)))?1.9:0;
            }
            if(p.mechanism===7 && i===Math.floor(count*0.88)) kick+=3.2;
            const resonantA=kick*0.14+ringA*a1-decay*decay*a2;
            const resonantB=kick*0.11+ringB*b1-decay*decay*b2;
            a2=a1; a1=resonantA; b2=b1; b1=resonantB;
            const rattle=(turn%2?resonantA:resonantB);
            const rotor=sin(phase)+0.35*sin(2*phase)+0.12*sin(5*phase);
            let sample;
            switch(p.mechanism) {
                case 1: // Teeth rubbing and slipping under load.
                    sample=0.11*rotor+0.55*rattle+friction*(0.05+0.18*p.roughness)
                        +0.11*p.load*sin(phase*3.1+3*sin(phase*0.017))*(0.5+0.5*sin(tau*1.7*t));
                    break;
                case 2:
                    sample=1.05*(resonantA+resonantB)+0.08*rotor*exp(-progress*9)
                        +friction*0.13*exp(-progress*12);
                    break;
                case 3:
                    sample=rattle*1.35+0.014*rotor+friction*contact*0.18;
                    break;
                case 4:
                    sample=0.28*rotor*(0.3+contact)+0.4*contact*friction
                        +0.21*sin(phase*0.5)*(0.4+p.load)+0.18*rattle;
                    break;
                case 5: {
                    const position=0.55+0.45*sin(tau*(1.1+p.speed*3)*t);
                    sample=(0.25*sin(phase*(3.1+p.load))+0.09*sin(phase*6.2))*position
                        +0.05*rattle+friction*(0.015+0.035*p.roughness);
                    break;
                }
                case 6:
                    sample=0.13*sin(phase*1.9+2*sin(teeth*0.38))+0.53*rattle
                        +0.08*rotor+friction*(0.015+0.09*p.roughness);
                    break;
                case 7: {
                    const creak=sin(phase*0.62+4*sin(phase*0.023));
                    sample=0.27*creak*(0.55+0.45*sin(teeth*1.4))+0.45*rattle
                        +0.14*sin(phase*0.31)+friction*p.roughness*0.1;
                    break;
                }
                default:
                    sample=0.24*rotor+0.09*sin(phase*8)*(0.25+p.load)
                        +rattle*(0.1+p.looseness*0.3)+friction*(0.015+p.roughness*0.15);
            }
            output[i]=sample*envelope;
        }
        return SoundDSP.finish(output,p.masterVolume);
    }
}
