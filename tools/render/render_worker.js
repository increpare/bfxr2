#!/usr/bin/env node
'use strict';
// Persistent batch renderer for driving from Python during optimization.
//
// stdin:  NDJSON, one request per line: {"id": <uint32>, "seed": <uint32>, "params": {...}}
// stdout: one binary frame per request, in request order:
//         uint32LE id | int32LE status | uint32LE n_samples | n_samples * float32LE
//         status: 0=ok, 1=render_failed, 2=bad_request (id=0xFFFFFFFF if unparseable)
// stderr: one JSON ready line at startup, then diagnostics only.
const { createBfxrContext } = require('./bfxr_context');

const STATUS_OK = 0;
const STATUS_RENDER_FAILED = 1;
const STATUS_BAD_REQUEST = 2;
const UNKNOWN_ID = 0xFFFFFFFF;

const bfxr = createBfxrContext();
const info = bfxr.paramInfo();
process.stderr.write(JSON.stringify({ ready: true, version: info.version, sampleRate: info.sampleRate }) + '\n');

function writeFrame(id, status, samples) {
    const n = samples ? samples.length : 0;
    const header = Buffer.alloc(12);
    header.writeUInt32LE(id >>> 0, 0);
    header.writeInt32LE(status, 4);
    header.writeUInt32LE(n, 8);
    if (n > 0) {
        return process.stdout.write(Buffer.concat([
            header,
            Buffer.from(samples.buffer, samples.byteOffset, n * 4),
        ]));
    }
    return process.stdout.write(header);
}

function handleLine(line) {
    if (line.length === 0) return true;
    let req;
    try {
        req = JSON.parse(line);
    } catch (e) {
        return writeFrame(UNKNOWN_ID, STATUS_BAD_REQUEST, null);
    }
    const id = Number.isInteger(req.id) && req.id >= 0 ? req.id : UNKNOWN_ID;
    if (id === UNKNOWN_ID || typeof req.params !== 'object' || req.params === null) {
        return writeFrame(id, STATUS_BAD_REQUEST, null);
    }
    let buffer = null;
    try {
        buffer = bfxr.render(req.params, (req.seed || 0) >>> 0);
    } catch (e) {
        process.stderr.write(`render error id=${id}: ${e.message}\n`);
    }
    if (buffer === null) {
        return writeFrame(id, STATUS_RENDER_FAILED, null);
    }
    return writeFrame(id, STATUS_OK, buffer);
}

// Manual line splitting with backpressure: pause stdin while stdout drains.
let pending = '';
process.stdin.on('data', (chunk) => {
    pending += chunk.toString('utf8');
    let idx;
    let ok = true;
    while ((idx = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0, idx).trim();
        pending = pending.slice(idx + 1);
        ok = handleLine(line);
    }
    if (!ok) {
        process.stdin.pause();
        process.stdout.once('drain', () => process.stdin.resume());
    }
});
process.stdin.on('end', () => {
    if (pending.trim().length > 0) handleLine(pending.trim());
    // No process.exit() here: it would drop buffered stdout frames. The
    // process ends on its own once pending writes drain.
});
