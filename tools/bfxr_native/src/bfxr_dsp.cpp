#include "bfxr_dsp.h"

#include "akwf_tables.h"

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace bfxr {
namespace {

constexpr double kMinLength = 0.18;
constexpr int kLoResNoisePeriod = 8;
constexpr int kSampleRate = 44100;

inline double lerp(double a, double b, double t) { return a + t * (b - a); }

inline double clampd(double v, double lo, double hi) {
  return std::max(lo, std::min(v, hi));
}

inline int32_t to_int32(double v) {
  // Matches JS `x|0` (ToInt32) for values in normal DSP ranges.
  return static_cast<int32_t>(v);
}

inline float to_f32(double v) { return static_cast<float>(v); }

inline double get(const ParamMap& p, const char* name) {
  auto it = p.find(name);
  return it == p.end() ? 0.0 : it->second;
}

struct Dsp {
  ParamMap params;
  Mulberry32* rng = nullptr;

  double frequency_period_samples = 0;
  double frequency_maxPeriod_samples = 0;
  bool pitch_jump_reached = false;
  bool pitch_jump_2_reached = false;

  double masterVolume = 0;
  int waveType = 0;
  double sustainPunch = 0;
  double phase = 0;
  double minFreqency = 0;
  bool muted = false;
  double overtones = 0;
  double overtoneFalloff = 0;
  double compression_factor = 1;

  bool filters = false;
  double vibratoPhase = 0;
  double vibratoSpeed = 0;
  double vibratoAmplitude = 0;

  double envelopeVolume = 0;
  int envelopeStage = 0;
  double envelopeTime = 0;
  double envelopeLength0 = 0;
  double envelopeLength1 = 0;
  double envelopeLength2 = 0;
  double attack_length_samples = 0;
  double envelope_full_length_samples = 0;

  double bitcrush_freq_sweep = 0;
  double bitcrush_phase = 0;
  double bitcrush_last = 0;
  double bitcrush_freq = 0;

  double envelopeOverLength0 = 0;
  double envelopeOverLength1 = 0;
  double envelopeOverLength2 = 0;

  bool flanger = false;
  double flangerDeltaOffset = 0;
  int flangerPos = 0;
  double flangerOffset = 0;
  int flangerInt = 0;

  float flangerBuffer[1024]{};
  float noiseBuffer[32]{};
  float loResNoiseBuffer[32]{};
  int oneBitNoiseState = 0;
  double oneBitNoise = 0;

  double pitch_jump_repeat_length_samples = 0;
  double pitch_jump_amount = 0;
  double pitch_jump_2_amount = 0;
  double pitch_jump_current_timestamp_samples = 0;
  double pitch_jump_timestamp_sample = 0;
  double pitch_jump_2_timestamp_sample = 0;

  double slide = 0;
  double frequency_acceleration = 0;
  double squareDuty = 0;
  double dutySweep = 0;

  double lpFilterCutoff = 0;
  double lpFilterDeltaCutoff = 0;
  double lpFilterDamping = 0;
  bool lpFilterOn = false;
  double lpFilterPos = 0;
  double lpFilterDeltaPos = 0;
  double lpFilterOldPos = 0;
  double hpFilterPos = 0;
  double hpFilterCutoff = 0;
  double hpFilterDeltaCutoff = 0;

  double param_reset_period_samples = 0;
  double param_reset_current_timestamp_samples = 0;

  double periodTemp = 0;
  double sample = 0;
  double pos = 0;
  double superSample = 0;

  void clampTotalLength() {
    double totalTime =
        get(params, "attackTime") + get(params, "sustainTime") + get(params, "decayTime");
    if (totalTime < kMinLength) {
      double multiplier = kMinLength / totalTime;
      params["attackTime"] = get(params, "attackTime") * multiplier;
      params["sustainTime"] = get(params, "sustainTime") * multiplier;
      params["decayTime"] = get(params, "decayTime") * multiplier;
    }
  }

  void reset(bool total_reset) {
    frequency_period_samples =
        100.0 / (get(params, "frequency_start") * get(params, "frequency_start") + 0.001);
    double minimum_frequency =
        std::pow(get(params, "min_frequency_relative_to_starting_frequency"), 0.4) *
        get(params, "frequency_start");
    frequency_maxPeriod_samples = 100.0 / (minimum_frequency * minimum_frequency + 0.001);

    pitch_jump_reached = false;
    pitch_jump_2_reached = false;

    if (total_reset) {
      masterVolume = get(params, "masterVolume") * get(params, "masterVolume");
      waveType = to_int32(get(params, "waveType"));

      if (get(params, "sustainTime") < 0.01) {
        params["sustainTime"] = 0.01;
      }

      clampTotalLength();

      sustainPunch = get(params, "sustainPunch");
      phase = 0;
      minFreqency = get(params, "min_frequency_relative_to_starting_frequency");
      muted = false;
      overtones = get(params, "overtones") * 10.0;
      overtoneFalloff = get(params, "overtoneFalloff");
      compression_factor = 1.0 / (1.0 + 4.0 * get(params, "compressionAmount"));

      filters = get(params, "lpFilterCutoff") != 1.0 || get(params, "hpFilterCutoff") != 0.0;

      vibratoPhase = 0.0;
      vibratoSpeed = get(params, "vibratoSpeed") * get(params, "vibratoSpeed") * 0.01;
      vibratoAmplitude = get(params, "vibratoDepth") * 0.5;

      envelopeVolume = 0.0;
      envelopeStage = 0;
      envelopeTime = 0;
      envelopeLength0 = get(params, "attackTime") * get(params, "attackTime") * 100000.0;
      envelopeLength1 = get(params, "sustainTime") * get(params, "sustainTime") * 100000.0;
      envelopeLength2 = get(params, "decayTime") * get(params, "decayTime") * 100000.0 + 10;
      attack_length_samples = envelopeLength0;
      envelope_full_length_samples = envelopeLength0 + envelopeLength1 + envelopeLength2;

      bitcrush_freq_sweep = -get(params, "bitCrushSweep") / envelope_full_length_samples;
      bitcrush_phase = 0;
      bitcrush_last = 0;

      envelopeOverLength0 = 1.0 / envelopeLength0;
      envelopeOverLength1 = 1.0 / envelopeLength1;
      envelopeOverLength2 = 1.0 / envelopeLength2;

      flanger = get(params, "flangerOffset") != 0.0 || get(params, "flangerSweep") != 0.0;
      flangerDeltaOffset =
          get(params, "flangerSweep") * get(params, "flangerSweep") * get(params, "flangerSweep") *
          0.2;
      flangerPos = 0;

      oneBitNoiseState = 1 << 14;
      oneBitNoise = 0;

      for (int i = 0; i < 1024; ++i) flangerBuffer[i] = 0.f;
      for (int i = 0; i < 32; ++i) {
        noiseBuffer[i] = to_f32(rng->next() * 2.0 - 1.0);
      }
      for (int i = 0; i < 32; ++i) {
        loResNoiseBuffer[i] = ((i % kLoResNoisePeriod) == 0)
                                  ? to_f32(rng->next() * 2.0 - 1.0)
                                  : loResNoiseBuffer[i - 1];
      }

      pitch_jump_repeat_length_samples =
          lerp(envelope_full_length_samples, kSampleRate / 50.0,
               get(params, "pitch_jump_repeat_speed")) +
          32;

      double pitch_jump_window_size_samples = envelope_full_length_samples;
      if (pitch_jump_repeat_length_samples > 0) {
        pitch_jump_window_size_samples = pitch_jump_repeat_length_samples;
      }

      if (get(params, "pitch_jump_amount") > 0.0) {
        pitch_jump_amount =
            1.0 - get(params, "pitch_jump_amount") * get(params, "pitch_jump_amount") * 0.9;
      } else {
        pitch_jump_amount =
            1.0 + get(params, "pitch_jump_amount") * get(params, "pitch_jump_amount") * 10.0;
      }
      if (get(params, "pitch_jump_2_amount") > 0.0) {
        pitch_jump_2_amount =
            1.0 - get(params, "pitch_jump_2_amount") * get(params, "pitch_jump_2_amount") * 0.9;
      } else {
        pitch_jump_2_amount =
            1.0 + get(params, "pitch_jump_2_amount") * get(params, "pitch_jump_2_amount") * 10.0;
      }

      pitch_jump_current_timestamp_samples = 0;

      if (get(params, "pitch_jump_onset_percent") == 1.0) {
        pitch_jump_timestamp_sample = 0;
      } else {
        pitch_jump_timestamp_sample =
            get(params, "pitch_jump_onset_percent") * pitch_jump_window_size_samples + 32;
      }
      if (get(params, "pitch_jump_onset2_percent") == 1.0) {
        pitch_jump_2_timestamp_sample = 0;
      } else {
        pitch_jump_2_timestamp_sample =
            get(params, "pitch_jump_onset2_percent") * pitch_jump_window_size_samples + 32;
      }

      if (waveType == 9) {
        double sf = get(params, "frequency_start");
        double mf = get(params, "min_frequency_relative_to_starting_frequency");

        double startFrequency_min = param_min("frequency_start");
        double startFrequency_max = param_max("frequency_start");
        double startFrequency_mid = (startFrequency_max + startFrequency_min) / 2;

        double minFrequency_min = param_min("min_frequency_relative_to_starting_frequency");
        double minFrequency_max = param_max("min_frequency_relative_to_starting_frequency");
        double minFrequency_mid = (minFrequency_max + minFrequency_min) / 2;

        double delta_start = (sf - startFrequency_min) / (startFrequency_max - startFrequency_min);
        double delta_min = (mf - minFrequency_min) / (minFrequency_max - minFrequency_min);

        sf = startFrequency_mid + delta_start;
        mf = minFrequency_mid + delta_min;

        frequency_period_samples = 100.0 / (sf * sf + 0.001);
        frequency_maxPeriod_samples = 100.0 / (mf * mf + 0.001);
      }
    }

    slide = 1.0 - get(params, "frequency_slide") * get(params, "frequency_slide") *
                      get(params, "frequency_slide") * 0.01;
    frequency_acceleration = -get(params, "frequency_acceleration") *
                             get(params, "frequency_acceleration") *
                             get(params, "frequency_acceleration") * 0.000001;

    flangerOffset = get(params, "flangerOffset") * get(params, "flangerOffset") * 1020.0;
    if (get(params, "flangerOffset") < 0.0) {
      flangerOffset = -flangerOffset;
    }

    bitcrush_freq = 1.0 - std::pow(get(params, "bitCrush"), 1.0 / 3.0);

    if (to_int32(get(params, "waveType")) == 0) {
      squareDuty = 0.5 - get(params, "squareDuty") * 0.5;
      dutySweep = -get(params, "dutySweep") * 0.00005;
    }

    lpFilterCutoff = get(params, "lpFilterCutoff") * get(params, "lpFilterCutoff") *
                     get(params, "lpFilterCutoff") * 0.1;
    lpFilterDeltaCutoff = 1.0 + get(params, "lpFilterCutoffSweep") * 0.0001;
    lpFilterDamping = 5.0 / (1.0 + get(params, "lpFilterResonance") *
                                       get(params, "lpFilterResonance") * 20.0) *
                      (0.01 + lpFilterCutoff);
    if (lpFilterDamping > 0.8) lpFilterDamping = 0.8;
    lpFilterDamping = 1.0 - lpFilterDamping;
    lpFilterOn = get(params, "lpFilterCutoff") != 1.0;

    lpFilterPos = 0.0;
    lpFilterDeltaPos = 0.0;
    hpFilterPos = 0.0;
    hpFilterCutoff = get(params, "hpFilterCutoff") * get(params, "hpFilterCutoff") * 0.1;
    hpFilterDeltaCutoff = 1.0 + get(params, "hpFilterCutoffSweep") * 0.0003;

    param_reset_period_samples =
        lerp(envelope_full_length_samples, kSampleRate / 10.0, get(params, "repeatSpeed"));
    param_reset_current_timestamp_samples = 0;
  }

  // Returns false if generate_sound exited early without producing a buffer
  // (JS `return true` before assigning this.buffer).
  bool generate_sound(std::vector<float>& out_buffer) {
    const size_t length = static_cast<size_t>(envelope_full_length_samples);
    std::vector<float> buffer(length, 0.f);

    bool finished = false;
    int last_nonzero_sample_index = -1;

    for (size_t i = 0; i < length; ++i) {
      if (finished) {
        // Match JS: return without assigning this.buffer.
        return false;
      }

      if (param_reset_period_samples != 0) {
        param_reset_current_timestamp_samples++;
        if (param_reset_current_timestamp_samples >= param_reset_period_samples) {
          param_reset_current_timestamp_samples = 0;
          reset(false);
        }
      }

      pitch_jump_current_timestamp_samples++;
      if (pitch_jump_current_timestamp_samples >= pitch_jump_repeat_length_samples) {
        pitch_jump_current_timestamp_samples = 0;
        if (pitch_jump_reached) {
          frequency_period_samples /= pitch_jump_amount;
          pitch_jump_reached = false;
        }
        if (pitch_jump_2_reached) {
          frequency_period_samples /= pitch_jump_2_amount;
          pitch_jump_2_reached = false;
        }
      }

      if (!pitch_jump_reached) {
        if (pitch_jump_current_timestamp_samples >= pitch_jump_timestamp_sample) {
          pitch_jump_reached = true;
          frequency_period_samples *= pitch_jump_amount;
        }
      }

      if (!pitch_jump_2_reached) {
        if (pitch_jump_current_timestamp_samples >= pitch_jump_2_timestamp_sample) {
          frequency_period_samples *= pitch_jump_2_amount;
          pitch_jump_2_reached = true;
        }
      }

      slide += frequency_acceleration;
      frequency_period_samples *= slide;

      if (frequency_period_samples > frequency_maxPeriod_samples) {
        frequency_period_samples = frequency_maxPeriod_samples;
        if (minFreqency > 0.0) {
          muted = true;
        }
      }

      periodTemp = frequency_period_samples;

      if (vibratoAmplitude > 0.0) {
        vibratoPhase += vibratoSpeed;
        periodTemp = frequency_period_samples * (1.0 + std::sin(vibratoPhase) * vibratoAmplitude);
      }

      periodTemp = to_int32(periodTemp);
      if (periodTemp < 8) periodTemp = 8;

      if (waveType == 0) {
        squareDuty += dutySweep;
        if (squareDuty < 0.0)
          squareDuty = 0.001;
        else if (squareDuty > 0.5)
          squareDuty = 0.5;
      }

      if (++envelopeTime > attack_length_samples) {
        envelopeTime = 0;
        switch (++envelopeStage) {
          case 1:
            attack_length_samples = envelopeLength1;
            break;
          case 2:
            attack_length_samples = envelopeLength2;
            break;
        }
      }

      switch (envelopeStage) {
        case 0:
          envelopeVolume = envelopeTime * envelopeOverLength0;
          break;
        case 1:
          envelopeVolume =
              1.0 + (1.0 - envelopeTime * envelopeOverLength1) * 2.0 * sustainPunch;
          break;
        case 2:
          envelopeVolume = 1.0 - envelopeTime * envelopeOverLength2;
          break;
        case 3:
          envelopeVolume = 0.0;
          finished = true;
          break;
      }

      if (flanger) {
        flangerOffset += flangerDeltaOffset;
        flangerInt = to_int32(flangerOffset);
        if (flangerInt < 0)
          flangerInt = -flangerInt;
        else if (flangerInt > 1023)
          flangerInt = 1023;
      }

      if (filters && hpFilterDeltaCutoff != 0.0) {
        hpFilterCutoff *= hpFilterDeltaCutoff;
        if (hpFilterCutoff < 0.00001)
          hpFilterCutoff = 0.00001;
        else if (hpFilterCutoff > 0.1)
          hpFilterCutoff = 0.1;
      }

      superSample = 0.0;
      for (int j = 0; j < 8; ++j) {
        phase++;
        if (phase >= periodTemp) {
          phase = phase - periodTemp;

          switch (waveType) {
            case 3:
              for (int n = 0; n < 32; ++n) noiseBuffer[n] = to_f32(rng->next() * 2.0 - 1.0);
              break;
            case 6:
              for (int n = 0; n < 32; ++n) {
                loResNoiseBuffer[n] = ((n % kLoResNoisePeriod) == 0)
                                          ? to_f32(rng->next() * 2.0 - 1.0)
                                          : loResNoiseBuffer[n - 1];
              }
              break;
            case 9: {
              int feedBit = ((oneBitNoiseState >> 1) & 1) ^ (oneBitNoiseState & 1);
              oneBitNoiseState = (oneBitNoiseState >> 1) | (feedBit << 14);
              oneBitNoise = (~oneBitNoiseState & 1) - 0.5;
              break;
            }
          }
        }

        sample = 0;
        double overtonestrength = 1;
        for (double k = 0; k <= overtones; ++k) {
          double tempphase = std::fmod(phase * (k + 1), periodTemp);
          // JS `%` for positives matches fmod for these integer-valued operands.
          int wtype = waveType;
          double tempsample = 0;

          switch (wtype) {
            case 0:
              sample += overtonestrength * ((tempphase / periodTemp < squareDuty) ? 0.5 : -0.5);
              break;
            case 1:
              sample += overtonestrength * (1.0 - (tempphase / periodTemp) * 2.0);
              break;
            case 2: {
              pos = tempphase / periodTemp;
              pos = pos > 0.5 ? (pos - 1.0) * 6.28318531 : pos * 6.28318531;
              tempsample = pos < 0 ? 1.27323954 * pos + 0.405284735 * pos * pos
                                   : 1.27323954 * pos - 0.405284735 * pos * pos;
              sample += overtonestrength *
                        (tempsample < 0
                             ? 0.225 * (tempsample * -tempsample - tempsample) + tempsample
                             : 0.225 * (tempsample * tempsample - tempsample) + tempsample);
              break;
            }
            case 3: {
              int idx = to_int32(tempphase * 32 / to_int32(periodTemp)) % 32;
              if (idx < 0) idx += 32;
              sample += overtonestrength * noiseBuffer[idx];
              break;
            }
            case 4:
              sample += overtonestrength * (std::abs(1.0 - (tempphase / periodTemp) * 2.0) - 1.0);
              break;
            case 5: {
              int sample_index = to_int32(tempphase * 256 / to_int32(periodTemp)) % 256;
              if (sample_index < 0) sample_index += 256;
              double wave_sample = granular_0044[sample_index] / 32768.0 - 1.0;
              sample += overtonestrength * wave_sample;
              break;
            }
            case 6:
              sample += std::tan(3.14159265358979323846 * tempphase / periodTemp) * overtonestrength;
              break;
            case 7: {
              pos = tempphase / periodTemp;
              pos = pos > 0.5 ? (pos - 1.0) * 6.28318531 : pos * 6.28318531;
              tempsample = pos < 0 ? 1.27323954 * pos + 0.405284735 * pos * pos
                                   : 1.27323954 * pos - 0.405284735 * pos * pos;
              double value = 0.75 * (tempsample < 0
                                         ? 0.225 * (tempsample * -tempsample - tempsample) + tempsample
                                         : 0.225 * (tempsample * tempsample - tempsample) + tempsample);

              pos = std::fmod(tempphase * 20, periodTemp) / periodTemp;
              pos = pos > 0.5 ? (pos - 1.0) * 6.28318531 : pos * 6.28318531;
              tempsample = pos < 0 ? 1.27323954 * pos + 0.405284735 * pos * pos
                                   : 1.27323954 * pos - 0.405284735 * pos * pos;
              value += 0.25 * (tempsample < 0
                                   ? 0.225 * (tempsample * -tempsample - tempsample) + tempsample
                                   : 0.225 * (tempsample * tempsample - tempsample) + tempsample);
              sample += overtonestrength * value;
              break;
            }
            case 8: {
              double amp = tempphase / periodTemp;
              sample += overtonestrength * (std::abs(1.0 - amp * amp * 2.0) - 1.0);
              break;
            }
            case 9:
              sample += overtonestrength * oneBitNoise;
              break;
            case 10: {
              int sample_index = to_int32(tempphase * 256 / to_int32(periodTemp)) % 256;
              if (sample_index < 0) sample_index += 256;
              double wave_sample = fmsynth_0012[sample_index] / 32768.0 - 1.0;
              sample += overtonestrength * wave_sample;
              break;
            }
            case 11: {
              int sample_index = to_int32(tempphase * 256 / to_int32(periodTemp)) % 256;
              if (sample_index < 0) sample_index += 256;
              double wave_sample = hvoice_0012[sample_index] / 32768.0 - 1.0;
              sample += overtonestrength * wave_sample;
              break;
            }
          }
          overtonestrength *= (1.0 - overtoneFalloff);
        }

        if (filters) {
          lpFilterOldPos = lpFilterPos;
          lpFilterCutoff *= lpFilterDeltaCutoff;
          if (lpFilterCutoff < 0.0)
            lpFilterCutoff = 0.0;
          else if (lpFilterCutoff > 0.1)
            lpFilterCutoff = 0.1;

          if (lpFilterOn) {
            lpFilterDeltaPos += (sample - lpFilterPos) * lpFilterCutoff;
            lpFilterDeltaPos *= lpFilterDamping;
          } else {
            lpFilterPos = sample;
            lpFilterDeltaPos = 0.0;
          }

          lpFilterPos += lpFilterDeltaPos;

          hpFilterPos += lpFilterPos - lpFilterOldPos;
          hpFilterPos *= 1.0 - hpFilterCutoff;
          sample = hpFilterPos;
        }

        if (flanger) {
          flangerBuffer[flangerPos & 1023] = to_f32(sample);
          sample += flangerBuffer[(flangerPos - flangerInt + 1024) & 1023];
          flangerPos = (flangerPos + 1) & 1023;
        }

        superSample += sample;
      }

      if (superSample > 8.0)
        superSample = 8.0;
      else if (superSample < -8.0)
        superSample = -8.0;

      bitcrush_phase += bitcrush_freq;
      if (bitcrush_phase > 1) {
        bitcrush_phase = 0;
        bitcrush_last = superSample;
      }
      double multiplier = lerp(1, 50 * bitcrush_freq, std::sqrt(bitcrush_freq));
      bitcrush_freq = std::max(std::min(bitcrush_freq + multiplier * bitcrush_freq_sweep, 1.0),
                               0.00001);
      superSample = bitcrush_last;

      superSample = masterVolume * envelopeVolume * superSample * 0.125;

      if (superSample > 0) {
        superSample = std::pow(superSample, compression_factor);
      } else {
        superSample = -std::pow(-superSample, compression_factor);
      }

      if (muted) {
        buffer.resize(i);
        break;
      }

      if (std::abs(superSample) > 0.2e-2) {
        last_nonzero_sample_index = static_cast<int>(i);
      }
      buffer[i] = to_f32(clampd(superSample, -1.0, 1.0));
    }

    if (last_nonzero_sample_index < static_cast<int>(buffer.size()) - 1) {
      last_nonzero_sample_index = std::max(last_nonzero_sample_index, 10);
      buffer.resize(static_cast<size_t>(last_nonzero_sample_index + 1));
    }
    out_buffer = std::move(buffer);
    return true;
  }
};

}  // namespace

RenderResult render_bfxr(ParamMap params, Mulberry32& rng) {
  Dsp dsp;
  dsp.params = std::move(params);
  dsp.rng = &rng;
  dsp.reset(true);

  RenderResult result;
  if (!dsp.generate_sound(result.samples)) {
    result.ok = false;
    result.samples.clear();
    return result;
  }
  result.ok = true;
  return result;
}

RenderResult render_bfxr(const ParamMap& overrides, uint32_t seed) {
  Mulberry32 rng(seed);
  return render_bfxr(merge_params(overrides), rng);
}

}  // namespace bfxr
