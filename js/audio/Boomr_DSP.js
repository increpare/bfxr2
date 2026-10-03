// Pressure, turbulent gas, ground/shell transmission and diffuse reflections.
// Each release mechanism has its own timing and spectrum; there is no shared snap.
class Boomr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.5,0.12,5),frames=Math.round(rate*duration);
        const out=new Float32Array(frames),size=value('size',0.5),pressure=value('pressure',0.7),blast=value('blast',0.65);
        const debris=value('debris',0.35),spread=value('spread',0.5),tail=value('tail',0.45),muffle=value('muffle',0.15);
        const mechanism=Math.round(value('mechanism',0,0,7)),space=value('space',0.25);
        const random=SoundDSP.rng(value('seed',0.5)),exp=Math.exp,min=Math.min,pow=Math.pow,sin=Math.sin;
        const tau=2*Math.PI,coefficient=hz=>1-exp(-tau*hz/rate);
        const types=[
            {front:1,gas:1,body:1,decay:1,brightness:1},
            {front:0.55,gas:1.3,body:0.8,decay:1.75,brightness:0.65},
            {front:1.5,gas:0.2,body:1.6,decay:1.5,brightness:0.08},
            {front:1.1,gas:0.65,body:1.8,decay:1.45,brightness:0.4},
            {front:0.7,gas:0.65,body:1.5,decay:0.8,brightness:0.5},
            {front:0.6,gas:0.5,body:0.22,decay:0.2,brightness:1.5},
            {front:0.35,gas:1.6,body:0.3,decay:2,brightness:2.5},
            {front:0.9,gas:0.15,body:2.2,decay:0.55,brightness:0.15}
        ];
        const type=types[mechanism];
        const gas=value('gas',0.25),aftershock=value('aftershock',0.25),rubbleSize=value('rubbleSize',0.5);
        const events=[{time:mechanism===7 ? 0.08+size*0.07 : 0.007,gain:1}];
        if(mechanism===4) for(let j=0;j<5;j++) events.push({time:duration*(0.12+j*0.12)*(0.8+random()*0.3),gain:0.75-j*0.09});
        if(mechanism===2) for(let j=0;j<3;j++) events.push({time:0.06+(0.1+size*0.18)*pow(1.42,j),gain:0.44*pow(0.63,j)});
        const pressureDecay=(0.024+size*0.18)*type.decay;
        const gasDecay=(0.022+duration*(0.045+tail*0.28))*type.decay;
        const frontTime=(0.0014+size*0.01)*(mechanism===2?2.5:mechanism===5?0.45:1);
        const lowRate=coefficient(40+120*(1-size)),midRate=coefficient(200+650*(1-size));
        const dcRate=coefficient(15),motionRate=coefficient(4+10*(1-size));
        for(const event of events) {
            const start=Math.round(event.time*rate);
            let low=0,mid=0,high=0,dc=0,drift=0,wind=0,gasLow=0,gasDC=0,shellPhase=0;
            for(let i=start;i<frames;i++) {
                const t=(i-start)/rate,n=random()*2-1,n2=random()*2-1;
                low+=lowRate*(n-low);mid+=midRate*(n-mid);dc+=dcRate*(low-dc);
                drift+=motionRate*(n2-drift);
                gasLow+=lowRate*(n2-gasLow);gasDC+=dcRate*(gasLow-gasDC);
                const cooling=exp(-t/(gasDecay*0.65));
                const highRate=coefficient(140+(650+8500*pow(1-size,2))*type.brightness*cooling);
                high+=highRate*(n2-high);wind+=coefficient(85+260*cooling)*(n2-wind);
                const q=t/frontTime,front=(1-q)*exp(-q);
                const pressureBody=(low-dc)*5.5*exp(-t/pressureDecay);
                const gasAttack=mechanism===1?(1-exp(-t/(0.026+size*0.08))):1-exp(-t/0.002);
                const billow=0.8+Math.abs(drift)*6;
                const plume=((high-wind)*0.65+wind*3.2)*exp(-t/gasDecay)*gasAttack*billow;
                const rollingSource=mechanism===1?gasLow-gasDC:low-dc;
                const roll=rollingSource*4.2*exp(-t/(0.05+duration*(0.08+tail*0.25)))*(1-exp(-t/0.028));
                let transmission=0;
                if(mechanism===1) {
                    // A short hollow fuel container flexing as it opens.
                    shellPhase+=tau*(95+170*(1-size))*(1-0.14*(1-exp(-t/0.04)))/rate;
                    transmission=(sin(shellPhase)+0.23*sin(shellPhase*2.37))*exp(-t/(0.018+size*0.045))*0.2;
                } else if(mechanism===2) {
                    // Cavitation re-expansions, seeded at aperiodic spacings above.
                    transmission=(1-t/(frontTime*2))*exp(-t/(frontTime*2))*0.9;
                } else if(mechanism===3) {
                    transmission=(mid-low)*5.5*exp(-t/(0.08+size*0.2))*(1-exp(-t/0.012));
                }
                out[i]+=event.gain*(pressure*(front*type.front+pressureBody*type.body+transmission)
                    +blast*type.gas*plume+tail*type.body*roll)*0.8;
            }
        }
        // A gas jet has an audible opening and several uneven billows, rather
        // than sharing the detonation's instantaneous noise envelope.
        const gasRandom=SoundDSP.rng(value('seed',0.5)*0.71+0.193);
        const jetDelay=mechanism===6 ? 0.015 : mechanism===1 ? 0.045 : 0.07+size*0.045;
        const jetLife=(0.1+duration*(0.12+tail*0.3))*(mechanism===6?1.5:mechanism===2?0.35:mechanism===5?0.12:1);
        const gasLowRate=coefficient(50+80*(1-size));
        const gasHighRate=coefficient(mechanism===2 ? 170 : 700+4700*pow(1-size,0.65));
        let jetLow=0,jetHigh=0,jetMotion=0;
        for(let i=0;i<frames;i++) {
            const t=i/rate-jetDelay;
            const n=gasRandom()*2-1;
            jetLow+=gasLowRate*(n-jetLow);jetHigh+=gasHighRate*(n-jetHigh);
            jetMotion+=coefficient(13)*(gasRandom()*2-1-jetMotion);
            if(t>=0 && gas>0) {
                const opening=(1-exp(-t/(0.02+size*0.035)));
                const envelope=opening*exp(-t/jetLife);
                const billow=0.48+Math.abs(jetMotion)*9+0.25*pow(sin(t*(11+size*9)),2);
                out[i]+=gas*(mechanism===5?0.2:1)*envelope*billow*((jetHigh-jetLow)*1.9+jetLow*2.2);
            }
            if(mechanism===7 && t+jetDelay<events[0].time) {
                const u=(t+jetDelay)/events[0].time;
                out[i]+=(jetHigh-jetLow)*blast*pow(u,3)*0.65;
            }
        }
        // Secondary fronts travel through heavy material. Separate random streams
        // keep their placement stable when the user changes gas or debris level.
        const shockRandom=SoundDSP.rng(value('seed',0.5)*0.61+0.317);
        const shockCount=2+Math.round(aftershock*4);
        for(let event=0;event<shockCount && aftershock>0;event++) {
            const arrival=0.12+duration*(0.04+event*0.115)*(0.8+shockRandom()*0.4);
            const start=Math.round(arrival*rate),life=(0.025+size*0.1)*(0.7+shockRandom()*0.6);
            const strength=aftershock*pow(0.7,event)*(0.75+size*0.8)*(mechanism===5?0.06:1);
            let low=0,dc=0;
            const lp=coefficient(55+90*(1-size));
            for(let i=start;i<Math.min(frames,start+Math.ceil(life*8*rate));i++) {
                const t=(i-start)/rate,q=t/(0.006+size*0.016);
                low+=lp*(shockRandom()*2-1-low);dc+=coefficient(12)*(low-dc);
                out[i]+=strength*((1-q)*exp(-q)*0.8+(low-dc)*7*(1-exp(-t/0.009))*exp(-t/life));
            }
        }
        const pieces=Math.round(debris*48);
        for(let piece=0;piece<pieces;piece++) {
            const start=Math.floor((0.018+rubbleSize*0.055+random()*duration*(0.04+spread*0.8))*rate);
            const chunk=random(),life=(0.002+chunk*0.025)*(0.25+rubbleSize*2.5),gain=debris*(0.1+random()*0.3)*(0.7+rubbleSize);
            const length=min(frames-start,Math.ceil(life*rate*7)),damping=exp(-1/(life*rate));
            const dustRate=coefficient((1200+random()*8500)*pow(1-rubbleSize*0.94,2)),bodyRate=coefficient(45+random()*600*pow(1-rubbleSize*0.85,2));
            let dust=0,body=0,envelope=1;
            for(let j=0;j<length;j++) {
                const noise=random()*2-1;
                dust+=dustRate*(noise-dust);body+=bodyRate*(noise-body);
                const q=(j/rate)/(0.0004+rubbleSize*0.009);
                out[start+j]+=(dust*(1-rubbleSize*0.7)+body*(0.5+rubbleSize*5)+(1-q)*exp(-q)*rubbleSize)*envelope*gain;envelope*=damping;
            }
        }
        if(space>0) {
            // Three unequal, damped recirculating paths smear the pressure field.
            const delays=[0.071,0.113,0.173].map(t=>new Float32Array(Math.max(1,Math.round(t*(0.6+space*1.8)*rate))));
            const heads=[0,0,0],smoothed=[0,0,0];
            for(let i=0;i<frames;i++) {
                const input=out[i];let echo=0;
                for(let j=0;j<3;j++) {
                    const buffer=delays[j],head=heads[j],sample=buffer[head];
                    smoothed[j]+=0.08*(sample-smoothed[j]);
                    buffer[head]=input*0.36+smoothed[j]*(0.2+space*0.48);
                    echo+=smoothed[j];heads[j]=(head+1)%buffer.length;
                }
                out[i]+=echo*space*0.7;
            }
        }
        const finalRate=coefficient(80+15000*pow(1-muffle,3));
        let filtered=0;
        for(let i=0;i<frames;i++){filtered+=finalRate*(out[i]-filtered);out[i]=filtered;}
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
