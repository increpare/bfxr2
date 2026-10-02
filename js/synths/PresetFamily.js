// Sample a measured family as a joint sound state, preserving its correlations.
// This file contains no renderer or analysis dependencies.
class PresetFamily {
    static compatible(a, b) {
        if (a.waveType !== b.waveType) return false;
        return ['pitch','tone','noise','vibrato','level'].every(name =>
            !a[name] || !b[name] || a[name].curve === b[name].curve);
    }

    static sample(family, random = Math.random) {
        if (!family || !family.exemplars.length) throw new Error('Preset family needs exemplars');
        const anchor = family.exemplars[Math.floor(random() * family.exemplars.length)];
        const p = JSON.parse(JSON.stringify(anchor));
        const partners = family.exemplars.filter(candidate => candidate !== anchor && this.compatible(anchor, candidate));
        if (partners.length) {
            const partner = partners[Math.floor(random() * partners.length)];
            const amount = random() * 0.3;
            for (const [name, value] of Object.entries(p)) {
                if (name === 'masterVolume' || name === 'waveType') continue;
                if (typeof value === 'number' && typeof partner[name] === 'number') {
                    p[name] = value + (partner[name] - value) * amount;
                } else if (value && typeof value === 'object' && partner[name]) {
                    // Keep the anchor's curve; its discrete trajectory is part of its identity.
                    for (const side of ['start','end']) value[side] += (partner[name][side] - value[side]) * amount;
                }
            }
        }
        const offset = extent => (random() - 0.5) * extent;
        const clamp = value => Math.max(0, Math.min(1, value));
        const time = 0.85 + random() * 0.3;
        if (p.duration !== undefined) p.duration *= time;
        for (const name of ['attack','release']) if (p[name] !== undefined) p[name] *= time;
        for (const [name, extent] of [['pitch',0.07],['tone',0.1],['noise',0.06],['vibrato',0.1],['level',0.1]]) {
            if (!p[name]) continue;
            const shift = offset(extent);
            for (const side of ['start','end']) p[name][side] = clamp(p[name][side] + shift);
        }
        for (const name of ['resonance','echo']) if (p[name] !== undefined) {
            // Even a little echo adds a long tail to a dry click or static fleck.
            p[name] = name === 'echo' && anchor.echo === 0 ? 0 : clamp(p[name] + offset(0.08));
        }
        return p;
    }
}
