#!/usr/bin/env node
// Reproducible examples from the same randomized buttons used by the app.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createContext, root, plain} = require('../../tests/helpers/synth-context');
const {encodeWav16} = require('./wav');
const families = ["Boomr", "Pewpr", "Zappr", "Whooshr", "Bouncr", "Rollr", "Breathr", "Choirr", "Pluckr", "Glitchr", "Pulser", "Rumblr"];
const api = createContext(families), rate = 44100;
const output = path.resolve(process.argv[2] || path.join(root, 'examples/Deluge'));
const collection = {}, sounds = [];

function seedFor(text) {
    let hash = 2166136261;
    for (const character of text) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
    return (hash >>> 0) / 4294967296;
}
function measure(pcm, label) {
    let peak=0, energy=0;
    for (const sample of pcm) {
        assert.ok(Number.isFinite(sample), `${label}: non-finite sample`);
        peak=Math.max(peak,Math.abs(sample)); energy+=sample*sample;
    }
    const rms=Math.sqrt(energy/pcm.length);
    assert.ok(peak<1 && peak>0.025 && rms>0.0015, `${label}: peak ${peak}, RMS ${rms}`);
    assert.ok(pcm[0]===0 && pcm[pcm.length-1]===0, `${label}: edge fade`);
    return {frames:pcm.length,duration:pcm.length/rate,peak,rms,
        pcmSha256:crypto.createHash('sha256').update(Buffer.from(pcm.buffer,pcm.byteOffset,pcm.byteLength)).digest('hex')};
}
fs.mkdirSync(output,{recursive:true});
for (const family of families) {
    const recipes=plain(api.run(`var synth=new ${family}(); synth.recipes`)), files=[];
    assert.equal(recipes.length,8);
    for (const recipe of recipes) {
        const generationSeed=seedFor(`Deluge/v1/${family}/${recipe.id}`);
        const params=plain(api.run(`Math.random=SoundDSP.rng(${generationSeed});
            synth.generate_recipe(${JSON.stringify(recipe.id)}); synth.params`));
        const serialized=JSON.stringify(params);
        const pcm=api.run('synth.generate_sound(); synth.sound.getBuffer().slice()');
        const metrics=measure(pcm,`${family}/${recipe.id}`);
        const restored=api.run(`var restored=new ${family}(); restored.apply_params(${serialized});
            restored.generate_sound(); restored.sound.getBuffer()`);
        assert.equal(measure(restored,`${family}/${recipe.id} reload`).pcmSha256,metrics.pcmSha256);
        const file=`${family.toLowerCase()}_${recipe.id}.wav`;
        fs.writeFileSync(path.join(output,file),encodeWav16(pcm,rate));
        files.push([recipe.name,serialized,serialized]);
        sounds.push({synth:family,id:recipe.id,name:recipe.name,tip:recipe.tip,file,generationSeed,...metrics,pcm});
        console.log(`${family.padEnd(6)} ${recipe.name.padEnd(20)} ${metrics.duration.toFixed(2)} s  RMS ${metrics.rms.toFixed(3)}`);
    }
    collection[family]={files,selected_file_index:0,create_new_sound:true,play_on_change:true,
        locked_params:plain(api.run('synth.locked_params'))};
}
collection.active_tab_index=20;
fs.writeFileSync(path.join(output,'Deluge.bcol'),JSON.stringify(collection,null,2)+'\n');

const playlist=[["Boomr", "grenade"], ["Pewpr", "railgun"], ["Zappr", "tesla_coil"], ["Whooshr", "sword_swing"], ["Bouncr", "rubber_ball"], ["Rollr", "minecart"], ["Breathr", "gasp"], ["Choirr", "angelic"], ["Pluckr", "kalimba"], ["Glitchr", "buffer_skip"], ["Pulser", "android_core"], ["Rumblr", "stone_door"]];
const clips=[], gap=Math.round(0.3*rate); let frame=0;
for (const [family,id] of playlist) {
    const sound=sounds.find(s=>s.synth===family&&s.id===id);
    assert.ok(sound,`${family}/${id} exists`);
    const pcm=sound.pcm.slice(), gain=Math.min(2.5,0.085/sound.rms,0.7/sound.peak);
    for(let i=0;i<pcm.length;i++)pcm[i]*=gain;
    clips.push({synth:family,name:sound.name,file:sound.file,start:frame/rate,end:(frame+pcm.length)/rate,gain,pcm});
    frame+=pcm.length+gap;
}
const reel=new Float32Array(frame-gap);
for(const clip of clips)reel.set(clip.pcm,Math.round(clip.start*rate));
const showcaseFile='deluge_showcase.wav', showcaseMetrics=measure(reel,'Showcase');
fs.writeFileSync(path.join(output,showcaseFile),encodeWav16(reel,rate));
const withoutPCM=({pcm,...entry})=>entry;
fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({sampleRate:rate,format:'mono PCM16 WAV',
    sounds:sounds.map(withoutPCM),showcase:{file:showcaseFile,...showcaseMetrics,gap:gap/rate,clips:clips.map(withoutPCM)}},null,2)+'\n');
const descriptions={
    "Boomr": "Pressure blasts, shockwaves and scattered debris.",
    "Pewpr": "Staged weapon pulses, charge, recoil and ricochets.",
    "Zappr": "Electrical arcs, crackles, hum and sparks.",
    "Whooshr": "Moving air, whistles and Doppler swishes.",
    "Bouncr": "Material contacts with shrinking bounce flights.",
    "Rollr": "Continuous rolling contacts, surfaces and wheel motion.",
    "Breathr": "Breathing, exertion and turbulent airflow.",
    "Choirr": "Detuned vowel ensembles and harmonic swells.",
    "Pluckr": "Feedback strings with excitation and damping.",
    "Glitchr": "Repeated, corrupted and missing digital fragments.",
    "Pulser": "Double pressure beats and turbulent body rhythms.",
    "Rumblr": "Low structural modes, shuddering pressure and grit."
};
const lines=['# The tab deluge','',
    '96 editable sounds: eight randomized categories in each of twelve new tabs. Every preset click makes another variation.','',
    'Open **Deluge.bcol** with **Open Data**, or drag it onto Bfxr. This replaces the lists in these twelve tabs; save your collection first if needed. Select an example to hear and edit it. All twelve also work as copied layers in Stackr.','',
    `The [${showcaseMetrics.duration.toFixed(1)}-second reel](${showcaseFile}) plays twelve complete sounds with 0.3-second gaps. Levels are balanced for the reel; individual WAVs match their saved settings exactly.`,'',
    '| Start | Tab | Sound |','| --- | --- | --- |',
    ...clips.map(c=>`| ${c.start.toFixed(2)} s | ${c.synth} | ${c.name} |`),''];
for (const family of families) {
    lines.push(`## ${family}`,'',descriptions[family],'','| Preset | Length |','| --- | --- |',
        ...sounds.filter(s=>s.synth===family).map(s=>`| [${s.name}](${s.file}) | ${s.duration.toFixed(2)} s |`),'');
}
lines.push('## Rebuild','',
    '`node tools/render/deluge_examples.js` regenerates this collection, 96 WAVs, the reel and validation report. An optional argument chooses another output directory. WAVs are generated locally and ignored by Git.','',
    'Every example is checked for finite, bounded, audible audio, faded edges and bit-identical sound after reloading its saved parameters. See [validation.json](validation.json).','');
fs.writeFileSync(path.join(output,'README.md'),lines.join('\n'));
console.log(`Wrote ${sounds.length} examples and a ${showcaseMetrics.duration.toFixed(2)} s reel to ${output}`);
