// Footstep synthesis from the existing PureData terrain patches, without playback.
class Footsteppr_DSP {
    static terrains = ['snow', 'grass', 'dirt', 'gravel', 'wood'];

    static render(params) {
        const length = 0.1 + 0.7 * (1 - params.swiftness);
        pd_set_stream_length_seconds(length);
        const envelope = resize_fn(add_fns(
            resize_fn(step(params.heel), 0, 1, 0, 0.3333),
            resize_fn(step(params.roll), 0, 1, 0.125, 0.875),
            resize_fn(step(params.ball), 0, 1, 0.6667, 1)
        ), 0, 1, 0, length);
        const terrain = this.terrains[params.terrain] || this.terrains[0];
        let signal = puredata_functions[terrain](pd_fn(envelope));
        signal = pd_mul(signal, pd_c(params.masterVolume));
        signal = pd_clip(signal, pd_c(-1), pd_c(1));
        return pd_mul(signal, pd_c(4));
    }
}
