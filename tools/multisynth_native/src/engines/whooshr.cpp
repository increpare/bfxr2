// Port of js/audio/Whooshr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_whooshr(const Params& p) {
  const double rate = kRate, duration = p.value("duration", 0.6, 0.1, 5);
  const int length = static_cast<int>(jsround(rate * duration));
  std::vector<float> out(length);
  Rng random(p.value("seed", 0.5));
  const double size = p.value("size", 0.4), air = p.value("air", 0.8), whistle = p.value("whistle", 0.25);
  const double movement = p.value("movement", 0.7), focus = p.value("focus", 0.6), flutter = p.value("flutter", 0.1);
  const double pi = kPi, tau = 2 * pi;
  const double base = 190 * jspow(2, (1 - size) * 3.1), offset = random() * tau, beat = 8 + random() * 10;
  double low = 0, broad = 0, phase = offset;
  // The JS loop body, split so its sines, exponentials and the envelope power are batched.
  double arg[kBlock], position[kBlock], approach[kBlock], cutoff[kBlock], envelope[kBlock], swell[kBlock], sway[kBlock];
  double lowDecay[kBlock], broadDecay[kBlock], bands[kBlock], phases[kBlock], tone[kBlock], overtone[kBlock];
  for (int first = 0; first < length; first += kBlock) {
    const int n = std::min(kBlock, length - first);
    for (int k = 0; k < n; k++) {
      const double u = static_cast<double>(first + k) / (length - 1);
      position[k] = (u - 0.5) * 2;
      approach[k] = 1 - movement * 0.7 * position[k];
      cutoff[k] = std::min(12000.0, (350 + 5500 * (1 - size)) * approach[k]);
      arg[k] = pi * u;
    }
    vsin(tone, arg, n);
    vpow(envelope, tone, 0.6 + focus * 5, n);
    for (int k = 0; k < n; k++) arg[k] = tau * beat * ((first + k) / rate) + offset;
    vsin(swell, arg, n);
    for (int k = 0; k < n; k++) arg[k] = tau * beat * ((first + k) / rate);
    vsin(sway, arg, n);
    for (int k = 0; k < n; k++) arg[k] = -tau * cutoff[k] / rate;
    vexp(lowDecay, arg, n);
    for (int k = 0; k < n; k++) arg[k] = -tau * cutoff[k] * 0.14 / rate;
    vexp(broadDecay, arg, n);
    for (int k = 0; k < n; k++) {
      const double noise = random() * 2 - 1;
      low += (1 - lowDecay[k]) * (noise - low);
      broad += (1 - broadDecay[k]) * (noise - broad);
      phase += tau * base * approach[k] * (1 + flutter * 0.025 * sway[k]) / rate;
      if (phase > tau) phase -= tau;
      bands[k] = low - broad; phases[k] = phase; arg[k] = phase * 2;
    }
    vsin(tone, phases, n);
    vsin(overtone, arg, n);
    for (int k = 0; k < n; k++) {
      const double gust = 1 - flutter * 0.65 + flutter * 0.65 * swell[k] * swell[k];
      out[first + k] = static_cast<float>((bands[k] * air * 2.7 + (tone[k] + 0.12 * overtone[k]) * whistle * 0.45)
          * (envelope[k] / (1 + focus * position[k] * position[k] * 7)) * gust);
    }
  }
  finish(out, p.value("masterVolume", 0.5));
  return out;
}

MSN_ENGINE("Whooshr", render_whooshr);

}  // namespace msn
