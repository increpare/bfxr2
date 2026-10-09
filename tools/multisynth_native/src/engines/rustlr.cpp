// Port of js/audio/Rustlr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_rustlr(const Params& p) {
  struct Material { double cutoff, soft, highpass, crease, stick, flex; };
  static const Material materials[6] = {
      {4200, 0.35, 0.65, 0.85, 0.5, 720},   {950, 1, 0.2, 0.08, 0.15, 180},
      {1900, 0.65, 0.32, 0.38, 1, 330},     {6400, 0.25, 0.72, 1.1, 0.6, 1150},
      {12500, 0.06, 0.92, 1.35, 0.3, 2600}, {4500, 0.15, 0.55, 0.5, 0.2, 1500}};
  const double rate = kRate, duration = p.value("duration", 0.65, 0.08, 3);
  const int frames = static_cast<int>(jsround(duration * rate));
  std::vector<float> out(frames);
  const int kind = static_cast<int>(jsround(p.value("material", 0, 0, 5)));
  const Material material = materials[kind];
  const int gesture = static_cast<int>(jsround(p.value("gesture", 1, 0, 3)));
  const double grain = p.value("grain", 0.45), density = p.value("density", 0.5);
  const double motion = p.value("motion", 0, -1, 1), pressure = p.value("pressure", 0.5);
  const double brightness = p.value("brightness", 0.5);
  const int folds = static_cast<int>(jsround(p.value("folds", 3, 1, 12)));
  Rng random(p.value("seed", 0.5));
  const double pi = kPi;
  const double cutoff = material.cutoff * (0.22 + brightness * 1.18) / (1 + grain * 0.65) * (0.8 + pressure * 0.4);
  const double filter = 1 - std::exp(-2 * pi * cutoff / rate);
  const double slowFilter = 1 - std::exp(-2 * pi * std::max(60.0, cutoff * 0.13) / rate);
  const double flexFilter = 1 - std::exp(-2 * pi * material.flex * (0.7 + pressure * 0.8) / rate);
  const double grainFrames = std::max(8.0, jsround((0.0007 + grain * grain * 0.023) * (1 + material.soft) * rate));
  const double count = std::max(8.0, jsround(duration * (48 + density * 780) / (1 + grain * 1.4)));
  const int clusterCount = folds + 2;
  std::vector<double> centers;
  for (int i = 0; i < clusterCount; i++) centers.push_back((i + 0.2 + random() * 0.6) / clusterCount);
  const double normalizer = 1 / std::sqrt(1 + count * grainFrames / frames * 0.12);
  const double gain = (0.24 + pressure * 0.76) * normalizer * 2;
  double arg[kBlock], tone[kBlock], window[kBlock];
  // The JS loop bodies below are split so their windows and envelopes are batched.
  auto addGrain = [&](int start, int length, double strength, bool crease) {
    double low = 0, slow = 0, flex = 0, previousFlex = 0;
    // Compliant folds bend for longer; thin film releases abruptly.
    const double attack = 0.025 + material.soft * 0.22;
    const int stop = std::min(length, frames - start);
    for (int first = 0; first < stop; first += kBlock) {
      const int n = std::min(kBlock, stop - first);
      auto age = [&](int k) { return static_cast<double>(first + k) / length; };
      if (crease) {
        for (int k = 0; k < n; k++) arg[k] = -age(k) * (5 - material.soft * 2);
        vexp(tone, arg, n);
        for (int k = 0; k < n; k++) window[k] = std::min(1.0, age(k) / attack) * tone[k];
      } else {
        for (int k = 0; k < n; k++) arg[k] = pi * age(k);
        vsin(tone, arg, n);
        for (int k = 0; k < n; k++) window[k] = tone[k] * tone[k];
      }
      for (int k = 0; k < n; k++) {
        const double noise = random() * 2 - 1;
        low += (noise - low) * filter;
        slow += (low - slow) * slowFilter;
        flex += (low - flex) * flexFilter;
        const double surface = low - slow * material.highpass;
        const double bending = (flex - previousFlex) * rate / (material.flex * 2 * pi);
        add(out[start + first + k], (surface + (crease ? bending * (0.5 + material.soft) : 0.0)) * window[k] * strength);
        previousFlex = flex;
      }
    }
  };
  for (int i = 0; i < count; i++) {
    double position;
    if (kind == 5) {
      // Zip teeth follow the pull's changing speed, with small seeded defects.
      position = jspow((i + 0.25 + random() * 0.5) / count, 1.35 - motion * 0.35);
    } else {
      const double center = centers[static_cast<size_t>(std::floor(random() * clusterCount))];
      const double first = random(), second = random();
      position = std::max(0.0, std::min(0.96, center + (first + second - 1) * (0.035 + density * 0.24)));
    }
    const double length = std::max(6.0, jsround(grainFrames * (0.45 + random() * 1.1)));
    const double start = jsround(position * (frames - length));
    const double strength = gain * (0.16 + random() * 0.3) * (kind == 5 ? 1.4 : 1);
    addGrain(static_cast<int>(std::max(0.0, start)), static_cast<int>(length), strength, false);
  }
  for (int fold = 0; fold < folds; fold++) {
    const double position = (fold + 0.3 + random() * 0.45) / folds;
    const double length = std::max(8.0, jsround((0.003 + grain * 0.022 + material.soft * 0.016) * rate * (0.65 + random() * 0.65)));
    const double start = std::max(0.0, jsround(position * (frames - length)));
    const double strength = gain * (0.42 + random() * 0.45) * material.crease;
    addGrain(static_cast<int>(start), static_cast<int>(length), strength, true);
  }
  // Elastic loading and release modulate the friction, especially for leather.
  // Pressure raises the breakaway force and makes a slip last longer.
  const double slipLoss = std::exp(-1 / ((0.0015 + material.soft * 0.017) * (0.6 + pressure) * rate));
  double friction = 0, frictionSlow = 0, shear = 0, slip = 0, motionLow = 0;
  double breakaway = 0.7 + random() * 0.6;
  double positions[kBlock], arch[kBlock], lift[kBlock], envelope[kBlock], travel[kBlock];
  for (int first = 0; first < frames; first += kBlock) {
    const int n = std::min(kBlock, frames - first);
    for (int k = 0; k < n; k++) {
      positions[k] = static_cast<double>(first + k) / (frames - 1);
      arg[k] = pi * positions[k];
    }
    vsin(tone, arg, n);
    for (int k = 0; k < n; k++) arch[k] = std::max(0.0, tone[k]);
    vpow(lift, arch, 0.6, n);
    if (gesture == 0) {
      vpow(envelope, arch, 0.35, n);
      for (int k = 0; k < n; k++) arg[k] = -positions[k] * 4.5;
      vexp(tone, arg, n);
      for (int k = 0; k < n; k++) envelope[k] = envelope[k] * tone[k] * 2;
    } else if (gesture == 1) {
      vpow(envelope, arch, 0.7, n);
      for (int k = 0; k < n; k++) arg[k] = pi * 2 * positions[k];
      vsin(tone, arg, n);
      for (int k = 0; k < n; k++) envelope[k] = envelope[k] * (0.55 + 0.45 * std::fabs(tone[k]));
    } else if (gesture == 2) {
      vpow(envelope, arch, 0.45, n);
    } else {
      vpow(envelope, arch, 0.5, n);
      for (int k = 0; k < n; k++) arg[k] = pi * folds * positions[k];
      vsin(tone, arg, n);
      for (int k = 0; k < n; k++) envelope[k] = envelope[k] * (0.2 + 0.8 * std::fabs(tone[k]));
    }
    for (int k = 0; k < n; k++) arg[k] = motion * (positions[k] - 0.5) * 5 - std::fabs(motion) * 1.4;
    vexp(travel, arg, n);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      friction += (random() * 2 - 1 - friction) * filter;
      frictionSlow += (friction - frictionSlow) * slowFilter;
      motionLow += (random() * 2 - 1 - motionLow) * 0.0012;
      const double speed = (0.3 + lift[k]) * (0.7 + std::min(0.8, std::fabs(motionLow) * 12));
      shear += speed * (30 + density * 130) / rate / (0.6 + pressure * material.stick * 2);
      if (shear > breakaway) {
        shear -= breakaway;
        slip += 0.45 + pressure * material.stick * 1.5;
        breakaway = 0.65 + random() * 0.8;
      }
      slip *= slipLoss;
      const double bed = (friction - frictionSlow * material.highpass) * gain * (0.07 + density * 0.12)
          * (0.6 + material.soft * 1.3) * speed * (0.45 + material.stick * slip + shear * 0.35);
      out[i] = static_cast<float>((out[i] + bed) * envelope[k] * travel[k]);
    }
  }
  finish(out, p.value("masterVolume", 0.5));
  return out;
}

MSN_ENGINE("Rustlr", render_rustlr);

}  // namespace msn
