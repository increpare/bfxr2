// Port of js/audio/Glitchr_DSP.js.
#include "dsp.h"
#include "vmath.h"

namespace msn {

namespace {

// Math.hypot as V8 computes it: scaled by the larger magnitude, Kahan-summed.
double jshypot(double a, double b) {
  const double values[2] = {std::fabs(a), std::fabs(b)};
  const double largest = std::max(values[0], values[1]);
  if (largest == 0) return 0;
  double sum = 0, compensation = 0;
  for (double value : values) {
    const double n = value / largest, summand = n * n - compensation, preliminary = sum + summand;
    compensation = (preliminary - sum) - summand;
    sum = preliminary;
  }
  return std::sqrt(sum) * largest;
}

}  // namespace

std::vector<float> render_glitchr(const Params& p) {
  const double tau = kPi * 2;
  const double rate = kRate, duration = p.value("duration", 0.7, 0.08, 4);
  const int frames = static_cast<int>(jsround(duration * rate));
  std::vector<float> out(frames);
  Rng random(p.value("seed", 0.5));
  const int mode = static_cast<int>(jsround(p.value("mode", 0, 0, 7)));
  const double base = 80 * jspow(2, p.value("pitch", 0.5) * 4), fragment = p.value("fragment", 0.3), repeat = p.value("repeat", 0.4);
  const double chaos = p.value("chaos", 0.5), dropout = p.value("dropout", 0.2), crush = p.value("crush", 0.3), rateLoss = p.value("rate", 0.3);
  const int chunk = static_cast<int>(std::max(80.0, jsround((0.009 + fragment * 0.18) * rate)));
  const int hold = 1 + static_cast<int>(jsround(rateLoss * 27));
  const double steps = jspow(2, 13 - jsround(crush * 11));
  // A short, evolving source gives repeated buffers recognisable attacks and timbre.
  const int length = static_cast<int>(jsround(rate * 0.83));
  std::vector<float> source(length);
  static const double notes[5] = {1, 1.25, 0.75, 1.5, 1.125};
  double sourceLow = 0;
  // The JS loop body, split so its sines and decays are batched.
  double arg[kBlock], locals[kBlock], pitches[kBlock], sine[kBlock], sine2[kBlock], sine4[kBlock], decay[kBlock], click[kBlock];
  for (int first = 0; first < length; first += kBlock) {
    const int n = std::min(kBlock, length - first);
    for (int k = 0; k < n; k++) {
      const double t = (first + k) / rate, note = std::floor(t / 0.137), local = t - note * 0.137;
      const double f = base * notes[static_cast<int>(note) % 5];
      locals[k] = local; pitches[k] = f; arg[k] = tau * f * local;
    }
    vsin(sine, arg, n);
    for (int k = 0; k < n; k++) arg[k] = tau * pitches[k] * 2.01 * locals[k];
    vsin(sine2, arg, n);
    for (int k = 0; k < n; k++) arg[k] = tau * pitches[k] * 3.97 * locals[k];
    vsin(sine4, arg, n);
    for (int k = 0; k < n; k++) arg[k] = -locals[k] * 18;
    vexp(decay, arg, n);
    for (int k = 0; k < n; k++) arg[k] = -locals[k] * 120;
    vexp(click, arg, n);
    for (int k = 0; k < n; k++) {
      const double noise = random() * 2 - 1; sourceLow += (noise - sourceLow) * 0.12;
      const double pluck = (sine[k] + 0.35 * sine2[k] + 0.18 * sine4[k]) * decay[k];
      const double transient = (noise - sourceLow) * click[k] * 0.25;
      source[first + k] = static_cast<float>((pluck * 0.55 + transient + sourceLow * 0.24) * std::min(1.0, locals[k] / 0.001));
    }
  }
  auto read = [&](double position) {
    const double wrapped = std::fmod(std::fmod(position, length) + length, length);
    const int index = static_cast<int>(std::floor(wrapped));
    const double mix = wrapped - index;
    return source[index] * (1 - mix) + source[(index + 1) % length] * mix;
  };
  double head = 0, anchor = 0, speed = 1, sample = 0, previous = 0, dc = 0, scrubLow = 0;
  bool skip = false;
  double dataPhase = 0;
  int dataBit = 0, dataCount = 0;
  uint32_t shift = 1 + static_cast<uint32_t>(std::floor(random() * 65534));
  double bandLow = 0, bandMid = 0, bandHigh = 0, packetGain[4] = {1, 1, 1, 1}, resolutions[4];
  for (int band = 0; band < 4; band++) resolutions[band] = jspow(2, 3 + band - (crush * 2));
  struct Grain { int age; double length, head, speed; };
  std::vector<Grain> grains;
  struct Partial { double phase, frequency, gain; };
  Partial frozen[6];
  for (int n = 0; n < 6; n++) frozen[n] = {random() * tau, base * (1 + n * 0.51), 0};
  int grainCountdown = 0;
  double grainOrigin = 0;
  for (int i = 0; i < frames; i++) {
    const double t = i / rate;
    const int j = i % chunk;
    if (j == 0) {
      const bool fresh = i == 0 || random() > repeat;
      skip = i > 0 && random() < dropout * 0.86;
      if (fresh) {
        anchor = std::floor(random() * (length - chunk));
        speed = jspow(2, (random() - 0.5) * chaos * 2.4);
        grainOrigin = anchor;
      }
      if (mode == 0 || mode == 6) head = anchor;
      if (mode == 2) {
        if (fresh) head = anchor;
        const double direction = random() < 0.55 ? -1 : 1;
        speed = direction * (0.2 + random() * 2.8) * (0.4 + chaos);
      }
      for (double& gain : packetGain) gain = 0.25 + random() * 1.2;
      if (mode == 7 && fresh) {
        for (Partial& partial : frozen) {
          partial.frequency = std::min(9000.0, base * (0.5 + jsround(random() * 11) / 4));
          double real = 0, imaginary = 0;
          for (int k = 0; k < 256; k++) {
            const double captured = read(anchor + k), phase = tau * partial.frequency * k / rate;
            real += captured * std::cos(phase); imaginary += captured * std::sin(phase);
          }
          partial.gain = 0.025 + std::min(0.22, jshypot(real, imaginary) / 128);
        }
      }
    }
    double value = 0;
    if (mode == 0) {
      // The device replays a stalled buffer until a fresh packet arrives.
      value = read(head); head += speed;
      if (head >= anchor + chunk) head = anchor;
      value *= min3(1.0, j / 16.0, (chunk - j) / 16.0);
    } else if (mode == 1) {
      // Crude subband coding: independent bands have damaged packet gains and precision.
      const double captured = read(head); head += speed * (1 + chaos * 0.45 * std::sin(tau * (8 + fragment * 25) * t));
      bandLow += (captured - bandLow) * 0.018; bandMid += (captured - bandMid) * 0.11; bandHigh += (captured - bandHigh) * 0.43;
      const double bands[4] = {bandLow, bandMid - bandLow, bandHigh - bandMid, captured - bandHigh};
      for (int band = 0; band < 4; band++) {
        const double coded = jsround(bands[band] * resolutions[band]) / resolutions[band];
        value += coded * packetGain[band] * (0.7 + 0.3 * std::sin(tau * (11 + band * 7 + chaos * 13) * t + band));
      }
      value = value * 1.7 + std::sin(tau * base * 1.43 * t) * std::fabs(bandMid - bandLow) * chaos * 0.6;
    } else if (mode == 2) {
      // Continuous reversible read-head motion; interpolation preserves tape-like bends.
      head += speed * (1 + chaos * 0.8 * std::sin(tau * (1.5 + fragment * 5) * t));
      const double captured = read(head); scrubLow += (captured - scrubLow) * std::min(0.95, 0.07 + std::fabs(speed) * 0.19);
      value = scrubLow * 1.5 + (random() * 2 - 1) * 0.018 * chaos;
    } else if (mode == 3) {
      const int decimation = 2 + static_cast<int>(jsround(rateLoss * 95 + crush * 25 * (static_cast<double>(i) / frames)));
      if (i % decimation == 0) {
        const double levels = jspow(2, 8 - jsround(crush * 6)), captured = read(head);
        int word = static_cast<int>(jsround((captured + 1) * levels));
        if (random() < chaos * 0.22) word ^= 1 << static_cast<int>(std::floor(random() * std::max(1.0, jsround(crush * 7))));
        previous = word / levels - 1;
      }
      head += 0.65 + speed * 0.45; value = previous * 0.85;
    } else if (mode == 4) {
      // A deterministic shift register transmits binary FSK and leaking logic edges.
      const int baud = static_cast<int>(jsround(rate / (100 + fragment * 1700)));
      if (dataCount-- <= 0) {
        shift = ((shift >> 1) ^ ((0u - (shift & 1u)) & 0xB400u)) & 65535u;
        dataBit = shift & 1u; dataCount = baud;
      }
      dataPhase += tau * std::min(rate * 0.42, base * (dataBit ? 7.3 + chaos : 4.17)) / rate;
      const double carrier = std::sin(dataPhase);
      value = (carrier > 0 ? 1 : -1) * 0.30 + carrier * 0.22 + (dataBit * 2 - 1) * 0.08;
    } else if (mode == 5) {
      // Several independent windowed grains overlap, with jumps and reverse fragments.
      if (grainCountdown-- <= 0) {
        const double size = std::max(100.0, jsround(chunk * (0.6 + random() * 0.9)));
        const double start = grainOrigin + (random() - 0.5) * length * chaos;
        const double pitch = jspow(2, (random() - 0.5) * chaos * 3);
        grains.push_back({0, size, start, pitch * (random() < chaos * 0.5 ? -1 : 1)});
        grainCountdown = static_cast<int>(std::max(30.0, jsround(size / (2.5 + repeat * 2))));
      }
      for (int n = static_cast<int>(grains.size()) - 1; n >= 0; n--) {
        Grain& grain = grains[n];
        const double window = 0.5 - 0.5 * std::cos(tau * grain.age / grain.length);
        value += read(grain.head) * window * 0.8; grain.head += grain.speed;
        if (++grain.age >= grain.length) grains.erase(grains.begin() + n);
      }
    } else if (mode == 6) {
      // Retrigger a complete captured phrase inside a longer packet.
      const int phrase = static_cast<int>(std::max(55.0, jsround(chunk / (1 + jsround(repeat * 5))))), position = j % phrase;
      value = read(anchor + position * (0.65 + speed * 0.35)) * min3(1.0, position / 12.0, (phrase - position) / 12.0);
      value *= 0.6 + 0.4 * std::exp(-position / (phrase * 0.25));
    } else {
      // Retain the measured partial levels while their phases continue across packets.
      for (Partial& partial : frozen) {
        partial.phase += tau * partial.frequency * (1 + chaos * 0.012 * std::sin(tau * 3 * t)) / rate;
        value += std::sin(partial.phase) * partial.gain;
      }
    }
    if (i % hold == 0) sample = jsround(value * steps) / steps;
    // A short DC blocker prevents flipped sign bits and data pulses shifting the baseline.
    dc += (sample - dc) * 0.001;
    out[i] = static_cast<float>(skip ? 0 : (sample - dc) * 0.85);
  }
  finish(out, p.value("masterVolume", 0.5));
  return out;
}

MSN_ENGINE("Glitchr", render_glitchr);

}  // namespace msn
