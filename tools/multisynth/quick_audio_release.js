(function () {
    'use strict';
    const auditionPolicy={version:'signal-support-half-v1',relativeAmplitudeFloor:.001,
        exposure:'halfway between first and last above-threshold samples',fallback:'half buffer duration',playback:'unchanged'};
    function auditionThreshold(buffer) {
        if(typeof buffer.getChannelData!=='function' || !(buffer.sampleRate>0) || !(buffer.numberOfChannels>0))return buffer.duration*.5;
        const channels=Array.from({length:buffer.numberOfChannels},(_,i)=>buffer.getChannelData(i));
        let peak=0,first=Infinity,last=-1;
        for(const data of channels)for(const v of data)peak=Math.max(peak,Math.abs(v));
        if(!(peak>1e-8))return buffer.duration*.5;
        for(const data of channels)for(let i=0;i<data.length;i++)if(Math.abs(data[i])>peak*auditionPolicy.relativeAmplitudeFloor){first=Math.min(first,i);last=Math.max(last,i);}
        return last<0?buffer.duration*.5:(first+last+1)/(2*buffer.sampleRate);
    }
    class CachedAudioPlayer {
        constructor({context,fetch,onAudition=()=>{},onEnded=()=>{},onState=()=>{},stopFadeSeconds=.005}) {
            Object.assign(this,{context,fetch,onAudition,onEnded,onState});
            this.stopFadeSeconds=stopFadeSeconds;this.releaseUntil=0;
            this.thresholds=new WeakMap(); this.cache=new Map(); this.serial=0; this.current=null;
            this.gain=context.createGain();this.gain.gain.value=.8;this.gain.connect(context.destination);
        }
        preload(url) {
            if (!this.cache.has(url)) {
                const promise=this.fetch(url).then(response => {
                    if (!response.ok) throw Error('Audio could not be loaded');
                    return response.arrayBuffer();
                }).then(bytes => this.context.decodeAudioData(bytes)).then(buffer=>{this.thresholds.set(buffer,auditionThreshold(buffer));return buffer;});
                this.cache.set(url,promise);
                promise.catch(() => {if(this.cache.get(url)===promise)this.cache.delete(url);});
            }
            return this.cache.get(url);
        }
        remember(current,ended=false) {
            if (!current.heard && (ended || this.context.currentTime-current.started >= current.heardAt)) {
                current.heard=true;this.onAudition(current.url);
            }
        }
        stop() {
            this.serial++;
            const current=this.current;this.current=null;
            if (current) {
                this.remember(current);
                const now=this.context.currentTime;
                const release=now>=current.started?Math.max(0,Math.min(.02,this.stopFadeSeconds)):0;
                const until=now+release;
                current.voice.gain.cancelScheduledValues(now);
                if(release>0){
                    current.voice.gain.setValueAtTime(1,now);
                    current.voice.gain.linearRampToValueAtTime(0,until);
                }
                current.source.stop(until);
                this.releaseUntil=Math.max(this.releaseUntil,until);
            }
            this.onState('stopped');
        }
        async play(url) {
            this.stop();const serial=this.serial;
            // Resume immediately in the input handler, before fetching/decoding.
            const resumed=this.context.resume();
            const [buffer]=await Promise.all([this.preload(url),resumed]);
            if (serial !== this.serial) return false;
            if (this.context.state !== 'running') throw Error('Playback paused. Press Play to continue.');
            const source=this.context.createBufferSource();source.buffer=buffer;
            const voice=this.context.createGain();voice.gain.value=1;source.connect(voice);voice.connect(this.gain);
            const started=Math.max(this.context.currentTime,this.releaseUntil);
            const current={source,voice,url,duration:buffer.duration,started,heardAt:this.thresholds.get(buffer),heard:false};
            this.current=current;
            source.onended=() => {
                source.disconnect();voice.disconnect();
                if (this.current !== current) return;
                this.remember(current,true);this.current=null;
                this.onState('ended',url);this.onEnded(url);
            };
            source.start(started,0);this.onState('playing',url);return true;
        }
        get progress() {
            const c=this.current;
            return c ? {url:c.url,duration:c.duration,elapsed:Math.min(c.duration,Math.max(0,this.context.currentTime-c.started))} : null;
        }
    }
    const api={CachedAudioPlayer,auditionThreshold,auditionPolicy};
    if (typeof module !== 'undefined') module.exports=api;
    if (typeof window !== 'undefined') window.BfxrQuickAudio=api;
}());
