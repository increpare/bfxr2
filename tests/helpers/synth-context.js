const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
function createContext(names = []) {
    const storage = new Map();
    const context = vm.createContext({console: {log(){}, error: console.error}, Float32Array,
        localStorage:{setItem(k,v){storage.set(k,v);},getItem(k){return storage.get(k);}}});
    vm.runInContext(`const SAMPLE_RATE=44100; function ULBS() {};
        const AUDIO_CONTEXT={currentTime:0,destination:{},createBuffer(channels,length,rate){
            const pcm=new Float32Array(length); return {getChannelData(){return pcm;},copyToChannel(data){pcm.set(data);}};
        },createBufferSource(){return {connect(){},disconnect(){},start(){},stop(){}};}};`,context);
    const sources=['js/globals.js','js/audio/riffwave.js','js/audio/RealizedSound.js',
        'js/synths/templates.js','js/synths/SynthBase.js','js/audio/SoundDSP.js','js/synths/PresetSynth.js',
        'js/synths/PresetFamily.js','js/synths/TransfxrPresets.js'];
    for(const name of names) sources.push(`js/audio/${name}_DSP.js`,`js/synths/${name}.js`);
    for(const source of sources) vm.runInContext(fs.readFileSync(path.join(root,source),'utf8'),context,{filename:source});
    return {context,run:code=>vm.runInContext(code,context),load:source=>vm.runInContext(fs.readFileSync(path.join(root,source),'utf8'),context,{filename:source})};
}
module.exports={createContext,root,plain:value=>JSON.parse(JSON.stringify(value))};
