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
        const rate = this.sampleRate;
        const output = new Float32Array(Math.ceil(score.duration * rate));
        if (!score.events.length || p.masterVolume === 0) return output;
        const synth = new ChattrFormants.FormantSynth({sampleRate:rate,schedule:this.acousticScore(p,score)});
        synth.lfsr = (0x51f15e + Math.round(p.seed * 65534)) | 0;
        synth.process(output);
        for (let i = 0; i < output.length; i++) {
            const fade = Math.min(1,i / (rate * 0.005),(output.length - 1 - i) / (rate * 0.015));
            output[i] = Math.tanh(output[i] * (1 + p.grit * 1.3)) * p.masterVolume * 0.95 * fade;
        }
        return output;
    }
}
