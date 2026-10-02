#!/usr/bin/env node
// Render the exact curated recipes, plus an editable collection, without a browser.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const output = path.resolve(process.argv[2] || path.join(root, 'examples/Transfxr'));
const ctx = vm.createContext({console});
for (const source of ['js/globals.js','js/synths/templates.js','js/synths/SynthBase.js',
    'js/audio/Transfxr_DSP.js','js/synths/Transfxr.js']) {
    vm.runInContext(fs.readFileSync(path.join(root,source),'utf8'),ctx,{filename:source});
}
const examples = vm.runInContext(`var s = new Transfxr(); Transfxr.examples.map(example => {
    s.generate_example(example.id, false);
    return {name:example.name, id:example.id, params:JSON.stringify(s.params),
        pcm:Transfxr_DSP.render(s.params)};
});`,ctx);
function wav(pcm) {
    const data=Buffer.alloc(44+pcm.length*2);
    data.write('RIFF'); data.writeUInt32LE(data.length-8,4); data.write('WAVEfmt ',8);
    data.writeUInt32LE(16,16); data.writeUInt16LE(1,20); data.writeUInt16LE(1,22);
    data.writeUInt32LE(44100,24); data.writeUInt32LE(88200,28);
    data.writeUInt16LE(2,32); data.writeUInt16LE(16,34); data.write('data',36);
    data.writeUInt32LE(pcm.length*2,40);
    for(let i=0;i<pcm.length;i++) data.writeInt16LE(Math.round(Math.max(-1,Math.min(1,pcm[i]))*32767),44+i*2);
    return data;
}
fs.mkdirSync(output,{recursive:true});
const pause=11025;
const reel=new Float32Array(examples.reduce((sum,e)=>sum+e.pcm.length+pause,0));
let offset=0;
for(const example of examples) {
    fs.writeFileSync(path.join(output,example.id+'.wav'),wav(example.pcm));
    reel.set(example.pcm,offset);offset+=example.pcm.length+pause;
    let energy=0,peak=0;
    for(const value of example.pcm){energy+=value*value;peak=Math.max(peak,Math.abs(value));}
    console.log(`${example.name}: ${(example.pcm.length/44100).toFixed(2)} s, peak ${peak.toFixed(3)}, RMS ${Math.sqrt(energy/example.pcm.length).toFixed(3)}`);
}
fs.writeFileSync(path.join(output,'transfxr_showcase.wav'),wav(reel));
const locked_params=vm.runInContext('s.locked_params',ctx);
const collection={Transfxr:{files:examples.map(e=>[e.name.replace(/ /g,''),e.params,e.params]),
    selected_file_index:0,create_new_sound:true,play_on_change:true,locked_params},active_tab_index:2};
fs.writeFileSync(path.join(output,'Transfxr.bcol'),JSON.stringify(collection,null,2)+'\n');
console.log('Wrote WAVs and Transfxr.bcol to '+output);
