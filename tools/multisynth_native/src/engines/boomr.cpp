// Port of js/audio/Boomr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

std::vector<float> render_boomr(const Params& p) {
  const double rate = kRate, duration = p.value("duration", 1.5, 0.12, 5);
  const int frames = static_cast<int>(jsround(rate * duration));
  std::vector<float> out(frames);
  const double size = p.value("size", 0.5), pressure = p.value("pressure", 0.7), blast = p.value("blast", 0.65);
  const double debris = p.value("debris", 0.35), spread = p.value("spread", 0.5), tail = p.value("tail", 0.45);
  const double muffle = p.value("muffle", 0.15);
  const int mechanism = static_cast<int>(jsround(p.value("mechanism", 0, 0, 7)));
  const double space = p.value("space", 0.25);
  Rng random(p.value("seed", 0.5));
  const double tau = kTau;
  auto coefficient = [&](double hz) { return 1 - std::exp(-tau * hz / rate); };
  struct Type { double front, gas, body, decay, brightness; };
  static const Type types[8] = {
      {1, 1, 1, 1, 1},          {0.55, 1.3, 0.8, 1.75, 0.65}, {1.5, 0.2, 1.6, 1.5, 0.08},
      {1.1, 0.65, 1.8, 1.45, 0.4}, {0.7, 0.65, 1.5, 0.8, 0.5},  {0.6, 0.5, 0.22, 0.2, 1.5},
      {0.35, 1.6, 0.3, 2, 2.5},  {0.9, 0.15, 2.2, 0.55, 0.15}};
  const Type type = types[mechanism];
  const double gas = p.value("gas", 0.25), aftershock = p.value("aftershock", 0.25);
  const double rubbleSize = p.value("rubbleSize", 0.5);
  struct Event { double time, gain; };
  std::vector<Event> events{{mechanism == 7 ? 0.08 + size * 0.07 : 0.007, 1}};
  if (mechanism == 4)
    for (int j = 0; j < 5; j++) {
      const double time = duration * (0.12 + j * 0.12) * (0.8 + random() * 0.3);
      events.push_back({time, 0.75 - j * 0.09});
    }
  if (mechanism == 2)
    for (int j = 0; j < 3; j++)
      events.push_back({0.06 + (0.1 + size * 0.18) * jspow(1.42, j), 0.44 * jspow(0.63, j)});
  const double pressureDecay = (0.024 + size * 0.18) * type.decay;
  const double gasDecay = (0.022 + duration * (0.045 + tail * 0.28)) * type.decay;
  const double frontTime = (0.0014 + size * 0.01) * (mechanism == 2 ? 2.5 : mechanism == 5 ? 0.45 : 1);
  const double lowRate = coefficient(40 + 120 * (1 - size)), midRate = coefficient(200 + 650 * (1 - size));
  const double dcRate = coefficient(15), motionRate = coefficient(4 + 10 * (1 - size));
  const double sizeSquared = jspow(1 - size, 2);
  // The JS sample loops, split so that their exponentials and sines are batched.
  double arg[kBlock];
  for (const Event& event : events) {
    const int start = static_cast<int>(jsround(event.time * rate));
    double low = 0, mid = 0, high = 0, dc = 0, drift = 0, wind = 0, gasLow = 0, gasDC = 0, shellPhase = 0;
    double cooling[kBlock], highDecay[kBlock], windDecay[kBlock], frontDecay[kBlock], pressureFade[kBlock];
    double gasRise[kBlock], plumeFade[kBlock], rollFade[kBlock], rollRise[kBlock], extraA[kBlock], extraB[kBlock];
    double shell[kBlock], shell2[kBlock];
    for (int first = start; first < frames; first += kBlock) {
      const int n = std::min(kBlock, frames - first);
      auto time = [&](int k) { return (first + k - start) / rate; };
      // exp(-t / seconds) across the block
      auto decay = [&](double* out, double seconds) {
        for (int k = 0; k < n; k++) arg[k] = -time(k) / seconds;
        vexp(out, arg, n);
      };
      decay(cooling, gasDecay * 0.65);
      for (int k = 0; k < n; k++) arg[k] = -tau * (140 + (650 + 8500 * sizeSquared) * type.brightness * cooling[k]) / rate;
      vexp(highDecay, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -tau * (85 + 260 * cooling[k]) / rate;
      vexp(windDecay, arg, n);
      decay(frontDecay, frontTime);
      decay(pressureFade, pressureDecay);
      decay(gasRise, mechanism == 1 ? 0.026 + size * 0.08 : 0.002);
      decay(plumeFade, gasDecay);
      decay(rollFade, 0.05 + duration * (0.08 + tail * 0.25));
      decay(rollRise, 0.028);
      if (mechanism == 1) {
        // A short hollow fuel container flexing as it opens.
        decay(extraA, 0.04);
        decay(extraB, 0.018 + size * 0.045);
        for (int k = 0; k < n; k++) {
          shellPhase += tau * (95 + 170 * (1 - size)) * (1 - 0.14 * (1 - extraA[k])) / rate;
          arg[k] = shellPhase; extraA[k] = shellPhase * 2.37;
        }
        vsin(shell, arg, n);
        vsin(shell2, extraA, n);
      } else if (mechanism == 2) {
        // Cavitation re-expansions, seeded at aperiodic spacings above.
        decay(extraA, frontTime * 2);
      } else if (mechanism == 3) {
        decay(extraA, 0.08 + size * 0.2);
        decay(extraB, 0.012);
      }
      for (int k = 0; k < n; k++) {
        const double t = time(k), noise = random() * 2 - 1, n2 = random() * 2 - 1;
        low += lowRate * (noise - low); mid += midRate * (noise - mid); dc += dcRate * (low - dc);
        drift += motionRate * (n2 - drift);
        gasLow += lowRate * (n2 - gasLow); gasDC += dcRate * (gasLow - gasDC);
        high += (1 - highDecay[k]) * (n2 - high); wind += (1 - windDecay[k]) * (n2 - wind);
        const double q = t / frontTime, front = (1 - q) * frontDecay[k];
        const double pressureBody = (low - dc) * 5.5 * pressureFade[k];
        const double billow = 0.8 + std::fabs(drift) * 6;
        const double plume = ((high - wind) * 0.65 + wind * 3.2) * plumeFade[k] * (1 - gasRise[k]) * billow;
        const double rollingSource = mechanism == 1 ? gasLow - gasDC : low - dc;
        const double roll = rollingSource * 4.2 * rollFade[k] * (1 - rollRise[k]);
        double transmission = 0;
        if (mechanism == 1) transmission = (shell[k] + 0.23 * shell2[k]) * extraB[k] * 0.2;
        else if (mechanism == 2) transmission = (1 - t / (frontTime * 2)) * extraA[k] * 0.9;
        else if (mechanism == 3) transmission = (mid - low) * 5.5 * extraA[k] * (1 - extraB[k]);
        add(out[first + k], event.gain * (pressure * (front * type.front + pressureBody * type.body + transmission)
            + blast * type.gas * plume + tail * type.body * roll) * 0.8);
      }
    }
  }
  // A gas jet has an audible opening and several uneven billows, rather
  // than sharing the detonation's instantaneous noise envelope.
  Rng gasRandom(p.value("seed", 0.5) * 0.71 + 0.193);
  const double jetDelay = mechanism == 6 ? 0.015 : mechanism == 1 ? 0.045 : 0.07 + size * 0.045;
  const double jetLife = (0.1 + duration * (0.12 + tail * 0.3)) * (mechanism == 6 ? 1.5 : mechanism == 2 ? 0.35 : mechanism == 5 ? 0.12 : 1);
  const double gasLowRate = coefficient(50 + 80 * (1 - size));
  const double gasHighRate = coefficient(mechanism == 2 ? 170 : 700 + 4700 * jspow(1 - size, 0.65));
  const double motionCoefficient = coefficient(13);
  double jetLow = 0, jetHigh = 0, jetMotion = 0;
  double openDecay[kBlock], jetFade[kBlock], surge[kBlock];
  for (int first = 0; first < frames; first += kBlock) {
    const int n = std::min(kBlock, frames - first);
    auto time = [&](int k) { return (first + k) / rate - jetDelay; };
    if (gas > 0) {
      for (int k = 0; k < n; k++) arg[k] = -time(k) / (0.02 + size * 0.035);
      vexp(openDecay, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -time(k) / jetLife;
      vexp(jetFade, arg, n);
      for (int k = 0; k < n; k++) arg[k] = time(k) * (11 + size * 9);
      vsin(surge, arg, n);
    }
    for (int k = 0; k < n; k++) {
      const double t = time(k);
      const double noise = gasRandom() * 2 - 1;
      jetLow += gasLowRate * (noise - jetLow); jetHigh += gasHighRate * (noise - jetHigh);
      jetMotion += motionCoefficient * (gasRandom() * 2 - 1 - jetMotion);
      if (t >= 0 && gas > 0) {
        const double opening = (1 - openDecay[k]);
        const double envelope = opening * jetFade[k];
        const double billow = 0.48 + std::fabs(jetMotion) * 9 + 0.25 * (surge[k] * surge[k]);
        add(out[first + k], gas * (mechanism == 5 ? 0.2 : 1) * envelope * billow * ((jetHigh - jetLow) * 1.9 + jetLow * 2.2));
      }
      if (mechanism == 7 && t + jetDelay < events[0].time) {
        const double u = (t + jetDelay) / events[0].time;
        add(out[first + k], (jetHigh - jetLow) * blast * jspow(u, 3) * 0.65);
      }
    }
  }
  // Secondary fronts travel through heavy material. Separate random streams
  // keep their placement stable when the user changes gas or debris level.
  Rng shockRandom(p.value("seed", 0.5) * 0.61 + 0.317);
  const int shockCount = 2 + static_cast<int>(jsround(aftershock * 4));
  double frontDecay[kBlock], rise[kBlock], fade[kBlock];
  for (int event = 0; event < shockCount && aftershock > 0; event++) {
    const double arrival = 0.12 + duration * (0.04 + event * 0.115) * (0.8 + shockRandom() * 0.4);
    const int start = static_cast<int>(jsround(arrival * rate));
    const double life = (0.025 + size * 0.1) * (0.7 + shockRandom() * 0.6);
    const double strength = aftershock * jspow(0.7, event) * (0.75 + size * 0.8) * (mechanism == 5 ? 0.06 : 1);
    double low = 0, dc = 0;
    const double lp = coefficient(55 + 90 * (1 - size)), dcCoefficient = coefficient(12);
    const int stop = static_cast<int>(std::min<double>(frames, start + std::ceil(life * 8 * rate)));
    for (int first = start; first < stop; first += kBlock) {
      const int n = std::min(kBlock, stop - first);
      auto time = [&](int k) { return (first + k - start) / rate; };
      for (int k = 0; k < n; k++) arg[k] = -(time(k) / (0.006 + size * 0.016));
      vexp(frontDecay, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -time(k) / 0.009;
      vexp(rise, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -time(k) / life;
      vexp(fade, arg, n);
      for (int k = 0; k < n; k++) {
        const double q = time(k) / (0.006 + size * 0.016);
        low += lp * (shockRandom() * 2 - 1 - low); dc += dcCoefficient * (low - dc);
        add(out[first + k], strength * ((1 - q) * frontDecay[k] * 0.8 + (low - dc) * 7 * (1 - rise[k]) * fade[k]));
      }
    }
  }
  const int pieces = static_cast<int>(jsround(debris * 48));
  for (int piece = 0; piece < pieces; piece++) {
    const int start = static_cast<int>(std::floor((0.018 + rubbleSize * 0.055 + random() * duration * (0.04 + spread * 0.8)) * rate));
    const double chunk = random(), life = (0.002 + chunk * 0.025) * (0.25 + rubbleSize * 2.5);
    const double gain = debris * (0.1 + random() * 0.3) * (0.7 + rubbleSize);
    const int length = static_cast<int>(std::min<double>(frames - start, std::ceil(life * rate * 7)));
    const double damping = std::exp(-1 / (life * rate));
    const double dustRate = coefficient((1200 + random() * 8500) * jspow(1 - rubbleSize * 0.94, 2));
    const double bodyRate = coefficient(45 + random() * 600 * jspow(1 - rubbleSize * 0.85, 2));
    double dust = 0, body = 0, envelope = 1;
    for (int first = 0; first < length; first += kBlock) {
      const int n = std::min(kBlock, length - first);
      for (int k = 0; k < n; k++) arg[k] = -(((first + k) / rate) / (0.0004 + rubbleSize * 0.009));
      vexp(frontDecay, arg, n);
      for (int k = 0; k < n; k++) {
        const double noise = random() * 2 - 1;
        dust += dustRate * (noise - dust); body += bodyRate * (noise - body);
        const double q = ((first + k) / rate) / (0.0004 + rubbleSize * 0.009);
        add(out[start + first + k], (dust * (1 - rubbleSize * 0.7) + body * (0.5 + rubbleSize * 5) + (1 - q) * frontDecay[k] * rubbleSize) * envelope * gain);
        envelope *= damping;
      }
    }
  }
  if (space > 0) {
    // Three unequal, damped recirculating paths smear the pressure field.
    std::vector<float> delays[3];
    const double seconds[3] = {0.071, 0.113, 0.173};
    for (int j = 0; j < 3; j++)
      delays[j].assign(static_cast<size_t>(std::max(1.0, jsround(seconds[j] * (0.6 + space * 1.8) * rate))), 0.0f);
    size_t heads[3] = {0, 0, 0};
    double smoothed[3] = {0, 0, 0};
    for (int i = 0; i < frames; i++) {
      const double input = out[i];
      double echo = 0;
      for (int j = 0; j < 3; j++) {
        std::vector<float>& buffer = delays[j];
        const size_t head = heads[j];
        const double sample = buffer[head];
        smoothed[j] += 0.08 * (sample - smoothed[j]);
        buffer[head] = static_cast<float>(input * 0.36 + smoothed[j] * (0.2 + space * 0.48));
        echo += smoothed[j]; heads[j] = (head + 1) % buffer.size();
      }
      add(out[i], echo * space * 0.7);
    }
  }
  const double finalRate = coefficient(80 + 15000 * jspow(1 - muffle, 3));
  double filtered = 0;
  for (int i = 0; i < frames; i++) { filtered += finalRate * (out[i] - filtered); out[i] = static_cast<float>(filtered); }
  finish(out, p.value("masterVolume", 0.5));
  return out;
}

MSN_ENGINE("Boomr", render_boomr);

}  // namespace msn
