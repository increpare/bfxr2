// Port of js/audio/Pluckr_DSP.js.
#include "dsp.h"

namespace msn {

std::vector<float> render_pluckr(const Params& p) {
  const double PI = kPi;
  const double rate = kRate, duration = p.value("duration", 1.8, 0.15, 5);
  std::vector<float> out(static_cast<size_t>(jsround(duration * rate)));
  const double volume = p.value("masterVolume", 0.5);
  if (volume == 0) { finish(out, 0); return out; }
  const int length = static_cast<int>(out.size());
  Rng random(p.value("seed", 0.5));
  const int count = static_cast<int>(jsround(p.value("strings", 3, 1, 8)));
  const int material = static_cast<int>(jsround(p.value("material", 0, 0, 5)));
  const double pitch = 55 * jspow(2, p.value("pitch", 0.5) * 4), damping = p.value("damping", 0.25);
  const double brightness = p.value("brightness", 0.6);
  const double coupling = p.value("coupling", 0.15), strum = p.value("strum", 0.2), pluck = p.value("pluck", 0.3);
  const double inharmonic = p.value("inharmonic", 0.05);
  const double tremolo = p.value("tremolo", 0), vibrato = p.value("vibrato", 0), speed = p.value("tremoloRate", 4, 0.2, 12);
  // Flexible fibres lose high frequencies; rigid filaments disperse travelling waves.
  struct Matter { double life, average, filter, bright, excite, dispersion; int stages; };
  static const Matter matters[6] = {
      {1, 0.5, 0.18, 0.8, 1, 0, 0},        {1.45, 0.14, 0.65, 0.35, 1.5, 0.2, 1},
      {0.62, 0.55, 0.12, 0.5, 0.6, 0.6, 1}, {0.075, 0.65, 0.1, 0.28, 0.35, 0.4, 1},
      {1.3, 0.06, 0.85, 0.15, 1.8, -0.72, 2}, {0.95, 0.25, 0.4, 0.5, 1.1, -0.45, 2}};
  const Matter matter = matters[material];
  static const int notes[8] = {0, 7, 12, 16, 19, 24, 28, 31};
  struct String {
    std::vector<float> buffer;
    int index = 0;
    double previous = 0, low = 0, allpass = 0, allpassInput = 0;
    float waveInputs[2] = {0, 0}, waveOutputs[2] = {0, 0};
    double fraction = 0, feedback = 0;
    int start = 0;
  };
  std::vector<String> strings(count);
  const double gain = 0.65 / std::sqrt(static_cast<double>(count));
  for (int s = 0; s < count; s++) {
    const double frequency = pitch * jspow(2, notes[s] / 12.0 + (random() - 0.5) * inharmonic * 0.07);
    const double period = rate / frequency, omega = 2 * PI / period, a = matter.dispersion;
    const double dispersionDelay = matter.stages * 2 * std::atan2((1 - a) * std::sin(omega / 2), (1 + a) * std::cos(omega / 2)) / omega;
    const double desired = std::max(2.0, period - matter.average - dispersionDelay), delay = std::max(2.0, std::floor(desired));
    const int size = static_cast<int>(delay);
    String& string = strings[s];
    string.buffer.assign(size, 0.0f);
    double low = 0, mean = 0;
    const double location = 0.05 + pluck * 0.9;
    for (int i = 0; i < size; i++) {
      low += (random() * 2 - 1 - low) * std::min(1.0, (0.05 + brightness * 0.9) * matter.excite);
      const double x = i / delay, triangle = x < location ? x / location : (1 - x) / (1 - location);
      string.buffer[i] = static_cast<float>(low * 0.75 + (triangle - 0.5) * (1 - brightness) * 0.75);
      mean += string.buffer[i];
    }
    mean /= delay;
    for (int i = 0; i < size; i++) string.buffer[i] = static_cast<float>(string.buffer[i] - mean);
    // Clamp the physical loop before deriving its fractional-delay coefficient.
    string.fraction = (1 - (desired - delay)) / (1 + (desired - delay));
    string.feedback = std::exp(-3 / (frequency * (0.07 + jspow(1 - damping, 2) * 4) * matter.life));
    string.start = static_cast<int>(jsround(s * strum * std::min(rate * 0.11, static_cast<double>(length) / std::max(1, count) * 0.65)));
  }
  double bridge = 0;
  for (int i = 0; i < length; i++) {
    double sum = 0, bridgeNext = 0;
    const double dispersion = matter.dispersion + (material == 5 ? 0.22 * std::sin(2 * PI * 1.7 * i / rate) : 0);
    for (int s = 0; s < count; s++) {
      String& string = strings[s];
      if (i < string.start) continue;
      const double current = string.buffer[string.index];
      const double averaged = current * (1 - matter.average) + string.previous * matter.average;
      string.previous = current;
      string.low += (averaged - string.low) * (matter.filter + brightness * matter.bright);
      const double input = string.low;
      double dispersed = string.fraction * input + string.allpassInput - string.fraction * string.allpass;
      string.allpassInput = input; string.allpass = dispersed;
      for (int stage = 0; stage < matter.stages; stage++) {
        const double next = dispersion * dispersed + string.waveInputs[stage] - dispersion * string.waveOutputs[stage];
        string.waveInputs[stage] = static_cast<float>(dispersed);
        string.waveOutputs[stage] = static_cast<float>(next);
        dispersed = next;
      }
      string.buffer[string.index] = static_cast<float>(string.feedback * (dispersed * (1 - coupling * 0.025) + bridge * coupling * 0.025));
      string.index++; if (string.index == static_cast<int>(string.buffer.size())) string.index = 0;
      sum += current; bridgeNext += current;
    }
    bridge = bridgeNext / count;
    // Preserve the exact legacy render when pitch motion is disabled.
    out[i] = static_cast<float>(sum * gain * (vibrato > 0 ? 1 : 1 - tremolo * (0.5 - 0.5 * std::cos(2 * PI * speed * i / rate))));
  }
  // A smooth varying delay bends pitch without changing the string's decay or material.
  if (vibrato > 0) {
    const std::vector<float> dry = out;
    const double depth = (jspow(2, vibrato * 0.75 / 12) - 1) * rate / (2 * PI * speed);
    for (int i = 0; i < length; i++) {
      const double motion = 0.5 - 0.5 * std::cos(2 * PI * speed * i / rate);
      const double position = std::max(0.0, i - depth * 2 * motion), floored = std::floor(position), fraction = position - floored;
      const int index = static_cast<int>(floored);
      out[i] = static_cast<float>((dry[index] * (1 - fraction) + dry[std::min(index + 1, length - 1)] * fraction) * (1 - tremolo * motion));
    }
  }
  finish(out, volume);
  return out;
}

MSN_ENGINE("Pluckr", render_pluckr);

}  // namespace msn
