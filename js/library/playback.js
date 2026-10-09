// Lazy Web Audio setup and one independent source/gain pair per play.
const LibraryPlayback = {
    context: null,
    voices: new Set(),
    unlocking: false,
    listening: false,

    options(options = {}) {
        if (!options || typeof options !== 'object') throw new TypeError('Playback options must be an object');
        const volume = options.volume ?? 1, pitch = options.pitch ?? 0, loop = options.loop ?? false;
        if (!Number.isFinite(volume) || volume < 0) throw new RangeError('volume must be a finite nonnegative number');
        if (!Number.isFinite(pitch) || pitch < -96 || pitch > 96) throw new RangeError('pitch must be between -96 and 96 semitones');
        if (typeof loop !== 'boolean') throw new TypeError('loop must be a boolean');
        return {volume, pitch, loop};
    },

    audio() {
        if (!this.context || this.context.state === 'closed') {
            const Constructor = global.AudioContext || global.webkitAudioContext;
            if (!Constructor) throw new Error('This browser does not support Web Audio');
            this.context = new Constructor();
        }
        this.unlock();
        return this.context;
    },

    unlock() {
        if (!this.context || this.context.state === 'running' || this.unlocking) return;
        this.unlocking = true;
        // Attach immediately: some browsers leave resume() pending until a gesture.
        this.listen();
        Promise.resolve(this.context.resume()).then(() => {
            this.unlocking = false;
            if (this.context.state === 'running') this.unlisten();
        }, () => { this.unlocking = false; });
    },

    gesture() {
        // Retry even if an earlier autoplay-blocked resume remains pending.
        LibraryPlayback.unlocking = false;
        LibraryPlayback.unlock();
    },

    listen() {
        if (this.listening || !global.addEventListener) return;
        this.listening = true;
        for (const event of ['pointerdown', 'touchend', 'keydown']) {
            global.addEventListener(event, this.gesture, {capture: true, passive: true});
        }
    },

    unlisten() {
        if (!this.listening) return;
        this.listening = false;
        for (const event of ['pointerdown', 'touchend', 'keydown']) {
            global.removeEventListener(event, this.gesture, {capture: true});
        }
    },

    play(sound, options) {
        const settings = this.options(options);
        const context = this.audio(), key = LibraryCache.key(sound), entry = LibraryCache.sound(sound);
        if (!entry.buffer) {
            entry.buffer = context.createBuffer(1, entry.pcm.length, SAMPLE_RATE);
            entry.buffer.copyToChannel(entry.pcm, 0);
            LibraryCache.remember(key, entry);
        }
        const source = context.createBufferSource(), gain = context.createGain();
        source.buffer = entry.buffer;
        source.loop = settings.loop;
        source.playbackRate.value = 2 ** (settings.pitch / 12);
        gain.gain.value = settings.volume;
        source.connect(gain); gain.connect(context.destination);
        let active = true;
        const cleanup = () => {
            if (!active) return;
            active = false;
            source.disconnect(); gain.disconnect();
            this.voices.delete(voice);
        };
        const voice = {stop() {
            if (!active) return;
            source.stop(); cleanup();
        }};
        source.onended = cleanup;
        this.voices.add(voice);
        try { source.start(context.currentTime); } catch (error) { cleanup(); throw error; }
        return voice;
    },

    stopAll() { for (const voice of this.voices) voice.stop(); }
};
