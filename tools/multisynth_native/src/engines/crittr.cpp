// Port of js/audio/Crittr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_crittr(const Params& p) {
  const double rate = kRate, tau = kPi * 2;
  const double duration = p.value("duration", 1.2, 0.15, 5);
  std::vector<float> output(static_cast<size_t>(jsround(duration * rate)));
  const double volume = p.value("masterVolume", 0.5);
  if (volume == 0) { finish(output, 0); return output; }
  const int length = static_cast<int>(output.size());
  Rng random(p.value("seed", 0.5));
  const int voice = static_cast<int>(jsround(p.value("voice", 0, 0, 7)));
  const double pitch = 45 * jspow(2, 5 * p.value("pitch", 0.45));
  const double size = p.value("size", 0.45), morph = p.value("morph", 0.45);
  const double breath = p.value("breath", 0.15), growl = p.value("growl", 0.2);
  const double flutter = p.value("flutter", 0.2), contour = p.value("contour", 0.25, -1, 1);
  const int calls = static_cast<int>(jsround(p.value("calls", 2, 1, 12)));
  const double slot = static_cast<double>(length) / calls, active = slot * (1 - p.value("gap", 0.2, 0, 0.85));
  const double attack = std::max(40.0, active * (voice == 6 ? 0.025 : voice == 7 ? 0.13 : 0.09));
  const double release = std::max(80.0, active * 0.28);
  const double scale = jspow(2, (0.5 - size) * 2.8);
  static const double anatomies[8][3] = {{550, 1260, 2550}, {820, 2100, 3900}, {360, 950, 1840}, {1100, 2800, 4700},
                                         {430, 1500, 3200}, {670, 1740, 3550}, {430, 1150, 2450}, {700, 1900, 3100}};
  const double radii[3] = {std::exp(-kPi * 100 / rate), std::exp(-kPi * 160 / rate), std::exp(-kPi * 230 / rate)};
  const double weights[3] = {1.15, 0.85, 0.5};
  double frequencies[3], radiiSquared[3], gains[3], coefficients[3] = {0, 0, 0}, y1[3] = {0, 0, 0}, y2[3] = {0, 0, 0};
  for (int band = 0; band < 3; band++) {
    frequencies[band] = std::min(10000.0, anatomies[voice][band] * scale);
    radiiSquared[band] = radii[band] * radii[band];
    gains[band] = (1 - radii[band]) * 0.95;
  }
  std::vector<double> callMotion(calls);
  for (double& motion : callMotion) motion = random() * 2 - 1;
  const double flutterRate = 7 + flutter * 38, flutterStep = tau * flutterRate / rate;
  static const double duties[8] = {0.24, 0.12, 0.3, 0.07, 0.38, 0.1, 0.2, 0.28};
  const double duty = duties[voice];
  double phase = random() * tau;
  double flutterPhase = random() * tau;
  double previous = 0, previous2 = 0, noiseLow = 0;
  // The JS loop body, split so its sines, cosines and exponentials are batched.
  // Only the values the chosen voice uses are computed.
  double arg[kBlock], position[kBlock], envelope[kBlock], motion[kBlock], tremor[kBlock], bend[kBlock], glide[kBlock];
  double phases[kBlock], cycles[kBlock], cosine[kBlock], noises[kBlock], lows[kBlock], sine[kBlock], half[kBlock];
  double third[kBlock], tone[kBlock], tone3[kBlock], burst[kBlock], shape[kBlock];
  for (int first = 0; first < length; first += kBlock) {
    const int n = std::min(kBlock, length - first);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const int call = static_cast<int>(std::min<double>(calls - 1, std::floor(i / slot)));
      const double local = i - call * slot;
      position[k] = std::min(1.0, local / active);
      envelope[k] = std::max(0.0, min3(1.0, local / attack, (active - local) / release));
      motion[k] = callMotion[call];
      bend[k] = contour * ((position[k] - 0.5) * 1.9 + motion[k] * 0.3);
      arg[k] = flutterPhase;
      flutterPhase += flutterStep;
    }
    vsin(tremor, arg, n);
    if (voice == 6) {
      for (int k = 0; k < n; k++) arg[k] = -position[k] * 13;
      vexp(shape, arg, n);
      for (int k = 0; k < n; k++) bend[k] += 0.5 * shape[k] - position[k] * 0.3;
    }
    if (voice == 7) {
      for (int k = 0; k < n; k++) arg[k] = kPi * std::min(1.0, position[k] * 1.35);
      vsin(shape, arg, n);
      for (int k = 0; k < n; k++) bend[k] += 0.5 * shape[k] - 0.3 * position[k];
    }
    for (int k = 0; k < n; k++) arg[k] = bend[k] * 0.69314718056;
    vexp(glide, arg, n);
    for (int k = 0; k < n; k++) {
      phase += tau * pitch * glide[k] * (1 + flutter * 0.045 * tremor[k]) / rate;
      phases[k] = phase;
      cycles[k] = phase / tau - std::floor(phase / tau);
      arg[k] = tau * cycles[k] / duty;
      noises[k] = random() * 2 - 1;
      noiseLow += (noises[k] - noiseLow) * 0.06;
      lows[k] = noiseLow;
    }
    vcos(cosine, arg, n);
    vsin(sine, phases, n);
    for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.5;
    vsin(half, arg, n);
    for (int k = 0; k < n; k++) arg[k] = phases[k] / 3;
    vsin(third, arg, n);
    if (voice == 1 || voice == 3 || voice == 5 || voice == 7) {
      const double ratio = voice == 3 ? 1.47 : voice == 5 ? 2.71 : 2;
      for (int k = 0; k < n; k++) arg[k] = voice == 1 ? phases[k] * ratio + 0.8 * sine[k] : phases[k] * ratio;
      vsin(tone, arg, n);
    }
    if (voice == 6) {
      for (int k = 0; k < n; k++) arg[k] = -position[k] * 20;
      vexp(burst, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -position[k] * 4.5;
      vexp(shape, arg, n);
    }
    if (voice == 7) {
      for (int k = 0; k < n; k++) arg[k] = phases[k] * 3;
      vsin(tone3, arg, n);
      for (int k = 0; k < n; k++) arg[k] = kPi * position[k];
      vsin(shape, arg, n);
    }
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double pulse = cycles[k] < duty ? 0.5 - 0.5 * cosine[k] : 0;
      const double noise = noises[k];
      double excitation = (pulse - duty * 0.5) * 3.4;
      if (voice == 1) excitation += 0.22 * tone[k];
      if (voice == 2) excitation *= 0.7 + 0.3 * half[k];
      if (voice == 3) excitation *= 0.6 + 0.4 * tone[k];
      if (voice == 4) excitation = 0.48 * sine[k] + excitation * 0.3;
      if (voice == 5) excitation += 0.2 * tone[k];
      if (voice == 6) excitation = excitation * (0.85 + 0.15 * half[k]) + noise * 0.65 * burst[k];
      if (voice == 7) excitation += 0.18 * tone[k] + 0.09 * tone3[k];
      excitation = excitation * (1 - breath * 0.8) + noise * breath * 0.9;
      // Change resonances at control rate; oscillator pitch stays independent.
      if ((i & 31) == 0) {
        const double opening = morph * (std::sin(kPi * position[k]) + 0.3 * motion[k]);
        coefficients[0] = 2 * radii[0] * std::cos(tau * std::min(11000.0, frequencies[0] * (1 + opening * 0.65)) / rate);
        coefficients[1] = 2 * radii[1] * std::cos(tau * std::min(11000.0, frequencies[1] * (1 - opening * 0.23)) / rate);
        coefficients[2] = 2 * radii[2] * std::cos(tau * std::min(11000.0, frequencies[2] * (1 + opening * 0.17)) / rate);
        if (voice == 6 || voice == 7) {
          // Bark opens rapidly; meow moves from a nasal /m/ through /a/ into /u/.
          const double mouth = voice == 6 ? std::exp(-position[k] * 5) : jspow(std::sin(kPi * position[k]), 1.4);
          coefficients[0] = 2 * radii[0] * std::cos(tau * std::min(11000.0, frequencies[0] * (0.58 + morph * mouth * 0.95)) / rate);
          coefficients[1] = 2 * radii[1] * std::cos(tau * std::min(11000.0, frequencies[1] * (1 - morph * position[k] * 0.58)) / rate);
        }
      }
      double resonant = 0;
      for (int band = 0; band < 3; band++) {
        const double sample = gains[band] * (excitation - previous2) + coefficients[band] * y1[band] - radiiSquared[band] * y2[band];
        y2[band] = y1[band]; y1[band] = sample;
        resonant += sample * weights[band];
      }
      previous2 = previous; previous = excitation;
      const double subharmonic = growl * (0.28 * half[k] + 0.1 * third[k]) * (0.85 + lows[k] * 0.7);
      const double throat = resonant * 1.65 + 0.12 * (1 - breath) * sine[k] + subharmonic;
      const double trill = 1 - flutter * 0.42 + flutter * 0.42 * tremor[k];
      const double articulation = voice == 6 ? shape[k] : voice == 7 ? 0.75 + 0.25 * shape[k] : 1;
      output[i] = static_cast<float>(throat * envelope[k] * trill * articulation);
    }
  }
  finish(output, volume);
  return output;
}

MSN_ENGINE("Crittr", render_crittr);

}  // namespace msn
