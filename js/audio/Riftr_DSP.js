// A four-line feedback delay network with an orthogonal scattering junction.
// Fractional moving taps bend the field; serial allpasses disperse it in time.
class Riftr_DSP {
    static render(p) {
        const {sin, cos, exp, pow, floor, round, min, max, PI} = Math;
        const value = (name, fallback, low = 0, high = 1) => SoundDSP.clamp(
            Number.isFinite(p[name]) ? p[name] : fallback, low, high);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const duration = value('duration', 1.8, 0.15, 6), count = round(duration * rate);
        const output = new Float32Array(count), excitation = round(value('excitation', 0, 0, 4));
        const pitch = value('pitch', 0.45), bend = value('bend', -0.2, -1, 1), space = value('space', 0.5);
        const feedback = value('feedback', 0.65) * 0.955;
        const dispersion = value('dispersion', 0.55), motion = value('motion', 0.3);
        const field = value('field', 0.7), reverse = value('reverse', 0);
        const tau = 2 * PI, basePitch = 55 * pow(2, pitch * 5.8);
        const pitchStep = pow(2, bend * 3 / count);
        const baseDelay = (0.003 + space * space * 0.095) * rate;
        const ratios = [0.719, 1, 1.337, 1.731];
        const lines = ratios.map((ratio, index) => {
            const delay = max(7, baseDelay * ratio);
            const depth = motion * delay * 0.09;
            const step = tau * (0.17 + motion * 2.3) * (1 + index * 0.13) / rate;
            const phase = random() * tau;
            return {buffer:new Float32Array(Math.ceil(delay + depth + 3)), delay, depth, index:0,
                real:cos(phase), imag:sin(phase), c:cos(step), s:sin(step), filter:0, read:0};
        });
        const allpasses = [0.0023, 0.0051, 0.0113, 0.0197].map(seconds => ({
            buffer:new Float32Array(max(1, round(seconds * rate * (0.3 + space) * (0.1 + dispersion)))), index:0
        }));
        const apGain = 0.15 + dispersion * 0.59;
        const damping = 0.48 + (1 - dispersion) * 0.4;
        const pulseRadius = exp(-1 / (rate * (0.015 + space * 0.025)));
        const tearRadius = exp(-1 / (rate * (0.025 + duration * 0.16)));
        let phase=0, increment=tau*basePitch/rate, pulse=1, tear=1, noiseLow=0;
        const phaseOffset = random() * tau;
        let packet=0, packetEnvelope=0;
        const packetStep = (8 + motion * 28) / rate;
        const packetRadius = exp(-1 / (rate * 0.013));
        for (let i = 0; i < count; i++) {
            const progress = i / (count - 1);
            phase += increment; increment *= pitchStep;
            const noise = random() * 2 - 1;
            noiseLow += (noise - noiseLow) * 0.12;
            const carrier = sin(phase + 0.55 * sin(phase * 1.417 + phaseOffset));
            let input;
            switch (excitation) {
                case 1: {
                    const arc = max(0, sin(PI * min(1, progress / 0.72)));
                    input = (carrier * 0.65 + sin(phase * 0.498) * 0.28 + noiseLow * 0.12) * arc * arc;
                    break;
                }
                case 2:
                    input = (carrier * 0.48 + sin(phase * 0.501) * 0.32)
                        * sin(PI * progress) * (0.65 + 0.35 * sin(tau * progress * (2 + motion * 7)));
                    break;
                case 3:
                    input = (noiseLow * 0.95 + carrier * 0.36 + sin(phase * 0.25) * 0.21) * tear;
                    break;
                case 4:
                    packet += packetStep;
                    if (packet >= 1 || i === 0) { packet %= 1; packetEnvelope = 0.45 + random() * 0.5; }
                    input = (sin(phase + floor(progress * 13) * 1.7) + noise * 0.12) * packetEnvelope * (1 - progress);
                    packetEnvelope *= packetRadius;
                    break;
                default:
                    input = (carrier * 0.9 + sin(phase * 2.071) * 0.18 + noiseLow * 0.04) * pulse;
            }
            pulse *= pulseRadius; tear *= tearRadius;
            let sum = 0;
            for (const line of lines) {
                const newReal = line.real * line.c - line.imag * line.s;
                line.imag = line.real * line.s + line.imag * line.c; line.real = newReal;
                let position = line.index - line.delay - line.depth * line.imag;
                if (position < 0) position += line.buffer.length;
                const before = floor(position), fraction = position - before;
                const after = before + 1 === line.buffer.length ? 0 : before + 1;
                const sample = line.buffer[before] * (1 - fraction) + line.buffer[after] * fraction;
                line.filter += (sample - line.filter) * damping;
                line.read = line.filter;
                sum += line.read;
            }
            // I - 2vv^T with v=(1,1,1,1)/2 conserves energy at the junction.
            for (const line of lines) {
                line.buffer[line.index] = input * 0.5 + feedback * (line.read - sum * 0.5);
                if (++line.index === line.buffer.length) line.index = 0;
            }
            let wet = sum * 0.65;
            if (dispersion > 0) {
                for (const stage of allpasses) {
                    const delayed = stage.buffer[stage.index];
                    const scattered = delayed - apGain * wet;
                    stage.buffer[stage.index] = wet + apGain * scattered;
                    if (++stage.index === stage.buffer.length) stage.index = 0;
                    wet = scattered;
                }
            }
            output[i] = (1 - field) * input + field * wet;
        }
        if (reverse > 0) {
            for (let i = 0; i < floor(count / 2); i++) {
                const opposite = count - 1 - i, a = output[i], b = output[opposite];
                output[i] = a * (1 - reverse) + b * reverse;
                output[opposite] = b * (1 - reverse) + a * reverse;
            }
        }
        return SoundDSP.finish(output, value('masterVolume', 0.5));
    }
}
