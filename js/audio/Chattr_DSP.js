// Deterministic phoneme speech: continuous formants, consonant noise and a little personality.
// The acoustic core and English formant bank are attributed in THIRD_PARTY_CHATTR.md.
class Chattr_DSP {
    static sampleRate = 44100;
    static maxLength = 160;
    static maxDuration = 60;
    static vowelPhones = new Set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split(' '));
    static coarse = {AA:'AA',AE:'AA',AH:'AA',AO:'OW',AW:'AA',AY:'AA',EH:'EH',ER:'EH',EY:'EH',IH:'IY',IY:'IY',OW:'OW',OY:'OW',UH:'UW',UW:'UW'};

    static random(seed) {
        let state = (seed | 0) || 1;
        return () => {
            state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
            return (state >>> 0) / 4294967296;
        };
    }

    static schedule(p) {
        if (p.voiceMode === 1) return this.chatterSchedule(p);
        const tokens = Chattr_Pronunciation.tokenize(p.text.slice(0, this.maxLength));
        const random = this.random(1 + Math.round(p.seed * 65534));
        const beat = 0.14 / (0.65 + p.speed * 1.7);
        const events = [];
        let time = 0.025, truncated = !!tokens.truncated;
        words: for (let t = 0; t < tokens.length; t++) {
            const token = tokens[t];
            if (token.punctuation) {
                time += beat * (/[.!?…]/.test(token.punctuation) ? 2.5 : 1.2);
                continue;
            }
            const ending = tokens.slice(t + 1).find(next => next.punctuation);
            const question = ending && /[?？]/.test(ending.punctuation);
            const excited = ending && /[!！]/.test(ending.punctuation);
            const finalWord = !tokens[t + 1] || !!tokens[t + 1].punctuation;
            const melody = (random() - 0.5) * 2.8;
            const wordStart = time, wordEvent = events.length;
            for (let i = 0; i < token.phones.length; i++) {
                const {phone, stress} = token.phones[i];
                const sound = ChattrFormants.bank[phone];
                const isVowel = this.vowelPhones.has(phone);
                const vowel = isVowel ? phone : (token.phones.slice(i + 1).find(ph => this.vowelPhones.has(ph.phone)) ||
                    token.phones.slice(0, i).reverse().find(ph => this.vowelPhones.has(ph.phone)) || {phone:'AH'}).phone;
                const duration = beat * (isVowel ? (stress === 1 ? 1.35 : stress === 2 ? 1.15 : 0.8) :
                    sound.isStop ? 0.75 : sound.voicing < 0.8 ? 1 : 0.8) * (0.97 + random() * 0.06) *
                    (finalWord && i === token.phones.length - 1 ? 1.18 : 1);
                if (time + duration > this.maxDuration - 0.08) {
                    events.splice(wordEvent); // Stop at a whole word, with room for the final release.
                    time = wordStart; truncated = true;
                    break words;
                }
                const pitch = 75 * Math.pow(4, p.pitch) * Math.pow(2, p.expression *
                    (melody + (stress === 1 ? 1.8 : 0) + (excited ? 1.5 : 0)) / 12);
                const bend = p.inflection * 3 + (finalWord ? p.expression * (question ? 4 : -2) : 0);
                // Keep the old portrait event shape while exposing the actual phoneme and word.
                events.push({phone, stress, word:token.word, approximate:token.approximate,
                    start:time, duration, pitch, bend, coarse:this.coarse[vowel],
                    vowel:['AA','EH','IY','OW','UW'].indexOf(this.coarse[vowel]),
                    noisy:sound.voicing < 0.8, plosive:!!sound.isStop, accent:stress === 1 ? 1.1 : 1});
                time += duration;
            }
            time += beat * (0.18 + p.spacing * 1.3);
        }
        return {events, duration:events.length ? Math.min(this.maxDuration,time + 0.08) : 0.08, truncated};
    }

    static target(p, event, glide = false) {
        const clarity = p.articulation ?? 0.8;
        const bank = ChattrFormants.bank;
        let full = {...bank[event.phone]};
        if (glide && full.glideTo) full = {...full, ...full.glideTo};
        // Unstressed AH is schwa; keeping it distinct makes English rhythm much less wooden.
        if (event.phone === 'AH' && event.stress === 0) Object.assign(full,{F1:480,F2:1500,F3:2500});
        const simple = bank[event.coarse];
        const scale = Math.pow(2, (0.5 - p.mouth) * 0.9);
        const result = {};
        for (const key of ['voicing','F1','F2','F3','BW1','BW2','BW3','A1','A2','A3']) {
            result[key] = simple[key] + (full[key] - simple[key]) * clarity;
            if (/^(F|BW)/.test(key)) result[key] *= scale;
        }
        // Textures change the source spectrum, with all sources still passing through the mouth.
        result.effort = p.texture === 1 ? 0.25 : p.texture === 2 ? 0.95 : 0.6;
        result.tilt = p.texture === 1 ? -0.5 : p.texture === 2 ? 0.55 : -0.05;
        result.F0 = event.pitch;
        if (p.texture === 2) result.F0 = 55 * Math.pow(2, Math.round(12 * Math.log2(result.F0 / 55)) / 12);
        result.gain = 4.5 * event.accent * (p.texture === 1 ? 1.3 : p.texture === 2 ? 0.75 : 1);
        result.aspiration = p.breath * 0.35 * result.voicing;
        result.vibratoDepth = event.pitch * p.wobble * 0.055;
        result.vibratoRate = 5 + p.wobble * 4;
        result.tremoloDepth = p.grit * 0.4;
        result.tremoloRate = event.pitch * 0.5;
        return result;
    }

    static acousticScore(p, score) {
        const clarity = p.articulation ?? 0.8;
        const events = [];
        const emit = (seconds, target, ramp) => events.push({atMs:seconds * 1000, target, transitionMs:ramp * 1000});
        const quiet = {A1:0,A2:0,A3:0,aspiration:0};
        for (let i = 0; i < score.events.length; i++) {
            const e = score.events[i], next = score.events[i + 1];
            let target = this.target(p, e);
            const end = this.target(p, e, true);
            const vowel = this.vowelPhones.has(e.phone);
            // H takes the following vowel's shape; it is an unvoiced breath through that mouth.
            if (e.phone === 'HH' && next && this.vowelPhones.has(next.phone)) {
                const nextTarget = this.target(p, next);
                for (const key of ['F1','F2','F3']) target[key] = end[key] = nextTarget[key];
            }
            const bend = Math.pow(2, e.bend / 12);
            end.F0 *= bend;
            let start = e.start;
            if (e.plosive && clarity > 0) {
                const closure = e.duration * 0.55 * clarity;
                // Bilabial/alveolar/velar bursts have different spectra; full articulation closes first.
                emit(start,{...target,A1:target.A1 * (1 - clarity),A2:target.A2 * (1 - clarity),
                    A3:target.A3 * (1 - clarity)},Math.min(0.006,closure));
                start += closure;
            }
            emit(start,target,Math.min(e.plosive ? 0.004 : vowel ? 0.025 : 0.012, e.duration * 0.22));
            // Diphthongs and pitch move continuously; filters are never reset between phonemes.
            emit(start + (e.start + e.duration - start) * 0.35,end,(e.start + e.duration - start) * 0.55);
            // Low articulation separates the vowel-like chirps; high articulation connects speech.
            const gap = (1 - clarity) * Math.min(0.024, e.duration * 0.25);
            if (gap > 0 || !next || next.start > e.start + e.duration + 0.001) {
                emit(e.start + e.duration - gap,quiet,0.007);
            }
        }
        return events;
    }

    static render(p, score = this.schedule(p)) {
        if (p.voiceMode === 1) {
            const output = this.renderChatterRaw(p,score);
            for (let i=0;i<output.length;i++) {
                const fade=Math.min(1,i/(this.sampleRate*.004),(output.length-1-i)/(this.sampleRate*.012));
                output[i]=Math.tanh(output[i]*(1+p.grit*.7))*p.masterVolume*.95*fade;
            }
            return output;
        }
        const rate = this.sampleRate;
        const output = new Float32Array(Math.ceil(score.duration * rate));
        if (!score.events.length || p.masterVolume === 0) return output;
        const source = p.waveType >= 0 ? BfxrWaveforms.create(p.waveType,p.seed) : null;
        const synth = new ChattrFormants.FormantSynth({sampleRate:rate,schedule:this.acousticScore(p,score),source});
        synth.lfsr = (0x51f15e + Math.round(p.seed * 65534)) | 0;
        synth.process(output);
        for (let i = 0; i < output.length; i++) {
            const fade = Math.min(1,i / (rate * 0.005),(output.length - 1 - i) / (rate * 0.015));
            output[i] = Math.tanh(output[i] * (1 + p.grit * 1.3)) * p.masterVolume * 0.95 * fade;
        }
        return output;
    }

    // Original procedural voice samples. Each character has a small, stable alphabet:
    // text chooses the sample, while prosody changes playback pitch and the cut-off.
    // No recordings or phoneme-engine buffers are used by this path.
    static characterProfiles = [
        {formant:1,    width:1,   pulse:.72, sub:.06, fm:.05, ring:0,   air:.02, crush:0,  nasal:0},
        {formant:.76,  width:1.5, pulse:.26, sub:.42, fm:.02, ring:0,   air:.09, crush:0,  nasal:0},
        {formant:1.12, width:.6,  pulse:.95, sub:.02, fm:.25, ring:0,   air:.02, crush:0,  nasal:.75},
        {formant:1.03, width:1.4, pulse:.15, sub:.1,  fm:1.8, ring:0,   air:.01, crush:0,  nasal:0},
        {formant:1.3,  width:1.8, pulse:.08, sub:0,   fm:.08, ring:0,   air:.2,  crush:0,  nasal:0},
        {formant:1.06, width:.85, pulse:1,   sub:0,   fm:.6,  ring:.5,  air:0,   crush:0,  nasal:.25},
        {formant:.7,   width:1.1, pulse:.9,  sub:.65, fm:.5,  ring:.2,  air:.07, crush:0,  nasal:.12},
        {formant:1.15, width:.7,  pulse:1,   sub:.02, fm:.18, ring:.15, air:.12, crush:24, nasal:.45}
    ];
    static grainVowels = [[730,1180,2520],[510,1780,2600],[310,2210,3030],[480,880,2450],[340,690,2240]];

    static characterVoice(p) {
        const character=Math.max(0,Math.min(7,Math.round(p.character || 0)));
        const random=this.random((Math.round((p.voiceSeed??.37)*0x7fffffff)^0x59c351^character*9749)|0);
        const profile=this.characterProfiles[character];
        return {...profile,character,formant:profile.formant*(.86+random()*.3),
            width:profile.width*(.8+random()*.45),pulse:profile.pulse*(.75+random()*.35),
            basePitch:155+random()*55,duty:.22+random()*.2,tilt:.65+random()*.55,
            rasp:random()*.24,alphabet:Math.floor(random()*101)};
    }

    static chatterSchedule(p) {
        const tokens=Chattr_Pronunciation.tokenize(p.text.slice(0,this.maxLength));
        const voice=this.characterVoice(p), beat=.12/(.7+p.speed*1.85), events=[];
        const swing=.08+this.random(Math.round(p.seed*65534)+1)()*.16;
        let time=.018,truncated=!!tokens.truncated;
        words: for(let t=0;t<tokens.length;t++) {
            const token=tokens[t];
            if(token.punctuation) {
                time+=beat*(/[.!?…]/.test(token.punctuation)?2.7:1.4);
                continue;
            }
            // Digraphs are one sample; all remaining letters have their own syllable.
            const glyphs=token.word.match(/sh|ch|th|ph|ng|[a-z]/g)||[];
            const ending=tokens.slice(t+1).find(next=>next.punctuation);
            const question=ending&&ending.punctuation==='?', excited=ending&&ending.punctuation==='!';
            const finalWord=!tokens[t+1]||!!tokens[t+1].punctuation;
            const start=time,eventStart=events.length;
            let wordHash=0;
            for(const c of token.word) wordHash=(Math.imul(wordHash,31)+c.charCodeAt(0))|0;
            const melody=((wordHash>>>0)%11-5)*.35;
            for(let i=0;i<glyphs.length;i++) {
                const glyph=glyphs[i], code=glyph.charCodeAt(0)+(glyph.length>1?glyph.charCodeAt(1):0);
                const isVowel=/^[aeiouy]$/.test(glyph);
                const vowel=isVowel?({a:0,e:1,i:2,o:3,u:4,y:2})[glyph]:(code*7+voice.alphabet)%5;
                const shape=(code*13+voice.alphabet)%7;
                const duration=beat*(isVowel?1.06:.78)*(1+(i%2?swing:-swing))*(i===glyphs.length-1?1.12:1);
                if(time+duration>this.maxDuration-.08) {
                    events.splice(eventStart);time=start;truncated=true;break words;
                }
                const position=glyphs.length>1?i/(glyphs.length-1):.5;
                const syllable=(shape-3)*.62;
                const phrase=Math.sin(position*Math.PI)*2.3+(excited?2:0)+
                    (finalWord?position*(question?4:-1.8):0);
                let pitch=85*Math.pow(5,p.pitch)*Math.pow(2,(syllable+p.expression*(phrase+melody))/12);
                if(voice.character===5) pitch=55*Math.pow(2,Math.round(12*Math.log2(pitch/55))/12);
                const bend=p.inflection*5+p.expression*((shape%3-1)*2+(finalWord&&question?2:0));
                events.push({grain:glyph,glyph,word:token.word,start:time,duration,pitch,bend,vowel,shape,
                    noisy:/^[sfh]|sh|th|ph$/.test(glyph),plosive:/^[bptdkcg]$/.test(glyph),
                    accent:i===0?1.08:1,phone:['AA','EH','IY','OW','UW'][vowel],stress:isVowel?1:null});
                time+=duration+beat*(.055+p.articulation*.11);
            }
            time+=beat*(.38+p.spacing*2.1);
        }
        return {events,duration:events.length?Math.min(this.maxDuration,time+.065):.08,truncated};
    }

    static vocalGrain(p,voice,event,seconds) {
        const rate=this.sampleRate, length=Math.ceil(Math.max(.06,seconds)*rate)+2, pcm=new Float32Array(length);
        const random=this.random(Math.round((p.voiceSeed??.37)*0x7fffffff)^event.grain.charCodeAt(0)*9871^0x139a8c);
        const palette=p.waveType>=0?BfxrWaveforms.create(p.waveType,p.voiceSeed??.37):null;
        const formants=this.grainVowels[event.vowel];
        const neighbor=this.grainVowels[(event.vowel+1+event.shape%3)%5];
        const scale=voice.formant*Math.pow(2,(.5-p.mouth)*1.15);
        const filters=formants.map(()=>({a:0,r:0,gain:0,y1:0,y2:0}));
        const tau=2*Math.PI;
        let phase=0, subPhase=0,noiseLow=0,dc=0;
        for(let i=0;i<length;i++) {
            const t=i/rate;
            const attack=Math.min(1,t/.018);
            const shape=Math.exp(-t*(12+event.shape*1.5))*.32;
            if(i%24===0) {
                for(let f=0;f<3;f++) {
                    const filter=filters[f];
                    const frequency=Math.min(rate*.36,(formants[f]*(1-shape)+neighbor[f]*shape)*scale);
                    const bandwidth=(85+f*65)*voice.width*(1+p.breath*.55);
                    const radius=Math.exp(-Math.PI*bandwidth/rate);
                    filter.a=2*radius*Math.cos(tau*frequency/rate);
                    filter.r=radius*radius;
                    filter.gain=(1-radius)*(f===0?1:f===1?.78:.32);
                }
            }
            const grit=p.grit+voice.rasp;
            const modulation=1+grit*.025*Math.sin(tau*t*37)+grit*.01*(random()-.5);
            const step=voice.basePitch*modulation/rate;
            phase=(phase+step)%1;subPhase=(subPhase+step*.5)%1;
            const angle=tau*phase;
            const sine=Math.sin(angle+voice.fm*Math.sin(angle*2)*(1-.6*attack));
            const pulse=(phase<voice.duty?1:-1)+BfxrWaveforms.blep(phase,step)-BfxrWaveforms.blep((phase+1-voice.duty)%1,step);
            const raw=palette?palette(phase,step):sine*(1-voice.pulse)+pulse*voice.pulse*.65;
            const sub=Math.sin(tau*subPhase)*(voice.sub+grit*.08);
            const noise=random()*2-1;
            noiseLow+=.16*(noise-noiseLow);
            const onset=event.plosive?Math.exp(-t*155):event.noisy?Math.exp(-t*48)*.55:0;
            const excitation=(raw+sub)*(event.plosive?Math.min(1,t/.007):1)+
                (noise-noiseLow)*(voice.air+p.breath*.2+onset*p.articulation*.8);
            let value=0;
            for(const filter of filters) {
                const y=filter.gain*excitation+filter.a*filter.y1-filter.r*filter.y2;
                filter.y2=filter.y1;filter.y1=y;value+=y;
            }
            const nasal=Math.sin(angle*3)*voice.nasal*.075;
            const direct=voice.character===3?sine*.11:voice.character===4?sine*.22:voice.character===1?sub*.17:raw*.045;
            value=value*3.8*voice.tilt+direct+nasal;
            value*=1-voice.ring*.5+voice.ring*.5*Math.sin(angle*.5);
            if(voice.character===6) value*=.75+.25*Math.sin(tau*subPhase);
            if(voice.crush) value=Math.round(value*voice.crush)/voice.crush;
            dc+=.003*(value-dc);
            pcm[i]=(value-dc)*Math.min(1,t/.0025);
        }
        // A fixed gain per grain keeps textures comparable without hiding unstable DSP.
        // The returned raw renderer remains unclipped and is tested before the output stage.
        let energy=0;
        const window=Math.round(rate*.05);
        for(let i=0;i<window;i++) energy+=pcm[i]*pcm[i];
        const gain=Math.min(5,.29/Math.max(.001,Math.sqrt(energy/window)));
        for(let i=0;i<pcm.length;i++) pcm[i]*=gain;
        return pcm;
    }

    static renderChatterRaw(p,score=this.chatterSchedule(p)) {
        const rate=this.sampleRate, output=new Float32Array(Math.ceil(score.duration*rate));
        if(!score.events.length||p.masterVolume===0) return output;
        const voice=this.characterVoice(p), grains=new Map();
        // Work out the complete sample length before rendering. The same letter always
        // replays the same grain, even when a later word needs a higher playback rate.
        for(const event of score.events) {
            const duration=event.duration*event.pitch/voice.basePitch*Math.pow(2,(Math.max(0,event.bend)+p.wobble*.65)/12)+.003;
            const old=grains.get(event.grain);
            if(!old||duration>old.duration) grains.set(event.grain,{event,duration});
        }
        for(const [key,{event,duration}] of grains) grains.set(key,this.vocalGrain(p,voice,event,duration));
        for(const event of score.events) {
            const grain=grains.get(event.grain), start=Math.round(event.start*rate), count=Math.round(event.duration*rate);
            let cursor=0;
            for(let i=0;i<count&&start+i<output.length;i++) {
                const u=i/Math.max(1,count-1), index=Math.floor(cursor), fraction=cursor-index;
                const value=index+1<grain.length?grain[index]+(grain[index+1]-grain[index])*fraction:0;
                const envelope=Math.min(1,i/(rate*.0035),(count-1-i)/(rate*(.008+.007*(1-p.articulation))));
                const body=1-.22*u+ p.expression*.08*Math.sin(Math.PI*u);
                output[start+i]+=value*envelope*body*event.accent;
                const wobble=p.wobble*.65*Math.sin(2*Math.PI*(i/rate)*(5+voice.alphabet%6));
                cursor+=event.pitch/voice.basePitch*Math.pow(2,(event.bend*u+wobble)/12);
            }
        }
        return output;
    }
}
