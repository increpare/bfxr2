// Two independently saved sounds, played together at a constant total gain.
class Mixr_DSP {
    static render(p, renderSource = source => Stackr.render_source(source, Number.isFinite(source.renderSeed) ? source.renderSeed : p.seed)) {
        let sources;
        try { sources = JSON.parse(p.sources); } catch { sources = []; }
        if (!Array.isArray(sources)) sources = [];
        const pcm = sources.slice(0, 2).map(source => source ? renderSource(source) : null);
        const balance = Number.isFinite(p.balance) ? SoundDSP.clamp(p.balance, 0, 1) : 0.5;
        const volume = Number.isFinite(p.masterVolume) ? SoundDSP.clamp(p.masterVolume, 0, 1) : 0.5;
        const out = new Float32Array(Math.min(SoundDSP.rate * 12, Math.max(4410, ...pcm.map(a => a ? a.length : 0))));
        const both = pcm[0] && pcm[1];
        for (let slot = 0; slot < pcm.length; slot++) {
            if (!pcm[slot]) continue;
            const gain = (both ? (slot === 0 ? 1 - balance : balance) : 1) * volume * 2;
            for (let i = 0; i < pcm[slot].length && i < out.length; i++) out[i] += pcm[slot][i] * gain;
        }
        for (let i = 0; i < out.length; i++) {
            out[i] = Number.isFinite(out[i]) ? SoundDSP.clamp(out[i], -1, 1) : 0;
            if (i > out.length - 128) out[i] *= (out.length - 1 - i) / 127;
        }
        return out;
    }
}
