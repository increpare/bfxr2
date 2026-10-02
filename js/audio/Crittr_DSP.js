// Nonverbal calls: pulsed breath drives three moving throat resonances.
class Crittr_DSP {
    static render(p) {
        const {sin, cos, exp, floor, round, min, max, PI} = Math;
        const value = (name, fallback, low=0, high=1) => Number.isFinite(p[name])
            ? min(high,max(low,p[name])) : fallback;
        const rate = SoundDSP.rate, tau = PI*2;
        const duration = value('duration',1.2,0.15,5);
        const output = new Float32Array(round(duration*rate));
        const volume = value('masterVolume',0.5);
        if (volume === 0) return SoundDSP.finish(output,0);
        const random = SoundDSP.rng(value('seed',0.5));
        const voice = round(value('voice',0,0,5));
        const pitch = 45*2**(5*value('pitch',0.45));
        const size = value('size',0.45), morph = value('morph',0.45);
        const breath = value('breath',0.15), growl = value('growl',0.2);
        const flutter = value('flutter',0.2), contour = value('contour',0.25,-1,1);
        const calls = round(value('calls',2,1,12));
        const slot = output.length/calls, active = slot*(1-value('gap',0.2,0,0.85));
        const attack = max(40,active*0.09), release = max(80,active*0.28);
        const scale = 2**((0.5-size)*2.8);
        const anatomies = [[550,1260,2550],[820,2100,3900],[360,950,1840],
            [1100,2800,4700],[430,1500,3200],[670,1740,3550]];
        const frequencies = anatomies[voice].map(frequency => min(10000,frequency*scale));
        const radii = [exp(-PI*100/rate),exp(-PI*160/rate),exp(-PI*230/rate)];
        const coefficients = [0,0,0], y1 = [0,0,0], y2 = [0,0,0];
        const radiiSquared = radii.map(radius => radius*radius);
        const gains = radii.map(radius => (1-radius)*0.95);
        const callMotion = Array.from({length:calls},() => random()*2-1);
        const flutterRate = 7+flutter*38, flutterStep = tau*flutterRate/rate;
        const duty = [0.24,0.12,0.3,0.07,0.38,0.1][voice];
        let phase = random()*tau, flutterPhase = random()*tau;
        let previous=0, previous2=0, noiseLow=0;
        for (let i=0;i<output.length;i++) {
            const call = min(calls-1,floor(i/slot)), local = i-call*slot;
            const position = min(1,local/active);
            const envelope = max(0,min(1,local/attack,(active-local)/release));
            const tremor = sin(flutterPhase);
            flutterPhase += flutterStep;
            const bend = contour*((position-0.5)*1.9+callMotion[call]*0.3);
            phase += tau*pitch*exp(bend*0.69314718056)*(1+flutter*0.045*tremor)/rate;
            const cycle = phase/tau-floor(phase/tau);
            const pulse = cycle<duty ? 0.5-0.5*cos(tau*cycle/duty) : 0;
            const noise = random()*2-1;
            noiseLow += (noise-noiseLow)*0.06;
            let excitation = (pulse-duty*0.5)*3.4;
            if (voice===1) excitation += 0.22*sin(phase*2+0.8*sin(phase));
            if (voice===2) excitation *= 0.7+0.3*sin(phase*0.5);
            if (voice===3) excitation *= 0.6+0.4*sin(phase*1.47);
            if (voice===4) excitation = 0.48*sin(phase)+excitation*0.3;
            if (voice===5) excitation += 0.2*sin(phase*2.71);
            excitation = excitation*(1-breath*0.8)+noise*breath*0.9;
            // Change resonances at control rate; oscillator pitch stays independent.
            if ((i&31)===0) {
                const opening = morph*(sin(PI*position)+0.3*callMotion[call]);
                coefficients[0] = 2*radii[0]*cos(tau*min(11000,frequencies[0]*(1+opening*0.65))/rate);
                coefficients[1] = 2*radii[1]*cos(tau*min(11000,frequencies[1]*(1-opening*0.23))/rate);
                coefficients[2] = 2*radii[2]*cos(tau*min(11000,frequencies[2]*(1+opening*0.17))/rate);
            }
            let resonant=0;
            for (let band=0;band<3;band++) {
                const sample = gains[band]*(excitation-previous2)+coefficients[band]*y1[band]-radiiSquared[band]*y2[band];
                y2[band]=y1[band]; y1[band]=sample;
                resonant += sample*(band===0?1.15:band===1?0.85:0.5);
            }
            previous2=previous; previous=excitation;
            const subharmonic = growl*(0.28*sin(phase*0.5)+0.1*sin(phase/3))*(0.85+noiseLow*0.7);
            const throat = resonant*1.65+0.12*(1-breath)*sin(phase)+subharmonic;
            const trill = 1-flutter*0.42+flutter*0.42*tremor;
            output[i] = throat*envelope*trill;
        }
        return SoundDSP.finish(output,volume);
    }
}
