(function () {
    'use strict';
    class CachedAudioPlayer {
        constructor({context,fetch,onAudition=()=>{},onEnded=()=>{},onState=()=>{}}) {
            Object.assign(this,{context,fetch,onAudition,onEnded,onState});
            this.cache=new Map(); this.serial=0; this.current=null;
            this.gain=context.createGain();this.gain.gain.value=.8;this.gain.connect(context.destination);
        }
        preload(url) {
            if (!this.cache.has(url)) {
                const promise=this.fetch(url).then(response => {
                    if (!response.ok) throw Error('Audio could not be loaded');
                    return response.arrayBuffer();
                }).then(bytes => this.context.decodeAudioData(bytes));
                this.cache.set(url,promise);
                promise.catch(() => {if(this.cache.get(url)===promise)this.cache.delete(url);});
            }
            return this.cache.get(url);
        }
        remember(current,ended=false) {
            if (!current.heard && (ended || this.context.currentTime-current.started >= current.duration*.5)) {
                current.heard=true;this.onAudition(current.url);
            }
        }
        stop() {
            this.serial++;
            const current=this.current;this.current=null;
            if (current) {this.remember(current);current.source.stop();}
            this.onState('stopped');
        }
        async play(url) {
            this.stop();const serial=this.serial;
            // Resume immediately in the input handler, before fetching/decoding.
            const resumed=this.context.resume();
            const [buffer]=await Promise.all([this.preload(url),resumed]);
            if (serial !== this.serial) return false;
            if (this.context.state !== 'running') throw Error('Playback paused. Press Play to continue.');
            const source=this.context.createBufferSource();source.buffer=buffer;source.connect(this.gain);
            const current={source,url,duration:buffer.duration,started:this.context.currentTime,heard:false};
            this.current=current;
            source.onended=() => {
                if (this.current !== current) return;
                this.remember(current,true);this.current=null;
                this.onState('ended',url);this.onEnded(url);
            };
            source.start(0,0);this.onState('playing',url);return true;
        }
        get progress() {
            const c=this.current;
            return c ? {url:c.url,duration:c.duration,elapsed:Math.min(c.duration,Math.max(0,this.context.currentTime-c.started))} : null;
        }
    }
    const api={CachedAudioPlayer};
    if (typeof module !== 'undefined') module.exports=api;
    if (typeof window !== 'undefined') window.BfxrQuickAudio=api;
}());
