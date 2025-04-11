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
        COSTABLENAME[i] = Math.cos( 2 * Math.PI * i / PD_COSTABLESIZE);
    }
    COSTABLENAME[0] = 1;
    COSTABLENAME[PD_COSTABLESIZE] = 1;
    COSTABLENAME[(PD_COSTABLESIZE/4)|0] = 0;
    COSTABLENAME[(3*PD_COSTABLESIZE/4)|0] = 0;
    COSTABLENAME[(PD_COSTABLESIZE/2)|0] = -1;
}

function gt(signal_a,signal_b){
    var result = new Float32Array(signal_a.length);
    for (let i = 0; i < signal_a.length; i++) {
        result[i] = signal_a[i] < signal_b[i] ? 1 : 0;
    }
    return result;
}

generate_tables();
var puredata_stream_length = 0;
function pd_set_stream_length_seconds(seconds){
    puredata_stream_length = seconds * SAMPLE_RATE;
}

function pd_fn(fn){
    var result = new Float32Array(puredata_stream_length);
    for (let i = 0; i < result.length; i++) {
        result[i] = fn(i/SAMPLE_RATE);
    }
    return result;
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
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = Math.max(min, Math.min(buffer[i], max));
    }
    return result;
}

// cosine wave oscillator
// https://pd.iem.sh/objects/osc~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.h#L73C1-L99C6
function pd_osc(freq_signal){
    /* original code:
    t_osc *x = (t_osc *)(w[1]);
    t_sample *in = (t_sample *)(w[2]);
    t_sample *out = (t_sample *)(w[3]);
    int n = (int)(w[4]);
    float *tab = COSTABLENAME, *addr;
    t_float f1, f2, frac;
    double dphase = x->x_phase + UNITBIT32;
    int normhipart;
    union tabfudge tf;
    float conv = x->x_conv;

    tf.tf_d = UNITBIT32;
    normhipart = tf.tf_i[HIOFFSET];
#if 0
    while (n--)
    {
        tf.tf_d = dphase;
        dphase += *in++ * conv;
        addr = tab + (tf.tf_i[HIOFFSET] & (COSTABLESIZE-1));
        tf.tf_i[HIOFFSET] = normhipart;
        frac = tf.tf_d - UNITBIT32;
        f1 = addr[0];
        f2 = addr[1];
        *out++ = f1 + frac * (f2 - f1);
    }
        */
    var result = new Float32Array(freq_signal.length);
    let dphase = PD_UNITBIT32;
    let conv = 2 * Math.PI / SAMPLE_RATE;
    
    // The bit manipulation in C is not directly translatable to JavaScript
    // Instead, we'll use a simpler approach that achieves the same result
    let phase = 0;
    
    for (let i = 0; i < freq_signal.length; i++) {
        // Update phase based on frequency
        phase += freq_signal[i] * conv;
        
        // Keep phase in [0, 2π]
        while (phase >= 2 * Math.PI) {
            phase -= 2 * Math.PI;
        }
        
        // Get table index and fractional part
        let index = (phase / (2 * Math.PI)) * PD_COSTABLESIZE;
        let idx1 = Math.floor(index) % PD_COSTABLESIZE;
        let idx2 = (idx1 + 1) % PD_COSTABLESIZE;
        let frac = index - idx1;
        
        // Linear interpolation between adjacent table values
        let f1 = COSTABLENAME[idx1];
        let f2 = COSTABLENAME[idx2];
        result[i] = f1 + frac * (f2 - f1);
    }
    
    return result;
}

function pd_mul(buffer, multiplier_signal){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = buffer[i] * multiplier_signal[i];
    }
    return result;
}

function pd_div(buffer, divisor_signal){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = buffer[i] / divisor_signal[i];
    }
    return result;
}

function pd_add(buffer, addend_signal){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = buffer[i] + addend_signal[i];
    }
    return result;
}

function pd_addmul(...buffers){
    var result = new Float32Array(buffers[0].length);
    for (let i = 0; i < result.length; i++) {
        result[i] = buffers[0][i];
        for (let j = 1; j < buffers.length; j++) {
            result[i] *= buffers[j][i];
        }
    }
    return result;
}

function pd_c(value){
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
// absolute black magic.  Don't understand it - did my best, then let cursor fix it.
function pd_vcf(buffer, res_freq_signal, q_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let re = 0;
    let im = 0;
    
    // Create a proper tabfudge-like structure to match the original C code
    let tf = {
        d: 0,
        i: new Uint32Array(2)
    };
    
    // Get the normhipart constant similar to the C code
    tf.d = PD_UNITBIT32;
    const normhipart = tf.i[PD_HIOFFSET];
    
    for (let i = 0; i < buffer.length; i++) {
        let q = q_signal[i];
        let qinv = q > 0 ? (1/q) : 0;
        let ampcorrect = 2 - 2/(q+2);
        let coefr = 0;
        let coefi = 0;
        let tab = COSTABLENAME;
        
        // Get the frequency coefficient - use the right conversion factor
        let cf = res_freq_signal[i] * CONVERSION_FACTOR;
        if (cf < 0) cf = 0;
        
        // Use the same conversion as in the original C code
        let cfindx = cf * (PD_COSTABLESIZE/6.28318);
        
        // Calculate resonance factor
        let r = (qinv > 0) ? (1 - cf * qinv) : 0;
        if (r < 0) r = 0;
        let oneminusr = 1 - r;
        
        // Bit-twiddling to get the table index and fraction - similar to original code
        let dphase = cfindx + PD_UNITBIT32;
        tf.d = dphase;
        let tabindex = tf.i[PD_HIOFFSET] & (PD_COSTABLESIZE-1);
        
        tf.i[PD_HIOFFSET] = normhipart;
        let frac = tf.d - PD_UNITBIT32;
        
        // Get the real coefficient using interpolation
        let f1 = tab[tabindex];
        let f2 = tab[tabindex+1];
        coefr = r * (f1 + frac * (f2 - f1));
        
        // Get the imaginary coefficient using interpolation
        tabindex = ((tabindex - (PD_COSTABLESIZE/4)) & (PD_COSTABLESIZE-1));
        f1 = tab[tabindex];
        f2 = tab[tabindex+1];
        coefi = r * (f1 + frac * (f2 - f1));
        
        // Apply the filter
        let inputSample = buffer[i];
        let re2 = re;
        re = ampcorrect * oneminusr * inputSample + coefr * re2 - coefi * im;
        im = coefi * re2 + coefr * im;
        
        // Handle numerical instability
        if (Math.abs(re) < 1e-10) re = 0;
        if (Math.abs(im) < 1e-10) im = 0;
        
        output_buffer[i] = re;
    }

    return output_buffer;
}
