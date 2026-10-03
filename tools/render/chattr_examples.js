#!/usr/bin/env node
// Render the same words along the articulation continuum, for direct listening comparisons.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname,'../..');
const output = path.resolve(process.argv[2] || path.join(root,'examples/Chattr'));
const context = vm.createContext({console});
for (const file of ['js/globals.js','js/audio/AKWF.js','js/audio/BfxrWaveforms.js','js/synths/templates.js','js/synths/SynthBase.js',
    'js/audio/ChattrLexicon.js','js/audio/ChattrFormants.js','js/audio/Chattr_Pronunciation.js',
    'js/audio/Chattr_DSP.js','js/synths/Chattr.js']) {
    vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),context,{filename:file});
}
const examples = vm.runInContext(`var s=new Chattr();
    s.generate_character('clear_speaker',false);
    s.set_param('text','The sheep found a phone. Hello, little world!');
    var examples=[0,0.5,1].map(articulation=>{
        s.set_param('articulation',articulation);
        return {id:'articulation-'+Math.round(articulation*100),params:{...s.params},pcm:Chattr_DSP.render(s.params)};
    });
    s.generate_character('village_mouse',false);
    examples.push({id:'village-mouse',params:{...s.params},pcm:Chattr_DSP.render(s.params)});
    examples;`,context);
function wav(pcm) {
    const buffer=Buffer.alloc(44+pcm.length*2);
    buffer.write('RIFF'); buffer.writeUInt32LE(buffer.length-8,4); buffer.write('WAVEfmt ',8);
    buffer.writeUInt32LE(16,16); buffer.writeUInt16LE(1,20); buffer.writeUInt16LE(1,22);
    buffer.writeUInt32LE(44100,24); buffer.writeUInt32LE(88200,28);
    buffer.writeUInt16LE(2,32); buffer.writeUInt16LE(16,34); buffer.write('data',36);
    buffer.writeUInt32LE(pcm.length*2,40);
    for(let i=0;i<pcm.length;i++) buffer.writeInt16LE(Math.round(pcm[i]*32767),44+i*2);
    return buffer;
}
fs.mkdirSync(output,{recursive:true});
for(const example of examples) {
    fs.writeFileSync(path.join(output,example.id+'.wav'),wav(example.pcm));
    fs.writeFileSync(path.join(output,example.id+'.bfxr'),JSON.stringify({synth_type:'Chattr',
        version:'2.0.0',file_name:example.id,params:example.params},null,2)+'\n');
    let energy=0,peak=0;
    for(const v of example.pcm){energy+=v*v;peak=Math.max(peak,Math.abs(v));}
    console.log(`${example.id}: ${(example.pcm.length/44100).toFixed(2)} s, peak ${peak.toFixed(3)}, RMS ${Math.sqrt(energy/example.pcm.length).toFixed(3)}`);
}
fs.writeFileSync(path.join(output,'listen.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><title>Chattr articulation</title>
<style>body{max-width:650px;margin:40px auto;padding:20px;background:#fff3d6;color:#49382d;font:17px/1.5 system-ui}audio{display:block;width:100%}h2{font-size:18px}</style>
<h1>From chatter to speech</h1><p>The same words and neutral voice at three articulation settings, followed by Village Mouse.</p>
<p>“The sheep found a phone. Hello, little world!”</p>
${examples.map(e=>`<h2>${e.id.replace(/-/g,' ')}</h2><audio controls src="${e.id}.wav"></audio>`).join('\n')}
<p>Generated locally with Chattr. Reload the .bfxr files in the main app to edit these voices.</p></html>`);
console.log('Wrote listening comparison to '+output);
