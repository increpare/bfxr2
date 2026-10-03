// A break is a shower of brief fracture bursts, then rough shard contacts.
// Only the explicitly stylized Crystal and Pixel materials sustain tuned modes.
class Fractr_DSP {
    static materials = [
        {pitch:1.65, ring:0.22, noise:1.7, cutoff:11000, grit:0.28, ratios:[1, 2.71, 4.83]}, // Glass
        {pitch:0.84, ring:0.15, noise:2.1, cutoff:6500, grit:0.6, ratios:[1, 1.91, 3.77]}, // Ice
        {pitch:1.05, ring:1.75, noise:0.025, cutoff:10000, grit:0, ratios:[1, 1.505, 2.014]}, // Crystal
        {pitch:0.17, ring:0.08, noise:3.8, cutoff:1700, grit:1, ratios:[1, 1.63, 2.42]}, // Stone
        {pitch:1.0, ring:0.6, noise:0.015, cutoff:10000, grit:0, ratios:[1, 2, 4]}, // Pixel
        {pitch:0.65, ring:0.26, noise:1.8, cutoff:7000, grit:0.42, ratios:[1, 2.39, 5.17]}, // Armor
        {pitch:0.39, ring:0.1, noise:2.8, cutoff:3800, grit:0.45, ratios:[1, 1.82, 3.03]}, // Bone
        {pitch:0.55, ring:0.015, noise:2.8, cutoff:5100, grit:0.65, ratios:[1, 1.77, 3.11]} // Biscuit
    ];

    static render(p) {
        const {round, min, max, pow, exp, sin, cos, PI} = Math;
        const value = (name, fallback, low = 0, high = 1) => SoundDSP.clamp(
            Number.isFinite(p[name]) ? p[name] : fallback, low, high);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const duration = value('duration', 1.8, 0.15, 6);
        const output = new Float32Array(round(duration * rate));
        const materialIndex = round(value('material', 0, 0, 7));
        const material = this.materials[materialIndex];
        const tuned = materialIndex === 2 || materialIndex === 4;
        const fragments = round(value('fragments', 32, 3, 96));
        const size = value('fragmentSize', 0.4), spread = value('spread', 0.6);
        const stress = value('stress', 0.4), fracture = value('fracture', 0.75);
        const decay = value('decay', 0.4), gravity = value('gravity', 0.5), bounce = value('bounce', 0.4);
        const cascadeTime = duration * (0.012 + spread * 0.72) * (1 - gravity * 0.6);
        const gain = 1.45 * value('shards',0.35) / pow(fragments, 0.3), tau = 2 * PI;
        const bounceCount = round(bounce * 4);

        for (let shard = 0; shard < fragments; shard++) {
            const shardSize = max(0, min(1, size + (random() - 0.5) * 0.26));
            const progress = (shard + random() * 0.65) / fragments;
            let time = 0.006 + cascadeTime * pow(progress, 0.75 + 0.7 * gravity);
            if (materialIndex === 4) time = round(time * 48) / 48 + 0.006;
            const start = round(time * rate);
            let frequency = 2700 * pow(2, -shardSize * 4.5) * material.pitch * (0.65 + 0.7 * random());
            if (materialIndex === 4) frequency = 110 * pow(2, round(12 * Math.log2(frequency / 110)) / 12);
            const ringTime = (0.006 + decay * 0.23) * material.ring * (0.8 + random() * 0.4);
            const contactTime = tuned ? 0.0025 : 0.0018 + (0.004 + decay * 0.025) * (0.4 + shardSize) * (0.7 + material.grit);
            const noiseRadius = exp(-1 / (rate * contactTime));
            const crackRadius = exp(-1 / (rate * (0.0003 + shardSize * 0.00065)));
            const cutoff = material.cutoff * pow(2, -shardSize * 1.6);
            const dustFilter = 1 - exp(-tau * cutoff / rate);
            const bodyFilter = 1 - exp(-tau * (130 + 1700 * (1 - shardSize) * material.pitch) / rate);
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
            const end = min(output.length, contacts[contacts.length - 1].sample + round(max(ringTime, contactTime) * 7 * rate));
            const modes = material.ratios.map((ratio, index) => {
                const angle = tau * min(11000, frequency * ratio) / rate;
                const radius = exp(-(1 + index * 0.55) / (ringTime * rate));
                return {c:cos(angle) * radius, s:sin(angle) * radius};
            });
            // Unrolled three-mode rotators keep the busiest 96-shard cascades cheap.
            const a = modes[0], b = modes[1], c = modes[2];
            let ar=0, ai=0, br=0, bi=0, cr=0, ci=0, noiseEnvelope=0, nextContact=0, dust=0, body=0;
            let crackEnvelope=0, crackLeft=0, nextCrack=0, contactStrength=0;
            for (let i = start; i < end; i++) {
                if (nextContact < contacts.length && i === contacts[nextContact].sample) {
                    const hit = contacts[nextContact++].strength;
                    const modeGain = tuned ? 1 : 0.12;
                    ar += hit * modeGain; br += hit * modeGain * 0.44; cr += hit * modeGain * 0.24;
                    noiseEnvelope += hit * material.noise * (tuned ? 1 : 0.58);
                    // An initial split has several tiny failures; later contacts scrape once.
                    contactStrength = hit;
                    crackLeft = tuned ? 0 : (nextContact === 1 ? 3 + round(shardSize * 4) : 1);
                    nextCrack = i;
                }
                if (crackLeft > 0 && i === nextCrack) {
                    crackEnvelope += contactStrength * (0.5 + random() * 0.9);
                    nextCrack += 5 + round(random() * (25 + shardSize * 100));
                    crackLeft--;
                }
                const an = ar * a.c - ai * a.s;
                ai = ar * a.s + ai * a.c; ar = an;
                const bn = br * b.c - bi * b.s;
                bi = br * b.s + bi * b.c; br = bn;
                const cn = cr * c.c - ci * c.s;
                ci = cr * c.s + ci * c.c; cr = cn;
                const noise = random() * 2 - 1;
                dust += (noise - dust) * dustFilter;
                body += (noise - body) * bodyFilter;
                const rough = dust + body * material.grit;
                output[i] += (ar + br + cr) * 0.52 + rough * noiseEnvelope
                    + (dust - body * 0.5) * crackEnvelope;
                noiseEnvelope *= noiseRadius;
                crackEnvelope *= crackRadius;
            }
        }
        // The parent object fails before its loose fragments land. Bipolar stress
        // releases have finite width: sharp tensile snaps, not a sustained hiss.
        // Their clusters branch in time, with a slower mass response underneath.
        const structuralRandom = SoundDSP.rng(value('seed', 0.5) * 0.79 + 0.137);
        const splitTime = 0.011 + stress * 0.029;
        const widths = [0.00012, 0.00065, 0.0002, 0.0022, 0.00015, 0.00023, 0.0011, 0.00022];
        const mass = [0.06, 0.9, 0.08, 1, 0.02, 0.35, 1.3, 0.15][materialIndex];
        const width = widths[materialIndex] * (0.7 + size * 0.8);
        const splitGain = fracture * (tuned ? 0.25 : materialIndex===7 ? 2.2 : 3.4);
        const branches = materialIndex===7 ? 34 + round(size*28) : materialIndex===6 ? 5 : 7 + round(size * 9);
        for (let branch = 0; branch < branches; branch++) {
            const u = branch / branches;
            const branchSpan = materialIndex===7 ? 0.065 + stress*0.07 : materialIndex===6 ? 0.017 : materialIndex===1 ? 0.045 + stress*0.025 : 0.022 + stress*0.035;
            const delay = branch === 0 ? 0 : 0.001 + pow(u, 1.6) * branchSpan * (0.75+structuralRandom()*0.5);
            const start = round((splitTime + delay) * rate);
            const release = width * (0.7 + structuralRandom() * 0.9);
            const weight = splitGain * (branch === 0 ? 1 : 0.25 + 0.4 * (1 - u)) * (0.75 + structuralRandom()*0.5);
            const length = min(output.length - start, round((release * 9 + 0.009 * mass) * rate));
            let gritLow = 0, massGrit = 0;
            const gritRate = 1 - exp(-tau * material.cutoff * 0.55 / rate);
            for (let j = 0; j < length; j++) {
                const t = j / rate, q = t / release;
                gritLow += gritRate * (structuralRandom() * 2 - 1 - gritLow);
                const tensile = (1 - q) * exp(-q);
                const tearing = gritLow * exp(-t / (release * 3)) * 0.55;
                const bodyQ = t / (0.002 + mass * 0.004);
                massGrit += 0.12 * (structuralRandom()*2-1-massGrit);
                const body = ((1 - bodyQ) + massGrit*(materialIndex===3 || materialIndex===6 ? 6 : 1.2)) * exp(-bodyQ) * mass * 0.95;
                output[start + j] += weight * (tensile + tearing + body);
            }
        }
        if (!tuned && stress > 0) {
            // Intermittent pre-failure strain; no ringing musical mode.
            let slow = 0, fast = 0;
            const end = min(output.length, round(splitTime * rate));
            for (let i = round(0.005 * rate); i < end; i++) {
                const u = i / end, noise = structuralRandom() * 2 - 1;
                slow += 0.006 * (noise - slow); fast += 0.055 * (noise - fast);
                const stutter = pow(0.5 + 0.5 * sin(u * (36 + materialIndex * 9)), 5);
                output[i] += (fast - slow) * stutter * stress * u * 2.5;
            }
        }
        return SoundDSP.finish(output, value('masterVolume', 0.5));
    }
}
