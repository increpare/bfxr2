// Emit NDJSON {preset, seed, params} for the app's preset generators.
//   node render/preset_cli.js --preset all --count 100 --seed 0
'use strict';
const { createBfxrContext } = require('./bfxr_context.js');

const PRESETS = [
    'generate_pickup_coin', 'generate_laser_shoot', 'generate_explosion',
    'generate_powerup', 'generate_hit_hurt', 'generate_jump',
    'generate_blip_select', 'randomize_params',
];

const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
    args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
}
const preset = args.preset || 'all';
const count = parseInt(args.count || '1', 10);
const seed0 = parseInt(args.seed || '0', 10);
if (preset !== 'all' && !PRESETS.includes(preset)) {
    process.stderr.write(`unknown preset ${preset}; known: ${PRESETS.join(', ')}\n`);
    process.exit(1);
}

const ctx = createBfxrContext();
const lines = [];
for (let i = 0; i < count; i++) {
    const name = preset === 'all' ? PRESETS[i % PRESETS.length] : preset;
    const json = ctx.samplePreset(name, seed0 + i);
    if (json !== null) {
        lines.push(JSON.stringify({ preset: name, seed: seed0 + i, params: JSON.parse(json) }));
    }
}
process.stdout.write(lines.join('\n') + '\n');
