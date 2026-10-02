// Eight firing mechanisms share gesture controls, but not a common oscillator
// body or noisy attack. Frequencies and feedback stay bounded before finishing.
class Pewpr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',0.7,0.12,5),frames=Math.round(duration*rate),out=new Float32Array(frames);
        const kind=Math.round(value('kind',0,0,7)),shots=Math.round(value('shots',1,1,8));
        const pitch=value('pitch',0.55),sweep=value('sweep',-0.65,-1,1),charge=value('charge',0),punch=value('punch',0.65);
        const body=value('body',0.45),recoil=value('recoil',0.2),grit=value('grit',0.1);
        const character=value('character',0.5),modulation=value('modulation',0.45);
        const random=SoundDSP.rng(value('seed',0.5)),sin=Math.sin,exp=Math.exp,pow=Math.pow,min=Math.min,max=Math.max;
        const tau=2*Math.PI,base=65*pow(2,pitch*5),chargeTime=duration*charge*0.58;
        const spacing=(duration-chargeTime)*0.62/max(1,shots-1),gain=0.75/Math.sqrt(1+0.2*(shots-1));
        const coefficient=hz=>1-exp(-tau*hz/rate);
        if(chargeTime>0) {
            let phase=0,second=0,low=0;
            for(let i=0;i<min(frames,Math.ceil(chargeTime*rate));i++) {
                const t=i/rate,u=t/chargeTime,n=random()*2-1;
                phase+=tau*min(4200,base*(0.2+u*u)*(kind===7?0.15:1))/rate;
                second+=tau*(15+modulation*45)*u/rate;low+=0.018*(n-low);
                const chargeTone=kind===5?sin(phase+sin(second)*2):kind===7?low*4+sin(phase)*0.45
                    :sin(phase+sin(second)*modulation*0.6)+0.18*sin(phase*1.99);
                out[i]+=chargeTone*charge*u*u*min(1,t/0.01)*0.13;
            }
        }
        for(let shot=0;shot<shots;shot++) {
            const firing=0.006+chargeTime+shot*spacing,start=Math.floor(firing*rate);
            if(start>=frames) continue;
            const available=(frames-start)/rate;
            const bodyTime=max(0.008,(duration-chargeTime)*(0.06+body*0.27)/Math.sqrt(shots));
            const detune=1+(random()-0.5)*0.025,phaseOffset=random()*tau;
            let phase=phaseOffset,second=0,third=0,subPhase=0,low=0,mid=0,breath=0;
            let cavityA=0,cavityB=0,previousA=0,previousB=0;
            const echoLength=Math.max(1,Math.round(rate*(0.011+character*0.06)));
            const echo=new Float32Array(echoLength);let echoHead=0,echoLow=0;
            const coilCount=4+Math.round(character*9),coilTime=0.02+bodyTime*0.42;
            const coilTimes=Array.from({length:coilCount},(_,j)=>coilTime*(1-pow(1-j/coilCount,1.4+modulation*2)));
            let coilIndex=0,coilEnvelope=0,coilPhase=0,coilFrequency=base;
            for(let i=start;i<frames;i++) {
                const age=(i-start)/rate,u=age/bodyTime,n=random()*2-1;
                low+=coefficient(70+pitch*210)*(n-low);
                mid+=coefficient(600+character*2300)*(n-mid);
                breath+=coefficient(100+character*700)*(n-breath);
                const motion=sin(tau*(3+modulation*37)*age);
                const sweepMotion=kind===6?min(1,age/max(available*0.7,0.01)):(1-exp(-u))*2.6;
                const frequency=min(kind===1||kind===5?2100:5000,base*detune*pow(2,sweep*sweepMotion));
                phase+=tau*frequency/rate;
                second+=tau*min(6500,frequency*(1.003+character*0.027))/rate;
                third+=tau*(9+modulation*67)/rate;
                subPhase+=tau*(28+pitch*65)*(1+0.15*motion*modulation)/rate;
                const envelope=exp(-u),attack=min(1,age/0.0007);
                let sound=0;
                if(kind===0) {
                    // A coherent optical packet with a short dispersive echo.
                    const chirp=phase+(0.05+modulation*1.1)*sin(third)*exp(-u*0.6)+character*sin(second*0.5);
                    sound=(sin(chirp)+character*0.24*sin(2*chirp))*envelope*(0.25+body*0.7);
                    sound+=punch*sin(phase*(1.4+character*0.8))*exp(-age/0.005)*0.55;
                    sound+=grit*(mid-low)*exp(-age/(bodyTime*0.4));
                } else if(kind===1) {
                    // Noninteger FM and sputtering confinement make plasma wobble.
                    const fm=(0.4+character*4.5)*(0.65+0.35*motion);
                    const packet=0.65+0.35*sin(third+sin(third*0.37)*modulation*3);
                    sound=(sin(phase+fm*sin(second*0.501+modulation*sin(third)))
                        +0.23*sin(phase*1.498))*packet*envelope*(0.35+body*0.7);
                    sound+=(mid-low)*grit*envelope*1.8+punch*low*exp(-age/0.012)*2;
                } else if(kind===2) {
                    // No carrier sweep: a broadband pressure release excites a barrel.
                    const shockTime=0.0008+character*0.0035,q=age/shockTime;
                    const barrel=(mid-low)*exp(-age/(0.012+bodyTime*0.28));
                    sound=punch*(1-q)*exp(-q)*1.8+barrel*(0.5+grit*2.5);
                    // Pellet groups arrive separately as dispersion increases.
                    const scatterAge=age-(0.001+modulation*0.025);
                    if(scatterAge>0){const scatterQ=scatterAge/shockTime;
                        sound+=punch*(1-scatterQ)*exp(-scatterQ)*0.9;}
                    sound+=low*exp(-age/(0.026+bodyTime*0.45))*body*5;
                    const action=age-(0.04+character*0.09);
                    if(action>0) sound+=recoil*(mid+sin(subPhase)*0.15)*exp(-action/(0.004+modulation*0.013));
                    const pelletGate=pow(0.5+0.5*sin(tau*(45+modulation*180)*age),2);
                    sound*=1-modulation*0.85+modulation*0.85*pelletGate;
                } else if(kind===3) {
                    // Independently dispersed chirps; higher rays fan away faster.
                    const dispersion=character*base*bodyTime*(age-bodyTime*(1-exp(-u)));
                    const flutter=modulation*sin(third)*1.4;
                    sound=(sin(phase+dispersion*2.1+flutter)+0.55*sin(second*1.417+dispersion*5.7-flutter)
                        +0.3*sin(phase*2.137-dispersion*3.2))*envelope;
                    sound*=0.3+body*0.5;
                    sound*=0.7+0.3*sin(third+modulation*sin(third*0.47));
                    sound+=punch*(mid-low)*exp(-age/0.0025)*0.5;
                    sound+=grit*(mid-low)*envelope*(0.2+0.6*modulation);
                } else if(kind===4) {
                    // Sequential coils accelerate toward a final discharge.
                    if(coilIndex<coilTimes.length&&age>=coilTimes[coilIndex]) {
                        coilEnvelope=0.45+0.55*coilIndex/coilCount;coilPhase=0;
                        coilFrequency=min(7000,base*(0.55+coilIndex*(0.25+modulation*0.45)));
                        coilIndex++;
                    }
                    coilPhase+=tau*coilFrequency/rate;
                    coilEnvelope*=exp(-1/(rate*(0.0012+character*0.003)));
                    sound=sin(coilPhase+modulation*sin(coilPhase*0.5))*coilEnvelope*(0.4+punch);
                    const discharge=age-coilTime;
                    if(discharge>0) {
                        const q=discharge/(0.003+character*0.006);
                        sound+=punch*(1-q)*exp(-q)+grit*(mid-low)*exp(-discharge/0.018);
                        sound+=recoil*sin(subPhase)*exp(-discharge/(bodyTime*0.6))*0.6;
                    }
                    sound+=sin(phase)*envelope*body*0.08;
                } else if(kind===5) {
                    // A glottal source feeds two moving vocal cavities.
                    const glottis=sin(phase*(0.17+character*0.12)+modulation*sin(third)*0.8);
                    const source=glottis*(0.65+0.35*sin(phase*0.46))+grit*(mid-breath)*0.4;
                    const f1=220+character*750+modulation*160*motion;
                    const f2=800+character*1600+modulation*350*sin(third*0.71);
                    const radius=0.94,drive=0.08;
                    const a=source*drive+2*radius*Math.cos(tau*f1/rate)*cavityA-radius*radius*previousA;
                    const b=source*drive+2*radius*Math.cos(tau*f2/rate)*cavityB-radius*radius*previousB;
                    previousA=cavityA;cavityA=a;previousB=cavityB;cavityB=b;
                    sound=Math.tanh((a+b*0.6)*0.3)*(1-exp(-age/0.008))*envelope*(0.5+body);
                    sound+=punch*(mid-low)*exp(-age/0.006)*0.45;
                } else if(kind===6) {
                    // A long, smooth field with beating detuned carriers and release.
                    const hold=min(available*0.78,bodyTime*(1.8+body*1.5));
                    const beamEnvelope=(1-exp(-age/0.018))*exp(-pow(age/max(hold,0.005),6));
                    const interference=0.65+0.35*sin(third*(0.15+modulation)*2);
                    sound=(sin(phase)+sin(second+character*sin(third)*0.4)*0.7
                        +0.25*sin(phase*1.501+sin(third)*modulation))*beamEnvelope*interference*0.5;
                    sound+=grit*(mid-low)*beamEnvelope*0.7;
                    sound+=punch*sin(phase)*exp(-age/0.008)*0.25;
                } else {
                    // A pressure well gathers inward, then collapses in a deep pulse.
                    const collapse=bodyTime*(0.4+character*1.2),inward=min(1,age/max(collapse,0.005));
                    const suction=pow(inward,2)*exp(-pow(age/max(collapse,0.005),6));
                    sound=(low*2+sin(subPhase*(1.2+character))*0.3)*suction;
                    const after=age-collapse;
                    if(after>0) {
                        const q=after/(0.006+character*0.018);
                        const pulse=(1-q)*exp(-q)*punch*1.6;
                        const fold=sin(subPhase+sin(third*0.25)*modulation*2);
                        sound+=pulse+(fold*0.35+low*grit*3)*exp(-after/(bodyTime*(0.6+body)));
                    }
                }
                // A low afterkick belongs to energy sources; ballistic and coil
                // weapons already produce their own mechanical return.
                if(kind!==2&&kind!==4&&kind!==7) {
                    const kickAge=age-bodyTime*0.7;
                    if(kickAge>0) sound+=recoil*sin(subPhase)*exp(-kickAge/(0.018+bodyTime*0.45))*min(1,kickAge/0.006)*0.3;
                }
                const delayed=echo[echoHead];echoLow+=0.25*(delayed-echoLow);
                echo[echoHead]=sound+(kind===6?0.3:0.12)*echoLow;
                echoHead=(echoHead+1)%echoLength;
                const echoGain=kind===3?0.35:kind===7?0.45:0.1;
                out[i]+=gain*(sound+echoLow*recoil*echoGain)*attack;
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}
