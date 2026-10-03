// Shared deterministic audio utilities for the specialized sound makers.
class SoundDSP {
    static rate = 44100;
    static clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
    static rng(seed) {
        let state = Math.floor(seed * 4294967295) >>> 0;
        const imul = Math.imul;
        return () => {
            state = (state + 0x6D2B79F5) | 0;
            let t = imul(state ^ state >>> 15, 1 | state);
            t = t + imul(t ^ t >>> 7, 61 | t) ^ t;
            return ((t ^ t >>> 14) >>> 0) / 4294967296;
        };
    }
    static finish(buffer, volume = 0.5, options = {}) {
        let mean = 0;
        for (const value of buffer) mean += Number.isFinite(value) ? value : 0;
        mean /= Math.max(1, buffer.length);
        const fadeLength = Math.max(1, Math.min(220, Math.floor(buffer.length / 2)));
        for (let i = 0; i < buffer.length; i++) {
            const value = Number.isFinite(buffer[i]) ? buffer[i] - mean : 0;
            const fade = options.loop ? 1 : Math.min(1, i / fadeLength, (buffer.length - 1 - i) / fadeLength);
            buffer[i] = Math.tanh(value) * this.clamp(volume, 0, 1) * 0.95 * fade;
        }
        return buffer;
    }
}
