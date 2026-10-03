#!/usr/bin/env node
// Restore discovery audio from saved states, without regenerating its proposals.
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {root,createContext,wav}=require('./render_corpus');
function renderSaved(directory){
 const output=path.resolve(directory),corpus=JSON.parse(fs.readFileSync(path.join(output,'corpus.json'),'utf8'));
 const context=createContext(),render=vm.runInContext('(p)=>{const s=new Transfxr();s.apply_params(p);return Transfxr_DSP.render(s.params);}',context);
 for(const sound of corpus.sounds){
  const target=path.resolve(output,sound.audio);
  if(!target.startsWith(output+path.sep))throw Error('Audio path escapes survey directory');
  fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,wav(render(sound.params)));
 }
 console.log('Restored '+corpus.sounds.length+' saved discovery sounds');
}
if(require.main===module)renderSaved(process.argv[2]||path.join(root,'examples/Transfxr/survey'));
module.exports={renderSaved};
