'use strict';
// Minimal mono 16-bit PCM WAV encoder. (js/audio/riffwave.js builds per-byte
// JS arrays and is far too slow for batch use.)

function encodeWav16(samples, sampleRate) {
    const n = samples.length;
    const dataBytes = n * 2;
    const buf = Buffer.alloc(44 + dataBytes);

    buf.write('RIFF', 0, 'ascii');
    buf.writeUInt32LE(36 + dataBytes, 4);
    buf.write('WAVE', 8, 'ascii');
    buf.write('fmt ', 12, 'ascii');
    buf.writeUInt32LE(16, 16); // fmt chunk size
    buf.writeUInt16LE(1, 20); // PCM
    buf.writeUInt16LE(1, 22); // mono
    buf.writeUInt32LE(sampleRate, 24);
    buf.writeUInt32LE(sampleRate * 2, 28); // byte rate
    buf.writeUInt16LE(2, 32); // block align
    buf.writeUInt16LE(16, 34); // bits per sample
    buf.write('data', 36, 'ascii');
    buf.writeUInt32LE(dataBytes, 40);

    for (let i = 0; i < n; i++) {
        let v = samples[i];
        if (v > 1) v = 1;
        else if (v < -1) v = -1;
        buf.writeInt16LE((v * 32767) | 0, 44 + i * 2);
    }
    return buf;
}

module.exports = { encodeWav16 };
