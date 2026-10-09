// Port of js/audio/Zappr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_zappr(const Params& p) {
  const double rate = kRate, duration = p.value("duration", 1.2, 0.12, 5);
  const int frames = static_cast<int>(jsround(duration * rate));
  std::vector<float> out(frames);
  const int arcs = static_cast<int>(jsround(p.value("arcs", 7, 1, 24)));
  const double voltage = p.value("voltage", 0.55), branching = p.value("branching", 0.4);
  const double crackle = p.value("crackle", 0.45), hum = p.value("hum", 0.2), spark = p.value("spark", 0.65);
  const double spread = p.value("spread", 0.7), decay = p.value("decay", 0.4);
  Rng random(p.value("seed", 0.5));
  const double tau = 2 * kPi, humFrequency = 42 + voltage * 65;
  struct Event { double time, life, frequency, gain; };
  std::vector<Event> events;
  for (int arc = 0; arc < arcs; arc++) {
    const double position = arc == 0 ? 0.004 : (arc + random() * 0.65) / arcs * duration * (0.03 + spread * 0.86);
    const double life = 0.008 + decay * 0.1, frequency = 400 + voltage * 4800 * (0.6 + random() * 0.8);
    const double gain = 0.55 + random() * 0.4;
    events.push_back({position, life, frequency, gain});
    const int branches = static_cast<int>(jsround(branching * (2 + random() * 5)));
    for (int branch = 0; branch < branches; branch++) {
      const double time = position + life * (0.3 + random() * 2);
      const double branchLife = life * (0.18 + random() * 0.55);
      const double branchFrequency = frequency * (0.5 + random() * 1.2);
      const double branchGain = branching * (0.15 + random() * 0.25);
      events.push_back({time, branchLife, branchFrequency, branchGain});
    }
  }
  double phase = 0, crackleEnv = 0, noiseLow = 0;
  const double crackleFall = std::exp(-1 / (rate * (0.001 + decay * 0.014)));
  // Both JS loop bodies are split so their sines, exponentials and powers are batched.
  double arg[kBlock], phases[kBlock], sparks[kBlock], sine[kBlock], sine3[kBlock], sine7[kBlock], fade[kBlock], strike[kBlock];
  for (int first = 0; first < frames; first += kBlock) {
    const int n = std::min(kBlock, frames - first);
    for (int k = 0; k < n; k++) {
      const double noise = random() * 2 - 1;
      noiseLow += 0.075 * (noise - noiseLow);
      phase += tau * humFrequency / rate; if (phase > tau) phase -= tau;
      if (random() < crackle * (12 + voltage * 130) / rate) crackleEnv = 0.15 + random() * 0.55;
      crackleEnv *= crackleFall;
      phases[k] = phase; sparks[k] = crackleEnv * (noise - noiseLow) * crackle;
    }
    vsin(sine, phases, n);
    for (int k = 0; k < n; k++) arg[k] = phases[k] * 3;
    vsin(sine3, arg, n);
    for (int k = 0; k < n; k++) arg[k] = phases[k] * 7;
    vsin(sine7, arg, n);
    for (int k = 0; k < n; k++) arg[k] = std::max(0.0, 1 - (first + k) / rate / duration);
    vpow(fade, arg, 0.2 + decay * 0.6, n);
    for (int k = 0; k < n; k++) {
      const double t = (first + k) / rate;
      const double field = hum * (sine[k] + 0.28 * sine3[k] + 0.15 * sine7[k]) * 0.27;
      out[first + k] = static_cast<float>((field + sparks[k]) * std::min(1.0, t / 0.006) * fade[k]);
    }
  }
  for (const Event& event : events) {
    const double life = event.life, frequency = event.frequency, gain = event.gain;
    const int start = static_cast<int>(jsround(event.time * rate));
    const int length = static_cast<int>(std::min<double>(frames - start, std::ceil(life * rate * 6)));
    double phase = random() * tau, low = 0;
    for (int first = 0; first < length; first += kBlock) {
      const int n = std::min(kBlock, length - first);
      for (int k = 0; k < n; k++) arg[k] = -((first + k) / rate) / life;
      vexp(fade, arg, n);
      for (int k = 0; k < n; k++) arg[k] = tau * ((first + k) / rate) * (75 + voltage * 290);
      vsin(strike, arg, n);
      for (int k = 0; k < n; k++) {
        const double noise = random() * 2 - 1;
        phase += tau * frequency * (0.3 + 0.7 * fade[k]) / rate; if (phase > tau) phase -= tau;
        low += 0.2 * (noise - low);
        sparks[k] = (0.4 + spark * 0.5) * (noise - low);
        phases[k] = phase; arg[k] = phase * 0.47;
      }
      vsin(sine, arg, n);
      for (int k = 0; k < n; k++) arg[k] = phases[k] + sine[k] * voltage * 2;
      vsin(sine, arg, n);
      for (int k = 0; k < n; k++) {
        const int j = first + k;
        const double discharge = sparks[k] + sine[k] * (1 - spark * 0.65);
        const double restrike = 0.65 + 0.35 * std::max(0.0, strike[k]);
        add(out[start + j], discharge * gain * fade[k] * restrike * std::min(1.0, j / 12.0));
      }
    }
  }
  finish(out, p.value("masterVolume", 0.5));
  return out;
}

MSN_ENGINE("Zappr", render_zappr);

}  // namespace msn
