/*
    This file implements PureData DSP functions to operate on audio buffers.
*/

const PD_COSTABLESIZE = 2048;
const PD_UNITBIT32 = 1572864;  /* 3*2^19; bit 32 has place value 1 */
const PD_HIOFFSET = 1;
const PD_LOWOFFSET = 0;

var COSTABLENAME;

function generate_tables(){
    COSTABLENAME = new Float32Array(PD_COSTABLESIZE+1);
    for (let i = 0; i < PD_COSTABLESIZE; i++) {
        COSTABLENAME[i] = Math.cos(i * 2 * Math.PI / PD_COSTABLESIZE);
    }
    COSTABLENAME[0] = 1;
    COSTABLENAME[PD_COSTABLESIZE] = 1;
    COSTABLENAME[(PD_COSTABLESIZE/4)|0] = 0;
    COSTABLENAME[(3*PD_COSTABLESIZE/4)|0] = 0;
    COSTABLENAME[(PD_COSTABLESIZE/2)|0] = -1;
}

generate_tables();
var puredata_stream_length = 0;
function pd_set_stream_length_seconds(seconds){
    puredata_stream_length = seconds * SAMPLE_RATE;
}

// white noise signal (in the range from -1 to 1).
// https://pd.iem.sh/objects/noise~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.c#L372
function pd_noise(){
    var result = new Float32Array(puredata_stream_length);
    for (let i = 0; i < result.length; i++) {
        result[i] = Math.random() * 2 - 1;
    }
    return result;
}

function pd_clip(buffer, min, max){
    for (let i = 0; i < buffer.length; i++) {
        buffer[i] = Math.max(min, Math.min(buffer[i], max));
    }
    return buffer;
}

function pd_mul(buffer, multiplier){
    for (let i = 0; i < buffer.length; i++) {
        buffer[i] *= multiplier;
    }
    return buffer;
}

function pd_div(buffer, divisor){
    for (let i = 0; i < buffer.length; i++) {
        buffer[i] /= divisor;
    }
    return buffer;
}

function pd_add(buffer, addend){
    for (let i = 0; i < buffer.length; i++) {
        buffer[i] += addend;
    }
    return buffer;
}


function pd_constant_signal(value){
    var result = new Float32Array(puredata_stream_length);    
    result.fill(value);
    return result;
}

// lop one-pole low pass filter.
// https://pd.iem.sh/objects/lop~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_filter.c#L139
function pd_lop(buffer, filter_coeff_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let last =  buffer[0];
    
    for (let i = 0; i < buffer.length; i++) {
        let coef = filter_coeff_signal[i]*CONVERSION_FACTOR;
        if (coef > 1){
            coef = 1;
        }
        if (coef < 0){
            coef = 0;
        }
        last = coef * buffer[i] + (1-coef) * last;
        output_buffer[i] = last;
    }

    return output_buffer;    
}

// hip one-pole high pass filter.
// https://pd.iem.sh/objects/hip~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_filter.c#L9
function pd_hip(buffer, filter_coeff_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let last =  buffer[0];
    
    for (let i = 0; i < buffer.length; i++) {
        let f = filter_coeff_signal[i];
        let coef = 1 - f*CONVERSION_FACTOR;
        if (coef< 0){
            coef = 0;
        }
        else if (coef > 1){
            coef = 1;
        }
        
        if (coef < 1){
            const normal = 0.5*(1+coef);
            const cur = buffer[i] + coef*last;
            output_buffer[i] = normal*(cur-last);
            last = cur;
        }
        else {
            output_buffer[i] = buffer[i];
        }
    }

    return output_buffer;    
}


/* voltage-controlled band/low-pass filter
    1st
    signal - audio signal to be filtered.
    2nd
    signal - resonant frequency in Hz.
    3rd
    float - set Q.
*/
// https://pd.iem.sh/objects/vcf~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.c#L289
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.h#L131
function pd_vcf(buffer, res_freq_signal, q_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let re = 0;
    let im = 0;
    let addr=[0,0];
    
    for (let i = 0; i < buffer.length; i++) {
        let q = q_signal[i];
        let qinv = q>0 ? (1/q) : 0;
        let ampcorrect = 2-2/(q+2);
        let coefr=0;
        let coefi=0;
        let tab = COSTABLENAME;
        dphase=0;
        var tf_i = [0,0];
        let normhipart=0;//int
        let tabindex=0;

        
        var cf=0;
        var cfindx=0;
        var r=0;
        var oneminusr=0;

        cf = res_freq_signal[i]*CONVERSION_FACTOR
        if (cf<0){
            cf=0;
        }
        cfindx = cf*(PD_COSTABLESIZE/Math.PI*2)
        r = (qinv>0) ? (1 -cf*qinv) : 0;
        if (r<0){
            r=0;
        }
        oneminusr = 1-r;
        dphase = cfindx+PD_UNITBIT32;
        let tf_d = dphase;
        tabindex = tf_i[PD_HIOFFSET] & (PD_COSTABLESIZE-1);
        tf_i[PD_HIOFFSET] =  normhipart;
        let frac = tf_d - PD_UNITBIT32;
        let f1 = tab[tabindex];
        let f2 = tab[tabindex+1];
        coefr = r*(f1+frac*(f2-f1));

        tabindex += ((tabindex-((PD_COSTABLESIZE/4)|0)) & (PD_COSTABLESIZE-1));
        f1 = tab[tabindex];
        f2 = tab[tabindex+1];
        coefi = r*(f1+frac*(f2-f1));

        f1 = buffer[i];  // Fixed: use current sample instead of always buffer[0]
        re2 = re;
        re = ampcorrect*oneminusr*f1 + coefr*re2-coefi*im;
        im = coefi*re2+coefr*im;

        output_buffer[i] = re;
        //don't bother with multiple outputs...
        //output number 2 should be  the imaginary part.
    }

    return output_buffer;
}
