// Mix independently rendered source snapshots on a short timeline.
class Stackr_DSP {
    static render(params, renderSource = layer => Stackr.render_source(layer, params.seed), onLayer = () => {}) {
        let layers;
        try { layers = JSON.parse(params.layers); } catch { layers = []; }
        if (!Array.isArray(layers)) layers = [];
        const rate = SoundDSP.rate;
        const spacing = Number.isFinite(params.spacing) ? params.spacing : 1;
        const sources = layers.slice(0, 6).map(layer => {
            const pcm = renderSource(layer);
            const speed = Math.pow(2, layer.pitch / 12);
            const start = Math.round(layer.start * spacing * rate);
            const length = Math.ceil(pcm.length / speed);
            onLayer(layer, length / rate);
            return {pcm, speed, start, length, gain:layer.gain};
        });
        const end = sources.length ? Math.max(...sources.map(s => s.start + s.length)) : 4410;
        const output = new Float32Array(Math.min(rate * 12, Math.max(2, end)));
        for (const source of sources) {
            for (let i = 0; i < source.length && i + source.start < output.length; i++) {
                const position = i * source.speed;
                const index = Math.floor(position);
                const fraction = position - index;
                const a = source.pcm[index] || 0;
                const b = source.pcm[Math.min(index + 1, source.pcm.length - 1)] || 0;
                output[i + source.start] += (a + (b - a) * fraction) * source.gain * 2;
            }
        }
        // Preserve true silence before each event. Each source already removes DC.
        for (let i = 0; i < output.length; i++) {
            const fade = Math.min(1, i / 128, (output.length - 1 - i) / 128);
            output[i] = Math.tanh(output[i]) * params.masterVolume * 0.95 * fade;
        }
        return output;
    }
}
