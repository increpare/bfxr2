// Repeated, lost and quantized oscillator fragments mimic a damaged sound buffer.
class Glitchr_DSP {
    static render(p){
        const {sin,pow,round,max,min,PI}=Math;
        const v=(k,d,a=0,b=1)=>Number.isFinite(p[k])?SoundDSP.clamp(p[k],a,b):d;
        const rate=SoundDSP.rate,duration=v('duration',0.7,0.08,4),out=new Float32Array(round(duration*rate));
        const random=SoundDSP.rng(v('seed',0.5)),tau=PI*2,base=80*pow(2,v('pitch',0.5)*5);
        const chunk=max(80,round((0.006+v('fragment',0.3)*0.14)*rate));
        const repeat=v('repeat',0.4),chaos=v('chaos',0.5),dropout=v('dropout',0.2),crush=v('crush',0.3);
        const hold=1+round(v('rate',0.3)*27),steps=pow(2,13-round(crush*10));
        let frequency=base,origin=0,phase=0,sample=0;
        for(let start=0;start<out.length;start+=chunk){
            const fresh=random()>repeat||start===0,skip=random()<dropout*0.86&&start>0;
            if(fresh){frequency=base*pow(2,(random()-0.5)*chaos*4);origin=random()*tau;}
            phase=origin;
            const gain=0.4+random()*0.25,length=min(chunk,out.length-start),edge=min(100,length/4);
            for(let j=0;j<length;j++){
                phase+=tau*min(8500,frequency)/rate;
                if(j%hold===0)sample=round((sin(phase+chaos*sin(phase*1.71))+0.2*sin(phase*2))*steps)/steps;
                const envelope=min(1,j/edge,(length-1-j)/edge);
                out[start+j]=skip?0:sample*gain*envelope;
            }
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}
