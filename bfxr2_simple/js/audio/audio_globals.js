const SAMPLE_RATE = 44100;
const CONVERSION_FACTOR = (2*Math.PI)/SAMPLE_RATE;

var AUDIO_CONTEXT;
function checkAudioContextExists() {
    try {
        if (AUDIO_CONTEXT == null) {
            if (typeof AudioContext != 'undefined') {
                AUDIO_CONTEXT = new AudioContext();
            } else if (typeof webkitAudioContext != 'undefined') {
                AUDIO_CONTEXT = new webkitAudioContext();
            }
        }
    } catch (ex) {
        window.console.log(ex)
    }
}

checkAudioContextExists();
//unlock bullshit
function ULBS() {
    if (AUDIO_CONTEXT.state === 'suspended') {
        var unlock = function() {
            AUDIO_CONTEXT.resume().then(function() {
                document.body.removeEventListener('touchstart', unlock);
                document.body.removeEventListener('touchend', unlock);
                document.body.removeEventListener('mousedown', unlock);
                document.body.removeEventListener('mouseup', unlock);
                document.body.removeEventListener('keydown', unlock);
                document.body.removeEventListener('keyup', unlock);
            });
        };

        document.body.addEventListener('touchstart', unlock, false);
        document.body.addEventListener('touchend', unlock, false);
        document.body.addEventListener('mousedown', unlock, false);
        document.body.addEventListener('mouseup', unlock, false);
        document.body.addEventListener('keydown', unlock, false);
        document.body.addEventListener('keyup', unlock, false);
    }
}