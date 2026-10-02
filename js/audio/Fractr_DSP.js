// Each shard has its own size, fracture time, flight, bounces and three material
// modes. Rendering particles into a shared buffer produces an actual cascade.
class Fractr_DSP {
    static materials = [
        {pitch:1.35, ring:1.0, noise:0.07, ratios:[1, 2.71, 4.83]}, // Glass
        {pitch:0.84, ring:0.52, noise:0.15, ratios:[1, 1.91, 3.77]}, // Ice
        {pitch:1.05, ring:1.75, noise:0.025, ratios:[1, 1.505, 2.014]}, // Crystal
        {pitch:0.17, ring:0.3, noise:0.27, ratios:[1, 1.63, 2.42]}, // Stone
        {pitch:1.0, ring:0.6, noise:0.015, ratios:[1, 2, 4]}, // Pixel
        {pitch:0.55, ring:0.76, noise:0.16, ratios:[1, 2.39, 5.17]}, // Armor
        {pitch:0.39, ring:0.38, noise:0.18, ratios:[1, 1.82, 3.03]} // Bone
    ];

    static render(p) {
        const {round, min, max, pow, exp, sin, cos, PI} = Math;
        const value = (name, fallback, low = 0, high = 1) => SoundDSP.clamp(
            Number.isFinite(p[name]) ? p[name] : fallback, low, high);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const duration = value('duration', 1.8, 0.15, 6);
        const output = new Float32Array(round(duration * rate));
        const materialIndex = round(value('material', 0, 0, 6));
        const material = this.materials[materialIndex];
        const fragments = round(value('fragments', 32, 3, 96));
        const size = value('fragmentSize', 0.4), spread = value('spread', 0.6);
        const decay = value('decay', 0.4), gravity = value('gravity', 0.5), bounce = value('bounce', 0.4);
        const cascadeTime = duration * (0.012 + spread * 0.72) * (1 - gravity * 0.6);
        const gain = 1.45 / pow(fragments, 0.3), tau = 2 * PI;
        const noiseRadius = exp(-1 / (rate * (0.0015 + 0.004 * size)));
        const bounceCount = round(bounce * 4);

        for (let shard = 0; shard < fragments; shard++) {
            const shardSize = max(0, min(1, size + (random() - 0.5) * 0.26));
            const progress = (shard + random() * 0.65) / fragments;
            let time = 0.006 + cascadeTime * pow(progress, 0.75 + 0.7 * gravity);
            if (materialIndex === 4) time = round(time * 48) / 48 + 0.006;
            const start = round(time * rate);
            let frequency = 2700 * pow(2, -shardSize * 4.5) * material.pitch * (0.8 + 0.4 * random());
            if (materialIndex === 4) frequency = 110 * pow(2, round(12 * Math.log2(frequency / 110)) / 12);
            const ringTime = (0.006 + decay * 0.23) * material.ring * (0.8 + random() * 0.4);
            const strength = gain * (0.55 + random() * 0.65) * (1 - progress * 0.3);
            const flight = (0.045 + 0.34 * (1 - gravity)) * (0.4 + 0.6 * shardSize);
            const contacts = [{sample:start, strength}];
            let nextTime = time, nextFlight = flight, nextStrength = strength;
            for (let j = 0; j < bounceCount; j++) {
                nextTime += nextFlight;
                nextFlight *= 0.43 + bounce * 0.24;
                nextStrength *= 0.27 + bounce * 0.42;
                contacts.push({sample:round(nextTime * rate), strength:nextStrength});
            }
            const end = min(output.length, contacts[contacts.length - 1].sample + round(ringTime * 7 * rate));
            const modes = material.ratios.map((ratio, index) => {
                const angle = tau * min(11000, frequency * ratio) / rate;
                const radius = exp(-(1 + index * 0.55) / (ringTime * rate));
                return {c:cos(angle) * radius, s:sin(angle) * radius};
            });
            // Unrolled three-mode rotators keep the busiest 96-shard cascades cheap.
            const a = modes[0], b = modes[1], c = modes[2];
            let ar=0, ai=0, br=0, bi=0, cr=0, ci=0, noiseEnvelope=0, nextContact=0, dust=0;
            for (let i = start; i < end; i++) {
                if (nextContact < contacts.length && i === contacts[nextContact].sample) {
                    const hit = contacts[nextContact++].strength;
                    ar += hit; br += hit * 0.44; cr += hit * 0.24;
                    noiseEnvelope += hit * material.noise;
                }
                const an = ar * a.c - ai * a.s;
                ai = ar * a.s + ai * a.c; ar = an;
                const bn = br * b.c - bi * b.s;
                bi = br * b.s + bi * b.c; br = bn;
                const cn = cr * c.c - ci * c.s;
                ci = cr * c.s + ci * c.c; cr = cn;
                const noise = random() * 2 - 1;
                dust += (noise - dust) * (materialIndex === 3 ? 0.08 : 0.65);
                output[i] += (ar + br + cr) * 0.52 + dust * noiseEnvelope;
                noiseEnvelope *= noiseRadius;
            }
        }
        return SoundDSP.finish(output, value('masterVolume', 0.5));
    }
}
