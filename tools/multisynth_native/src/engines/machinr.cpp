// Port of js/audio/Machinr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_machinr(const Params& p) {
  const double rate = kRate;
  const int count = static_cast<int>(std::max(2.0, jsround(p.number("duration") * rate)));
  std::vector<float> output(count);
  Rng random(p.number("seed"));
  const double speed = p.number("speed"), load = p.number("load"), roughness = p.number("roughness");
  const double looseness = p.number("looseness"), size = p.number("size");
  const int mechanism = static_cast<int>(p.number("mechanism"));
  const double tau = 2 * kPi;
  const double scale = jspow(2, (0.5 - size) * 2.6);
  const double base = (35 + 230 * speed * speed) * scale * (1 - 0.32 * load);
  const double toothRate = (5 + speed * 48) * (1 - load * 0.28);
  const double attack = std::max(0.003, p.number("startTime")) * rate;
  const double release = std::max(0.006, p.number("stopTime")) * rate;
  // Contact resonances share a material size, but alternate on an escapement.
  const double ringFrequency = std::min(8500.0, (650 + 1100 * (1 - size)) * scale);
  const double decay = std::exp(-1 / (rate * (0.007 + 0.035 * looseness)));
  const double ringA = 2 * decay * std::cos(tau * ringFrequency / rate);
  const double ringB = 2 * decay * std::cos(tau * ringFrequency * 0.63 / rate);
  const double contactDecay = std::exp(-1 / (rate * (0.007 + 0.025 * load)));
  double contactRate = toothRate;
  if (mechanism == 3) contactRate = 1.3 + speed * 8;
  if (mechanism == 4) contactRate = 7 + speed * 30;
  if (mechanism == 7) contactRate = 4 + speed * 17;
  const int latchA = static_cast<int>(std::floor(rate * 0.008));
  const int latchB = static_cast<int>(std::floor(count * (0.19 + 0.12 * load)));
  const int closure = static_cast<int>(std::floor(count * 0.88));
  double a1 = 0, a2 = 0, b1 = 0, b2 = 0, phase = 0, teeth = 0, slowNoise = 0, friction = 0;
  double previousTooth = -1, contact = 0, eventStrength = 1;
  int turn = 0;
  const double rotorOffset = random() * tau;
  // The JS loop body, split so its sines and exponentials are batched. Only
  // the terms the chosen mechanism uses are computed.
  double arg[kBlock], sway[kBlock], envelopes[kBlock], phases[kBlock], mesh[kBlock], frictions[kBlock];
  double contacts[kBlock], rattles[kBlock], latches[kBlock], rotor[kBlock], samples[kBlock];
  double s1[kBlock], s2[kBlock], s3[kBlock], s4[kBlock];
  for (int first = 0; first < count; first += kBlock) {
    const int n = std::min(kBlock, count - first);
    auto progress = [&](int k) { return static_cast<double>(first + k) / (count - 1); };
    auto sines = [&](double* out, const double* in, double factor) {
      for (int k = 0; k < n; k++) arg[k] = in[k] * factor;
      vsin(out, arg, n);
    };
    for (int k = 0; k < n; k++) arg[k] = tau * 7.3 * ((first + k) / rate) + rotorOffset;
    vsin(sway, arg, n);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double engage = std::min(1.0, i / attack), stop = std::min(1.0, (count - 1 - i) / release);
      envelopes[k] = engage * stop;
      const double noise = random() * 2 - 1;
      slowNoise += (noise - slowNoise) * 0.0015;
      friction += (noise - friction) * (0.09 + 0.5 * roughness);
      double spin = (0.18 + 0.82 * engage) * (0.2 + 0.8 * stop);
      if (mechanism == 6) spin *= 1 - 0.7 * progress(k);
      const double wobble = 1 + roughness * (0.085 * sway[k] + slowNoise * 1.2);
      phase += tau * base * spin * wobble / rate;
      teeth += contactRate * spin * wobble / rate;
      const double tooth = std::floor(teeth);
      double kick = 0;
      if (tooth != previousTooth) {
        previousTooth = tooth;
        turn++;
        eventStrength = 0.45 + random() * 0.55;
        kick = (0.15 + looseness * 0.7) * eventStrength;
        if (mechanism == 3) kick = 0.75;
        if (mechanism == 4) kick *= random() > roughness * 0.22 ? 1 : 0.1;
        contact = eventStrength;
      }
      contact *= contactDecay;
      // Shutters use two explicit latch contacts; the door strikes at closure.
      if (mechanism == 2) kick = (i == latchA || i == latchB) ? 1.9 : 0;
      if (mechanism == 7 && i == closure) kick += 3.2;
      const double resonantA = kick * 0.14 + ringA * a1 - decay * decay * a2;
      const double resonantB = kick * 0.11 + ringB * b1 - decay * decay * b2;
      a2 = a1; a1 = resonantA; b2 = b1; b1 = resonantB;
      phases[k] = phase; mesh[k] = teeth; frictions[k] = friction; contacts[k] = contact;
      rattles[k] = turn % 2 ? resonantA : resonantB;
      latches[k] = resonantA + resonantB;
    }
    if (mechanism != 5 && mechanism != 7) {
      vsin(s1, phases, n);
      sines(s2, phases, 2);
      sines(s3, phases, 5);
      for (int k = 0; k < n; k++) rotor[k] = s1[k] + 0.35 * s2[k] + 0.12 * s3[k];
    }
    switch (mechanism) {
      case 1:  // Teeth rubbing and slipping under load.
        sines(s1, phases, 0.017);
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 3.1 + 3 * s1[k];
        vsin(s2, arg, n);
        for (int k = 0; k < n; k++) arg[k] = tau * 1.7 * ((first + k) / rate);
        vsin(s3, arg, n);
        for (int k = 0; k < n; k++)
          samples[k] = 0.11 * rotor[k] + 0.55 * rattles[k] + frictions[k] * (0.05 + 0.18 * roughness)
              + 0.11 * load * s2[k] * (0.5 + 0.5 * s3[k]);
        break;
      case 2:
        for (int k = 0; k < n; k++) arg[k] = -progress(k) * 9;
        vexp(s1, arg, n);
        for (int k = 0; k < n; k++) arg[k] = -progress(k) * 12;
        vexp(s2, arg, n);
        for (int k = 0; k < n; k++)
          samples[k] = 1.05 * latches[k] + 0.08 * rotor[k] * s1[k] + frictions[k] * 0.13 * s2[k];
        break;
      case 3:
        for (int k = 0; k < n; k++)
          samples[k] = rattles[k] * 1.35 + 0.014 * rotor[k] + frictions[k] * contacts[k] * 0.18;
        break;
      case 4:
        sines(s1, phases, 0.5);
        for (int k = 0; k < n; k++)
          samples[k] = 0.28 * rotor[k] * (0.3 + contacts[k]) + 0.4 * contacts[k] * frictions[k]
              + 0.21 * s1[k] * (0.4 + load) + 0.18 * rattles[k];
        break;
      case 5:
        for (int k = 0; k < n; k++) arg[k] = tau * (1.1 + speed * 3) * ((first + k) / rate);
        vsin(s1, arg, n);
        sines(s2, phases, 3.1 + load);
        sines(s3, phases, 6.2);
        for (int k = 0; k < n; k++) {
          const double position = 0.55 + 0.45 * s1[k];
          samples[k] = (0.25 * s2[k] + 0.09 * s3[k]) * position
              + 0.05 * rattles[k] + frictions[k] * (0.015 + 0.035 * roughness);
        }
        break;
      case 6:
        sines(s1, mesh, 0.38);
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 1.9 + 2 * s1[k];
        vsin(s2, arg, n);
        for (int k = 0; k < n; k++)
          samples[k] = 0.13 * s2[k] + 0.53 * rattles[k]
              + 0.08 * rotor[k] + frictions[k] * (0.015 + 0.09 * roughness);
        break;
      case 7:
        sines(s1, phases, 0.023);
        for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.62 + 4 * s1[k];
        vsin(s2, arg, n);
        sines(s3, mesh, 1.4);
        sines(s4, phases, 0.31);
        for (int k = 0; k < n; k++) {
          const double creak = s2[k];
          samples[k] = 0.27 * creak * (0.55 + 0.45 * s3[k]) + 0.45 * rattles[k]
              + 0.14 * s4[k] + frictions[k] * roughness * 0.1;
        }
        break;
      default:
        sines(s1, phases, 8);
        for (int k = 0; k < n; k++)
          samples[k] = 0.24 * rotor[k] + 0.09 * s1[k] * (0.25 + load)
              + rattles[k] * (0.1 + looseness * 0.3) + frictions[k] * (0.015 + roughness * 0.15);
    }
    for (int k = 0; k < n; k++) output[first + k] = static_cast<float>(samples[k] * envelopes[k]);
  }
  finish(output, p.number("masterVolume"));
  return output;
}

MSN_ENGINE("Machinr", render_machinr);

}  // namespace msn
