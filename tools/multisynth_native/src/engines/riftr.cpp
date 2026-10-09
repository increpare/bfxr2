// Port of js/audio/Riftr_DSP.js.
#include "dsp.h"
#include "vmath.h"

#include <limits>

namespace msn {

std::vector<float> render_riftr(const Params& p) {
  const double PI = kPi;
  const double rate = kRate;
  Rng random(p.value("seed", 0.5));
  const double duration = p.value("duration", 1.8, 0.15, 6);
  const int count = static_cast<int>(jsround(duration * rate));
  std::vector<float> output(count);
  const int excitation = static_cast<int>(jsround(p.value("excitation", 0, 0, 4)));
  const double volume = p.value("masterVolume", 0.5);
  if (volume == 0) { finish(output, 0); return output; }
  const double pitch = p.value("pitch", 0.45), bend = p.value("bend", -0.2, -1, 1), space = p.value("space", 0.5);
  const double feedback = p.value("feedback", 0.65) * 0.955;
  const double dispersion = p.value("dispersion", 0.55), motion = p.value("motion", 0.3);
  const double field = p.value("field", 0.7), reverse = p.value("reverse", 0);
  const double tau = 2 * PI, basePitch = 55 * jspow(2, pitch * 5.8);
  const double pitchStep = jspow(2, bend * 3 / count);
  const double baseDelay = (0.003 + space * space * 0.095) * rate;
  static const double ratios[4] = {0.719, 1, 1.337, 1.731};
  struct Line {
    std::vector<float> buffer;
    double delay, depth;
    int index;
    double real, imag, c, s, filter, read;
  };
  Line lines[4];
  for (int index = 0; index < 4; index++) {
    const double delay = std::max(7.0, baseDelay * ratios[index]);
    const double depth = motion * delay * 0.09;
    const double step = tau * (0.17 + motion * 2.3) * (1 + index * 0.13) / rate;
    const double phase = random() * tau;
    lines[index] = {std::vector<float>(static_cast<size_t>(std::ceil(delay + depth + 3))), delay, depth, 0,
                    std::cos(phase), std::sin(phase), std::cos(step), std::sin(step), 0, 0};
  }
  struct Allpass { std::vector<float> buffer; int index; };
  static const double allpassSeconds[4] = {0.0023, 0.0051, 0.0113, 0.0197};
  Allpass allpasses[4];
  for (int k = 0; k < 4; k++)
    allpasses[k] = {std::vector<float>(static_cast<size_t>(
        std::max(1.0, jsround(allpassSeconds[k] * rate * (0.3 + space) * (0.1 + dispersion))))), 0};
  const double apGain = 0.15 + dispersion * 0.59;
  const double damping = 0.48 + (1 - dispersion) * 0.4;
  const double pulseRadius = std::exp(-1 / (rate * (0.015 + space * 0.025)));
  const double tearRadius = std::exp(-1 / (rate * (0.025 + duration * 0.16)));
  double phase = 0, increment = tau * basePitch / rate, pulse = 1, tear = 1, noiseLow = 0;
  const double phaseOffset = random() * tau;
  double packet = 0, packetEnvelope = 0;
  const double packetStep = (8 + motion * 28) / rate;
  const double packetRadius = std::exp(-1 / (rate * 0.013));
  // A read past the end of a Float32Array is undefined, which poisons the
  // line with NaN; finish() later silences it. Mirror that instead of faulting.
  const double undefined = std::numeric_limits<double>::quiet_NaN();
  // The JS sample loop, with the excitation's sines batched ahead of the field.
  double arg[kBlock], phases[kBlock], inner[kBlock], carriers[kBlock], tone[kBlock], shapeA[kBlock], shapeB[kBlock];
  for (int first = 0; first < count; first += kBlock) {
    const int n = std::min(kBlock, count - first);
    auto progressAt = [&](int k) { return static_cast<double>(first + k) / (count - 1); };
    for (int k = 0; k < n; k++) {
      phase += increment; increment *= pitchStep;
      phases[k] = phase; arg[k] = phase * 1.417 + phaseOffset;
    }
    if (excitation != 4) {
      vsin(inner, arg, n);
      for (int k = 0; k < n; k++) arg[k] = phases[k] + 0.55 * inner[k];
      vsin(carriers, arg, n);
    }
    switch (excitation) {
      case 1:
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.498;
        vsin(tone, arg, n);
        for (int k = 0; k < n; k++) arg[k] = PI * std::min(1.0, progressAt(k) / 0.72);
        vsin(shapeA, arg, n);
        break;
      case 2:
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.501;
        vsin(tone, arg, n);
        for (int k = 0; k < n; k++) arg[k] = PI * progressAt(k);
        vsin(shapeA, arg, n);
        for (int k = 0; k < n; k++) arg[k] = tau * progressAt(k) * (2 + motion * 7);
        vsin(shapeB, arg, n);
        break;
      case 3:
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.25;
        vsin(tone, arg, n);
        break;
      case 4:
        for (int k = 0; k < n; k++) arg[k] = phases[k] + std::floor(progressAt(k) * 13) * 1.7;
        vsin(tone, arg, n);
        break;
      default:
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 2.071;
        vsin(tone, arg, n);
    }
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double progress = progressAt(k);
      const double noise = random() * 2 - 1;
      noiseLow += (noise - noiseLow) * 0.12;
      const double carrier = excitation != 4 ? carriers[k] : 0;
      double input;
      switch (excitation) {
        case 1: {
          const double arc = std::max(0.0, shapeA[k]);
          input = (carrier * 0.65 + tone[k] * 0.28 + noiseLow * 0.12) * arc * arc;
          break;
        }
        case 2:
          input = (carrier * 0.48 + tone[k] * 0.32)
              * shapeA[k] * (0.65 + 0.35 * shapeB[k]);
          break;
        case 3:
          input = (noiseLow * 0.95 + carrier * 0.36 + tone[k] * 0.21) * tear;
          break;
        case 4:
          packet += packetStep;
          if (packet >= 1 || i == 0) { packet = std::fmod(packet, 1.0); packetEnvelope = 0.45 + random() * 0.5; }
          input = (tone[k] + noise * 0.12) * packetEnvelope * (1 - progress);
          packetEnvelope *= packetRadius;
          break;
        default:
          input = (carrier * 0.9 + tone[k] * 0.18 + noiseLow * 0.04) * pulse;
      }
      pulse *= pulseRadius; tear *= tearRadius;
      double sum = 0;
      for (Line& line : lines) {
        const double newReal = line.real * line.c - line.imag * line.s;
        line.imag = line.real * line.s + line.imag * line.c; line.real = newReal;
        const int length = static_cast<int>(line.buffer.size());
        double position = line.index - line.delay - line.depth * line.imag;
        if (position < 0) position += length;
        const double floored = std::floor(position), fraction = position - floored;
        const int before = static_cast<int>(floored);
        const int after = before + 1 == length ? 0 : before + 1;
        const double lower = before < length ? static_cast<double>(line.buffer[before]) : undefined;
        const double upper = after < length ? static_cast<double>(line.buffer[after]) : undefined;
        const double sample = lower * (1 - fraction) + upper * fraction;
        line.filter += (sample - line.filter) * damping;
        line.read = line.filter;
        sum += line.read;
      }
      // I - 2vv^T with v=(1,1,1,1)/2 conserves energy at the junction.
      for (Line& line : lines) {
        line.buffer[line.index] = static_cast<float>(input * 0.5 + feedback * (line.read - sum * 0.5));
        if (++line.index == static_cast<int>(line.buffer.size())) line.index = 0;
      }
      double wet = sum * 0.65;
      if (dispersion > 0) {
        for (Allpass& stage : allpasses) {
          const double delayed = stage.buffer[stage.index];
          const double scattered = delayed - apGain * wet;
          stage.buffer[stage.index] = static_cast<float>(wet + apGain * scattered);
          if (++stage.index == static_cast<int>(stage.buffer.size())) stage.index = 0;
          wet = scattered;
        }
      }
      output[i] = static_cast<float>((1 - field) * input + field * wet);
    }
  }
  if (reverse > 0) {
    for (int i = 0; i < count / 2; i++) {
      const int opposite = count - 1 - i;
      const double a = output[i], b = output[opposite];
      output[i] = static_cast<float>(a * (1 - reverse) + b * reverse);
      output[opposite] = static_cast<float>(b * (1 - reverse) + a * reverse);
    }
  }
  finish(output, volume);
  double peak = 0;
  for (float sample : output) peak = std::max(peak, std::fabs(static_cast<double>(sample)));
  // One bounded gain for the whole sound restores presence after cancellation.
  if (peak > volume * 0.00001) {
    const double gain = std::min(4.0, std::max(1.0, volume * 0.9 / peak));
    if (gain > 1) for (float& sample : output) sample = static_cast<float>(sample * gain);
  }
  return output;
}

MSN_ENGINE("Riftr", render_riftr);

}  // namespace msn
