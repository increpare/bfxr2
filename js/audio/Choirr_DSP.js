// Independent band-limited vocal sources excite three vowel formants per singer.
class Choirr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,round,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,tau=PI*2,duration=value('duration',2.5,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        const random=SoundDSP.rng(value('seed',0.5)),voices=round(value('voices',6,1,12));
        const pitch=55*pow(2,value('pitch',0.5)*4),vowel=value('vowel',0.35);
        const detune=value('detune',0.4),swell=value('swell',0.5),breath=value('breath',0.1),motion=value('motion',0.4);
        const harmony=round(value('harmony',1,0,4));
        const chords=[[0],[0,4,7,12],[0,3,7,12],[0,7,12,19],[0,1,6,10]];
        const vowels=[[350,800,2300],[750,1150,2600],[300,2200,3100]];
        const vIndex=vowel<0.5?0:1,blend=vowel<0.5?vowel*2:(vowel-0.5)*2;
        const gain=1.9/Math.sqrt(voices),radii=[exp(-PI*85/rate),exp(-PI*120/rate),exp(-PI*190/rate)];
        for(let voice=0;voice<voices;voice++) {
            const note=chords[harmony][voice%chords[harmony].length];
            const frequency=pitch*pow(2,note/12+(random()-0.5)*detune*0.08);
            const formantScale=0.92+random()*0.16;
            const coeff=radii.map((r,k)=>2*r*cos(tau*(vowels[vIndex][k]*(1-blend)+vowels[vIndex+1][k]*blend)*formantScale/rate));
            const y1=[0,0,0],y2=[0,0,0],squares=radii.map(r=>r*r),gains=radii.map(r=>1-r);
            const initial=random()*tau,vibratoRate=4.2+random()*1.8;
            const onset=round(random()*motion*min(out.length*0.1,3000));
            let phase=random(),previous=0,previous2=0;
            for(let i=onset;i<out.length;i++) {
                const age=(i-onset)/(out.length-onset),t=i/rate;
                const step=frequency*(1+motion*0.009*sin(tau*vibratoRate*t+initial))/rate;
                phase+=step;if(phase>=1)phase-=1;
                let source=2*phase-1;
                // PolyBLEP softens the discontinuity before the throat filters.
                if(phase<step){const x=phase/step;source-=x+x-x*x-1;}
                else if(phase>1-step){const x=(phase-1)/step;source-=x*x+x+x+1;}
                source=source*(1-breath*0.7)+(random()*2-1)*breath*0.35;
                let resonant=0;
                for(let band=0;band<3;band++) {
                    const sample=gains[band]*(source-previous2)+coeff[band]*y1[band]-squares[band]*y2[band];
                    y2[band]=y1[band];y1[band]=sample;
                    resonant+=sample*(band===0?1.2:band===1?0.8:0.5);
                }
                previous2=previous;previous=source;
                const envelope=pow(max(0,sin(PI*age)),0.25+swell*2.7);
                out[i]+=(resonant+sin(tau*phase)*0.065)*envelope*gain*(0.9+motion*0.1*sin(tau*0.7*t+initial));
            }
        }
        return SoundDSP.finish(out,volume);
    }
}
