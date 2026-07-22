#!/usr/bin/env node
'use strict';
// One-shot renderer:
//   node render_cli.js --in sound.bfxr --out out.wav [--seed 1]
//   node render_cli.js --dump-info
// --in accepts either a full .bfxr file ({synth_type, params, ...}) or a bare
// params JSON object.
const fs = require('node:fs');
const { createBfxrContext } = require('./bfxr_context');
const { encodeWav16 } = require('./wav');

function parseArgs(argv) {
    const args = { seed: 1 };
    for (let i = 2; i < argv.length; i++) {
        switch (argv[i]) {
            case '--in': args.in = argv[++i]; break;
            case '--out': args.out = argv[++i]; break;
            case '--seed': args.seed = parseInt(argv[++i], 10); break;
            case '--dump-info': args.dumpInfo = true; break;
            default:
                console.error(`Unknown argument: ${argv[i]}`);
                process.exit(2);
        }
    }
    return args;
}

function main() {
    const args = parseArgs(process.argv);
    const bfxr = createBfxrContext();

    if (args.dumpInfo) {
        process.stdout.write(JSON.stringify(bfxr.paramInfo(), null, 2) + '\n');
        return;
    }

    if (!args.in || !args.out) {
        console.error('Usage: render_cli.js --in sound.bfxr --out out.wav [--seed N] | --dump-info');
        process.exit(2);
    }

    const parsed = JSON.parse(fs.readFileSync(args.in, 'utf8'));
    const params = parsed.params !== undefined ? parsed.params : parsed;
    const buffer = bfxr.render(params, args.seed);
    if (buffer === null) {
        console.error('Render failed (DSP produced no buffer)');
        process.exit(1);
    }
    fs.writeFileSync(args.out, encodeWav16(buffer, bfxr.paramInfo().sampleRate));
    console.error(`Wrote ${args.out}: ${buffer.length} samples (${(buffer.length / 44100).toFixed(3)}s)`);
}

main();
