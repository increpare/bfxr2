RealizedSound.MIN_SAMPLE_RATE = SAMPLE_RATE;

function RealizedSound(length, sample_rate) {
    this._buffer = AUDIO_CONTEXT.createBuffer(1, length, sample_rate);
}


RealizedSound.prototype.getBuffer = function() {
    return this._buffer.getChannelData(0);
};

RealizedSound.prototype.play = function() {
    ULBS();

    var source = AUDIO_CONTEXT.createBufferSource();

    source.buffer = this._buffer;
    source.connect(AUDIO_CONTEXT.destination);

    var t = AUDIO_CONTEXT.currentTime;
    if (typeof source.start != 'undefined') {
        source.start(t);
    } else {
        source.noteOn(t);
    }
    source.onended = function() {
        source.disconnect()
    }
};


if (typeof AUDIO_CONTEXT == 'undefined') {
    RealizedSound = function RealizedSound(length, sample_rate) {
        this._sample_rate = sample_rate;
        this._buffer = new Array(length);
        this._audioElement = null;
    };

    RealizedSound.prototype.getBuffer = function() {
        this._audioElement = null;
        return this._buffer;
    };

    RealizedSound.prototype.play = function() {
        if (this._audioElement) {
            this._audioElement.cloneNode(false).play();
        } else {
            for (var i = 0; i < this._buffer.length; i++) {
                // bit_depth is always 8, rescale [-1.0, 1.0) to [0, 256)
                this._buffer[i] = 255 & Math.floor(128 * Math.max(0, Math.min(this._buffer[i] + 1, 2)));
            }
            var wav = MakeRiff(this._sample_rate, BIT_DEPTH, this._buffer);
            this._audioElement = new Audio();
            this._audioElement.src = wav.dataURI;
            this._audioElement.play();
        }
    };



    RealizedSound.MIN_SAMPLE_RATE = 1;
}

RealizedSound.prototype.getDataUri = function() {
    const BIT_DEPTH=16;
    var raw_buffer = this.getBuffer();
    var output_buffer = new Array(raw_buffer.length);
    for (var i = 0; i < raw_buffer.length; i++) {
        // bit_depth is always 16, rescale [-1.0, 1.0) to [0, 65536)
        // Use 32768 (2^15) for 16-bit audio conversion (range: -32768 to 32767)
        output_buffer[i] = Math.floor(32768 * Math.max(-1, Math.min(raw_buffer[i], 1)))|0;
    }
    var wav = MakeRiff(SAMPLE_RATE, BIT_DEPTH, output_buffer);
    return wav.dataURI;
}

RealizedSound.from_buffer = function(buffer) {
    var sound = new RealizedSound(buffer.length, RealizedSound.MIN_SAMPLE_RATE);
    sound._buffer.copyToChannel(buffer, 0);
    return sound;
};
