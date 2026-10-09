// Port of js/audio/Fractr_DSP.js.
#include "dsp.h"

namespace msn {

std::vector<float> render_fractr(const Params& p) {
  struct Material { double pitch, ring, noise, cutoff, grit, ratios[3]; };
  static const Material materials[8] = {
      {1.65, 0.22, 1.7, 11000, 0.28, {1, 2.71, 4.83}},    // Glass
      {0.84, 0.15, 2.1, 6500, 0.6, {1, 1.91, 3.77}},      // Ice
      {1.05, 1.75, 0.025, 10000, 0, {1, 1.505, 2.014}},   // Crystal
      {0.17, 0.08, 3.8, 1700, 1, {1, 1.63, 2.42}},        // Stone
      {1.0, 0.6, 0.015, 10000, 0, {1, 2, 4}},             // Pixel
      {0.65, 0.26, 1.8, 7000, 0.42, {1, 2.39, 5.17}},     // Armor
      {0.39, 0.1, 2.8, 3800, 0.45, {1, 1.82, 3.03}},      // Bone
      {0.55, 0.015, 2.8, 5100, 0.65, {1, 1.77, 3.11}}};   // Biscuit
  const double rate = kRate;
  Rng random(p.value("seed", 0.5));
  const double duration = p.value("duration", 1.8, 0.15, 6);
  const int frames = static_cast<int>(jsround(duration * rate));
  std::vector<float> output(frames);
  const int materialIndex = static_cast<int>(jsround(p.value("material", 0, 0, 7)));
  const Material& material = materials[materialIndex];
  const bool tuned = materialIndex == 2 || materialIndex == 4;
  const int fragments = static_cast<int>(jsround(p.value("fragments", 32, 3, 96)));
  const double size = p.value("fragmentSize", 0.4), spread = p.value("spread", 0.6);
  const double stress = p.value("stress", 0.4), fracture = p.value("fracture", 0.75);
  const double decay = p.value("decay", 0.4), gravity = p.value("gravity", 0.5), bounce = p.value("bounce", 0.4);
  const double cascadeTime = duration * (0.012 + spread * 0.72) * (1 - gravity * 0.6);
  const double gain = 1.45 * p.value("shards", 0.35) / jspow(fragments, 0.3), tau = 2 * kPi;
  const int bounceCount = static_cast<int>(jsround(bounce * 4));

  for (int shard = 0; shard < fragments; shard++) {
    const double shardSize = std::max(0.0, std::min(1.0, size + (random() - 0.5) * 0.26));
    const double progress = (shard + random() * 0.65) / fragments;
    double time = 0.006 + cascadeTime * jspow(progress, 0.75 + 0.7 * gravity);
    if (materialIndex == 4) time = jsround(time * 48) / 48 + 0.006;
    const int start = static_cast<int>(jsround(time * rate));
    double frequency = 2700 * jspow(2, -shardSize * 4.5) * material.pitch * (0.65 + 0.7 * random());
    if (materialIndex == 4) frequency = 110 * jspow(2, jsround(12 * std::log2(frequency / 110)) / 12);
    const double ringTime = (0.006 + decay * 0.23) * material.ring * (0.8 + random() * 0.4);
    const double contactTime = tuned ? 0.0025 : 0.0018 + (0.004 + decay * 0.025) * (0.4 + shardSize) * (0.7 + material.grit);
    const double noiseRadius = std::exp(-1 / (rate * contactTime));
    const double crackRadius = std::exp(-1 / (rate * (0.0003 + shardSize * 0.00065)));
    const double cutoff = material.cutoff * jspow(2, -shardSize * 1.6);
    const double dustFilter = 1 - std::exp(-tau * cutoff / rate);
    const double bodyFilter = 1 - std::exp(-tau * (130 + 1700 * (1 - shardSize) * material.pitch) / rate);
    const double strength = gain * (0.55 + random() * 0.65) * (1 - progress * 0.3);
    const double flight = (0.045 + 0.34 * (1 - gravity)) * (0.4 + 0.6 * shardSize);
    struct Contact { int sample; double strength; };
    Contact contacts[5] = {{start, strength}};
    const int contactCount = bounceCount + 1;
    double nextTime = time, nextFlight = flight, nextStrength = strength;
    for (int j = 0; j < bounceCount; j++) {
      nextTime += nextFlight;
      nextFlight *= 0.43 + bounce * 0.24;
      nextStrength *= 0.27 + bounce * 0.42;
      contacts[j + 1] = {static_cast<int>(jsround(nextTime * rate)), nextStrength};
    }
    const int end = static_cast<int>(std::min<double>(
        frames, contacts[contactCount - 1].sample + jsround(std::max(ringTime, contactTime) * 7 * rate)));
    struct Mode { double c, s; };
    Mode modes[3];
    for (int index = 0; index < 3; index++) {
      const double angle = tau * std::min(11000.0, frequency * material.ratios[index]) / rate;
      const double radius = std::exp(-(1 + index * 0.55) / (ringTime * rate));
      modes[index] = {std::cos(angle) * radius, std::sin(angle) * radius};
    }
    // Unrolled three-mode rotators keep the busiest 96-shard cascades cheap.
    const Mode a = modes[0], b = modes[1], c = modes[2];
    double ar = 0, ai = 0, br = 0, bi = 0, cr = 0, ci = 0, noiseEnvelope = 0, dust = 0, body = 0;
    double crackEnvelope = 0, contactStrength = 0;
    int nextContact = 0, crackLeft = 0, nextCrack = 0;
    for (int i = start; i < end; i++) {
      if (nextContact < contactCount && i == contacts[nextContact].sample) {
        const double hit = contacts[nextContact++].strength;
        const double modeGain = tuned ? 1 : 0.12;
        ar += hit * modeGain; br += hit * modeGain * 0.44; cr += hit * modeGain * 0.24;
        noiseEnvelope += hit * material.noise * (tuned ? 1 : 0.58);
        // An initial split has several tiny failures; later contacts scrape once.
        contactStrength = hit;
        crackLeft = tuned ? 0 : (nextContact == 1 ? 3 + static_cast<int>(jsround(shardSize * 4)) : 1);
        nextCrack = i;
      }
      if (crackLeft > 0 && i == nextCrack) {
        crackEnvelope += contactStrength * (0.5 + random() * 0.9);
        nextCrack += 5 + static_cast<int>(jsround(random() * (25 + shardSize * 100)));
        crackLeft--;
      }
      const double an = ar * a.c - ai * a.s;
      ai = ar * a.s + ai * a.c; ar = an;
      const double bn = br * b.c - bi * b.s;
      bi = br * b.s + bi * b.c; br = bn;
      const double cn = cr * c.c - ci * c.s;
      ci = cr * c.s + ci * c.c; cr = cn;
      const double noise = random() * 2 - 1;
      dust += (noise - dust) * dustFilter;
      body += (noise - body) * bodyFilter;
      const double rough = dust + body * material.grit;
      add(output[i], (ar + br + cr) * 0.52 + rough * noiseEnvelope + (dust - body * 0.5) * crackEnvelope);
      noiseEnvelope *= noiseRadius;
      crackEnvelope *= crackRadius;
    }
  }
  // The parent object fails before its loose fragments land: branching
  // clusters of bipolar stress releases over a slower mass response.
  Rng structuralRandom(p.value("seed", 0.5) * 0.79 + 0.137);
  const double splitTime = 0.011 + stress * 0.029;
  static const double widths[8] = {0.00012, 0.00065, 0.0002, 0.0022, 0.00015, 0.00023, 0.0011, 0.00022};
  static const double masses[8] = {0.06, 0.9, 0.08, 1, 0.02, 0.35, 1.3, 0.15};
  const double mass = masses[materialIndex];
  const double width = widths[materialIndex] * (0.7 + size * 0.8);
  const double splitGain = fracture * (tuned ? 0.25 : materialIndex == 7 ? 2.2 : 3.4);
  const int branches = materialIndex == 7 ? 34 + static_cast<int>(jsround(size * 28))
                       : materialIndex == 6 ? 5 : 7 + static_cast<int>(jsround(size * 9));
  for (int branch = 0; branch < branches; branch++) {
    const double u = static_cast<double>(branch) / branches;
    const double branchSpan = materialIndex == 7 ? 0.065 + stress * 0.07 : materialIndex == 6 ? 0.017
                              : materialIndex == 1 ? 0.045 + stress * 0.025 : 0.022 + stress * 0.035;
    const double delay = branch == 0 ? 0 : 0.001 + jspow(u, 1.6) * branchSpan * (0.75 + structuralRandom() * 0.5);
    const int start = static_cast<int>(jsround((splitTime + delay) * rate));
    const double release = width * (0.7 + structuralRandom() * 0.9);
    const double weight = splitGain * (branch == 0 ? 1 : 0.25 + 0.4 * (1 - u)) * (0.75 + structuralRandom() * 0.5);
    const int length = static_cast<int>(std::min<double>(frames - start, jsround((release * 9 + 0.009 * mass) * rate)));
    double gritLow = 0, massGrit = 0;
    const double gritRate = 1 - std::exp(-tau * material.cutoff * 0.55 / rate);
    for (int j = 0; j < length; j++) {
      const double t = j / rate, q = t / release;
      gritLow += gritRate * (structuralRandom() * 2 - 1 - gritLow);
      const double tensile = (1 - q) * std::exp(-q);
      const double tearing = gritLow * std::exp(-t / (release * 3)) * 0.55;
      const double bodyQ = t / (0.002 + mass * 0.004);
      massGrit += 0.12 * (structuralRandom() * 2 - 1 - massGrit);
      const double body = ((1 - bodyQ) + massGrit * (materialIndex == 3 || materialIndex == 6 ? 6 : 1.2)) * std::exp(-bodyQ) * mass * 0.95;
      add(output[start + j], weight * (tensile + tearing + body));
    }
  }
  if (!tuned && stress > 0) {
    // Intermittent pre-failure strain; no ringing musical mode.
    double slow = 0, fast = 0;
    const int end = static_cast<int>(std::min<double>(frames, jsround(splitTime * rate)));
    for (int i = static_cast<int>(jsround(0.005 * rate)); i < end; i++) {
      const double u = static_cast<double>(i) / end, noise = structuralRandom() * 2 - 1;
      slow += 0.006 * (noise - slow); fast += 0.055 * (noise - fast);
      const double stutter = jspow(0.5 + 0.5 * std::sin(u * (36 + materialIndex * 9)), 5);
      add(output[i], (fast - slow) * stutter * stress * u * 2.5);
    }
  }
  finish(output, p.value("masterVolume", 0.5));
  return output;
}

MSN_ENGINE("Fractr", render_fractr);

}  // namespace msn
