// Port of js/audio/Clonkr_DSP.js.
#include "dsp.h"

namespace msn {

std::vector<float> render_clonkr(const Params& p) {
  struct Material { double pitch, ring, brightness, ratios[8]; };
  static const Material materials[5] = {
      {0.7, 0.34, 0.55, {1, 2.17, 3.04, 4.61, 5.43, 6.8, 8.7, 10.3}},
      {1.55, 1.25, 0.95, {1, 2.32, 4.25, 6.63, 9.38, 12.4, 15.8, 18.1}},
      {0.92, 1.6, 1, {1, 1.48, 2.06, 2.63, 3.52, 4.89, 6.28, 8.13}},
      {1.12, 0.58, 0.74, {1, 1.87, 3.22, 4.74, 6.18, 7.91, 10.2, 12.6}},
      {0.42, 0.16, 0.2, {1, 1.99, 3.02, 4.08, 5.19, 6.31, 7.46, 8.64}}};
  const double rate = kRate;
  Rng random(p.value("seed", 0.5));
  const Material& material = materials[static_cast<int>(jsround(p.value("material", 0, 0, 4)))];
  const int action = static_cast<int>(jsround(p.value("action", 0, 0, 2)));
  const double size = p.value("size", 0.5), hollow = p.value("hollowness", 0.35);
  const double hardness = p.value("hardness", 0.65), damping = p.value("damping", 0.35);
  const double duration = p.value("duration", 0.7, 0.1, 2);
  const double decay = 0.009 + (0.022 + duration * 0.44 * material.ring) * (1 - 0.92 * damping);
  const double contactEnd = action == 0 ? 0.025 : duration;
  const int length = static_cast<int>(std::ceil((contactEnd + std::min(3.5, decay * 7)) * rate));
  std::vector<float> buffer(length), excitation(length);
  const int onset = static_cast<int>(jsround(0.006 * rate));
  auto impact = [&](double time, double strength) {
    const int start = static_cast<int>(jsround(time * rate));
    if (start >= length) return;
    // Soft strikers spread their force over a few milliseconds. A hard
    // striker approaches an impulse and excites the highest modes.
    const int width = static_cast<int>(std::max(1.0, jsround((1 - hardness) * 0.0025 * rate)));
    for (int j = 0; j < width && start + j < length; j++) {
      const double force = width == 1 ? 1 : std::sin(kPi * (j + 0.5) / width) * kPi / (2 * width);
      add(excitation[start + j], force * strength);
    }
    const int noiseLength = static_cast<int>(jsround((0.002 + (1 - hardness) * 0.009) * rate));
    for (int j = 0; j < noiseLength && start + j < length; j++) {
      add(buffer[start + j], (random() * 2 - 1) * std::exp(-j / (noiseLength * 0.2)) * strength * (0.07 + hardness * 0.2));
    }
  };

  impact(onset / rate, 1);
  if (action == 1) {
    double friction = 0;
    const int stop = static_cast<int>(jsround(contactEnd * rate));
    for (int i = onset; i < stop; i++) {
      const double progress = (i - onset) / std::max(1.0, contactEnd * rate - onset);
      friction += ((random() * 2 - 1) - friction) * (0.08 + 0.7 * hardness);
      const double grain = random() < (0.002 + hardness * 0.012) ? (random() * 2 - 1) * 0.2 : 0;
      add(excitation[i], (friction * 0.022 + grain) * jspow(std::sin(kPi * progress), 0.4));
      add(buffer[i], friction * (0.08 + 0.12 * hardness) * std::sin(kPi * progress));
    }
  } else if (action == 2) {
    const int count = static_cast<int>(jsround(4 + duration * 7 + hardness * 7));
    for (int hit = 1; hit < count; hit++) {
      const double progress = static_cast<double>(hit) / count;
      const double time = 0.012 + (contactEnd - 0.025) * (progress + (random() - 0.5) * 0.5 / count);
      const double strength = (0.35 + random() * 0.65) * (1 - progress * 0.6);
      impact(time, strength);
    }
  }

  const double base = 1400 * jspow(2, -size * 4.4) * material.pitch;
  struct Mode { double cos, sin, real, imaginary, weight; };
  Mode modes[8];
  double total = 0;
  for (int index = 0; index < 8; index++) {
    const double detune = 1 + (random() - 0.5) * 0.018;
    const double frequency = std::min(rate * 0.43, base * material.ratios[index] * detune);
    const double angle = kPi * 2 * frequency / rate;
    const double tau = decay / (1 + index * (0.08 + damping * 0.13));
    const double radius = std::exp(-1 / (tau * rate));
    const double weight = std::exp(-index * (0.28 + (1 - hardness) * 0.62 + (1 - material.brightness) * 0.4))
        * (index == 0 ? 1 + hollow * 1.2 : 1 - hollow * 0.35);
    modes[index] = {std::cos(angle) * radius, std::sin(angle) * radius, 0, 0, weight};
    total += weight;
  }
  const double scale = 1.4 / total;
  for (int i = onset; i < length; i++) {
    double sample = 0;
    for (Mode& mode : modes) {
      const double real = mode.real * mode.cos - mode.imaginary * mode.sin + excitation[i];
      mode.imaginary = mode.real * mode.sin + mode.imaginary * mode.cos;
      mode.real = real;
      sample += real * mode.weight;
    }
    add(buffer[i], sample * scale);
  }
  finish(buffer, p.value("masterVolume", 0.5));
  return buffer;
}

MSN_ENGINE("Clonkr", render_clonkr);

}  // namespace msn
