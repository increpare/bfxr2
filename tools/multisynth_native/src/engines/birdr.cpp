// Port of js/audio/Birdr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_birdr(const Params& p) {
  const double rate = kRate, tau = 2 * kPi, duration = p.value("duration", 0.8, 0.15, 5);
  std::vector<float> output(static_cast<size_t>(jsround(duration * rate)));
  const double volume = p.value("masterVolume", 0.5);
  if (volume == 0) { finish(output, 0); return output; }
  const int length = static_cast<int>(output.size());
  Rng random(p.value("seed", 0.5));
  const int voice = static_cast<int>(jsround(p.value("voice", 0, 0, 4)));
  const int count = static_cast<int>(jsround(p.value("syllables", 3, 1, 16)));
  const double gap = p.value("gap", 0.3, 0, 0.85);
  const double pitch = 180 * jspow(2, p.value("pitch", 0.58) * 4.8), sweep = p.value("sweep", -0.3, -1, 1), arch = p.value("arch", 0.45, -1, 1);
  const double trill = p.value("trill", 0.15), trillRate = 5 + p.value("trill_rate", 0.4) * 65;
  const double duet = p.value("duet", 0.1), rasp = p.value("rasp", 0.04), breath = p.value("breath", 0.03);
  const double rhythm = p.value("rhythm", 0.12), variation = p.value("variation", 0.25);
  // Repeat a contour with alternating answers and seeded drift, rather than choosing unrelated notes.
  std::vector<double> weights(count);
  for (double& weight : weights) weight = 1 + rhythm * (random() - 0.5) * 1.1;
  double total = 0;
  for (double weight : weights) total += weight;
  struct Syllable { double start, active, shift, curvature, phase; };
  std::vector<Syllable> syllables(count);
  double offset = 0;
  for (int index = 0; index < count; index++) {
    const double span = weights[index] / total * length;
    Syllable& syllable = syllables[index];
    syllable.start = offset; syllable.active = std::max(1.0, span * (1 - gap));
    syllable.shift = variation * ((index % 2 ? -0.6 : 0.15) + (random() - 0.5) * 0.2);
    syllable.curvature = 1 + variation * (random() - 0.5) * 0.5;
    syllable.phase = random() * tau;
    offset += span;
  }
  double phase = random() * tau;
  double second = random() * tau, noiseLow = 0;
  int call = 0;
  const double radii[2] = {std::exp(-kPi * 260 / rate), std::exp(-kPi * 480 / rate)};
  double y1[2] = {0, 0}, y2[2] = {0, 0};
  const double centers[2] = {voice == 3 ? 850.0 : 1550.0, voice == 3 ? 1850.0 : 3200.0};
  const double coeff[2] = {2 * radii[0] * std::cos(tau * centers[0] / rate), 2 * radii[1] * std::cos(tau * centers[1] / rate)};
  // The JS loop body, split so that every sine outside the pitch feedback is
  // batched. Only the sines the chosen voice uses are computed.
  double arg[kBlock], lead[kBlock], envelope[kBlock], bow[kBlock], tremor[kBlock], phases[kBlock], seconds[kBlock];
  double answer[kBlock], tone[kBlock], sine[kBlock], sine2[kBlock], sine3[kBlock], half[kBlock], slow[kBlock];
  int which[kBlock];
  for (int first = 0; first < length; first += kBlock) {
    const int n = std::min(kBlock, length - first);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      while (call < count - 1 && i >= syllables[call + 1].start) call++;
      const Syllable& syllable = syllables[call];
      const double local = i - syllable.start, u = std::min(1.0, local / syllable.active);
      const double attack = std::max(35.0, syllable.active * (voice == 4 ? 0.18 : 0.065));
      const double release = std::max(70.0, syllable.active * (voice == 3 ? 0.4 : 0.2));
      envelope[k] = std::max(0.0, min3(1.0, local / attack, (syllable.active - local) / release));
      which[k] = call; lead[k] = sweep * (u - 0.5) * 1.8;
      arg[k] = kPi * u; phases[k] = tau * trillRate * local / rate + syllable.phase;
    }
    vsin(bow, arg, n);
    vsin(tremor, phases, n);
    if (voice == 4) {
      vpow(arg, bow, 0.6, n);
      for (int k = 0; k < n; k++) envelope[k] *= arg[k];
    } else {
      for (int k = 0; k < n; k++) envelope[k] *= 0.88 + 0.12 * bow[k];
    }
    for (int k = 0; k < n; k++) {
      const Syllable& syllable = syllables[which[k]];
      const double contour = lead[k] + arch * bow[k] * syllable.curvature + syllable.shift;
      const double irregular = rasp * (0.035 * std::sin(phase * 0.47) + 0.022 * std::sin(second * 0.31));
      const double frequency = std::min(10500.0, pitch * jspow(2, contour + trill * 0.2 * tremor[k] + irregular));
      phase += tau * frequency / rate;
      second += tau * std::min(11500.0, frequency * (1.12 + 0.15 * bow[k] + duet * 0.35)) / rate;
      phases[k] = phase; seconds[k] = second;
    }
    vsin(answer, seconds, n);
    for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.5;
    vsin(half, arg, n);
    for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.19;
    vsin(slow, arg, n);
    if (voice < 2) {
      for (int k = 0; k < n; k++) arg[k] = phases[k] + (voice == 1 ? duet * 1.15 * answer[k] : 0);
      vsin(tone, arg, n);
    } else {
      vsin(sine, phases, n);
      if (voice != 4) {
        for (int k = 0; k < n; k++) arg[k] = phases[k] + (voice == 2 ? 0.8 : 1.3) * sine[k];
        vsin(tone, arg, n);
      }
      if (voice != 3) {
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 2;
        vsin(sine2, arg, n);
      }
      if (voice == 2) {
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 3;
        vsin(sine3, arg, n);
      }
    }
    for (int k = 0; k < n; k++) {
      const double noise = random() * 2 - 1;
      noiseLow += (noise - noiseLow) * 0.13;
      double source;
      switch (voice) {
        case 2: source = 0.7 * tone[k] + 0.23 * sine2[k] + 0.12 * sine3[k]; break;
        case 3: source = 0.55 * tone[k] + 0.3 * half[k] + rasp * noiseLow; break;
        case 4: source = 0.88 * sine[k] + 0.1 * sine2[k]; break;
        default: source = tone[k];
      }
      source += duet * 0.28 * answer[k] + rasp * 0.2 * half[k] * (0.65 + 0.35 * slow[k]);
      double resonant = 0;
      for (int band = 0; band < 2; band++) {
        const double sample = (1 - radii[band]) * source + coeff[band] * y1[band] - jspow(radii[band], 2) * y2[band];
        y2[band] = y1[band]; y1[band] = sample; resonant += sample;
      }
      if (voice == 2 || voice == 3) source = source * 0.62 + resonant * 0.85;
      source = source * (1 - breath * 0.45) + breath * (noise - noiseLow) * 0.25;
      const double pulse = 1 - trill * 0.35 + trill * 0.35 * tremor[k];
      output[first + k] = static_cast<float>(source * envelope[k] * pulse * 0.65);
    }
  }
  finish(output, volume);
  return output;
}

MSN_ENGINE("Birdr", render_birdr);

}  // namespace msn
