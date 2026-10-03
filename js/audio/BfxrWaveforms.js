// Bfxr's oscillator palette for continuous-pitch engines. IDs match Bfxr;
// each renderer owns its noise state, so saved sounds replay deterministically.
class BfxrWaveforms {
    static choices = [
        ['Triangle','A soft triangular wave.',4],['Sin','A pure sine wave.',2],
        ['Square','A hollow pulse.',0],['Saw','A bright sawtooth.',1],
        ['Breaker','A curved, broken tooth.',8],['Tan','A sharply distorted tangent.',6],
        ['Whistle','A sine with a high overtone.',7],['White','Broadband noise.',3],
        ['Voice','Bfxr’s sampled vocal wave.',11],['Bitnoise','Periodic one-bit noise.',9],
        ['Rasp','Bfxr’s granular wavetable.',5],['FMSyn','Bfxr’s FM wavetable.',10]
    ];
    static blep(phase,step) {
        if(phase<step){const t=phase/step;return t+t-t*t-1;}
        if(phase>1-step){const t=(phase-1)/step;return t*t+t+t+1;}
        return 0;
    }
    static create(type,seed=0.5) {
        let state=(Math.round(seed*0xffffffff)|0)||1;
        const random=()=>{state^=state<<13;state^=state>>>17;state^=state<<5;return (state>>>0)/2147483648-1;};
        let previous=1,cell=-1,white=0,bits=((state^0x4a35)&0x7fff)||1,bit=0.5;
        const table=type===5?AKWF.granular_0044:type===10?AKWF.fmsynth_0012:type===11?AKWF.hvoice_0012:null;
        return (phase,step)=>{
            if(phase<previous){cell=-1;const feed=(bits>>1&1)^(bits&1);bits=(bits>>1)|(feed<<14);bit=(~bits&1)-0.5;}
            previous=phase;
            if(table){const pos=phase*256,i=Math.floor(pos);return (table[i]+(table[(i+1)%256]-table[i])*(pos-i))/32768-1;}
            switch(type){
                case 0:return (phase<0.5?1:-1)+this.blep(phase,step)-this.blep((phase+0.5)%1,step);
                case 1:return 2*phase-1-this.blep(phase,step);
                case 3: {const next=Math.floor(phase*32);if(next!==cell){cell=next;white=random();}return white;}
                case 4:return 1-4*Math.abs(phase-0.5);
                case 6:return Math.max(-3,Math.min(3,Math.tan(Math.PI*phase)))/3;
                case 7:return .75*Math.sin(phase*2*Math.PI)+(step*20<.5?.25*Math.sin(phase*40*Math.PI):0);
                case 8:return 2*(Math.abs(1-2*phase*phase)-.609475708);
                case 9:return bit;
                default:return Math.sin(phase*2*Math.PI);
            }
        };
    }
}
