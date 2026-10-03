// Wheels traverse a shared, multiscale surface. Contact remains continuous;
// circumference defects and ground joints change the load instead of firing tones.
class Rollr_DSP {
    static surfaces=[
        {texture:220,grit:2200,body:0.45,joints:0},
        {texture:100,grit:1600,body:0.8,joints:1},
        {texture:340,grit:4600,body:0.65,joints:0},
        {texture:65,grit:1000,body:1.25,joints:0.2}
    ];

    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',2,0.2,5),length=Math.round(rate*duration);
        const out=new Float32Array(length),random=SoundDSP.rng(value('seed',0.5));
        const material=Math.round(value('material',0,0,3)),wheels=Math.round(value('wheels',2,1,6));
        const surface=this.surfaces[Math.round(value('surface',2,0,3))];
        const speed=value('speed',0.5),roughness=value('roughness',0.45),size=value('size',0.5);
        const hardness=value('hardness',0.6),slowing=value('slowing',0.35);
        const exp=Math.exp,pow=Math.pow,min=Math.min,max=Math.max,floor=Math.floor,abs=Math.abs,tau=Math.PI*2;
        const trackLength=8192,mask=trackLength-1;
        const ground=Float32Array.from({length:trackLength},()=>random()*2-1);
        const grit=Float32Array.from({length:trackLength},()=>random()*2-1);
        const sample=(track,position)=>{
            const index=floor(position),fraction=position-index;
            return track[index&mask]*(1-fraction)+track[(index+1)&mask]*fraction;
        };
        const rotation=(0.8+speed*15)/(0.8+size*0.8);
        const bodyFrequency=(110+650*pow(1-size,2))*[1,0.7,1.6,0.45][material];
        // Two lossy body bands keep wood, stone and metal distinct without a pitched carrier.
        const bodyCoefficient=1-exp(-tau*bodyFrequency/rate);
        const upperCoefficient=1-exp(-tau*bodyFrequency*[3.7,2.3,5.9,2][material]/rate);
        const subCoefficient=1-exp(-tau*35/rate);
        const brightness=(0.3+hardness*0.7)*[0.7,0.5,1,0.24][material];
        const contacts=Array.from({length:wheels},(_,index)=>({
            phase:random(),offset:index*0.29+random()*0.12,
            width:0.028+random()*0.025,weight:0.8+random()*0.4,
            body:0,upper:0,sub:0,air:0,previous:0,slip:0
        }));
        const gain=1/Math.sqrt(wheels);
        let distance=64+random()*128;
        for(let i=0;i<length;i++) {
            const u=i/(length-1),velocity=max(0.025,1-slowing*pow(u,1.1)*0.975);
            const travel=rotation*velocity;
            distance+=travel/rate;
            const airCoefficient=1-exp(-tau*min(14500,(250+travel*surface.grit*0.6)*(0.3+hardness*0.7))/rate);
            let mixed=0;
            for(const wheel of contacts) {
                const position=distance-wheel.offset;
                const turns=position+wheel.phase;
                const phase=turns-floor(turns);
                const defectDistance=min(phase,1-phase);
                // A broad flat spot returns once a revolution, under irregular surface load.
                const defect=exp(-pow(defectDistance/wheel.width,2));
                const undulation=sample(ground,position*7.3);
                const grain=sample(ground,position*surface.texture);
                const fine=sample(grit,position*surface.grit);
                const load=max(0.12,0.7+roughness*undulation*0.7);
                const jointPosition=position*1.7;
                const jointPhase=jointPosition-floor(jointPosition);
                const joint=exp(-pow(min(jointPhase,1-jointPhase)/0.022,2))*surface.joints;
                const bumps=defect*(0.09+roughness*0.08)+joint*roughness*0.16;
                const friction=(0.004+roughness*0.31)*load;
                const excitation=grain*(friction+bumps);
                wheel.sub+=(excitation-wheel.sub)*subCoefficient;
                wheel.body+=(excitation-wheel.body)*bodyCoefficient;
                wheel.upper+=(excitation-wheel.upper)*upperCoefficient;
                // Tiny losses of grip scrape briefly at sharp changes in the ground profile.
                const slope=abs(undulation-wheel.previous)*rate/max(1,travel);
                wheel.previous=undulation;
                wheel.slip+=(min(1,slope*0.045)*roughness-wheel.slip)*0.008;
                wheel.air+=(fine-wheel.air)*airCoefficient;
                const rumble=(wheel.body-wheel.sub)*surface.body*(1.6+size);
                const scrape=(wheel.upper-wheel.body)*brightness*1.8;
                const contact=wheel.air*brightness*(friction*0.28+bumps*0.9+wheel.slip*0.028);
                mixed+=(rumble+scrape+contact)*wheel.weight;
            }
            const window=min(1,i/(rate*0.024),(length-1-i)/(rate*0.055));
            out[i]=mixed*gain*window*pow(velocity,0.72)*2.6;
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
