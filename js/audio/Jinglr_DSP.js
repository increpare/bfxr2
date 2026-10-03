// A small score is saved with every jingle. Playback never invents new notes.
class Jinglr_DSP {
    static scales = [[0,2,4,5,7,9,11],[0,2,3,5,7,8,10],[0,2,4,7,9],[0,2,3,5,7,9,10]];
    static defaultPhrase = '[{"degree":0,"beats":0.5},{"degree":2,"beats":0.5},{"degree":4,"beats":0.5},{"degree":7,"beats":1}]';

    static number(value, fallback, min, max) {
        return Number.isFinite(value) ? SoundDSP.clamp(value,min,max) : fallback;
    }

    static phrase(value) {
        let notes;
        try { notes = typeof value === 'string' && value.length <= 4096 ? JSON.parse(value) : null; }
        catch (_) { notes = null; }
        if (!Array.isArray(notes) || !notes.length) notes = JSON.parse(this.defaultPhrase);
        return notes.slice(0,12).map(note => {
            const valid = note && typeof note === 'object' ? note : {};
            return {degree:valid.degree === null ? null : Math.round(this.number(valid.degree,0,-7,14)),
                beats:Math.round(this.number(valid.beats,0.5,0.25,2)*4)/4};
        });
    }

    static midi(degree, params) {
        if (degree === null) return null;
        const scale = this.scales[Math.round(this.number(params.scale,0,0,3))];
        const octave = Math.round(this.number(params.octave,4,3,6));
        const key = Math.round(this.number(params.key,0,0,11));
        const index = (degree % scale.length + scale.length) % scale.length;
        return (octave+1)*12 + key + Math.floor(degree/scale.length)*12 + scale[index];
    }

    static noteName(degree, params) {
        const midi = this.midi(degree,params);
        return midi === null ? 'Rest' : ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][midi%12] + (Math.floor(midi/12)-1);
    }

    static schedule(params) {
        const beat = 60 / this.number(params.tempo,140,60,220);
        const swing = this.number(params.swing,0,0,0.6);
        let cursor = 0;
        const phrase = this.phrase(params.phrase);
        const events = phrase.map((note,index) => {
            // Swing redistributes each pair's time, even when its beat values differ.
            const pair = Math.floor(index/2)*2;
            const shift = phrase[pair+1] ? Math.min(phrase[pair].beats,phrase[pair+1].beats)*swing : 0;
            const duration = (note.beats + (index%2 ? -shift : shift))*beat;
            const midi = this.midi(note.degree,params);
            const event = {degree:note.degree,beats:note.beats,midi,
                frequency:midi === null ? 0 : 440*Math.pow(2,(midi-69)/12),start:cursor,duration};
            cursor += duration;
            return event;
        });
        return {events,duration:cursor};
    }

    static voice(params) {
        const instrument=Math.round(this.number(params.instrument,0,0,7));
        const seed=Math.round(this.number(params.instrumentSeed,42731,0,99999));
        const random=SoundDSP.rng((instrument*100000+seed+1)/800001);
        const attackRanges=[[0.001,0.012],[0.001,0.006],[0.001,0.009],[0.006,0.04],
            [0.001,0.012],[0.012,0.06],[0.001,0.015],[0.025,0.12]];
        const attack=attackRanges[instrument];
        // Each code describes a whole instrument, not a pitch offset or a new melody.
        return {instrument,seed,attack:attack[0]+random()*(attack[1]-attack[0]),
            release:0.6+random()*0.85,damping:0.45+random()*1.9,
            slope:0.65+random()*1.5,color:0.2+random()*0.75,
            hollow:random(),filter:1.5+random()*9,body:0.65+random()*0.35,
            modulation:0.3+random()*3.5,modRatio:1+Math.floor(random()*4),
            spread:0.001+random()*0.005,pick:0.08+random()*0.4};
    }

    static render(params) {
        const score = this.schedule(params);
        const rate = SoundDSP.rate;
        const brightness = this.number(params.brightness,0.55,0,1);
        const decay = this.number(params.decay,0.45,0,1);
        const echo = this.number(params.echo,0.12,0,0.8);
        const voice = this.voice(params), instrument=voice.instrument;
        const tail = (0.035 + decay*0.26)*voice.release;
        const delay = 60/this.number(params.tempo,140,60,220)*0.75;
        const echoTail = echo > 0 ? delay*3 : 0;
        const pcm = new Float32Array(Math.ceil((score.duration+tail+echoTail)*rate));
        // Timbre, attacks and breath have their own RNG; melody seed only chooses notes.
        const random = SoundDSP.rng((voice.seed*7+instrument*100003+1)%1000003/1000003);
        const sin = Math.sin;
        for (const note of score.events) {
            if (note.midi === null) continue;
            const start = Math.round(note.start*rate);
            const gate = note.duration*(0.52+0.38*decay)*voice.body;
            const length = Math.ceil((gate+tail)*rate);
            const strength = 0.84+random()*0.16;
            const phase = random()*Math.PI*2;
            const partials=[];
            const addPartial=(ratio,gain,falloff,offset=0)=>{
                if (note.frequency*ratio<rate*0.45) partials.push({
                    step:Math.PI*2*note.frequency*ratio/rate,gain,
                    falloff:Math.exp(-falloff*voice.damping/rate),offset});
            };
            if (instrument===0) {
                // A plucked harmonic string; bright overtones die away first.
                for(let h=1;h<=10;h++) {
                    const pick=h===1 ? 1 : 0.25+0.75*Math.abs(sin(Math.PI*h*voice.pick));
                    addPartial(h,pick*Math.pow(0.12+brightness*0.85,h-1)/Math.pow(h,voice.slope),
                        (1.5+(1-decay)*7)*Math.sqrt(h));
                }
            } else if (instrument===1) {
                [1,2+voice.color*1.1,3.8+voice.hollow*2.3,7.5+voice.color*2.5].forEach((ratio,h)=>
                    addPartial(ratio,h===0 ? 0.8 : (0.1+brightness*0.85)/Math.pow(h+1,voice.slope),
                        (0.7+(1-decay)*5)*(1+h*0.6)));
            } else if (instrument===2) {
                // A pulse of varying duty, represented by band-limited harmonics.
                const duty=0.12+voice.hollow*0.38;
                for(let h=1;h<=16;h++) addPartial(h,
                    0.8*sin(Math.PI*h*duty)/sin(Math.PI*duty)*Math.pow(0.3+brightness*0.7,h-1)/Math.pow(h,voice.slope),
                    0.45+(1-decay)*2);
            } else if (instrument===3) {
                addPartial(1,0.8,0.35+(1-decay)*1.5);
                for(let h=2;h<=5;h++) addPartial(h,brightness*voice.color*0.5/Math.pow(h-1,voice.slope),
                    (0.35+(1-decay)*1.5)*(1+h*0.15));
            } else if (instrument===4) {
                // Hammered keys mix a warm body with short, ringing tine overtones.
                for(let h=1;h<=8;h++) addPartial(h,
                    (h===1 ? 0.85 : (0.2+brightness*0.7)*(h%2 ? 0.55 : 1))/Math.pow(h,voice.slope),
                    (0.8+(1-decay)*4)*(1+h*0.3));
                addPartial(4+voice.color*0.04,brightness*voice.hollow*0.35,12+(1-decay)*12);
            } else if (instrument===5) {
                // Reed character moves between hollow odd partials and a nasal full spectrum.
                for(let h=1;h<=12;h++) {
                    const resonance=1+voice.color*Math.exp(-Math.pow((h-(2+voice.hollow*4))/2,2))*2;
                    const even=h%2 ? 1 : 0.1+voice.hollow*0.85;
                    addPartial(h,0.65*resonance*even*Math.pow(0.35+brightness*0.65,h-1)/Math.pow(h,voice.slope),
                        0.2+(1-decay)*0.8);
                }
            } else if (instrument===6) {
                // An unmodulated center holds the note underneath the changing FM spectrum.
                addPartial(1,0.28,0.5+(1-decay)*3);
            } else {
                // Paired detuned partials make a bowed ensemble without moving its center pitch.
                for(let h=1;h<=10;h++) {
                    const gain=0.32*Math.pow(0.5+brightness*0.48,h-1)/Math.pow(h,voice.slope);
                    addPartial(h*(1-voice.spread),gain,0.15+(1-decay)*0.6);
                    addPartial(h*(1+voice.spread),gain,0.15+(1-decay)*0.6,voice.color*2);
                }
            }
            const startPhase=instrument===2 ? 0 : phase;
            const attackLength=Math.min(voice.attack,gate*0.65)*rate;
            let breath=0.005*brightness*(0.3+voice.hollow);
            const breathFalloff=Math.exp(-(0.5+(1-decay)*2)*voice.damping/rate);
            const cutoff=Math.min(rate*0.44,note.frequency*(voice.filter+brightness*9));
            const filter=1-Math.exp(-Math.PI*2*cutoff/rate);
            let filtered=0;
            const fundamental=Math.PI*2*note.frequency/rate;
            // Reserve room for FM sidebands at high registers.
            const fmIndex=Math.min(voice.modulation*(0.15+brightness),Math.max(0,(rate*0.4/note.frequency-1)/voice.modRatio));
            let fmAmount=fmIndex, fmGain=0.62;
            const fmFalloff=Math.exp(-(2+(1-decay)*8)*voice.damping/rate);
            const fmGainFalloff=Math.exp(-(0.6+(1-decay)*3)*voice.damping/rate);
            for (let i=0;i<length && start+i<pcm.length;i++) {
                const time = i/rate;
                const attack = i<attackLength ? i/attackLength : 1;
                const release = time>gate ? 1-(time-gate)/tail : 1;
                let sample = 0;
                for (const partial of partials) {
                    sample += sin(partial.step*i+startPhase+partial.offset)*partial.gain;
                    partial.gain *= partial.falloff;
                }
                if (instrument===3 || instrument===5) {
                    sample += (random()*2-1)*breath;
                    breath *= breathFalloff;
                }
                if (instrument===6) {
                    sample += sin(fundamental*i+startPhase+(fmIndex*0.18+fmAmount)*sin(fundamental*i*voice.modRatio))*fmGain;
                    fmAmount*=fmFalloff; fmGain*=fmGainFalloff;
                }
                filtered+=(sample-filtered)*filter;
                pcm[start+i] += filtered*attack*release*strength;
            }
        }
        if (echo>0) {
            const dry = pcm.slice();
            for (let repeat=1;repeat<=3;repeat++) {
                const offset = Math.round(delay*repeat*rate);
                const gain = Math.pow(echo*0.58,repeat);
                for (let i=0;i+offset<pcm.length;i++) pcm[i+offset] += dry[i]*gain;
            }
        }
        return SoundDSP.finish(pcm,this.number(params.masterVolume,0.5,0,1));
    }
}
