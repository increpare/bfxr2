// Two independently saved sounds, played together at a constant total gain.
// Alignment places B relative to A: Start (both begin together), Peak (loudest moments
// coincide) or Tail (B begins as A has mostly decayed). Offset adds a fixed delay to B.
class Mixr_DSP {
    static envelope(pcm, hop = 256) {
        const out = new Float32Array(Math.max(1, Math.ceil(pcm.length / hop)));
        for (let i = 0; i < out.length; i++) {
            let e = 0; const end = Math.min(pcm.length, (i + 1) * hop);
            for (let j = i * hop; j < end; j++) e += pcm[j] * pcm[j];
            out[i] = Math.sqrt(e / hop);
        }
        return out;
    }
    static peak_index(pcm, hop = 256) {
        const env = this.envelope(pcm, hop); let best = 0;
        for (let i = 1; i < env.length; i++) if (env[i] > env[best]) best = i;
        return best * hop + hop / 2;
    }
    static onset_index(pcm, hop = 256, fraction = 0.1) {
        const env = this.envelope(pcm, hop); let peak = 0;
        for (const v of env) peak = Math.max(peak, v);
        for (let i = 0; i < env.length; i++) if (env[i] >= peak * fraction) return i * hop;
        return 0;
    }
    static tail_index(pcm, hop = 256, fraction = 0.35) {
        const env = this.envelope(pcm, hop); let best = 0;
        for (let i = 1; i < env.length; i++) if (env[i] > env[best]) best = i;
        for (let i = best; i < env.length; i++) if (env[i] < env[best] * fraction) return i * hop;
        return pcm.length;
    }
    // Sample offset of B relative to A for the chosen alignment.
    static shift(a, b, align, offset) {
        let shift = Math.round(SoundDSP.clamp(Number.isFinite(offset) ? offset : 0, -2, 2) * SoundDSP.rate);
        if (a && b) {
            if (align === 1) shift += this.peak_index(a) - this.peak_index(b);
            else if (align === 2) shift += this.tail_index(a) - this.onset_index(b);
        }
        return shift;
    }
    static render(p, renderSource = source => Stackr.render_source(source, Number.isFinite(source.renderSeed) ? source.renderSeed : p.seed)) {
        let sources;
        try { sources = JSON.parse(p.sources); } catch { sources = []; }
        if (!Array.isArray(sources)) sources = [];
        const pcm = sources.slice(0, 2).map(source => source ? renderSource(source) : null);
        const balance = Number.isFinite(p.balance) ? SoundDSP.clamp(p.balance, 0, 1) : 0.5;
        const volume = Number.isFinite(p.masterVolume) ? SoundDSP.clamp(p.masterVolume, 0, 1) : 0.5;
        const align = Number.isFinite(p.align) ? Math.round(p.align) : 0;
        const both = pcm[0] && pcm[1];
        const shift = both ? this.shift(pcm[0], pcm[1], align, p.offset) : 0;
        const starts = [Math.max(0, -shift), Math.max(0, shift)];
        const out = new Float32Array(Math.min(SoundDSP.rate * 12, Math.max(4410, ...pcm.map((a, slot) => a ? a.length + starts[slot] : 0))));
        for (let slot = 0; slot < pcm.length; slot++) {
            if (!pcm[slot]) continue;
            const gain = (both ? (slot === 0 ? 1 - balance : balance) : 1) * volume * 2;
            const start = both ? starts[slot] : 0;
            for (let i = 0; i < pcm[slot].length && i + start < out.length; i++) out[i + start] += pcm[slot][i] * gain;
        }
        for (let i = 0; i < out.length; i++) {
            out[i] = Number.isFinite(out[i]) ? SoundDSP.clamp(out[i], -1, 1) : 0;
            if (i > out.length - 128) out[i] *= (out.length - 1 - i) / 127;
        }
        return out;
    }
}
