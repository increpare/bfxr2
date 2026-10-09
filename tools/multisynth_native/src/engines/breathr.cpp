// Port of js/audio/Breathr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_breathr(const Params& p) {
  const double rate = kRate, tau = kPi * 2, duration = p.value("duration", 2.7, 0.15, 5);
  std::vector<float> out(static_cast<size_t>(jsround(duration * rate)));
  const double volume = p.value("masterVolume", 0.5);
  if (volume == 0) { finish(out, 0); return out; }
  const int length = static_cast<int>(out.size());
  // Missing mode retains the original cycle for saved/raw parameter objects.
  const bool single = jsround(p.value("mode", 1, 0, 1)) == 0;
  const double inward = (1 - p.value("direction", 1, -1, 1)) / 2;
  Rng random(p.value("seed", 0.5));
  const int cycles = single ? 1 : static_cast<int>(jsround(p.value("cycles", 1, 1, 10)));
  const int source = static_cast<int>(jsround(p.value("source", 0, 0, 2)));
  const double effort = p.value("effort", 0.55), inhale = p.value("inhale", 0.42, 0.1, 0.9), hold = p.value("hold", 0.04, 0, 0.7);
  const double throat = p.value("throat", 0.5), rasp = p.value("rasp", 0.1), flutter = p.value("flutter", 0.15), space = p.value("space", 0.1);
  const double slot = static_cast<double>(length) / cycles, inEnd = (1 - hold) * inhale * 0.9;
  const double outStart = inEnd + hold * 0.9 + 0.025, outEnd = 0.965;
  const int delay = static_cast<int>(jsround(rate * (0.022 + space * 0.075)));
  const double gain = 1.5 + effort * 1.5;
  std::vector<double> variations(cycles);
  for (double& variation : variations) variation = 0.88 + random() * 0.24;
  const double radius = std::exp(-kPi * 550 / rate), r2 = radius * radius, bandGain = (1 - radius) * 1.6;
  double low = 0, highpass = 0, y1 = 0, y2 = 0, previous = 0, previous2 = 0, wander = 0, phase = random() * tau;
  double coefficient = 0, cutoff = 0, heldNoise = 0;
  // Values the JS loop recomputes per sample although only the breath direction changes them.
  const int heldSteps = static_cast<int>(jsround(5 + throat * 22));
  const double highIn = 1 - std::exp(-tau * (single ? 110 + 120 * inward : 230) / rate);
  const double highOut = 1 - std::exp(-tau * (single ? 110 + 120 * inward : 110) / rate);
  const double obstruction = source == 2 ? 0.72 + rasp * 0.27 : rasp * 0.22;
  // The JS loop body, split so its sines and powers are batched.
  double arg[kBlock], bow[kBlock], arch[kBlock], shape[kBlock], scale[kBlock], airflow[kBlock], sway[kBlock];
  double shiver[kBlock], phases[kBlock], flap[kBlock], body[kBlock], wanders[kBlock];
  bool inhaling[kBlock];
  for (int first = 0; first < length; first += kBlock) {
    const int n = std::min(kBlock, length - first);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double position = std::fmod(i, slot) / slot;
      const int cycle = static_cast<int>(std::min<double>(cycles - 1, std::floor(i / slot)));
      const bool in = position < inEnd, exhaling = position > outStart && position < outEnd;
      const double blend = single ? inward : in ? 1 : 0;
      const double local = single ? i / std::max(1.0, length - 1.0) : in ? position / inEnd : exhaling ? (position - outStart) / (outEnd - outStart) : 0;
      shape[k] = single ? (1 - 0.36 * local) * (1 - blend) + (0.8 + 0.2 * local) * blend : in ? 0.8 + 0.2 * local : 1 - 0.36 * local;
      arg[k] = kPi * local; scale[k] = variations[cycle]; inhaling[k] = in;
    }
    vsin(bow, arg, n);
    for (int k = 0; k < n; k++) arg[k] = std::max(0.0, bow[k]);
    // The exponent follows the breath direction, so each run of one direction is one batch.
    for (int from = 0, to; from < n; from = to) {
      for (to = from + 1; to < n && inhaling[to] == inhaling[from]; to++) {}
      vpow(arch + from, arg + from, single ? 0.7 + 0.1 * inward : inhaling[from] ? 0.8 : 0.7, to - from);
    }
    for (int k = 0; k < n; k++) { airflow[k] = arch[k] * shape[k] * scale[k]; arg[k] = tau * 2.3 * (first + k) / rate; }
    vsin(sway, arg, n);
    for (int k = 0; k < n; k++) arg[k] = tau * 7.3 * (first + k) / rate;
    vsin(shiver, arg, n);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const bool in = inhaling[k];
      const double noise = random() * 2 - 1;
      wander += (noise - wander) * 0.0025;
      if (source == 1 && i % heldSteps == 0) heldNoise = noise > 0 ? 0.8 : -0.8;
      const double excitation = source == 1 ? heldNoise : noise;
      if ((i & 31) == 0) {
        // Inhale jets are brighter; the mouth and chest soften the released air.
        const double blend = single ? inward : in ? 1 : 0;
        const double airHz = single ? (750 + effort * 1600) * (1 - blend) + (2400 + effort * 2700) * blend : in ? 2400 + effort * 2700 : 750 + effort * 1600;
        const double hz = airHz * (1 - throat * 0.38) * (0.75 + airflow[k] * 0.25);
        cutoff = 1 - std::exp(-tau * hz / rate);
        coefficient = 2 * radius * std::cos(tau * (single ? 510 + 490 * blend : in ? 1000 : 510) * (1.35 - throat * 0.6) / rate);
      }
      low += (excitation - low) * cutoff;
      highpass += (low - highpass) * (in ? highIn : highOut);
      const double turbulent = low - highpass;
      const double resonant = bandGain * (turbulent - previous2) + coefficient * y1 - r2 * y2;
      y2 = y1; y1 = resonant; previous2 = previous; previous = turbulent;
      phase += tau * (24 + (1 - throat) * 44) * (1 + flutter * 0.3 * sway[k] + wander * 0.9) / rate;
      phases[k] = phase; body[k] = turbulent * 0.85 + resonant * 0.8; wanders[k] = wander;
    }
    vsin(flap, phases, n);
    for (int k = 0; k < n; k++) arg[k] = std::max(0.0, flap[k]);
    vpow(flap, arg, 3, n);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double airway = 1 - obstruction + obstruction * flap[k];
      const double tremor = std::max(0.2, 1 + wanders[k] * flutter * 6 + flutter * 0.07 * shiver[k]);
      double envelope = airflow[k] * tremor;
      if (source == 1) envelope = jsround(envelope * 12) / 12;
      // Snore pressure pulses are driven by turbulent flow, not a sustained vocal note.
      const double tissue = source == 2 ? (flap[k] - 0.212) * rasp * 0.3 * arch[k] : 0;
      out[i] = static_cast<float>((body[k] * airway + tissue) * envelope * gain);
      if (i >= delay) add(out[i], out[i - delay] * space * 0.38);
    }
  }
  finish(out, volume);
  return out;
}

MSN_ENGINE("Breathr", render_breathr);

}  // namespace msn
