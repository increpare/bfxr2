checkAudioContextExists();

function playFootsteps() {
    checkAudioContextExists();

    var sample_length_seconds = 0.5;
    var sample_length_samples = sample_length_seconds * SAMPLE_RATE;
    
    //constant signal 0 
    pd_set_stream_length_seconds(1.0);
    var signal = pd_noise();
    var v_200 = pd_c(200);
    var v_1 = pd_c(1);
    var signal = pd_vcf(signal, v_200, v_1);

    var base_noise = pd_noise();
    var alt_noise = pd_noise();

    signal = base_noise;
    signal = pd_div(
        pd_lop(signal,pd_c(110)),
        pd_lop(signal,pd_c(900)));

    var side_div = pd_div(
        pd_lop(alt_noise,pd_c(50)),
        pd_lop(alt_noise,pd_c(70)));

    signal = pd_mul(signal,side_div)
    
    var s1_lop = pd_lop(alt_noise,pd_c(10));
    var s2_mul = pd_mul(s1_lop,pd_c(17));
    var s3_sqr = pd_mul(s2_mul,s2_mul);
    var s4_add = pd_add(s3_sqr,pd_c(0.5));

    signal = pd_mul(signal,s4_add);

    signal = pd_clip(signal,-1,1);
    signal = pd_hip(signal,pd_c(300));

    signal = pd_clip(signal, -1.0, 1.0);
    signal = pd_mul(signal, pd_c(0.5));
    var sound = RealizedSound.from_buffer(signal);
    sound.play();
}

var button_play = document.getElementById("button_play");
button_play.addEventListener("click", function(event) {
    playFootsteps();
    
});