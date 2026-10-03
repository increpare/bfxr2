// Captured plucks and transients are damaged by independent read/coding failures.
class Glitchr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,round,floor,abs,max,min,PI}=Math,tau=PI*2;
        const v=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=v('duration',0.7,0.08,4),out=new Float32Array(round(duration*rate));
        const random=SoundDSP.rng(v('seed',0.5)),mode=round(v('mode',0,0,7));
        const base=80*pow(2,v('pitch',0.5)*4),fragment=v('fragment',0.3),repeat=v('repeat',0.4);
        const chaos=v('chaos',0.5),dropout=v('dropout',0.2),crush=v('crush',0.3),rateLoss=v('rate',0.3);
        const chunk=max(80,round((0.009+fragment*0.18)*rate));
        const hold=1+round(rateLoss*27),steps=pow(2,13-round(crush*11));
        // A short, evolving source gives repeated buffers recognisable attacks and timbre.
        const source=new Float32Array(round(rate*0.83)),notes=[1,1.25,0.75,1.5,1.125];
        let sourceLow=0;
        for(let i=0;i<source.length;i++) {
            const t=i/rate,note=floor(t/0.137),local=t-note*0.137,f=base*notes[note%notes.length];
            const noise=random()*2-1;sourceLow+=(noise-sourceLow)*0.12;
            const pluck=(sin(tau*f*local)+0.35*sin(tau*f*2.01*local)+0.18*sin(tau*f*3.97*local))*exp(-local*18);
            const transient=(noise-sourceLow)*exp(-local*120)*0.25;
            source[i]=(pluck*0.55+transient+sourceLow*0.24)*min(1,local/0.001);
        }
        const read=position=>{
            const wrapped=((position%source.length)+source.length)%source.length;
            const index=floor(wrapped),mix=wrapped-index;
            return source[index]*(1-mix)+source[(index+1)%source.length]*mix;
        };
        let head=0,anchor=0,speed=1,skip=false,sample=0,previous=0,dc=0,scrubLow=0;
        let dataPhase=0,dataBit=0,dataCount=0,shift=1+floor(random()*65534);
        let bandLow=0,bandMid=0,bandHigh=0,packetGain=[1,1,1,1];
        const grains=[],frozen=Array.from({length:6},(_,n)=>({phase:random()*tau,frequency:base*(1+n*0.51),gain:0}));
        let grainCountdown=0,grainOrigin=0;
        for(let i=0;i<out.length;i++) {
            const t=i/rate,j=i%chunk;
            if(j===0) {
                const fresh=i===0||random()>repeat;
                skip=i>0&&random()<dropout*0.86;
                if(fresh) {
                    anchor=floor(random()*(source.length-chunk));
                    speed=pow(2,(random()-0.5)*chaos*2.4);
                    grainOrigin=anchor;
                }
                if(mode===0||mode===6)head=anchor;
                if(mode===2) {
                    if(fresh)head=anchor;
                    speed=(random()<0.55?-1:1)*(0.2+random()*2.8)*(0.4+chaos);
                }
                packetGain=packetGain.map(()=>0.25+random()*1.2);
                if(mode===7&&fresh) {
                    for(const partial of frozen) {
                        partial.frequency=min(9000,base*(0.5+round(random()*11)/4));
                        let real=0,imaginary=0;
                        for(let k=0;k<256;k++) {
                            const captured=read(anchor+k),phase=tau*partial.frequency*k/rate;
                            real+=captured*cos(phase);imaginary+=captured*sin(phase);
                        }
                        partial.gain=0.025+min(0.22,Math.hypot(real,imaginary)/128);
                    }
                }
            }
            let value=0;
            if(mode===0) {
                // The device replays a stalled buffer until a fresh packet arrives.
                value=read(head);head+=speed;
                if(head>=anchor+chunk)head=anchor;
                value*=min(1,j/16,(chunk-j)/16);
            } else if(mode===1) {
                // Crude subband coding: independent bands have damaged packet gains and precision.
                const captured=read(head);head+=speed*(1+chaos*0.45*sin(tau*(8+fragment*25)*t));
                bandLow+=(captured-bandLow)*0.018;bandMid+=(captured-bandMid)*0.11;bandHigh+=(captured-bandHigh)*0.43;
                const bands=[bandLow,bandMid-bandLow,bandHigh-bandMid,captured-bandHigh];
                for(let band=0;band<4;band++) {
                    const resolution=pow(2,3+band-(crush*2));
                    const coded=round(bands[band]*resolution)/resolution;
                    value+=coded*packetGain[band]*(0.7+0.3*sin(tau*(11+band*7+chaos*13)*t+band));
                }
                value=value*1.7+sin(tau*base*1.43*t)*abs(bandMid-bandLow)*chaos*0.6;
            } else if(mode===2) {
                // Continuous reversible read-head motion; interpolation preserves tape-like bends.
                head+=speed*(1+chaos*0.8*sin(tau*(1.5+fragment*5)*t));
                const captured=read(head);scrubLow+=(captured-scrubLow)*min(0.95,0.07+abs(speed)*0.19);
                value=scrubLow*1.5+(random()*2-1)*0.018*chaos;
            } else if(mode===3) {
                const decimation=2+round(rateLoss*95+crush*25*(i/out.length));
                if(i%decimation===0) {
                    const levels=pow(2,8-round(crush*6)),captured=read(head);
                    let word=round((captured+1)*levels);
                    if(random()<chaos*0.22)word^=1<<floor(random()*max(1,round(crush*7)));
                    previous=word/levels-1;
                }
                head+=0.65+speed*0.45;value=previous*0.85;
            } else if(mode===4) {
                // A deterministic shift register transmits binary FSK and leaking logic edges.
                const baud=round(rate/(100+fragment*1700));
                if(dataCount--<=0) {
                    shift=((shift>>>1)^(-(shift&1)&0xB400))&65535;
                    dataBit=shift&1;dataCount=baud;
                }
                dataPhase+=tau*min(rate*0.42,base*(dataBit?7.3+chaos:4.17))/rate;
                const carrier=sin(dataPhase);
                value=(carrier>0?1:-1)*0.30+carrier*0.22+(dataBit*2-1)*0.08;
            } else if(mode===5) {
                // Several independent windowed grains overlap, with jumps and reverse fragments.
                if(grainCountdown--<=0) {
                    const length=max(100,round(chunk*(0.6+random()*0.9)));
                    grains.push({age:0,length,head:grainOrigin+(random()-0.5)*source.length*chaos,
                        speed:pow(2,(random()-0.5)*chaos*3)*(random()<chaos*0.5?-1:1)});
                    grainCountdown=max(30,round(length/(2.5+repeat*2)));
                }
                for(let n=grains.length-1;n>=0;n--) {
                    const grain=grains[n],window=0.5-0.5*cos(tau*grain.age/grain.length);
                    value+=read(grain.head)*window*0.8;grain.head+=grain.speed;
                    if(++grain.age>=grain.length)grains.splice(n,1);
                }
            } else if(mode===6) {
                // Retrigger a complete captured phrase inside a longer packet.
                const phrase=max(55,round(chunk/(1+round(repeat*5)))),position=j%phrase;
                value=read(anchor+position*(0.65+speed*0.35))*min(1,position/12,(phrase-position)/12);
                value*=0.6+0.4*exp(-position/(phrase*0.25));
            } else {
                // Retain the measured partial levels while their phases continue across packets.
                for(const partial of frozen) {
                    partial.phase+=tau*partial.frequency*(1+chaos*0.012*sin(tau*3*t))/rate;
                    value+=sin(partial.phase)*partial.gain;
                }
            }
            if(i%hold===0)sample=round(value*steps)/steps;
            // A short DC blocker prevents flipped sign bits and data pulses shifting the baseline.
            dc+=(sample-dc)*0.001;
            out[i]=skip?0:(sample-dc)*0.85;
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}
