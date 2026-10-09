// Port of js/audio/Signlr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

namespace {

// Signlr_DSP.pings: the struck, ringing radar marker.
std::vector<float> pings(const Params& p) {
  const double rate = kRate, tau = kPi * 2;
  const double duration = p.value("duration", 1.4, .15, 5);
  const int packets = static_cast<int>(jsround(p.value("packets", 2, 1, 12)));
  std::vector<float> out(static_cast<size_t>(jsround(duration * rate)));
  const int length = static_cast<int>(out.size());
  Rng rng(p.value("seed", .5));
  const double root = 170 * jspow(2, p.value("carrier", .55) * 4.1), color = p.value("deviation", .15);
  const double fall = p.value("gap", .5, 0, .85), echo = p.value("echo", .4), drift = p.value("drift", 0, -1, 1);
  // Each seed describes one struck resonator, shared by the whole scan.
  double ratios[4] = {1, 0, 0, 0};
  ratios[1] = 2.01 + rng() * .12;
  ratios[2] = 3.1 + rng() * 1.7;
  ratios[3] = 5.2 + rng() * 2.2;
  const double weights[4] = {.8, .06 + color * .28, .03 + color * .17, .02 + color * .1};
  const double ring = .045 + (1 - fall) * .6, step = duration / packets;
  double phases[4];
  for (double& phase : phases) phase = rng() * tau;
  int offsets[3];
  double gains[3];
  for (int repeat = 1; repeat <= 3; repeat++) {
    offsets[repeat - 1] = static_cast<int>(jsround(rate * (.062 + p.value("seed", .5) * .055) * repeat));
    gains[repeat - 1] = jspow(echo * .52, repeat);
  }
  // The JS loop body, split so its sines and exponentials are batched.
  double arg[kBlock], rise[kBlock], bend[kBlock], tone[kBlock], fade[kBlock], samples[kBlock];
  for (int packet = 0; packet < packets; packet++) {
    const int start = static_cast<int>(jsround(packet * step * rate));
    const double frequency = root * jspow(2, drift * packet / std::max(1, packets - 1));
    const int stop = static_cast<int>(std::ceil(std::min(rate * (ring * 6), static_cast<double>(length - start))));
    for (int first = 0; first < stop; first += kBlock) {
      const int n = std::min(kBlock, stop - first);
      auto t = [&](int k) { return (first + k) / rate; };
      for (int k = 0; k < n; k++) arg[k] = -t(k) / .0007;
      vexp(rise, arg, n);
      for (int k = 0; k < n; k++) arg[k] = -t(k) / .006;
      vexp(bend, arg, n);
      for (int k = 0; k < n; k++) samples[k] = 0;
      for (int h = 0; h < 4; h++) {
        if (frequency * ratios[h] > 18000) continue;
        for (int k = 0; k < n; k++)
          arg[k] = tau * frequency * ratios[h] * (t(k) + color * .0008 * (1 - bend[k])) + phases[h];
        vsin(tone, arg, n);
        for (int k = 0; k < n; k++) arg[k] = -t(k) * (1 + h * 1.4) / ring;
        vexp(fade, arg, n);
        for (int k = 0; k < n; k++) samples[k] += tone[k] * weights[h] * fade[k];
      }
      for (int k = 0; k < n; k++) {
        const int i = first + k;
        const double attack = 1 - rise[k], sample = samples[k] * (attack * .7);
        add(out[start + i], sample);
        for (int repeat = 0; repeat < 3; repeat++) {
          const int target = start + i + offsets[repeat];
          if (target < length) add(out[target], sample * gains[repeat]);
        }
      }
    }
  }
  finish(out, p.value("masterVolume", .5));
  return out;
}

}  // namespace

std::vector<float> render_signlr(const Params& p) {
  const double rate = kRate, tau = 2 * kPi;
  const double duration = p.value("duration", 1.4, 0.15, 5);
  std::vector<float> output(static_cast<size_t>(jsround(duration * rate)));
  const double volume = p.value("masterVolume", 0.5);
  if (volume == 0) { finish(output, 0); return output; }
  const int length = static_cast<int>(output.size());
  const double seed = p.value("seed", 0.5);
  Rng random(seed);
  const int encoding = static_cast<int>(jsround(p.value("encoding", 0, 0, 4)));
  if (encoding == 4) return pings(p);
  const double carrier = 90 * jspow(2, p.value("carrier", 0.55) * 5.7);
  const double deviation = p.value("deviation", 0.35), drift = p.value("drift", 0, -1, 1);
  const double interference = p.value("interference", 0.08), corruption = p.value("corruption", 0.08);
  const double echo = p.value("echo", 0.15), symbols = 4 + 176 * jspow(p.value("symbols", 0.4), 2);
  const double symbolSamples = rate / symbols;
  const double packets = jsround(p.value("packets", 3, 1, 12));
  const double slot = length / packets, active = slot * (1 - p.value("gap", 0.25, 0, 0.85));
  const double edge = std::min(rate * 0.005, active * 0.12);
  const double symbolEdge = std::min(rate * 0.0007, symbolSamples * 0.06);
  const int delayA = static_cast<int>(jsround(rate * (0.073 + seed * 0.041)));
  const int delayB = static_cast<int>(jsround(delayA * 1.79));
  double phase = random() * tau, lastSymbol = -1, lastPacket = -1, bit = 1, symbolGain = 1;
  double noiseLow = 0, radioLow = 0, phaseCode = 0, scramble = 0, shift = 1;
  double carrierNow = carrier * jspow(2, -drift * 0.5);
  const double driftStep = jspow(2, drift / length);
  const double heterodyneStep = tau * (carrier * 1.013 + 37) / rate;
  double heterodyne = random() * tau;
  // The JS loop body, split so its sines, powers and exponentials are batched.
  double arg[kBlock], locals[kBlock], positions[kBlock], units[kBlock], bits[kBlock], gains[kBlock], codes[kBlock];
  double shifts[kBlock], hiss[kBlock], phases[kBlock], beats[kBlock], tone[kBlock], second[kBlock], beat[kBlock];
  for (int first = 0; first < length; first += kBlock) {
    const int n = std::min(kBlock, length - first);
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double packet = std::min(packets - 1, std::floor(i / slot)), local = i - packet * slot;
      const double symbol = std::floor(local / symbolSamples), symbolPosition = local - symbol * symbolSamples;
      const double unit = symbolPosition / symbolSamples;
      if (packet != lastPacket || symbol != lastSymbol) {
        lastPacket = packet; lastSymbol = symbol;
        // A four-symbol sync word precedes the seeded payload in every packet.
        if (symbol < 4) bit = std::fmod(symbol + packet, 2.0) != 0 ? 1 : -1;
        else bit = random() < 0.5 ? -1 : 1;
        symbolGain = random() < corruption * 0.85 ? 0.025 : 1;
        phaseCode = bit > 0 ? 0 : kPi;
        scramble = corruption * (random() * 2 - 1);
        // These frequency ratios hold for the whole symbol.
        if (encoding == 0) shift = jspow(2, deviation * bit * 0.7 + scramble * 0.2);
        if (encoding == 3) shift = 1 + deviation * 0.3 * bit;
      }
      const double noise = random() * 2 - 1;
      noiseLow += (noise - noiseLow) * 0.08;
      locals[k] = local; positions[k] = symbolPosition; units[k] = unit; bits[k] = bit; gains[k] = symbolGain;
      codes[k] = phaseCode; shifts[k] = shift; hiss[k] = (noise - noiseLow) * 0.22;
      if (encoding == 2) arg[k] = deviation * (1 - unit * 2) + scramble * 0.2;
    }
    if (encoding == 2) vpow(shifts, 2.0, arg, n);
    for (int k = 0; k < n; k++) {
      double frequency = carrierNow;
      if (encoding != 1) frequency *= shifts[k];
      phase += tau * std::min(14000.0, std::max(30.0, frequency)) / rate;
      carrierNow *= driftStep;
      heterodyne += heterodyneStep;
      phases[k] = encoding == 1 ? phase + codes[k] * (0.25 + deviation * 0.75) : phase;
      beats[k] = heterodyne;
    }
    vsin(tone, phases, n);
    vsin(beat, beats, n);
    if (encoding == 0) {
      for (int k = 0; k < n; k++) arg[k] = phases[k] * 2;
      vsin(second, arg, n);
    } else if (encoding == 2) {
      for (int k = 0; k < n; k++) arg[k] = -units[k] * (5 + deviation * 5);
      vexp(second, arg, n);
    } else if (encoding == 3) {
      for (int k = 0; k < n; k++) arg[k] = phases[k] * 0.037 + bits[k];
      vsin(second, arg, n);
    }
    for (int k = 0; k < n; k++) {
      const int i = first + k;
      const double local = locals[k], symbolPosition = positions[k];
      double encoded;
      if (encoding == 1) encoded = tone[k];
      else if (encoding == 2) encoded = tone[k] * second[k];
      else if (encoding == 3) encoded = tone[k] * (0.62 + 0.38 * second[k]);
      else encoded = tone[k] + 0.08 * deviation * second[k];
      const double packetEnvelope = std::max(0.0, min3(1.0, local / edge, (active - local) / edge));
      const double bitEnvelope = encoding == 2 ? std::min(1.0, symbolPosition / symbolEdge)
          : 0.88 + 0.12 * min3(1.0, symbolPosition / symbolEdge, (symbolSamples - symbolPosition) / symbolEdge);
      const double radio = hiss[k] + beat[k] * 0.14;
      const double squelch = 0.4 + 0.6 * packetEnvelope;
      double sample = encoded * 0.52 * gains[k] * packetEnvelope * bitEnvelope + radio * interference * squelch;
      // A narrow receiver rolls off the roughest static in radio mode.
      radioLow += (sample - radioLow) * 0.3;
      if (encoding == 3) sample = radioLow;
      if (i >= delayA) sample += output[i - delayA] * echo * 0.38;
      if (i >= delayB) sample -= output[i - delayB] * echo * 0.17;
      output[i] = static_cast<float>(sample);
    }
  }
  finish(output, volume);
  return output;
}

MSN_ENGINE("Signlr", render_signlr);

}  // namespace msn
