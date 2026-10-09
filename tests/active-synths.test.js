const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createContext, root} = require('./helpers/synth-context');

test('the app includes only current synth engines and existing script files', () => {
    const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
    const retired = ['Chattr', 'Pewpr', 'Rumblr', 'Weathr', 'Stackr', 'Tappr',
        'Notifr', 'Tickr', 'Holor', 'Rollr', 'Pulser'];
    const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map(m => m[1].split('?')[0]);
    for (const script of scripts) {
        assert.ok(fs.existsSync(path.join(root, script)), script);
        assert.ok(!retired.some(name => script.includes(name)), script);
    }
});

test('Mixr renders saved sources without any retired engine', () => {
    const {run} = createContext(['Clonkr', 'Mixr']);
    assert.equal(run(`(() => {
        const mix = new Mixr(), source = new Clonkr();
        source.generate_recipe('glass_ping');
        mix.set_source(0, source, 'Glass');
        mix.generate_sound();
        const pcm = mix.sound.getBuffer();
        const copy = new Mixr();
        copy.apply_params(JSON.parse(JSON.stringify(mix.params)));
        copy.generate_sound();
        return pcm.some(v => Math.abs(v) > .025) && pcm.every(Number.isFinite) &&
            copy.sound.getBuffer().every((v, i) => v === pcm[i]);
    })()`), true);
});
