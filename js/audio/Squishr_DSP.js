// Liquids combine chirped bubble resonances with pressure-driven filtered noise.
// Each gesture has its own event timing, pitch contour, and deformation envelope.
class Squishr_DSP {
    static render(params) {
        const value = (name, fallback, min = 0, max = 1) => SoundDSP.clamp(
            Number.isFinite(params[name]) ? params[name] : fallback, min, max);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const texture = Math.round(value('texture', 0, 0, 5));
        const viscosity = value('viscosity', 0.6), stretch = value('stretch', 0.4);
        const pressure = value('pressure', 0.6), wetness = value('wetness', 0.75);
        const bubbleSize = value('bubbleSize', 0.55), duration = value('duration', 0.65, 0.1, 3);
        const release = 0.06 + viscosity * 0.16 + stretch * 0.13;
        const length = Math.ceil((duration + release) * rate);
        const buffer = new Float32Array(length);
        const base = 1650 * Math.pow(2, -bubbleSize * 3.8);
        const amplitude = 0.45 + pressure * 0.7;
        const onset = 0.008;
        const events = [];
        const addBubble = (start, strength, pitch = 1, life = 1) => {
            const seconds = (0.026 + viscosity * 0.065 + stretch * 0.13) * life;
            events.push({start:Math.round(start * rate), length:Math.round(seconds * rate),
                frequency:base * pitch * (0.84 + random() * 0.32), strength, phase:random() * 0.2});
        };

        if (texture === 1) {
            const count = Math.max(1, Math.round(duration * (2 + pressure * 7)));
            for (let i = 0; i < count; i++) addBubble(onset + i * duration * 0.85 / count,
                0.7 + random() * 0.3, 0.8 + random() * 0.4, 1.1);
        } else if (texture === 2) {
            // Suction builds slowly, then breaks into one rounded release pop.
            addBubble(duration * 0.76, 1.2, 0.75, 1.5);
            addBubble(duration * 0.87, 0.55, 1.3, 0.7);
        } else if (texture === 3) {
            for (let i = 0; i < 7; i++) addBubble(onset + random() * duration * 0.34,
                0.4 + random() * 0.45, 0.6 + random() * 1.1, 0.6 + random() * 0.6);
        } else if (texture === 4) {
            const count = Math.max(1, Math.round(duration * (3 + pressure * 3)));
            for (let i = 0; i < count; i++) {
                const time = onset + i * duration * 0.82 / count;
                addBubble(time, 1, 0.62, 1.4);
                addBubble(time + 0.035, 0.45, 1.35, 0.7);
            }
        } else {
            const count = Math.max(2, Math.round(duration * (5 + pressure * 10)));
            for (let i = 0; i < count; i++) addBubble(onset + i * duration * 0.88 / count,
                0.3 + random() * 0.5, texture === 5 ? 0.7 : 0.5 + random() * 0.8,
                texture === 5 ? 2 : 0.65 + random() * 0.65);
        }

        let lowNoise = 0, smoothNoise = 0, bodyPhase = 0, previous = 0;
        const cutoff = 180 + (1 - viscosity) * 3800 + pressure * 500;
        const filter = 1 - Math.exp(-Math.PI * 2 * cutoff / rate);
        for (let i = 0; i < length; i++) {
            const time = i / rate, progress = Math.min(1, time / duration);
            const tail = time <= duration ? 1 : Math.exp(-(time - duration) / (release * 0.2));
            const noise = random() * 2 - 1;
            lowNoise += (noise - lowNoise) * filter;
            smoothNoise += (lowNoise - smoothNoise) * filter;
            let envelope;
            if (texture === 2) envelope = Math.sin(Math.PI * Math.min(1, progress / 0.85)) ** 2;
            else if (texture === 3) envelope = Math.exp(-progress * (5 - viscosity * 2));
            else if (texture === 4) envelope = (0.4 + 0.6 * Math.sin(progress * Math.PI * (3 + pressure * 3)) ** 2) * (1 - progress * 0.6);
            else envelope = Math.sin(Math.PI * progress) ** 0.55;
            const attack = Math.min(1, time / 0.009);
            const bodyFrequency = base * (texture === 5 ? 0.27 : 0.16)
                * (1 + Math.sin(time * (12 + pressure * 20)) * stretch * 0.3)
                * (texture === 2 ? 1.6 - progress : 1 - progress * stretch * 0.45);
            bodyPhase += Math.PI * 2 * bodyFrequency / rate;
            const body = Math.sin(bodyPhase + Math.sin(bodyPhase * 0.5) * stretch)
                * (texture === 5 ? 0.4 : 0.13) * (0.25 + viscosity * 0.75);
            const rasp = (smoothNoise * (0.6 + wetness * 0.45) + (lowNoise - previous) * (1 - viscosity) * 0.25);
            const noiseLevel = texture === 1 ? 0.015 : texture === 5 ? 0.14 : texture === 3 ? 1.1 : 0.7;
            const bodyLevel = texture === 1 ? 0.03 : 1;
            buffer[i] = (rasp * noiseLevel + body * bodyLevel) * envelope * tail * amplitude * attack;
            previous = lowNoise;
        }

        for (const event of events) {
            let phase = event.phase;
            for (let j = 0; j < event.length && event.start + j < length; j++) {
                const progress = j / event.length;
                let glide;
                if (texture === 2 || texture === 4) glide = 1.65 - progress * (1.1 + stretch * 0.3);
                else if (texture === 5) glide = 1 + Math.sin(progress * Math.PI * (3 + stretch * 5)) * stretch * 0.6;
                else glide = 0.65 + progress * (0.8 + pressure * 1.5) + Math.sin(progress * Math.PI) * stretch * 0.5;
                phase += Math.PI * 2 * event.frequency * glide / rate;
                const envelope = Math.min(1, j / (rate * 0.0015)) * Math.exp(-progress * (5 - viscosity * 2))
                    * Math.min(1, (1 - progress) * 15);
                const rounded = Math.sin(phase) + Math.sin(phase * 2) * (1 - viscosity) * 0.13;
                buffer[event.start + j] += rounded * envelope * event.strength * amplitude * (0.25 + wetness * 0.7);
            }
        }
        return SoundDSP.finish(buffer, value('masterVolume', 0.5));
    }
}
