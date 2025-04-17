class RealizedSound {
    static MIN_SAMPLE_RATE = SAMPLE_RATE;

    constructor(length, sample_rate) {
        this._buffer = AUDIO_CONTEXT.createBuffer(1, length, sample_rate);
    }


    getBuffer() {
        return this._buffer.getChannelData(0);
    }


    source = null;
    play() {
        ULBS();

        if (this.source!=null){
            this.stop();
        }
        this.source = AUDIO_CONTEXT.createBufferSource();

        this.source.buffer = this._buffer;
        this.source.connect(AUDIO_CONTEXT.destination);

        var t = AUDIO_CONTEXT.currentTime;
        if (typeof this.source.start != 'undefined') {
            this.source.start(t);
        } else {
            this.source.noteOn(t);
        }
        this.source.onended = function() {
            if (this.source){
                this.source.disconnect()
            }
        }
    }

    stop() {
        if (this.source==null){
            return;
        }
        this.source.stop();
        this.source.disconnect();
        this.source = null;
    }

    getDataUri() {
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

    static from_buffer(buffer) {
        var sound = new RealizedSound(buffer.length, RealizedSound.MIN_SAMPLE_RATE);
        sound._buffer.copyToChannel(buffer, 0);
        return sound;
    };
}
