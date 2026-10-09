// Only this object escapes the bundle's private closure.
global.bfxr = {
    version: '1.0.0',
    sampleRate: SAMPLE_RATE,
    synths: () => Object.keys(BFXR_SYNTHS),
    presets: name => LibrarySounds.categories(LibrarySounds.engine(name)).map(entry => entry[0]),
    preset: (name, id, seed) => LibrarySounds.preset(name, id, seed),
    render: sound => LibraryCache.sound(LibrarySounds.normalize(sound)).pcm.slice(),
    play: (sound, options) => LibraryPlayback.play(LibrarySounds.normalize(sound), options),
    playMutated: (sound, amount = .05, count = 15, options) => LibraryPlayback.play(
        LibraryCache.mutated(LibrarySounds.normalize(sound), amount, count), options),
    cache: sound => LibraryCache.warm(LibrarySounds.normalize(sound)),
    cacheMutations: (sound, amount = .05, count = 15) => LibraryCache.warmMutations(
        LibrarySounds.normalize(sound), amount, count),
    stopAll: () => LibraryPlayback.stopAll(),
    clearCache: () => LibraryCache.clear()
};
