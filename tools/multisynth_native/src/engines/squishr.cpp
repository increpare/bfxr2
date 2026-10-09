// Port of js/audio/Squishr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_squishr(const Params& p) {
  const double rate = kRate;
  Rng random(p.value("seed", 0.5));
  const int texture = static_cast<int>(jsround(p.value("texture", 0, 0, 5)));
  const double viscosity = p.value("viscosity", 0.6), stretch = p.value("stretch", 0.4);
  const double pressure = p.value("pressure", 0.6), wetness = p.value("wetness", 0.75);
  const double bubbleSize = p.value("bubbleSize", 0.55), duration = p.value("duration", 0.65, 0.1, 3);
  const double release = 0.06 + viscosity * 0.16 + stretch * 0.13;
  const int length = static_cast<int>(std::ceil((duration + release) * rate));
  std::vector<float> buffer(length);
  const double base = 1650 * jspow(2, -bubbleSize * 3.8);
  const double amplitude = 0.45 + pressure * 0.7;
  const double onset = 0.008;
  struct Event { int start, length; double frequency, strength, phase; };
  std::vector<Event> events;
  // Callers evaluate their random arguments left to right before this runs.
  auto addBubble = [&](double start, double strength, double pitch, double life) {
    const double seconds = (0.026 + viscosity * 0.065 + stretch * 0.13) * life;
    const double frequency = base * pitch * (0.84 + random() * 0.32);
    const double phase = random() * 0.2;
    events.push_back({static_cast<int>(jsround(start * rate)), static_cast<int>(jsround(seconds * rate)),
                      frequency, strength, phase});
  };

  if (texture == 1) {
    const int count = static_cast<int>(std::max(1.0, jsround(duration * (2 + pressure * 7))));
    for (int i = 0; i < count; i++) {
      const double strength = 0.7 + random() * 0.3;
      const double pitch = 0.8 + random() * 0.4;
      addBubble(onset + i * duration * 0.85 / count, strength, pitch, 1.1);
    }
  } else if (texture == 2) {
    // Suction builds slowly, then breaks into one rounded release pop.
    addBubble(duration * 0.76, 1.2, 0.75, 1.5);
    addBubble(duration * 0.87, 0.55, 1.3, 0.7);
  } else if (texture == 3) {
    for (int i = 0; i < 7; i++) {
      const double start = onset + random() * duration * 0.34;
      const double strength = 0.4 + random() * 0.45;
      const double pitch = 0.6 + random() * 1.1;
      const double life = 0.6 + random() * 0.6;
      addBubble(start, strength, pitch, life);
    }
  } else if (texture == 4) {
    const int count = static_cast<int>(std::max(1.0, jsround(duration * (3 + pressure * 3))));
    for (int i = 0; i < count; i++) {
      const double time = onset + i * duration * 0.82 / count;
      addBubble(time, 1, 0.62, 1.4);
      addBubble(time + 0.035, 0.45, 1.35, 0.7);
    }
  } else {
    const int count = static_cast<int>(std::max(2.0, jsround(duration * (5 + pressure * 10))));
    for (int i = 0; i < count; i++) {
      const double strength = 0.3 + random() * 0.5;
      const double pitch = texture == 5 ? 0.7 : 0.5 + random() * 0.8;
      const double life = texture == 5 ? 2 : 0.65 + random() * 0.65;
      addBubble(onset + i * duration * 0.88 / count, strength, pitch, life);
    }
  }

  double lowNoise = 0, smoothNoise = 0, bodyPhase = 0, previous = 0;
  const double cutoff = 180 + (1 - viscosity) * 3800 + pressure * 500;
  const double filter = 1 - std::exp(-kPi * 2 * cutoff / rate);
  // The JS sample loops, split so their sines, exponentials and powers are batched.
  double arg[kBlock], wobble[kBlock], shape[kBlock], phases[kBlock], inner[kBlock], bodies[kBlock];
  for (int first = 0; first < length; first += kBlock) {
    const int n = std::min(kBlock, length - first);
    auto progress = [&](int k) { return std::min(1.0, (first + k) / rate / duration); };
    for (int k = 0; k < n; k++) arg[k] = (first + k) / rate * (12 + pressure * 20);
    vsin(wobble, arg, n);
    if (texture == 2) {
      for (int k = 0; k < n; k++) arg[k] = kPi * std::min(1.0, progress(k) / 0.85);
      vsin(shape, arg, n);
      for (int k = 0; k < n; k++) shape[k] = shape[k] * shape[k];
    } else if (texture == 3) {
      for (int k = 0; k < n; k++) arg[k] = -progress(k) * (5 - viscosity * 2);
      vexp(shape, arg, n);
    } else if (texture == 4) {
      for (int k = 0; k < n; k++) arg[k] = progress(k) * kPi * (3 + pressure * 3);
      vsin(shape, arg, n);
      for (int k = 0; k < n; k++) shape[k] = (0.4 + 0.6 * (shape[k] * shape[k])) * (1 - progress(k) * 0.6);
    } else {
      for (int k = 0; k < n; k++) arg[k] = kPi * progress(k);
      vsin(inner, arg, n);
      vpow(shape, inner, 0.55, n);
    }
    for (int k = 0; k < n; k++) {
      const double bodyFrequency = base * (texture == 5 ? 0.27 : 0.16)
          * (1 + wobble[k] * stretch * 0.3)
          * (texture == 2 ? 1.6 - progress(k) : 1 - progress(k) * stretch * 0.45);
      bodyPhase += kPi * 2 * bodyFrequency / rate;
      phases[k] = bodyPhase; arg[k] = bodyPhase * 0.5;
    }
    vsin(inner, arg, n);
    for (int k = 0; k < n; k++) arg[k] = phases[k] + inner[k] * stretch;
    vsin(bodies, arg, n);
    for (int k = 0; k < n; k++) {
      const double time = (first + k) / rate;
      const double tail = time <= duration ? 1 : std::exp(-(time - duration) / (release * 0.2));
      const double noise = random() * 2 - 1;
      lowNoise += (noise - lowNoise) * filter;
      smoothNoise += (lowNoise - smoothNoise) * filter;
      const double envelope = shape[k];
      const double attack = std::min(1.0, time / 0.009);
      const double body = bodies[k] * (texture == 5 ? 0.4 : 0.13) * (0.25 + viscosity * 0.75);
      const double rasp = (smoothNoise * (0.6 + wetness * 0.45) + (lowNoise - previous) * (1 - viscosity) * 0.25);
      const double noiseLevel = texture == 1 ? 0.015 : texture == 5 ? 0.14 : texture == 3 ? 1.1 : 0.7;
      const double bodyLevel = texture == 1 ? 0.03 : 1;
      buffer[first + k] = static_cast<float>((rasp * noiseLevel + body * bodyLevel) * envelope * tail * amplitude * attack);
      previous = lowNoise;
    }
  }

  for (const Event& event : events) {
    double phase = event.phase;
    const int span = std::min(event.length, length - event.start);
    for (int first = 0; first < span; first += kBlock) {
      const int n = std::min(kBlock, span - first);
      auto progress = [&](int k) { return static_cast<double>(first + k) / event.length; };
      if (texture == 5) {
        for (int k = 0; k < n; k++) arg[k] = progress(k) * kPi * (3 + stretch * 5);
        vsin(wobble, arg, n);
      } else if (texture != 2 && texture != 4) {
        for (int k = 0; k < n; k++) arg[k] = progress(k) * kPi;
        vsin(wobble, arg, n);
      }
      for (int k = 0; k < n; k++) arg[k] = -progress(k) * (5 - viscosity * 2);
      vexp(shape, arg, n);
      for (int k = 0; k < n; k++) {
        double glide;
        if (texture == 2 || texture == 4) glide = 1.65 - progress(k) * (1.1 + stretch * 0.3);
        else if (texture == 5) glide = 1 + wobble[k] * stretch * 0.6;
        else glide = 0.65 + progress(k) * (0.8 + pressure * 1.5) + wobble[k] * stretch * 0.5;
        phase += kPi * 2 * event.frequency * glide / rate;
        phases[k] = phase; arg[k] = phase * 2;
      }
      vsin(inner, phases, n);
      vsin(bodies, arg, n);
      for (int k = 0; k < n; k++) {
        const int j = first + k;
        const double envelope = std::min(1.0, j / (rate * 0.0015)) * shape[k] * std::min(1.0, (1 - progress(k)) * 15);
        const double rounded = inner[k] + bodies[k] * (1 - viscosity) * 0.13;
        add(buffer[event.start + j], rounded * envelope * event.strength * amplitude * (0.25 + wetness * 0.7));
      }
    }
  }
  finish(buffer, p.value("masterVolume", 0.5));
  return buffer;
}

MSN_ENGINE("Squishr", render_squishr);

}  // namespace msn
