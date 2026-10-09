// Port of js/audio/Transfxr_DSP.js and js/audio/BfxrWaveforms.js.
#include "akwf_tables.h"
#include "dsp.h"
#include "vmath.h"
#include "waveforms.h"

#include <stdexcept>

namespace msn {

namespace {

double blep(double phase, double step) {
  if (phase < step) { const double t = phase / step; return t + t - t * t - 1; }
  if (phase > 1 - step) { const double t = (phase - 1) / step; return t * t + t + t + 1; }
  return 0;
}

}  // namespace

Waveform::Waveform(int type, double seed) : type_(type) {
  // (Math.round(seed*0xffffffff)|0)||1
  double v = std::fmod(jsround(seed * 4294967295.0), 4294967296.0);
  if (v < 0) v += 4294967296.0;
  state_ = static_cast<uint32_t>(v);
  if (state_ == 0) state_ = 1;
  bits_ = (state_ ^ 0x4a35u) & 0x7fffu;
  if (bits_ == 0) bits_ = 1;
  table_ = type == 5 ? bfxr::granular_0044 : type == 10 ? bfxr::fmsynth_0012 : type == 11 ? bfxr::hvoice_0012 : nullptr;
}

double Waveform::operator()(double phase, double step) {
  if (phase < previous_) {
    cell_ = -1;
    const uint32_t feed = ((bits_ >> 1) & 1u) ^ (bits_ & 1u);
    bits_ = (bits_ >> 1) | (feed << 14);
    bit_ = static_cast<double>(~bits_ & 1u) - 0.5;
  }
  previous_ = phase;
  if (table_) {
    const double pos = phase * 256, floored = std::floor(pos);
    const int i = static_cast<int>(floored);
    const double a = table_[i], b = table_[(i + 1) % 256];
    return (a + (b - a) * (pos - floored)) / 32768 - 1;
  }
  switch (type_) {
    case 0: return (phase < 0.5 ? 1 : -1) + blep(phase, step) - blep(mod1(phase + 0.5), step);
    case 1: return 2 * phase - 1 - blep(phase, step);
    case 3: {
      const double next = std::floor(phase * 32);
      if (next != cell_) {
        cell_ = next;
        state_ ^= state_ << 13; state_ ^= state_ >> 17; state_ ^= state_ << 5;
        white_ = static_cast<double>(state_) / 2147483648.0 - 1;
      }
      return white_;
    }
    case 4: return 1 - 4 * std::fabs(phase - 0.5);
    case 6: return std::max(-3.0, std::min(3.0, std::tan(kPi * phase))) / 3;
    case 7: return .75 * std::sin(phase * 2 * kPi) + (step * 20 < .5 ? .25 * std::sin(phase * 40 * kPi) : 0);
    case 8: return 2 * (std::fabs(1 - 2 * phase * phase) - .609475708);
    case 9: return bit_;
    default: return std::sin(phase * 2 * kPi);
  }
}

namespace {

// Transfxr_DSP.curves, by name; unknown names fall back to Linear.
int curve_index(const std::string& name) {
  static const char* names[] = {"Linear", "Ease In", "Ease Out", "Smooth", "Triangle", "Pulse", "Bounce", "Steps"};
  for (int i = 0; i < 8; i++) if (name == names[i]) return i;
  return 0;
}

double curve(int index, double t) {
  switch (index) {
    case 1: return t * t;
    case 2: return 1 - (1 - t) * (1 - t);
    case 3: return t * t * (3 - 2 * t);
    case 4: return 1 - std::fabs(2 * t - 1);
    case 5: return (1 - std::cos(2 * kPi * t)) / 2;
    case 6:
      // Ease-out bounce, bounded and ending exactly at the second state.
      if (t < 1 / 2.75) return 7.5625 * t * t;
      if (t < 2 / 2.75) { t -= 1.5 / 2.75; return 7.5625 * t * t + 0.75; }
      if (t < 2.5 / 2.75) { t -= 2.25 / 2.75; return 7.5625 * t * t + 0.9375; }
      t -= 2.625 / 2.75; return 7.5625 * t * t + 0.984375;
    case 7: return std::min(1.0, std::floor(t * 5) / 4);
    default: return t;
  }
}

struct Envelope {
  double start, end;
  int shape;
  double operator()(double t) const { return start + (end - start) * curve(shape, t); }
};

Envelope envelope(const Params& p, const char* name) {
  const Transition* value = p.transition(name);
  if (!value) throw std::runtime_error(std::string("missing transition: ") + name);
  return {value->start, value->end, curve_index(value->curve)};
}

int wave_id(double choice) {
  static const int ids[12] = {2, 4, 1, 0, 8, 6, 7, 3, 11, 9, 5, 10};
  return choice >= 0 && choice < 12 && choice == std::floor(choice) ? ids[static_cast<int>(choice)] : 2;
}

}  // namespace

std::vector<float> render_transfxr(const Params& p) {
  const double rate = 44100;
  const double duration = p.number("duration"), echo = p.number("echo");
  const int count = static_cast<int>(std::max(2.0, jsround(duration * rate)));
  const int delay = static_cast<int>(jsround(std::min(0.24, std::max(0.075, duration * 0.23)) * rate));
  const double feedback = echo * 0.65;
  const double echoes = feedback > 0 ? std::ceil(std::log(0.0001) / std::log(feedback)) : 0;
  // Controls arrive canonical (echo <= 0.8); anything else is not a sound the app can make.
  if (!(echoes >= 0 && echoes <= 64) || !(duration <= 60)) throw std::runtime_error("invalid audio buffer length");
  const int repeats = static_cast<int>(echoes);
  const int tail = repeats * delay;
  std::vector<float> output(static_cast<size_t>(count) + tail);
  const Envelope envelopes[4] = {envelope(p, "pitch"), envelope(p, "tone"), envelope(p, "vibrato"), envelope(p, "level")};
  double values[4] = {envelopes[0].start, envelopes[1].start, envelopes[2].start, envelopes[3].start};
  const double attack = std::max(0.003, p.number("attack")) * rate;
  const double release = std::max(0.006, p.number("release")) * rate;
  const double damping = 1 / (0.707 + p.number("resonance") * 5);
  Waveform waveform(wave_id(p.number("waveType")));
  const double waveTo = p.value("waveTo", -1, -1e9, 1e9);
  const bool morphing = waveTo >= 0 && waveTo == std::floor(waveTo);
  Waveform destination(morphing ? wave_id(waveTo) : 2);
  const Transition* morphValue = p.transition("morph");
  const Envelope morph = morphValue ? envelope(p, "morph") : Envelope{0, 1, 3};
  double blend = morphValue ? morphValue->start : 0;
  double phase = 0, ic1 = 0, ic2 = 0;
  // The JS sample loop, split so its control-rate pow/sin/tan and the output
  // tanh are batched; the oscillator and filter stay sample by sample.
  double pitch[kBlock], tone[kBlock], vibrato[kBlock], level[kBlock], blends[kBlock];
  double arg[kBlock], wobble[kBlock], bend[kBlock], octave[kBlock], cutoff[kBlock], gain[kBlock], shaped[kBlock];
  for (int first = 0; first < count; first += kBlock) {
    const int n = std::min(kBlock, count - first);
    for (int k = 0; k < n; k++) {
      const double t = static_cast<double>(first + k) / (count - 1);
      if (morphing) blend += (morph(t) - blend) * .012;
      // Two millisecond smoothing avoids clicks with stepped transitions.
      for (int j = 0; j < 4; j++) values[j] += (envelopes[j](t) - values[j]) * 0.012;
      pitch[k] = values[0]; tone[k] = values[1]; vibrato[k] = values[2]; level[k] = values[3]; blends[k] = blend;
    }
    for (int k = 0; k < n; k++) arg[k] = (first + k) / rate * kPi * 16;
    vsin(wobble, arg, n);
    for (int k = 0; k < n; k++) arg[k] = wobble[k] * vibrato[k] * 0.16;
    vpow(bend, 2, arg, n);
    for (int k = 0; k < n; k++) arg[k] = pitch[k] * 7;
    vpow(octave, 2, arg, n);
    vpow(cutoff, 160, tone, n);
    for (int k = 0; k < n; k++) arg[k] = kPi * (100 * cutoff[k]) / (rate * 2);
    vtan(gain, arg, n);
    for (int k = 0; k < n; k++) {
      const double frequency = 40 * octave[k] * bend[k];
      const double step = frequency / (rate * 2);
      const double g = gain[k];
      const double a1 = 1 / (1 + g * (g + damping));
      double sample = 0;
      // Oversample oscillator + topology-preserving state-variable filter.
      for (int sub = 0; sub < 2; sub++) {
        const double source = waveform(phase, step);
        const double osc = morphing ? source * (1 - blends[k]) + destination(phase, step) * blends[k] : source;
        phase = mod1(phase + step);
        const double v1 = a1 * (ic1 + g * (osc - ic2));
        const double v2 = ic2 + g * v1;
        ic1 = 2 * v1 - ic1;
        ic2 = 2 * v2 - ic2;
        sample += v2 * 0.5;
      }
      arg[k] = sample * 1.4;
    }
    vtanh(shaped, arg, n);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double fade = std::min(1.0, i / attack) * std::min(1.0, (count - 1 - i) / release);
      output[i] = static_cast<float>(shaped[k] * level[k] * fade);
    }
  }
  // Echo remains outside the voice envelope, so the last note can ring out.
  const int total = static_cast<int>(output.size());
  for (int i = delay; i < total; i++) add(output[i], output[i - delay] * feedback);
  const double volume = p.number("masterVolume");
  for (int first = 0; first < total; first += kBlock) {
    const int n = std::min(kBlock, total - first);
    for (int k = 0; k < n; k++) arg[k] = output[first + k];
    vtanh(shaped, arg, n);
    for (int k = 0; k < n; k++) {
      const double fade = tail ? std::min(1.0, (total - 1 - (first + k)) / 256.0) : 1;
      output[first + k] = static_cast<float>(shaped[k] * volume * 0.95 * fade);
    }
  }
  return output;
}

MSN_ENGINE("Transfxr", render_transfxr);

}  // namespace msn
