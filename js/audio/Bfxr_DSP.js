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


        this.frequency_period_samples = 100.0 / (params.frequency_start * params.frequency_start + 0.001);
        var minimum_frequency = Math.pow(params.min_frequency_relative_to_starting_frequency,0.4)*params.frequency_start;
        this.frequency_maxPeriod_samples = 100.0 / (minimum_frequency * minimum_frequency + 0.001);

        this.pitch_jump_reached = false;
        this.pitch_jump_2_reached = false;

        if (total_reset){

            this.masterVolume = params.masterVolume * params.masterVolume;
            
            this.waveType = (params.waveType)|0;

            if (params.sustainTime < 0.01) {
                params.sustainTime = 0.01;
            }

            this.clampTotalLength(params);

            this.sustainPunch = params.sustainPunch;

            this.phase = 0;

            this.minFreqency = params.min_frequency_relative_to_starting_frequency;
            this.muted = false;
            this.overtones = params.overtones * 10;
            this.overtoneFalloff = params.overtoneFalloff;

            this.compression_factor = 1 / (1 + 4 * params.compressionAmount);

            this.filters = params.lpFilterCutoff != 1.0 || params.hpFilterCutoff != 0.0;



            this.vibratoPhase = 0.0;
            this.vibratoSpeed = params.vibratoSpeed * params.vibratoSpeed * 0.01;
            this.vibratoAmplitude = params.vibratoDepth * 0.5;

            this.envelopeVolume = 0.0;
            this.envelopeStage = 0;
            this.envelopeTime = 0;
            this.envelopeLength0 = params.attackTime * params.attackTime * 100000.0;
            this.envelopeLength1 = params.sustainTime * params.sustainTime * 100000.0;
            this.envelopeLength2 = params.decayTime * params.decayTime * 100000.0 + 10;
            this.attack_length_samples = this.envelopeLength0;
            this.envelope_full_length_samples = this.envelopeLength0 + this.envelopeLength1 + this.envelopeLength2;

            
            this.bitcrush_freq_sweep = -params.bitCrushSweep / this.envelope_full_length_samples;
            this.bitcrush_phase = 0;
            this.bitcrush_last = 0;


            this.envelopeOverLength0 = 1.0 / this.envelopeLength0;
            this.envelopeOverLength1 = 1.0 / this.envelopeLength1;
            this.envelopeOverLength2 = 1.0 / this.envelopeLength2;

            this.flanger = params.flangerOffset != 0.0 || params.flangerSweep != 0.0;

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

            this.repeat_timestamp_samples = 0;

            //if 
            // when params.pitch_jump_repeat_speed is zero, it should not repeat (i.e. pitch_jump_repeat_length_samples should be the same as the envelope length)
            // when params.pitch_jump_repeat_speed is 1, it should repeat 10 times a second (i.e. sampleRate/50)        
            this.pitch_jump_repeat_length_samples = lerp(this.envelope_full_length_samples, Bfxr_DSP.sampleRate/50, params.pitch_jump_repeat_speed)+32;//adding 32 for safety
            
            // PITCH JUMP START


            var pitch_jump_window_size_samples = this.envelope_full_length_samples;
            if (this.pitch_jump_repeat_length_samples > 0) {
                pitch_jump_window_size_samples = this.pitch_jump_repeat_length_samples;
            }
                        
            if (params.pitch_jump_amount > 0.0) {
                this.pitch_jump_amount = 1.0 - params.pitch_jump_amount * params.pitch_jump_amount * 0.9;
            }
            else {
                this.pitch_jump_amount = 1.0 + params.pitch_jump_amount * params.pitch_jump_amount * 10.0;
            }        
            if (params.pitch_jump_2_amount > 0.0) {
                this.pitch_jump_2_amount = 1.0 - params.pitch_jump_2_amount * params.pitch_jump_2_amount * 0.9;
            }
            else {
                this.pitch_jump_2_amount = 1.0 + params.pitch_jump_2_amount * params.pitch_jump_2_amount * 10.0;
            }

            this.pitch_jump_current_timestamp_samples = 0;

            if (params.pitch_jump_onset_percent == 1.0) {
                this.pitch_jump_timestamp_sample = 0;
            }
            else {
                this.pitch_jump_timestamp_sample = params.pitch_jump_onset_percent * pitch_jump_window_size_samples + 32;
            }
            if (params.pitch_jump_onset2_percent == 1.0) {
                this.pitch_jump_2_timestamp_sample = 0;
            }
            else {
                this.pitch_jump_2_timestamp_sample = params.pitch_jump_onset2_percent * pitch_jump_window_size_samples + 32;
            }

            //scale by repeat_length_samples vs envelope_full_length_samples
            //need to scale by repeat_length_samples/envelope_full_length_samples
            // var pitch_jump_time_scale_factor = this.pitch_jump_repeat_length_samples / this.envelope_full_length_samples;
            // this.pitch_jump_timestamp_sample *= pitch_jump_time_scale_factor;
            // this.pitch_jump_2_timestamp_sample *= pitch_jump_time_scale_factor;

            //PITCH JUMP END

            if (this.waveType === 9) { //Bitnoise
                var sf = params.frequency_start;
                var mf = params.min_frequency_relative_to_starting_frequency;
    
                var startFrequency_min = this.param_info.param_min("frequency_start");
                var startFrequency_max = this.param_info.param_max("frequency_start");
                var startFrequency_mid = (startFrequency_max + startFrequency_min) / 2;
    
                var minFrequency_min = this.param_info.param_min("min_frequency_relative_to_starting_frequency");
                var minFrequency_max = this.param_info.param_max("min_frequency_relative_to_starting_frequency");
                var minFrequency_mid = (minFrequency_max + minFrequency_min) / 2;
    
                var delta_start = (sf - startFrequency_min) / (startFrequency_max - startFrequency_min)
                var delta_min = (mf - minFrequency_min) / (minFrequency_max - minFrequency_min)
    
                sf = startFrequency_mid + delta_start;
                mf = minFrequency_mid + delta_min;
    
                this.frequency_period_samples = 100.0 / (sf * sf + 0.001);
                this.frequency_maxPeriod_samples = 100.0 / (mf * mf + 0.001);
            }
        }

        // START sweep paramets designed to be reset with repeat speed
        this.slide = 1.0 - params.frequency_slide * params.frequency_slide * params.frequency_slide * 0.01;
        this.frequency_acceleration = -params.frequency_acceleration * params.frequency_acceleration * params.frequency_acceleration * 0.000001;

        this.flangerOffset = params.flangerOffset * params.flangerOffset * 1020.0;
        if (params.flangerOffset < 0.0) {
            this.flangerOffset = -this.flangerOffset;
        }
        
        this.bitcrush_freq = 1 - Math.pow(params.bitCrush, 1.0 / 3.0);

        
        if ((params.waveType)|0 == 0) {
            this.squareDuty = 0.5 - params.squareDuty * 0.5;
            this.dutySweep = -params.dutySweep * 0.00005;
        }
        
        this.lpFilterCutoff = params.lpFilterCutoff * params.lpFilterCutoff * params.lpFilterCutoff * 0.1;
        this.lpFilterDeltaCutoff = 1.0 + params.lpFilterCutoffSweep * 0.0001;
        this.lpFilterDamping = 5.0 / (1.0 + params.lpFilterResonance * params.lpFilterResonance * 20.0) * (0.01 + this.lpFilterCutoff);
        if (this.lpFilterDamping > 0.8) this.lpFilterDamping = 0.8;
        this.lpFilterDamping = 1.0 - this.lpFilterDamping;
        this.lpFilterOn = params.lpFilterCutoff != 1.0;

        this.lpFilterPos = 0.0;
        this.lpFilterDeltaPos = 0.0;
        this.hpFilterPos = 0.0;
        this.hpFilterCutoff = params.hpFilterCutoff * params.hpFilterCutoff * 0.1;
        this.hpFilterDeltaCutoff = 1.0 + params.hpFilterCutoffSweep * 0.0003;

        // END sweep paramets designed to be reset with repeat speed
        

        // when params.pitch_jump_repeat_speed, it should not repeat (i.e. be the same as the envelope length)
        // when params.pitch_jump_repeat_speed is 1, it should repeat 10 times a second (i.e. sampleRate/10)
        this.param_reset_period_samples = lerp(this.envelope_full_length_samples, Bfxr_DSP.sampleRate/10, params.repeatSpeed);
        this.param_reset_current_timestamp_samples = 0;

        

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
        var buffer = new Float32Array(this.envelope_full_length_samples);
			
        this.sampleCount = 0;
        var bufferSample = 0.0;
        
        var length = this.envelope_full_length_samples;
        var finished = false;
        var last_nonzero_sample_index = -1;
        for(var i = 0; i < length; i++)
        {
            if (finished) 
            {
                return true;					
            }
            
            // Repeats every this.pitch_jump_repeat_length_samples times, partially resetting the sound parameters
            if(this.param_reset_period_samples != 0)
            {
                this.param_reset_current_timestamp_samples++;
                if(this.param_reset_current_timestamp_samples >= this.param_reset_period_samples)
                {
                    this.param_reset_current_timestamp_samples = 0;
                    this.reset(false);
                }
            }
            
            this.pitch_jump_current_timestamp_samples++;
            if (this.pitch_jump_current_timestamp_samples>=this.pitch_jump_repeat_length_samples)
            {				
                this.pitch_jump_current_timestamp_samples=0;
                if (this.pitch_jump_reached)
                {
                    this.frequency_period_samples /= this.pitch_jump_amount;
                    this.pitch_jump_reached=false;
                }
                if (this.pitch_jump_2_reached)
                {
                    this.frequency_period_samples /= this.pitch_jump_2_amount;
                    this.pitch_jump_2_reached=false;
                }
            }
            
            // If this.pitch_jump_timestamp_sample is reached, shifts the pitch
            if(!this.pitch_jump_reached)
            {
                if(this.pitch_jump_current_timestamp_samples >= this.pitch_jump_timestamp_sample)
                {
                    this.pitch_jump_reached = true;
                    this.frequency_period_samples *= this.pitch_jump_amount;
                }
            }
            
            // If this.pitch_jump_timestamp_sample is reached, shifts the pitch
            if(!this.pitch_jump_2_reached)
            {
                if(this.pitch_jump_current_timestamp_samples >= this.pitch_jump_2_timestamp_sample)
                {
                    this.frequency_period_samples *= this.pitch_jump_2_amount;
                    this.pitch_jump_2_reached=true;
                }
            }
            
            // Acccelerate and apply slide
            this.slide += this.frequency_acceleration;
            this.frequency_period_samples *= this.slide;
            
            // Checks for frequency getting too low, and stops the sound if a min_frequency_relative_to_starting_frequency was set
            if(this.frequency_period_samples > this.frequency_maxPeriod_samples)
            {
                this.frequency_period_samples = this.frequency_maxPeriod_samples;
                if(this.minFreqency > 0.0) {
                        this.muted = true;
                }										
            }
            
            this.periodTemp = this.frequency_period_samples;
            
            // Applies the vibrato effect
            if(this.vibratoAmplitude > 0.0)
            {
                this.vibratoPhase += this.vibratoSpeed;
                this.periodTemp = this.frequency_period_samples * (1.0 + Math.sin(this.vibratoPhase) * this.vibratoAmplitude);
            }
            
            this.periodTemp = (this.periodTemp)|0;
            if(this.periodTemp < 8) this.periodTemp = 8;
            
            // Sweeps the square duty
            if (this.waveType === 0)
            {
                this.squareDuty += this.dutySweep;
                if(this.squareDuty < 0.0) this.squareDuty = 0.001;
                else if (this.squareDuty > 0.5) this.squareDuty = 0.5;
            }
            
            // Moves through the different stages of the volume envelope
            if(++this.envelopeTime > this.attack_length_samples)
            {
                this.envelopeTime = 0;
                
                switch(++this.envelopeStage)
                {
                    case 1: this.attack_length_samples = this.envelopeLength1; break;
                    case 2: this.attack_length_samples = this.envelopeLength2; break;
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
                        case 3: // White Noise
                        {
                            this.sample += overtonestrength*(this.noiseBuffer[((tempphase * 32 / (this.periodTemp|0))|0)%32]);
                            break;
                        }
                        case 4: // Triangle Wave
                        {						
                            this.sample += overtonestrength*(Math.abs(1-(tempphase / this.periodTemp)*2)-1);
                            break;
                        }
                        case 5: //Organ
                        {
                            var sample_index = ((tempphase * 256 / (this.periodTemp|0))|0)%256;
                            var wave_sample = AKWF.granular_0044[sample_index]/32768-1;
                            this.sample += overtonestrength*wave_sample;
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
                        case 11: //Voice - wave sampled from AKWF_hvoice_0012
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
            		
            
            
            //BIT CRUSH				
            this.bitcrush_phase+=this.bitcrush_freq;
            if (this.bitcrush_phase>1)
            {
                this.bitcrush_phase=0;
                this.bitcrush_last=this.superSample;	 
            }
            var multiplier = lerp(1,50*this.bitcrush_freq,Math.sqrt(this.bitcrush_freq));
            this.bitcrush_freq = Math.max(Math.min(this.bitcrush_freq+multiplier*this.bitcrush_freq_sweep,1),0.00001);
            this.superSample=this.bitcrush_last; 				
        
            // Averages out the super samples and applies volumes
            this.superSample = this.masterVolume * this.envelopeVolume * this.superSample * 0.125;		
                            
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
                //early out - resize buffer to current length, and return
                buffer = buffer.slice(0,i);
                break;
            }            
            
            //approimxate zero (say ~ e-19)
            if (Math.abs(this.superSample)>0.2e-2){
                last_nonzero_sample_index = i;
            }
            buffer[i] = Math.clamp(this.superSample, -1, 1);
        }
        
        if (last_nonzero_sample_index<buffer.length-1){
            //min value of 10
            last_nonzero_sample_index = Math.max(last_nonzero_sample_index,10);
            buffer = buffer.slice(0,last_nonzero_sample_index+1);
        }
        this.buffer = buffer;    
    }
}   