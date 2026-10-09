// Port of js/audio/Bouncr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_bouncr(const Params& p) {
  const double tau = kPi * 2, rate = kRate;
  const double duration = p.value("duration", 2, 0.2, 5);
  const int frames = static_cast<int>(jsround(rate * duration));
  std::vector<float> out(frames);
  Rng random(p.value("seed", 0.5));
  const int material = static_cast<int>(jsround(p.value("material", 0, 0, 4)));
  const int surface = static_cast<int>(jsround(p.value("surface", 0, 0, 5)));
  const int count = static_cast<int>(jsround(p.value("count", 1, 1, 20)));
  const double bounce = p.value("bounce", 0.65), gravity = p.value("gravity", 0.5);
  const double size = p.value("size", 0.5), hardness = p.value("hardness", 0.6), spin = p.value("spin", 0);
  const double force = p.value("force", 0.65), tail = p.value("tail", 0.4);
  // Frequency, decay, stiffness and inharmonic partials describe each body.
  struct Object { double pitch, decay, hard, ratios[4]; };
  static const Object objects[5] = {
      {0.55, 0.041, 0.22, {1, 1.97, 3.17, 4.8}}, {1, 0.030, 0.64, {1, 2.43, 4.13, 6.27}},
      {2.5, 0.16, 1, {1, 1.47, 2.71, 4.09}},     {3.3, 0.10, 0.95, {1, 2.76, 5.4, 8.13}},
      {0.72, 0.025, 0.86, {1, 1.91, 3.47, 5.31}}};
  struct Surface { double pitch, decay, hard, ring, ratios[4]; };
  static const Surface surfaces[6] = {
      {260, 0.022, 0.95, 0.30, {1, 1.61, 2.83, 4.41}}, {135, 0.075, 0.6, 0.72, {1, 2.18, 3.72, 5.41}},
      {330, 0.26, 0.93, 0.85, {1, 1.59, 2.32, 3.79}},  {710, 0.18, 1, 0.70, {1, 1.71, 3.04, 4.93}},
      {78, 0.017, 0.16, 0.18, {1, 1.83, 2.81, 4.18}},  {90, 0.016, 0.035, 0.15, {1, 2.11, 3.43, 4.72}}};
  const Object& object = objects[material];
  const Surface& target = surfaces[surface];
  const double stiffness = std::sqrt(object.hard * target.hard) * (0.18 + hardness * 0.82);
  const double transfer = 0.15 + target.hard * 0.85, decayScale = (0.3 + tail * 2.7) * (0.75 + force * 0.5);
  const double base = (95 + 790 * jspow(1 - size, 2)) * object.pitch;
  double time = 0.012, gap = std::min(duration * 0.42, 0.18 + 0.45 * (1 - gravity));
  for (int hit = 0; hit < count; hit++) {
    const int start = static_cast<int>(jsround(time * rate));
    if (start >= frames) break;
    const double strength = (0.18 + force * 0.82) * jspow(0.53 + bounce * 0.43, hit) * (0.94 + random() * 0.06);
    const double contact = (0.0008 + (1 - stiffness) * 0.013) / (0.65 + force * 0.8);
    const double objectDecay = object.decay * decayScale * (0.3 + transfer * 0.7) * (0.75 + bounce * 0.35);
    const double surfaceDecay = target.decay * decayScale * (0.8 + size * 0.5);
    const double detune = 1 + (random() - 0.5) * (0.025 + spin * 0.07);
    struct Mode { double frequency, phase, decay, gain; };
    Mode modes[8];
    for (int mode = 0; mode < 4; mode++) {
      modes[mode * 2] = {std::min(rate * 0.42, base * object.ratios[mode] * detune), 0,
                         objectDecay / (1 + mode * (0.2 + (1 - hardness) * 0.4)),
                         transfer * 0.72 * jspow(stiffness + 0.18, mode * 0.48) / (1 + mode * 0.8)};
      const double frequency = std::min(rate * 0.42, target.pitch * (1.6 - size) * target.ratios[mode] * (0.97 + random() * 0.06));
      modes[mode * 2 + 1] = {frequency, 0, surfaceDecay / (1 + mode * 0.48),
                             target.ring * 0.72 * jspow(stiffness + 0.12, mode * 0.6) / (1 + mode)};
    }
    // A broad soft contact cannot excite modes faster than its pressure pulse.
    for (Mode& mode : modes) mode.gain /= 1 + jspow(mode.frequency * contact * 0.4, 2);
    const int end = static_cast<int>(std::min<double>(
        frames, start + std::ceil(std::max(contact * 10, std::max(objectDecay, surfaceDecay) * 7) * rate)));
    double low = 0, rub = 0, absorbed = 0;
    const double tone = 1 - std::exp(-tau * (100 + stiffness * 11000) / rate);
    const double absorption = 1 - std::exp(-tau * (100 + jspow(target.hard, 2) * 14000) / rate);
    // The JS loop body, split so its sines and exponentials are batched.
    double arg[kBlock], t[kBlock], lows[kBlock], rubs[kBlock], wobble[kBlock], bend[kBlock], sine[kBlock], ring[kBlock];
    double body[kBlock], contactDecay[kBlock], scatterDecay[kBlock], scrapeDecay[kBlock];
    for (int first = start; first < end; first += kBlock) {
      const int n = std::min(kBlock, end - first);
      for (int k = 0; k < n; k++) {
        t[k] = (first + k - start) / rate;
        const double noise = random() * 2 - 1;
        low += (noise - low) * tone; rub += (noise - rub) * 0.08;
        lows[k] = low; rubs[k] = rub;
        arg[k] = tau * (110 + random() * 30) * t[k];
        body[k] = 0;
      }
      vsin(wobble, arg, n);
      // Integrating instantaneous frequency gives a smooth compressed-rubber release.
      if (material == 0) {
        for (int k = 0; k < n; k++) arg[k] = -t[k] / (contact * 2.5);
        vexp(bend, arg, n);
        for (int k = 0; k < n; k++) bend[k] = 1 + (0.2 + force * 0.65) * bend[k];
      } else {
        for (int k = 0; k < n; k++) bend[k] = 1;
      }
      for (Mode& mode : modes) {
        for (int k = 0; k < n; k++) { mode.phase += tau * mode.frequency * bend[k] / rate; arg[k] = mode.phase; }
        vsin(sine, arg, n);
        for (int k = 0; k < n; k++) arg[k] = -t[k] / mode.decay;
        vexp(ring, arg, n);
        for (int k = 0; k < n; k++) body[k] += sine[k] * mode.gain * ring[k];
      }
      for (int k = 0; k < n; k++) arg[k] = -t[k] / contact;
      vexp(contactDecay, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -t[k] / (0.014 + tail * 0.035);
      vexp(scatterDecay, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -t[k] / (0.025 + spin * 0.08);
      vexp(scrapeDecay, arg, n);
      for (int k = 0; k < n; k++) {
        const double attack = std::min(1.0, t[k] / (0.00025 + contact * 0.3));
        const double contactNoise = lows[k] * (0.18 + stiffness * 0.6) * contactDecay[k];
        const double scatter = (surface == 4 ? 0.6 : surface == 0 ? 0.16 : 0.04) * lows[k] * scatterDecay[k];
        const double scrape = rubs[k] * spin * 0.6 * scrapeDecay[k] * (0.65 + 0.35 * wobble[k]);
        absorbed += (body[k] + contactNoise + scatter + scrape - absorbed) * absorption;
        add(out[first + k], absorbed * strength * attack);
      }
    }
    time += gap; gap = std::max(0.006, gap * (0.4 + bounce * 0.54) * (1 - spin * 0.12));
  }
  finish(out, p.value("masterVolume", 0.5));
  return out;
}

MSN_ENGINE("Bouncr", render_bouncr);

}  // namespace msn
