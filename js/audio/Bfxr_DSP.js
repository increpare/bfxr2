/**
 * 
 * this uses ported/modified code from Thomas Vian's SfxrSynth:
	 * SfxrSynth
	 * 
	 * Copyright 2010 Thomas Vian
	 *
	 * Licensed under the Apache License, Version 2.0 (the "License");
	 * you may not use this file except in compliance with the License.
	 * You may obtain a copy of the License at
	 *
	 * 	http://www.apache.org/licenses/LICENSE-2.0
	 *
	 * Unless required by applicable law or agreed to in writing, software
	 * distributed under the License is distributed on an "AS IS" BASIS,
	 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	 * See the License for the specific language governing permissions and
	 * limitations under the License.
	 * 
	 * @author Thomas Vian
	 */

class Bfxr_DSP {
    static version = "1.0.4"

    static MIN_LENGTH = 0.18;
    static LoResNoisePeriod = 8;
    static sampleRate = 44100;
    static bitDepth = 16;

    static WaveType = {
        SQUARE: 0,
        SAW: 1,
        SINE: 2,
        NOISE: 3,
        TRIANGLE: 4,
        PINK: 5,
        TAN: 6,
        WHISTLE: 7,
        BREAKER: 8,
        BITNOISE: 9,
        FM_SYNTH: 10,
        BUZZ: 11,
        VOICE: 12
    };
    
    constructor(params,param_info) {

        this.params = params;
        this.param_info = param_info;

        this.reset(true);
    }

    /*
     * Resets the runing variables from the params
     * Used once at the start (total reset) and for the repeat effect (partial reset)
     * */
    reset(total_reset = true){
        var params=this.params;

        this.period = 100.0 / (params.startFrequency * params.startFrequency + 0.001);
        this.maxPeriod = 100.0 / (params.minFrequency * params.minFrequency + 0.001);

        this.slide = 1.0 - params.slide * params.slide * params.slide * 0.01;
        this.deltaSlide = -params.deltaSlide * params.deltaSlide * params.deltaSlide * 0.000001;

        if ((params.waveType)|0 == 0) {
            this.squareDuty = 0.5 - params.squareDuty * 0.5;
            this.dutySweep = -params.dutySweep * 0.00005;
        }

        this.changePeriod = Math.max(((1 - params.changeRepeat) + 0.1) / 1.1) * 20000 + 32;
        this.changePeriodTime = 0;

        if (params.changeAmount > 0.0) {
            this.changeAmount = 1.0 - params.changeAmount * params.changeAmount * 0.9;
        }
        else {
            this.changeAmount = 1.0 + params.changeAmount * params.changeAmount * 10.0;
        }

        if (total_reset){
            this.waveType = (params.waveType)|0;

            if (params.sustainTime < 0.01) {
                params.sustainTime = 0.01;
            }

            this.clampTotalLength(params);

            this.sustainPunch = params.sustainPunch;

            this.phase = 0;

            this.minFreqency = params.minFrequency;
            this.muted = false;
            this.overtones = params.overtones * 10;
            this.overtoneFalloff = params.overtoneFalloff;

            this.bitcrush_freq = 1 - Math.pow(params.bitCrush, 1.0 / 3.0);
            this.bitcrush_freq_sweep = -params.bitCrushSweep * 0.000015;
            this.bitcrush_phase = 0;
            this.bitcrush_last = 0;

            this.compression_factor = 1 / (1 + 4 * params.compressionAmount);

            this.filters = params.lpFilterCutoff != 1.0 || params.hpFilterCutoff != 0.0;

            this.lpFilterPos = 0.0;
            this.lpFilterDeltaPos = 0.0;
            this.lpFilterCutoff = params.lpFilterCutoff * params.lpFilterCutoff * params.lpFilterCutoff * 0.1;
            this.lpFilterDeltaCutoff = 1.0 + params.lpFilterCutoffSweep * 0.0001;
            this.lpFilterDamping = 5.0 / (1.0 + params.lpFilterResonance * params.lpFilterResonance * 20.0) * (0.01 + this.lpFilterCutoff);
            if (this.lpFilterDamping > 0.8) this.lpFilterDamping = 0.8;
            this.lpFilterDamping = 1.0 - this.lpFilterDamping;
            this.lpFilterOn = params.lpFilterCutoff != 1.0;

            this.hpFilterPos = 0.0;
            this.hpFilterCutoff = params.hpFilterCutoff * params.hpFilterCutoff * 0.1;
            this.hpFilterDeltaCutoff = 1.0 + params.hpFilterCutoffSweep * 0.0003;

            this.vibratoPhase = 0.0;
            this.vibratoSpeed = params.vibratoSpeed * params.vibratoSpeed * 0.01;
            this.vibratoAmplitude = params.vibratoDepth * 0.5;

            this.envelopeVolume = 0.0;
            this.envelopeStage = 0;
            this.envelopeTime = 0;
            this.envelopeLength0 = params.attackTime * params.attackTime * 100000.0;
            this.envelopeLength1 = params.sustainTime * params.sustainTime * 100000.0;
            this.envelopeLength2 = params.decayTime * params.decayTime * 100000.0 + 10;
            this.envelopeLength = this.envelopeLength0;
            this.envelopeFullLength = this.envelopeLength0 + this.envelopeLength1 + this.envelopeLength2;

            this.envelopeOverLength0 = 1.0 / this.envelopeLength0;
            this.envelopeOverLength1 = 1.0 / this.envelopeLength1;
            this.envelopeOverLength2 = 1.0 / this.envelopeLength2;

            this.flanger = params.flangerOffset != 0.0 || params.flangerSweep != 0.0;

            this.flangerOffset = params.flangerOffset * params.flangerOffset * 1020.0;
            if (params.flangerOffset < 0.0) {
                this.flangerOffset = -this.flangerOffset;
            }
            this.flangerDeltaOffset = params.flangerSweep * params.flangerSweep * params.flangerSweep * 0.2;
            this.flangerPos = 0;

            if (!this.flangerBuffer) {
                this.flangerBuffer = new Float32Array(1024);
            }
            if (!this.noiseBuffer) {
                this.noiseBuffer = new Float32Array(32);
            }
            if (!this.pinkNoiseBuffer) {
                this.pinkNoiseBuffer = new Float32Array(32);
            }
            if (!this.loResNoiseBuffer) {
                this.loResNoiseBuffer = new Float32Array(32);
            }
            this.oneBitNoiseState = 1 << 14;
            this.oneBitNoise = 0;
            this.buzzState = 1 << 14;
            this.buzz = 0;

            for (var i = 0; i < 1024; i++) {
                this.flangerBuffer[i] = 0.0;
            }
            for (i = 0; i < 32; i++) {
                this.noiseBuffer[i] = Math.random() * 2.0 - 1.0;
            }
            for (i = 0; i < 32; i++) {
                this.loResNoiseBuffer[i] = ((i % Bfxr_DSP.LoResNoisePeriod) == 0) ? Math.random() * 2.0 - 1.0 : this.loResNoiseBuffer[i - 1];
            }

            this.repeatTime = 0;

            if (params.repeatSpeed == 0.0) {
                this.repeatLimit = 0;
            } else {
                this.repeatLimit = ((1.0 - params.repeatSpeed) * (1.0 - params.repeatSpeed) * 20000)|0 + 32;
            }
        }

        
        this.changeTime = 0;
        this.changeReached = false;

        var change_window_size = this.envelopeFullLength;
        if (params.repeatLimit > 0) {
            change_window_size = params.repeatLimit;
        }
        if (params.changeSpeed == 1.0) {
            this.changeLimit = 0;
        }
        else {
            this.changeLimit = params.changeSpeed * change_window_size + 32;
        }


        if (params.changeAmount2 > 0.0) {
            this.changeAmount2 = 1.0 - params.changeAmount2 * params.changeAmount2 * 0.9;
        }
        else {
            this.changeAmount2 = 1.0 + params.changeAmount2 * params.changeAmount2 * 10.0;
        }


        this.changeTime2 = 0;
        this.changeReached2 = false;

        if (params.changeSpeed2 == 1.0) {
            this.changeLimit2 = 0;
        }
        else this.changeLimit2 = params.changeSpeed2 * change_window_size + 32;

        this.changeLimit *= (1 - params.changeRepeat + 0.1) / 1.1;
        this.changeLimit2 *= (1 - params.changeRepeat + 0.1) / 1.1;

        this.masterVolume = params.masterVolume * params.masterVolume;
        
        if (this.waveType === 9) {
            var sf = params.startFrequency;
            var mf = params.minFrequency;

            var startFrequency_min = this.param_info.param_min("startFrequency");
            var startFrequency_max = this.param_info.param_max("startFrequency");
            var startFrequency_mid = (startFrequency_max + startFrequency_min) / 2;

            var minFrequency_min = this.param_info.param_min("minFrequency");
            var minFrequency_max = this.param_info.param_max("minFrequency");
            var minFrequency_mid = (minFrequency_max + minFrequency_min) / 2;

            var delta_start = (sf - startFrequency_min) / (startFrequency_max - startFrequency_min)
            var delta_min = (mf - minFrequency_min) / (minFrequency_max - minFrequency_min)

            sf = startFrequency_mid + delta_start;
            mf = minFrequency_mid + delta_min;

            this.period = 100.0 / (sf * sf + 0.001);
            this.maxPeriod = 100.0 / (mf * mf + 0.001);
        }
    }

    clampTotalLength(p)
    {
        var totalTime = p.attackTime + p.sustainTime + p.decayTime;
        if (totalTime < Bfxr_DSP.MIN_LENGTH ) 
        {
            var multiplier = Bfxr_DSP.MIN_LENGTH / totalTime;
            p.attackTime = p.attackTime * multiplier;
            p.sustainTime = p.sustainTime * multiplier;
            p.decayTime = p.decayTime * multiplier;
        }
    }

    generate_sound() {
        var buffer = new Float32Array(this.envelopeFullLength);
			
        this.sampleCount = 0;
        var bufferSample = 0.0;
        
        var length = this.envelopeFullLength;
        var finished = false;
        for(var i = 0; i < length; i++)
        {
            if (finished) 
            {
                return true;					
            }
            
            // Repeats every this.repeatLimit times, partially resetting the sound parameters
            if(this.repeatLimit != 0)
            {
                if(++this.repeatTime >= this.repeatLimit)
                {
                    this.repeatTime = 0;
                    this.reset(false);
                }
            }
            
            this.changePeriodTime++;
            if (this.changePeriodTime>=this.changePeriod)
            {				
                this.changeTime=0;
                this.changeTime2=0;
                this.changePeriodTime=0;
                if (this.changeReached)
                {
                    this.period /= this.changeAmount;
                    this.changeReached=false;
                }
                if (this.changeReached2)
                {
                    this.period /= this.changeAmount2;
                    this.changeReached2=false;
                }
            }
            
            // If this.changeLimit is reached, shifts the pitch
            if(!this.changeReached)
            {
                if(++this.changeTime >= this.changeLimit)
                {
                    this.changeReached = true;
                    this.period *= this.changeAmount;
                }
            }
            
            // If this.changeLimit is reached, shifts the pitch
            if(!this.changeReached2)
            {
                if(++this.changeTime2 >= this.changeLimit2)
                {
                    this.period *= this.changeAmount2;
                    this.changeReached2=true;
                }
            }
            
            // Acccelerate and apply slide
            this.slide += this.deltaSlide;
            this.period *= this.slide;
            
            // Checks for frequency getting too low, and stops the sound if a minFrequency was set
            if(this.period > this.maxPeriod)
            {
                this.period = this.maxPeriod;
                if(this.minFreqency > 0.0) {
                        this.muted = true;
                }										
            }
            
            this.periodTemp = this.period;
            
            // Applies the vibrato effect
            if(this.vibratoAmplitude > 0.0)
            {
                this.vibratoPhase += this.vibratoSpeed;
                this.periodTemp = this.period * (1.0 + Math.sin(this.vibratoPhase) * this.vibratoAmplitude);
            }
            
            this.periodTemp = (this.periodTemp)|0;
            if(this.periodTemp < 8) this.periodTemp = 8;
            
            // Sweeps the square duty
            if (this.waveType === 0)
            {
                this.squareDuty += this.dutySweep;
                        if(this.squareDuty < 0.0) this.squareDuty = 0.0;
                else if (this.squareDuty > 0.5) this.squareDuty = 0.5;
            }
            
            // Moves through the different stages of the volume envelope
            if(++this.envelopeTime > this.envelopeLength)
            {
                this.envelopeTime = 0;
                
                switch(++this.envelopeStage)
                {
                    case 1: this.envelopeLength = this.envelopeLength1; break;
                    case 2: this.envelopeLength = this.envelopeLength2; break;
                }
            }
            
            // Sets the volume based on the position in the envelope
            switch(this.envelopeStage)
            {
                case 0: 
                    this.envelopeVolume = this.envelopeTime * this.envelopeOverLength0; 									
                    break;
                case 1: 
                    this.envelopeVolume = 1.0 + (1.0 - this.envelopeTime * this.envelopeOverLength1) * 2.0 * this.sustainPunch; 
                        break;
                case 2: 
                    this.envelopeVolume = 1.0 - this.envelopeTime * this.envelopeOverLength2; 								
                    break;
                case 3: 
                    this.envelopeVolume = 0.0; finished = true; 													
                    break;
            }
            
            // Moves the flanger offset
            if (this.flanger)
            {
                this.flangerOffset += this.flangerDeltaOffset;
                this.flangerInt = (this.flangerOffset)|0;
                        if(this.flangerInt < 0) 	this.flangerInt = -this.flangerInt;
                else if (this.flangerInt > 1023) this.flangerInt = 1023;
            }
            
            // Moves the high-pass filter cutoff
            if(this.filters && this.hpFilterDeltaCutoff != 0.0)
            {
                this.hpFilterCutoff *= this.hpFilterDeltaCutoff;
                        if(this.hpFilterCutoff < 0.00001) 	this.hpFilterCutoff = 0.00001;
                else if(this.hpFilterCutoff > 0.1) 		this.hpFilterCutoff = 0.1;
            }
            
            this.superSample = 0.0;
            for(var j = 0; j < 8; j++)
            {
                // Cycles through the period
                this.phase++;
                if(this.phase >= this.periodTemp)
                {
                    this.phase = this.phase - this.periodTemp;
                    
                    // Generates new random noise for this period
                    switch(this.waveType)
                    {
                        case 3:  // WHITE NOISE
                            for(var n = 0; n < 32; n++) this.noiseBuffer[n] = Math.random() * 2.0 - 1.0;
                            break;
                        case 6: // TAN
                            for(n = 0; n < 32; n++) this.loResNoiseBuffer[n] = ((n%Bfxr_DSP.LoResNoisePeriod)==0) ? Math.random()*2.0-1.0 : this.loResNoiseBuffer[n-1];							
                            break;
                        case 9: // Bitnoise
                        // Based on SN76489 periodic "white" noise
                        // http://www.smspower.org/Development/SN76489?sid=ae16503f2fb18070f3f40f2af56807f1#NoiseChannel
                        // This one matches the behaviour of the SN76489 in the BBC Micro.
                        var feedBit = (this.oneBitNoiseState >> 1 & 1) ^ (this.oneBitNoiseState & 1);
                        this.oneBitNoiseState = this.oneBitNoiseState >> 1 | (feedBit << 14);
                        this.oneBitNoise = (~this.oneBitNoiseState & 1) - 0.5;
                        break;
                        // case 11: // BUZZ
                        //     // Based on SN76489 periodic "white" noise
                        //     // http://www.smspower.org/Development/SN76489?sid=ae16503f2fb18070f3f40f2af56807f1#NoiseChannel
                        //     // This one doesn't match the behaviour of anything real, but it made a nice sound, so I kept it.
                        // var fb = (this.buzzState >> 3 & 1) ^ (this.buzzState & 1);
                        // this.buzzState = this.buzzState >> 1 | (fb << 14);
                        // this.buzz = (~this.buzzState & 1) - 0.5;
                        // break;
                    }
                }
                
                this.sample=0;
                var overtonestrength=1;
                for (var k=0;k<=this.overtones;k++)
                {
                    var tempphase = (this.phase*(k+1))%this.periodTemp;
                    // Gets the sample from the oscillator
                    var wtype = this.waveType;

                    switch(wtype)
                    {
                        case 0: // Square wave
                        {
                            this.sample += overtonestrength*(((tempphase / this.periodTemp) < this.squareDuty) ? 0.5 : -0.5);
                            break;
                        }
                        case 1: // Saw wave
                        {
                            this.sample += overtonestrength*(1.0 - (tempphase / this.periodTemp) * 2.0);
                            break;
                        }
                        case 2: // Sine wave (fast and accurate approx)
                        {								
                                this.pos = tempphase / this.periodTemp;
                                this.pos = this.pos > 0.5 ? (this.pos - 1.0) * 6.28318531 : this.pos * 6.28318531;
                            var tempsample = this.pos < 0 ? 1.27323954 * this.pos + .405284735 * this.pos * this.pos : 1.27323954 * this.pos - 0.405284735 * this.pos * this.pos;
                            this.sample += overtonestrength*(tempsample < 0 ? .225 * (tempsample *-tempsample - tempsample) + tempsample : .225 * (tempsample * tempsample - tempsample) + tempsample);								
                            break;
                        }
                        case 3: // Noise
                        {
                            this.sample += overtonestrength*(this.noiseBuffer[((tempphase * 32 / (this.periodTemp|0))|0)%32]);
                            break;
                        }
                        case 4: // Triangle Wave
                        {						
                            this.sample += overtonestrength*(Math.abs(1-(tempphase / this.periodTemp)*2)-1);
                            break;
                        }
                        case 5: // Pink Noise
                        {						
                            this.sample += overtonestrength*(this.pinkNoiseBuffer[((tempphase * 32 / (this.periodTemp|0))|0)%32]);
                            break;
                        }
                        case 6: // tan
                        {
                            //detuned
                            this.sample += Math.tan(Math.PI*tempphase/this.periodTemp)*overtonestrength;
                            break;
                        }
                        case 7: // Whistle 
                        {				
                            // Sin wave code
                            this.pos = tempphase / this.periodTemp;
                            this.pos = this.pos > 0.5 ? (this.pos - 1.0) * 6.28318531 : this.pos * 6.28318531;
                            tempsample = this.pos < 0 ? 1.27323954 * this.pos + .405284735 * this.pos * this.pos : 1.27323954 * this.pos - 0.405284735 * this.pos * this.pos;
                            var value = 0.75*(tempsample < 0 ? .225 * (tempsample *-tempsample - tempsample) + tempsample : .225 * (tempsample * tempsample - tempsample) + tempsample);
                            //then whistle (essentially an overtone with frequencyx20 and amplitude0.25
                            
                            this.pos = ((tempphase*20) % this.periodTemp) / this.periodTemp;
                            this.pos = this.pos > 0.5 ? (this.pos - 1.0) * 6.28318531 : this.pos * 6.28318531;
                            tempsample = this.pos < 0 ? 1.27323954 * this.pos + .405284735 * this.pos * this.pos : 1.27323954 * this.pos - 0.405284735 * this.pos * this.pos;
                            value += 0.25*(tempsample < 0 ? .225 * (tempsample *-tempsample - tempsample) + tempsample : .225 * (tempsample * tempsample - tempsample) + tempsample);
                            
                            this.sample += overtonestrength*value;//main wave
                            
                            break;
                        }
                        case 8: // Breaker
                        {	
                            var amp = tempphase/this.periodTemp;								
                            this.sample += overtonestrength*(Math.abs(1-amp*amp*2)-1);
                            break;
                        }
                        case 9: // Bitnoise (1-bit periodic "white" noise)
                        {
                            this.sample += overtonestrength*this.oneBitNoise;
                            break;
                        }
                        case 10: //FM Synth
                        {
                            var sample_index = ((tempphase * 256 / (this.periodTemp|0))|0)%256;
                            var wave_sample = AKWF.fmsynth_0012[sample_index]/32768-1;
                            this.sample += overtonestrength*wave_sample;
                            break;
                        }
                        case 11: //Organ
                        {
                            var sample_index = ((tempphase * 256 / (this.periodTemp|0))|0)%256;
                            var wave_sample = AKWF.granular_0044[sample_index]/32768-1;
                            this.sample += overtonestrength*wave_sample;
                            break;
                        } 
                        case 12: //Vox - wave sampled from AKWF_hvoice_0012
                        {
                            var sample_index = ((tempphase * 256 / (this.periodTemp|0))|0)%256;
                            var wave_sample = AKWF.hvoice_0012[sample_index]/32768-1;
                            this.sample += overtonestrength*wave_sample;
                            break;
                        }
                    }
                    overtonestrength*=(1-this.overtoneFalloff);
                    
                }					
                
                // Applies the low and high pass filters
                if (this.filters)
                {
                    this.lpFilterOldPos = this.lpFilterPos;
                    this.lpFilterCutoff *= this.lpFilterDeltaCutoff;
                            if(this.lpFilterCutoff < 0.0) this.lpFilterCutoff = 0.0;
                    else if(this.lpFilterCutoff > 0.1) this.lpFilterCutoff = 0.1;
                    
                    if(this.lpFilterOn)
                    {
                        this.lpFilterDeltaPos += (this.sample - this.lpFilterPos) * this.lpFilterCutoff;
                        this.lpFilterDeltaPos *= this.lpFilterDamping;
                    }
                    else
                    {
                        this.lpFilterPos = this.sample;
                        this.lpFilterDeltaPos = 0.0;
                    }
                    
                    this.lpFilterPos += this.lpFilterDeltaPos;
                    
                    this.hpFilterPos += this.lpFilterPos - this.lpFilterOldPos;
                    this.hpFilterPos *= 1.0 - this.hpFilterCutoff;
                    this.sample = this.hpFilterPos;
                }
                
                // Applies the flanger effect
                if (this.flanger)
                {
                    this.flangerBuffer[this.flangerPos&1023] = this.sample;
                    this.sample += this.flangerBuffer[(this.flangerPos - this.flangerInt + 1024) & 1023];
                    this.flangerPos = (this.flangerPos + 1) & 1023;
                }
                
                this.superSample += this.sample;
            }
            
            // Clipping if too loud
            if(this.superSample > 8.0) 	this.superSample = 8.0;
            else if(this.superSample < -8.0) 	this.superSample = -8.0;					 				 				
            
            // Averages out the super samples and applies volumes
            this.superSample = this.masterVolume * this.envelopeVolume * this.superSample * 0.125;				
            
            
            //BIT CRUSH				
            this.bitcrush_phase+=this.bitcrush_freq;
            if (this.bitcrush_phase>1)
            {
                this.bitcrush_phase=0;
                this.bitcrush_last=this.superSample;	 
            }
            this.bitcrush_freq = Math.max(Math.min(this.bitcrush_freq+this.bitcrush_freq_sweep,1),0);
            
            this.superSample=this.bitcrush_last; 				
        
                            
            //compressor
                
            if (this.superSample>0)
            {
                this.superSample = Math.pow(this.superSample,this.compression_factor);
            }
            else
            {
                this.superSample = -Math.pow(-this.superSample,this.compression_factor);
            }
            
            if (this.muted)
            {
                this.superSample = 0;
            }            
            
            
            buffer[i] = Math.clamp(this.superSample, -1, 1);
        }
        
        this.buffer = buffer;    
    }
}   