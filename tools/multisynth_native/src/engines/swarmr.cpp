// Port of js/audio/Swarmr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_swarmr(const Params& p) {
  const double rate = kRate, duration = p.value("duration", 1.8, 0.25, 5);
  const int frames = static_cast<int>(jsround(duration * rate));
  std::vector<float> out(frames);
  const int count = static_cast<int>(jsround(p.value("count", 14, 3, 32)));
  const int kind = static_cast<int>(jsround(p.value("kind", 0, 0, 5)));
  const double speed = p.value("speed", 0.5), cohesion = p.value("cohesion", 0.3), agitation = p.value("agitation", 0.25);
  const double size = p.value("size", 0.45), movement = p.value("movement", 0.5), scatter = p.value("scatter", 0.2);
  Rng random(p.value("seed", 0.5));
  const double pi = kPi;
  const double base = 90 * jspow(2, (1 - size) * 3.8), pulseRate = 2 + speed * 17;
  const double gain = 0.44 / std::sqrt(static_cast<double>(count)), tau = kPi * 2;
  for (int agent = 0; agent < count; agent++) {
    const int start = static_cast<int>(std::floor(random() * scatter * frames * 0.42));
    const double pulseOffset = random() * (1 - cohesion);
    const double initialPhase = random() * tau;
    const double spread = (random() - 0.5) * (0.08 + 0.8 * (1 - cohesion));
    const double detune = jspow(2, spread);
    const double driftPhase = random() * tau;
    const double driftRate = 0.4 + random() * 2;
    const double center = 0.4 + random() * 0.2;
    const double voiceGain = gain * (0.8 + random() * 0.4);
    const double pulseSpeed = pulseRate * (1 + (random() - 0.5) * (1 - cohesion) * 0.3);
    double phase = initialPhase, filteredNoise = 0, wingNoise = 0;
    // The JS loop body, split so its sines and powers are batched. Only the
    // values the chosen agent kind uses are computed.
    double arg[kBlock], drift[kBlock], beats[kBlock], wing[kBlock], airflow[kBlock], window[kBlock];
    double stroke[kBlock], envelope[kBlock], phases[kBlock], noises[kBlock], filtered[kBlock], turbulence[kBlock];
    double sine[kBlock], sine2[kBlock], sine3[kBlock], sine6[kBlock], blade[kBlock];
    for (int first = start; first < frames; first += kBlock) {
      const int n = std::min(kBlock, frames - first);
      auto age = [&](int k) { return static_cast<double>(first + k - start) / (frames - start); };
      for (int k = 0; k < n; k++) arg[k] = tau * driftRate * ((first + k) / rate) + driftPhase;
      vsin(drift, arg, n);
      for (int k = 0; k < n; k++) {
        beats[k] = mod1((first + k) / rate * pulseSpeed + pulseOffset);
        arg[k] = tau * beats[k];
      }
      if (kind != 3) {
        vsin(wing, arg, n);
        for (int k = 0; k < n; k++) arg[k] = pi * age(k);
        vsin(window, arg, n);
        for (int k = 0; k < n; k++) arg[k] = std::max(0.0, window[k]);
        vpow(window, arg, 0.7, n);
      }
      if (kind == 0 || kind == 2) {
        for (int k = 0; k < n; k++) arg[k] = tau * (driftRate * 1.73) * ((first + k) / rate) + initialPhase;
        vsin(airflow, arg, n);
        for (int k = 0; k < n; k++) airflow[k] = 1 + agitation * 0.4 * airflow[k];
      }
      if (kind == 0) {
        // Opposite strokes have different force; an individual wing never holds a pure note.
        for (int k = 0; k < n; k++) arg[k] = std::max(0.0, wing[k]);
        vpow(stroke, arg, 3, n);
        for (int k = 0; k < n; k++) arg[k] = std::max(0.0, -wing[k]);
        vpow(envelope, arg, 5, n);
        for (int k = 0; k < n; k++) stroke[k] = stroke[k] + 0.32 * envelope[k];
      } else if (kind == 1) {
        for (int k = 0; k < n; k++) arg[k] = std::max(0.0, wing[k]);
        vpow(envelope, arg, 6, n);
      }
      for (int k = 0; k < n; k++) {
        const int i = first + k;
        const double beat = beats[k];
        const double travel = 1 + movement * 0.55 * (1 - 2 * age(k));
        const double jitter = 1 + agitation * 0.12 * drift[k];
        double frequency = base * detune * travel * jitter;
        if (kind == 1) frequency *= 1.3 + 2.2 * (1 - beat);
        else if (kind == 2) frequency *= 0.32;
        else if (kind == 3) {
          frequency *= 2.3;
          // Each arrival contributes a tick even when the shared clock's
          // first pulse passed before this emitter entered a short sound.
          const double arrivalBeat = (i - start) * pulseSpeed / rate;
          envelope[k] = std::max(beat < 0.2 ? jspow(1 - beat / 0.2, 5) : 0.0,
                                 arrivalBeat < 0.2 ? jspow(1 - arrivalBeat / 0.2, 5) : 0.0);
          const double paired = beat - 0.24 - agitation * 0.035 * drift[k];
          if (paired >= 0 && paired < 0.16) envelope[k] += 0.62 * jspow(1 - paired / 0.16, 4);
          window[k] = min3(1.0, (i - start) / (rate * 0.002), (frames - 1 - i) / (rate * 0.005));
        }
        else if (kind == 4) frequency *= 0.75;
        else if (kind == 5) frequency *= 0.28;
        phase += tau * frequency / rate;
        // Keep accumulated phase small without a modulo in the oscillator loop.
        if (phase > tau) phase -= tau;
        const double noise = random() * 2 - 1;
        filteredNoise += 0.08 * (noise - filteredNoise);
        wingNoise += (noise - wingNoise) * (0.16 + 0.32 * (1 - size));
        phases[k] = phase; noises[k] = noise; filtered[k] = filteredNoise;
        turbulence[k] = wingNoise - filteredNoise;
      }
      vsin(sine, phases, n);
      if (kind == 0 || kind == 1 || kind == 4) {
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 2;
        vsin(sine2, arg, n);
      }
      if (kind == 0 || kind == 2) {
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 3;
        vsin(sine3, arg, n);
      }
      if (kind == 2) {
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 6;
        vsin(sine6, arg, n);
        // The motor turns below the blade-pass tone; narrow blade wakes carry broadband air.
        for (int k = 0; k < n; k++) arg[k] = 0.5 + 0.5 * sine3[k];
        vpow(blade, arg, 5, n);
      }
      for (int k = 0; k < n; k++) {
        double signal;
        switch (kind) {
          case 0:
            signal = (sine[k] + 0.22 * sine2[k] + 0.12 * sine3[k]) * (0.08 + 0.4 * stroke[k]);
            signal += (turbulence[k] * 3.4 + filtered[k] * 0.6) * (0.12 + 1.4 * stroke[k]) * airflow[k];
            break;
          case 1: signal = (sine[k] + 0.2 * sine2[k]) * envelope[k]; break;
          case 2:
            signal = (0.62 * sine[k] + 0.28 * sine3[k] + 0.15 * sine6[k]) * (0.75 + 0.25 * wing[k]);
            signal += (turbulence[k] * 2.1 + noises[k] * 0.12) * (0.25 + blade[k]) * airflow[k];
            break;
          case 3: signal = (noises[k] * 0.65 + sine[k] * 0.5) * envelope[k]; break;
          case 4: signal = sine[k] * (0.75 + 0.25 * wing[k]) + 0.12 * sine2[k]; break;
          default: signal = (filtered[k] * 2.5 + sine[k] * 0.25 + noises[k] * 0.07) * (0.7 + 0.3 * wing[k]);
        }
        const double distance = (age(k) - center) * 3;
        const double flyby = 1 / (1 + movement * distance * distance * 4);
        add(out[first + k], signal * window[k] * flyby * voiceGain);
      }
    }
  }
  finish(out, p.value("masterVolume", 0.5));
  return out;
}

MSN_ENGINE("Swarmr", render_swarmr);

}  // namespace msn
