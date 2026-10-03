// Packet scheduling with frequency/phase coding, dropouts and radio echoes.
class Signlr_DSP {
    static render(p) {
        const {sin, exp, floor, round, min, max, PI} = Math;
        const value = (name, fallback, low=0, high=1) => Number.isFinite(p[name])
            ? min(high,max(low,p[name])) : fallback;
        const rate = SoundDSP.rate, tau = 2*PI;
        const duration = value('duration',1.4,0.15,5);
        const output = new Float32Array(round(duration*rate));
        const volume = value('masterVolume',0.5);
        if (volume===0) return SoundDSP.finish(output,0);
        const seed = value('seed',0.5), random = SoundDSP.rng(seed);
        const encoding = round(value('encoding',0,0,4));
        if(encoding===4)return this.pings(p);
        const carrier = 90*2**(value('carrier',0.55)*5.7);
        const deviation = value('deviation',0.35), drift = value('drift',0,-1,1);
        const interference = value('interference',0.08), corruption = value('corruption',0.08);
        const echo = value('echo',0.15), symbols = 4+176*value('symbols',0.4)**2;
        const symbolSamples = rate/symbols;
        const packets = round(value('packets',3,1,12));
        const slot = output.length/packets, active = slot*(1-value('gap',0.25,0,0.85));
        const edge = min(rate*0.005,active*0.12);
        const symbolEdge = min(rate*0.0007,symbolSamples*0.06);
        const delayA = round(rate*(0.073+seed*0.041)), delayB = round(delayA*1.79);
        let phase=random()*tau, lastSymbol=-1, lastPacket=-1, bit=1, symbolGain=1;
        let noiseLow=0, radioLow=0, phaseCode=0, scramble=0;
        let carrierNow=carrier*2**(-drift*0.5);
        const driftStep = 2**(drift/output.length);
        const heterodyneStep = tau*(carrier*1.013+37)/rate;
        let heterodyne=random()*tau;
        for(let i=0;i<output.length;i++) {
            const packet=min(packets-1,floor(i/slot)), local=i-packet*slot;
            const symbol=floor(local/symbolSamples), symbolPosition=local-symbol*symbolSamples;
            const unit=symbolPosition/symbolSamples;
            if(packet!==lastPacket || symbol!==lastSymbol) {
                lastPacket=packet; lastSymbol=symbol;
                // A four-symbol sync word precedes the seeded payload in every packet.
                bit=symbol<4 ? ((symbol+packet)%2?1:-1) : (random()<0.5?-1:1);
                symbolGain=random()<corruption*0.85?0.025:1;
                phaseCode=bit>0?0:PI;
                scramble=corruption*(random()*2-1);
            }
            let frequency=carrierNow;
            if(encoding===0) frequency*=2**(deviation*bit*0.7+scramble*0.2);
            if(encoding===2) frequency*=2**(deviation*(1-unit*2)+scramble*0.2);
            if(encoding===3) frequency*=1+deviation*0.3*bit;
            phase+=tau*min(14000,max(30,frequency))/rate;
            carrierNow*=driftStep;
            heterodyne+=heterodyneStep;
            const noise=random()*2-1;
            noiseLow+=(noise-noiseLow)*0.08;
            let encoded;
            if(encoding===1) encoded=sin(phase+phaseCode*(0.25+deviation*0.75));
            else if(encoding===2) encoded=sin(phase)*exp(-unit*(5+deviation*5));
            else if(encoding===3) encoded=sin(phase)*(0.62+0.38*sin(phase*0.037+bit));
            else encoded=sin(phase)+0.08*deviation*sin(phase*2);
            const packetEnvelope=max(0,min(1,local/edge,(active-local)/edge));
            const bitEnvelope=encoding===2 ? min(1,symbolPosition/symbolEdge)
                : 0.88+0.12*min(1,symbolPosition/symbolEdge,(symbolSamples-symbolPosition)/symbolEdge);
            const radio=(noise-noiseLow)*0.22+sin(heterodyne)*0.14;
            const squelch=0.4+0.6*packetEnvelope;
            let sample=encoded*0.52*symbolGain*packetEnvelope*bitEnvelope+radio*interference*squelch;
            // A narrow receiver rolls off the roughest static in radio mode.
            radioLow+=(sample-radioLow)*0.3;
            if(encoding===3) sample=radioLow;
            if(i>=delayA) sample+=output[i-delayA]*echo*0.38;
            if(i>=delayB) sample-=output[i-delayB]*echo*0.17;
            output[i]=sample;
        }
        return SoundDSP.finish(output,volume);
    }
    static pings(p) {
        const rate=SoundDSP.rate,tau=Math.PI*2;
        const number=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const duration=number('duration',1.4,.15,5),packets=Math.round(number('packets',2,1,12));
        const out=new Float32Array(Math.round(duration*rate));
        const rng=SoundDSP.rng(number('seed',.5));
        const root=170*2**(number('carrier',.55)*4.1),color=number('deviation',.15);
        const fall=number('gap',.5,0,.85),echo=number('echo',.4),drift=number('drift',0,-1,1);
        // Each seed describes one struck resonator, shared by the whole scan.
        const ratios=[1,2.01+rng()*.12,3.1+rng()*1.7,5.2+rng()*2.2];
        const weights=[.8,.06+color*.28,.03+color*.17,.02+color*.1];
        const ring=.045+(1-fall)*.6,step=duration/packets;
        const phases=ratios.map(()=>rng()*tau);
        for(let packet=0;packet<packets;packet++) {
            const start=Math.round(packet*step*rate),frequency=root*2**(drift*packet/Math.max(1,packets-1));
            for(let i=0;i<Math.min(rate*(ring*6),out.length-start);i++) {
                const t=i/rate,attack=1-Math.exp(-t/.0007);
                let sample=0;
                for(let h=0;h<ratios.length;h++) {
                    if(frequency*ratios[h]>18000)continue;
                    const phase=tau*frequency*ratios[h]*(t+color*.0008*(1-Math.exp(-t/.006)));
                    sample+=Math.sin(phase+phases[h])*weights[h]*Math.exp(-t*(1+h*1.4)/ring);
                }
                sample*=attack*.7;
                out[start+i]+=sample;
                for(let repeat=1;repeat<=3;repeat++) {
                    const target=start+i+Math.round(rate*(.062+number('seed',.5)*.055)*repeat);
                    if(target<out.length)out[target]+=sample*(echo*.52)**repeat;
                }
            }
        }
        return SoundDSP.finish(out,number('masterVolume',.5));
    }

}
