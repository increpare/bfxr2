checkAudioContextExists();

function playFootsteps() {
    checkAudioContextExists();

    var sample_length_seconds = 0.5;
    var sample_length_samples = sample_length_seconds * SAMPLE_RATE;
    
    //constant signal 0 
    pd_set_stream_length_seconds(1.0);
    var signal = pd_noise();
    var v_200 = pd_constant_signal(200);
    var v_1 = pd_constant_signal(1);
    var signal = pd_vcf(signal, v_200, v_1);

    signal = pd_clip(signal, -1.0, 1.0);
    signal = pd_mul(signal, 0.5);

    var sound = RealizedSound.from_buffer(signal);
    sound.play();
}

var button_play = document.getElementById("button_play");
button_play.addEventListener("click", function(event) {
    playFootsteps();
    
});