// Port of js/audio/Choirr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_choirr(const Params& p) {
  const double rate = kRate, tau = kPi * 2, duration = p.value("duration", 2.5, 0.15, 5);
  std::vector<float> out(static_cast<size_t>(jsround(duration * rate)));
  const double volume = p.value("masterVolume", 0.5);
  if (volume == 0) { finish(out, 0); return out; }
  const int length = static_cast<int>(out.size());
  Rng random(p.value("seed", 0.5));
  const int voices = static_cast<int>(jsround(p.value("voices", 6, 1, 12)));
  const double pitch = 55 * jspow(2, p.value("pitch", 0.5) * 4), vowel = p.value("vowel", 0.35);
  const double detune = p.value("detune", 0.4), swell = p.value("swell", 0.5), breath = p.value("breath", 0.1);
  const double motion = p.value("motion", 0.4);
  const int harmony = static_cast<int>(jsround(p.value("harmony", 1, 0, 4)));
  static const std::vector<int> chords[5] = {{0}, {0, 4, 7, 12}, {0, 3, 7, 12}, {0, 7, 12, 19}, {0, 1, 6, 10}};
  static const double vowels[3][3] = {{350, 800, 2300}, {750, 1150, 2600}, {300, 2200, 3100}};
  const int vIndex = vowel < 0.5 ? 0 : 1;
  const double blend = vowel < 0.5 ? vowel * 2 : (vowel - 0.5) * 2;
  const double gain = 1.9 / std::sqrt(static_cast<double>(voices));
  const double radii[3] = {std::exp(-kPi * 85 / rate), std::exp(-kPi * 120 / rate), std::exp(-kPi * 190 / rate)};
  const double weights[3] = {1.2, 0.8, 0.5};
  const double exponent = 0.25 + swell * 2.7;
  for (int voice = 0; voice < voices; voice++) {
    const std::vector<int>& chord = chords[harmony];
    const int note = chord[voice % chord.size()];
    const double frequency = pitch * jspow(2, note / 12.0 + (random() - 0.5) * detune * 0.08);
    const double formantScale = 0.92 + random() * 0.16;
    double coeff[3], squares[3], gains[3], y1[3] = {0, 0, 0}, y2[3] = {0, 0, 0};
    for (int k = 0; k < 3; k++) {
      const double r = radii[k];
      coeff[k] = 2 * r * std::cos(tau * (vowels[vIndex][k] * (1 - blend) + vowels[vIndex + 1][k] * blend) * formantScale / rate);
      squares[k] = r * r;
      gains[k] = 1 - r;
    }
    const double initial = random() * tau, vibratoRate = 4.2 + random() * 1.8;
    const int onset = static_cast<int>(jsround(random() * motion * std::min(length * 0.1, 3000.0)));
    double phase = random(), previous = 0, previous2 = 0;
    // The JS loop body, split so its sines and the envelope power are batched.
    double arg[kBlock], vibrato[kBlock], sway[kBlock], envelope[kBlock], resonance[kBlock], tone[kBlock];
    for (int first = onset; first < length; first += kBlock) {
      const int n = std::min(kBlock, length - first);
      for (int k = 0; k < n; k++) arg[k] = tau * vibratoRate * ((first + k) / rate) + initial;
      vsin(vibrato, arg, n);
      for (int k = 0; k < n; k++) arg[k] = tau * 0.7 * ((first + k) / rate) + initial;
      vsin(sway, arg, n);
      for (int k = 0; k < n; k++) arg[k] = kPi * (static_cast<double>(first + k - onset) / (length - onset));
      vsin(tone, arg, n);
      for (int k = 0; k < n; k++) arg[k] = std::max(0.0, tone[k]);
      vpow(envelope, arg, exponent, n);
      for (int k = 0; k < n; k++) {
        const double step = frequency * (1 + motion * 0.009 * vibrato[k]) / rate;
        phase += step; if (phase >= 1) phase -= 1;
        double source = 2 * phase - 1;
        // PolyBLEP softens the discontinuity before the throat filters.
        if (phase < step) { const double x = phase / step; source -= x + x - x * x - 1; }
        else if (phase > 1 - step) { const double x = (phase - 1) / step; source -= x * x + x + x + 1; }
        source = source * (1 - breath * 0.7) + (random() * 2 - 1) * breath * 0.35;
        double resonant = 0;
        for (int band = 0; band < 3; band++) {
          const double sample = gains[band] * (source - previous2) + coeff[band] * y1[band] - squares[band] * y2[band];
          y2[band] = y1[band]; y1[band] = sample;
          resonant += sample * weights[band];
        }
        previous2 = previous; previous = source;
        resonance[k] = resonant;
        arg[k] = tau * phase;
      }
      vsin(tone, arg, n);
      for (int k = 0; k < n; k++)
        add(out[first + k], (resonance[k] + tone[k] * 0.065) * envelope[k] * gain * (0.9 + motion * 0.1 * sway[k]));
    }
  }
  finish(out, volume);
  return out;
}

MSN_ENGINE("Choirr", render_choirr);

}  // namespace msn
