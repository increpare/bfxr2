// Damped modal resonators: an object's material determines its inharmonic modes,
// while the contact gesture supplies impacts, friction, or bouncing collisions.
class Clonkr_DSP {
    static materials = [
        {pitch:0.7, ring:0.34, brightness:0.55, ratios:[1, 2.17, 3.04, 4.61, 5.43, 6.8, 8.7, 10.3]},
        {pitch:1.55, ring:1.25, brightness:0.95, ratios:[1, 2.32, 4.25, 6.63, 9.38, 12.4, 15.8, 18.1]},
        {pitch:0.92, ring:1.6, brightness:1, ratios:[1, 1.48, 2.06, 2.63, 3.52, 4.89, 6.28, 8.13]},
        {pitch:1.12, ring:0.58, brightness:0.74, ratios:[1, 1.87, 3.22, 4.74, 6.18, 7.91, 10.2, 12.6]},
        {pitch:0.42, ring:0.16, brightness:0.2, ratios:[1, 1.99, 3.02, 4.08, 5.19, 6.31, 7.46, 8.64]}
    ];

    static render(params) {
        const value = (name, fallback, min = 0, max = 1) => SoundDSP.clamp(
            Number.isFinite(params[name]) ? params[name] : fallback, min, max);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const material = this.materials[Math.round(value('material', 0, 0, 4))];
        const action = Math.round(value('action', 0, 0, 2));
        const size = value('size', 0.5), hollow = value('hollowness', 0.35);
        const hardness = value('hardness', 0.65), damping = value('damping', 0.35);
        const duration = value('duration', 0.7, 0.1, 2);
        const decay = 0.009 + (0.022 + duration * 0.44 * material.ring) * (1 - 0.92 * damping);
        const contactEnd = action === 0 ? 0.025 : duration;
        const length = Math.ceil((contactEnd + Math.min(3.5, decay * 7)) * rate);
        const buffer = new Float32Array(length), excitation = new Float32Array(length);
        const onset = Math.round(0.006 * rate);
        const impact = (time, strength) => {
            const start = Math.round(time * rate);
            if (start >= length) return;
            // Soft strikers spread their force over a few milliseconds. A hard
            // striker approaches an impulse and excites the highest modes.
            const width = Math.max(1, Math.round((1 - hardness) * 0.0025 * rate));
            for (let j = 0; j < width && start + j < length; j++) {
                const force = width === 1 ? 1 : Math.sin(Math.PI * (j + 0.5) / width) * Math.PI / (2 * width);
                excitation[start + j] += force * strength;
            }
            const noiseLength = Math.round((0.002 + (1 - hardness) * 0.009) * rate);
            for (let j = 0; j < noiseLength && start + j < length; j++) {
                buffer[start + j] += (random() * 2 - 1) * Math.exp(-j / (noiseLength * 0.2))
                    * strength * (0.07 + hardness * 0.2);
            }
        };

        impact(onset / rate, 1);
        if (action === 1) {
            let friction = 0;
            for (let i = onset; i < Math.round(contactEnd * rate); i++) {
                const progress = (i - onset) / Math.max(1, contactEnd * rate - onset);
                friction += ((random() * 2 - 1) - friction) * (0.08 + 0.7 * hardness);
                const grain = random() < (0.002 + hardness * 0.012) ? (random() * 2 - 1) * 0.2 : 0;
                excitation[i] += (friction * 0.022 + grain) * Math.sin(Math.PI * progress) ** 0.4;
                buffer[i] += friction * (0.08 + 0.12 * hardness) * Math.sin(Math.PI * progress);
            }
        } else if (action === 2) {
            const count = Math.round(4 + duration * 7 + hardness * 7);
            for (let hit = 1; hit < count; hit++) {
                const progress = hit / count;
                const time = 0.012 + (contactEnd - 0.025) * (progress + (random() - 0.5) * 0.5 / count);
                impact(time, (0.35 + random() * 0.65) * (1 - progress * 0.6));
            }
        }

        const base = 1400 * Math.pow(2, -size * 4.4) * material.pitch;
        const modes = material.ratios.map((ratio, index) => {
            const detune = 1 + (random() - 0.5) * 0.018;
            const frequency = Math.min(rate * 0.43, base * ratio * detune);
            const angle = Math.PI * 2 * frequency / rate;
            const tau = decay / (1 + index * (0.08 + damping * 0.13));
            const radius = Math.exp(-1 / (tau * rate));
            const weight = Math.exp(-index * (0.28 + (1 - hardness) * 0.62 + (1 - material.brightness) * 0.4))
                * (index === 0 ? 1 + hollow * 1.2 : 1 - hollow * 0.35);
            return {cos:Math.cos(angle) * radius, sin:Math.sin(angle) * radius, real:0, imaginary:0, weight};
        });
        const scale = 1.4 / modes.reduce((sum, mode) => sum + mode.weight, 0);
        for (let i = onset; i < length; i++) {
            let sample = 0;
            for (const mode of modes) {
                const real = mode.real * mode.cos - mode.imaginary * mode.sin + excitation[i];
                mode.imaginary = mode.real * mode.sin + mode.imaginary * mode.cos;
                mode.real = real;
                sample += real * mode.weight;
            }
            buffer[i] += sample * scale;
        }
        return SoundDSP.finish(buffer, value('masterVolume', 0.5));
    }
}
