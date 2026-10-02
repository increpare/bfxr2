// A continuous voice: curves move its controls between two states over time.
// No browser dependencies; output is mono PCM at the application's sample rate.
class Transfxr_DSP {
    static sampleRate = 44100;
    static curves = [
        ['Linear', t => t],
        ['Ease In', t => t * t],
        ['Ease Out', t => 1 - (1 - t) * (1 - t)],
        ['Smooth', t => t * t * (3 - 2 * t)],
        ['Triangle', t => 1 - Math.abs(2 * t - 1)],
        ['Pulse', t => (1 - Math.cos(2 * Math.PI * t)) / 2],
        ['Bounce', t => {
            // Ease-out bounce, bounded and ending exactly at the second state.
            if (t < 1 / 2.75) return 7.5625 * t * t;
            if (t < 2 / 2.75) { t -= 1.5 / 2.75; return 7.5625 * t * t + 0.75; }
            if (t < 2.5 / 2.75) { t -= 2.25 / 2.75; return 7.5625 * t * t + 0.9375; }
            t -= 2.625 / 2.75; return 7.5625 * t * t + 0.984375;
        }],
        ['Steps', t => Math.min(1, Math.floor(t * 5) / 4)]
    ];

    static frequency(value) { return 40 * Math.pow(2, value * 7); }
    static cutoff(value) { return 100 * Math.pow(160, value); }

    static transition(value) {
        const curve = (this.curves.find(c => c[0] === value.curve) || this.curves[0])[1];
        return t => value.start + (value.end - value.start) * curve(t);
    }

    // Polynomial correction removes the discontinuity at a saw/pulse edge.
    static polyBLEP(phase, step) {
        if (phase < step) { const t = phase / step; return t + t - t * t - 1; }
        if (phase > 1 - step) { const t = (phase - 1) / step; return t * t + t + t + 1; }
        return 0;
    }

    static render(p) {
        const rate = this.sampleRate;
        const count = Math.max(2, Math.round(p.duration * rate));
        const delay = Math.round(Math.min(0.24, Math.max(0.075, p.duration * 0.23)) * rate);
        const feedback = p.echo * 0.65;
        const repeats = feedback > 0 ? Math.ceil(Math.log(0.0001) / Math.log(feedback)) : 0;
        const tail = repeats * delay;
        const output = new Float32Array(count + tail);
        const controls = ['pitch', 'tone', 'noise', 'vibrato', 'level'];
        const envelopes = controls.map(name => this.transition(p[name]));
        const values = controls.map(name => p[name].start);
        const attack = Math.max(0.003, p.attack) * rate;
        const release = Math.max(0.006, p.release) * rate;
        const damping = 1 / (0.707 + p.resonance * 5);
        let phase = 0, ic1 = 0, ic2 = 0, seed = 0x12345678;
        for (let i = 0; i < count; i++) {
            const t = i / (count - 1);
            // Two millisecond smoothing avoids clicks with stepped transitions.
            for (let j = 0; j < controls.length; j++) values[j] += (envelopes[j](t) - values[j]) * 0.012;
            const [pitch, tone, noise, vibrato, level] = values;
            const frequency = this.frequency(pitch) * Math.pow(2, Math.sin(i / rate * Math.PI * 16) * vibrato * 0.16);
            const step = frequency / (rate * 2);
            const g = Math.tan(Math.PI * this.cutoff(tone) / (rate * 2));
            const a1 = 1 / (1 + g * (g + damping));
            let sample = 0;
            // Oversample oscillator + topology-preserving state-variable filter.
            for (let sub = 0; sub < 2; sub++) {
                let osc;
                switch (p.waveType) {
                    case 1: osc = 1 - 4 * Math.abs(phase - 0.5); break;
                    case 2: osc = 2 * phase - 1 - this.polyBLEP(phase, step); break;
                    case 3: osc = (phase < 0.5 ? 1 : -1) + this.polyBLEP(phase, step) - this.polyBLEP((phase + 0.5) % 1, step); break;
                    default: osc = Math.sin(phase * Math.PI * 2);
                }
                phase = (phase + step) % 1;
                seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5;
                const white = (seed >>> 0) / 2147483648 - 1;
                const input = osc * (1 - noise) + white * noise;
                const v1 = a1 * (ic1 + g * (input - ic2));
                const v2 = ic2 + g * v1;
                ic1 = 2 * v1 - ic1;
                ic2 = 2 * v2 - ic2;
                sample += v2 * 0.5;
            }
            const fade = Math.min(1, i / attack) * Math.min(1, (count - 1 - i) / release);
            output[i] = Math.tanh(sample * 1.4) * level * fade;
        }
        // Echo remains outside the voice envelope, so the last note can ring out.
        for (let i = 0; i < output.length; i++) {
            if (i >= delay) output[i] += output[i - delay] * feedback;
        }
        for (let i = 0; i < output.length; i++) {
            const fade = tail ? Math.min(1, (output.length - 1 - i) / 256) : 1;
            output[i] = Math.tanh(output[i]) * p.masterVolume * 0.95 * fade;
        }
        return output;
    }
}
