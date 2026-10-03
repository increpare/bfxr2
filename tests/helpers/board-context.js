// A headless context with every engine the Soundboard can draw on, including retired ones and Footsteppr.
const {createContext,root,plain}=require('./synth-context');
const ENGINES=['Bfxr','Transfxr','Clonkr','Machinr','Jinglr','Squishr','Crittr','Birdr','Signlr','Fractr','Riftr','Swarmr','Rustlr','Boomr','Zappr','Whooshr','Bouncr','Breathr','Choirr','Pluckr','Glitchr','Tappr','Pewpr','Tickr','Stackr','Mixr'];
function createBoardContext(){
 const api=createContext(ENGINES);
 api.run('var CONVERSION_FACTOR=(2*Math.PI)/44100;');
 for(const file of ['js/audio/puredata.js','js/audio/puredata_modules.js','js/audio/puredata_parser.js','js/synths/Footsteppr.js','js/synths/Soundboard.js'])api.load(file);
 return api;
}
// Active duration in seconds: the span where the 256-sample RMS envelope stays above 3% of its peak.
function activeDuration(pcm){
 const hop=256;let peak=0;const env=[];
 for(let i=0;i<pcm.length;i+=hop){let e=0;const end=Math.min(pcm.length,i+hop);for(let j=i;j<end;j++)e+=pcm[j]*pcm[j];const v=Math.sqrt(e/hop);env.push(v);if(v>peak)peak=v;}
 const threshold=Math.max(peak*0.03,0.0005);let first=-1,last=-1;
 env.forEach((v,i)=>{if(v>=threshold){if(first<0)first=i;last=i;}});
 return first<0?0:(last-first+1)*hop/44100;
}
module.exports={createBoardContext,activeDuration,ENGINES,root,plain};
