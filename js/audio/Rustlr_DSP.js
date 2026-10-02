// Surface friction gathers elastic tension, then releases as slips and folds.
// Each material has its own compliance and loss; no oscillator supplies a tone.
class Rustlr_DSP {
    static materials=[
        {cutoff:4200,soft:0.35,highpass:0.65,crease:0.85,stick:0.5,flex:720},
        {cutoff:950,soft:1,highpass:0.2,crease:0.08,stick:0.15,flex:180},
        {cutoff:1900,soft:0.65,highpass:0.32,crease:0.38,stick:1,flex:330},
        {cutoff:6400,soft:0.25,highpass:0.72,crease:1.1,stick:0.6,flex:1150},
        {cutoff:12500,soft:0.06,highpass:0.92,crease:1.35,stick:0.3,flex:2600},
        {cutoff:4500,soft:0.15,highpass:0.55,crease:0.5,stick:0.2,flex:1500}
    ];

    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate, duration=value('duration',0.65,0.08,3);
        const frames=Math.round(duration*rate), out=new Float32Array(frames);
        const kind=Math.round(value('material',0,0,5)), material=this.materials[kind];
        const gesture=Math.round(value('gesture',1,0,3)), grain=value('grain',0.45), density=value('density',0.5);
        const motion=value('motion',0,-1,1), pressure=value('pressure',0.5), brightness=value('brightness',0.5);
        const folds=Math.round(value('folds',3,1,12)), random=SoundDSP.rng(value('seed',0.5));
        const sin=Math.sin, exp=Math.exp, pow=Math.pow, abs=Math.abs, min=Math.min, max=Math.max;
        const round=Math.round, floor=Math.floor, pi=Math.PI;
        const cutoff=material.cutoff*(0.22+brightness*1.18)/(1+grain*0.65)*(0.8+pressure*0.4);
        const filter=1-exp(-2*pi*cutoff/rate), slowFilter=1-exp(-2*pi*max(60,cutoff*0.13)/rate);
        const flexFilter=1-exp(-2*pi*material.flex*(0.7+pressure*0.8)/rate);
        const grainFrames=max(8,round((0.0007+grain*grain*0.023)*(1+material.soft)*rate));
        const count=max(8,round(duration*(48+density*780)/(1+grain*1.4)));
        const clusterCount=folds+2, centers=[];
        for(let i=0;i<clusterCount;i++) centers.push((i+0.2+random()*0.6)/clusterCount);
        const normalizer=1/Math.sqrt(1+count*grainFrames/frames*0.12);
        const gain=(0.24+pressure*0.76)*normalizer*2;
        const addGrain=(start,length,strength,crease)=>{
            let low=0, slow=0, flex=0, previousFlex=0;
            for(let j=0;j<length && start+j<frames;j++) {
                const noise=random()*2-1;
                low+=(noise-low)*filter;
                slow+=(low-slow)*slowFilter;
                flex+=(low-flex)*flexFilter;
                const age=j/length;
                // Compliant folds bend for longer; thin film releases abruptly.
                const attack=crease ? 0.025+material.soft*0.22 : 0.5;
                const window=crease ? min(1,age/attack)*exp(-age*(5-material.soft*2))
                    : sin(pi*age)*sin(pi*age);
                const surface=low-slow*material.highpass;
                const bending=(flex-previousFlex)*rate/(material.flex*2*pi);
                out[start+j]+=(surface+(crease?bending*(0.5+material.soft):0))*window*strength;
                previousFlex=flex;
            }
        };
        for(let i=0;i<count;i++) {
            let position;
            if(kind===5) {
                // Zip teeth follow the pull's changing speed, with small seeded defects.
                position=pow((i+0.25+random()*0.5)/count,1.35-motion*0.35);
            } else {
                const center=centers[floor(random()*clusterCount)];
                position=max(0,min(0.96,center+(random()+random()-1)*(0.035+density*0.24)));
            }
            const length=max(6,round(grainFrames*(0.45+random()*1.1)));
            const start=round(position*(frames-length));
            addGrain(max(0,start),length,gain*(0.16+random()*0.3)*(kind===5?1.4:1),false);
        }
        for(let fold=0;fold<folds;fold++) {
            const position=(fold+0.3+random()*0.45)/folds;
            const length=max(8,round((0.003+grain*0.022+material.soft*0.016)*rate*(0.65+random()*0.65)));
            const start=max(0,round(position*(frames-length)));
            addGrain(start,length,gain*(0.42+random()*0.45)*material.crease,true);
        }
        // Elastic loading and release modulate the friction, especially for leather.
        // Pressure raises the breakaway force and makes a slip last longer.
        const slipLoss=exp(-1/((0.0015+material.soft*0.017)*(0.6+pressure)*rate));
        let friction=0, frictionSlow=0, shear=0, slip=0, motionLow=0;
        let breakaway=0.7+random()*0.6;
        for(let i=0;i<frames;i++) {
            const position=i/(frames-1), arch=max(0,sin(pi*position));
            friction+=(random()*2-1-friction)*filter;
            frictionSlow+=(friction-frictionSlow)*slowFilter;
            motionLow+=(random()*2-1-motionLow)*0.0012;
            const speed=(0.3+pow(arch,0.6))*(0.7+min(0.8,abs(motionLow)*12));
            shear+=speed*(30+density*130)/rate/(0.6+pressure*material.stick*2);
            if(shear>breakaway) {
                shear-=breakaway;
                slip+=0.45+pressure*material.stick*1.5;
                breakaway=0.65+random()*0.8;
            }
            slip*=slipLoss;
            const bed=(friction-frictionSlow*material.highpass)*gain*(0.07+density*0.12)
                *(0.6+material.soft*1.3)*speed*(0.45+material.stick*slip+shear*0.35);
            let envelope;
            if(gesture===0) envelope=pow(arch,0.35)*exp(-position*4.5)*2;
            else if(gesture===1) envelope=pow(arch,0.7)*(0.55+0.45*abs(sin(pi*2*position)));
            else if(gesture===2) envelope=pow(arch,0.45);
            else envelope=pow(arch,0.5)*(0.2+0.8*abs(sin(pi*folds*position)));
            const travel=exp(motion*(position-0.5)*5-abs(motion)*1.4);
            out[i]=(out[i]+bed)*envelope*travel;
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
