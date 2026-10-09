// Port of js/audio/Jinglr_DSP.js.
#include "dsp.h"
#include "vmath.h"

#include <cstdlib>
#include <cstring>

namespace msn {

namespace {

struct Note { bool rest; double degree, beats; };

// Reads the score as the synth stores it: [{"degree":number|null,"beats":number},...].
// Any other text counts as unparseable, which selects the default phrase.
bool parse_phrase(const char* s, std::vector<Note>& notes) {
  auto eat = [&](char c) {
    while (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r') ++s;
    if (*s != c) return false;
    if (c) ++s;
    return true;
  };
  if (!eat('[')) return false;
  do {
    Note note{false, 0, 0.5};
    if (!eat('{')) return false;
    if (!eat('}')) {
      do {
        if (!eat('"')) return false;
        const char* key = s;
        while (*s && *s != '"') ++s;
        const std::string name(key, s);
        if (!eat('"') || !eat(':')) return false;
        const bool null = eat('n');
        double number = NAN;
        if (null) {
          if (std::strncmp(s, "ull", 3) != 0) return false;
          s += 3;
        } else {
          char* stop = nullptr;
          number = std::strtod(s, &stop);
          if (stop == s) return false;
          s = stop;
        }
        const bool finite = std::isfinite(number);
        if (name == "degree") { note.rest = null; note.degree = finite ? jsround(clamp(number, -7, 14)) : 0; }
        if (name == "beats") note.beats = jsround((finite ? clamp(number, 0.25, 2) : 0.5) * 4) / 4;
      } while (eat(','));
      if (!eat('}')) return false;
    }
    notes.push_back(note);
  } while (eat(','));
  return eat(']') && eat('\0');
}

// Jinglr_DSP.phrase.
std::vector<Note> phrase(const Params& p) {
  std::vector<Note> notes;
  const auto text = p.strings.find("phrase");
  if (text == p.strings.end() || text->second.size() > 4096 || !parse_phrase(text->second.c_str(), notes))
    notes = {{false, 0, 0.5}, {false, 2, 0.5}, {false, 4, 0.5}, {false, 7, 1}};
  if (notes.size() > 12) notes.resize(12);
  return notes;
}

// Jinglr_DSP.midi for a sounding note.
double midi(double degree, const Params& p) {
  static const std::vector<int> scales[4] = {{0, 2, 4, 5, 7, 9, 11}, {0, 2, 3, 5, 7, 8, 10}, {0, 2, 4, 7, 9}, {0, 2, 3, 5, 7, 9, 10}};
  const std::vector<int>& scale = scales[static_cast<int>(jsround(p.value("scale", 0, 0, 3)))];
  const double octave = jsround(p.value("octave", 4, 3, 6)), key = jsround(p.value("key", 0, 0, 11));
  const double size = static_cast<double>(scale.size());
  const int index = static_cast<int>(std::fmod(std::fmod(degree, size) + size, size));
  return (octave + 1) * 12 + key + std::floor(degree / size) * 12 + scale[index];
}

struct Event { bool rest; double frequency, start, duration; };
struct Score { std::vector<Event> events; double duration; };

// Jinglr_DSP.schedule.
Score schedule(const Params& p) {
  const double beat = 60 / p.value("tempo", 140, 60, 220), swing = p.value("swing", 0, 0, 0.6);
  double cursor = 0;
  const std::vector<Note> notes = phrase(p);
  std::vector<Event> events;
  for (size_t index = 0; index < notes.size(); index++) {
    const Note& note = notes[index];
    // Swing redistributes each pair's time, even when its beat values differ.
    const size_t pair = index / 2 * 2;
    const double shift = pair + 1 < notes.size() ? std::min(notes[pair].beats, notes[pair + 1].beats) * swing : 0;
    const double duration = (note.beats + (index % 2 ? -shift : shift)) * beat;
    const double frequency = note.rest ? 0 : 440 * jspow(2, (midi(note.degree, p) - 69) / 12);
    events.push_back({note.rest, frequency, cursor, duration});
    cursor += duration;
  }
  return {events, cursor};
}

struct Voice {
  int instrument;
  double seed, attack, release, damping, slope, color, hollow, filter, body, modulation, modRatio, spread, pick;
};

// Jinglr_DSP.voice: each code describes a whole instrument.
Voice make_voice(const Params& p) {
  Voice voice;
  voice.instrument = static_cast<int>(jsround(p.value("instrument", 0, 0, 7)));
  voice.seed = jsround(p.value("instrumentSeed", 42731, 0, 99999));
  Rng random((voice.instrument * 100000 + voice.seed + 1) / 800001);
  static const double attackRanges[8][2] = {{0.001, 0.012}, {0.001, 0.006}, {0.001, 0.009}, {0.006, 0.04},
                                            {0.001, 0.012}, {0.012, 0.06},  {0.001, 0.015}, {0.025, 0.12}};
  const double* attack = attackRanges[voice.instrument];
  voice.attack = attack[0] + random() * (attack[1] - attack[0]);
  voice.release = 0.6 + random() * 0.85;
  voice.damping = 0.45 + random() * 1.9;
  voice.slope = 0.65 + random() * 1.5;
  voice.color = 0.2 + random() * 0.75;
  voice.hollow = random();
  voice.filter = 1.5 + random() * 9;
  voice.body = 0.65 + random() * 0.35;
  voice.modulation = 0.3 + random() * 3.5;
  voice.modRatio = 1 + std::floor(random() * 4);
  voice.spread = 0.001 + random() * 0.005;
  voice.pick = 0.08 + random() * 0.4;
  return voice;
}

}  // namespace

std::vector<float> render_jinglr(const Params& p) {
  const Score score = schedule(p);
  const double rate = kRate;
  const double brightness = p.value("brightness", 0.55, 0, 1);
  const double decay = p.value("decay", 0.45, 0, 1);
  const double echo = p.value("echo", 0.12, 0, 0.8);
  const Voice voice = make_voice(p);
  const int instrument = voice.instrument;
  const double tail = (0.035 + decay * 0.26) * voice.release;
  const double delay = 60 / p.value("tempo", 140, 60, 220) * 0.75;
  const double echoTail = echo > 0 ? delay * 3 : 0;
  std::vector<float> pcm(static_cast<size_t>(std::ceil((score.duration + tail + echoTail) * rate)));
  const int total = static_cast<int>(pcm.size());
  // Timbre, attacks and breath have their own RNG; melody seed only chooses notes.
  Rng random(std::fmod(voice.seed * 7 + instrument * 100003 + 1, 1000003.0) / 1000003);
  struct Partial { double step, gain, falloff, offset; };
  std::vector<Partial> partials;
  for (const Event& note : score.events) {
    if (note.rest) continue;
    const int start = static_cast<int>(jsround(note.start * rate));
    const double gate = note.duration * (0.52 + 0.38 * decay) * voice.body;
    const int length = static_cast<int>(std::ceil((gate + tail) * rate));
    const double strength = 0.84 + random() * 0.16;
    const double phase = random() * kPi * 2;
    partials.clear();
    auto addPartial = [&](double ratio, double gain, double falloff, double offset = 0) {
      if (note.frequency * ratio < rate * 0.45)
        partials.push_back({kPi * 2 * note.frequency * ratio / rate, gain, std::exp(-falloff * voice.damping / rate), offset});
    };
    if (instrument == 0) {
      // A plucked harmonic string; bright overtones die away first.
      for (int h = 1; h <= 10; h++) {
        const double pick = h == 1 ? 1 : 0.25 + 0.75 * std::fabs(std::sin(kPi * h * voice.pick));
        addPartial(h, pick * jspow(0.12 + brightness * 0.85, h - 1) / jspow(h, voice.slope), (1.5 + (1 - decay) * 7) * std::sqrt(h));
      }
    } else if (instrument == 1) {
      const double ratios[4] = {1, 2 + voice.color * 1.1, 3.8 + voice.hollow * 2.3, 7.5 + voice.color * 2.5};
      for (int h = 0; h < 4; h++)
        addPartial(ratios[h], h == 0 ? 0.8 : (0.1 + brightness * 0.85) / jspow(h + 1, voice.slope), (0.7 + (1 - decay) * 5) * (1 + h * 0.6));
    } else if (instrument == 2) {
      // A pulse of varying duty, represented by band-limited harmonics.
      const double duty = 0.12 + voice.hollow * 0.38;
      for (int h = 1; h <= 16; h++)
        addPartial(h, 0.8 * std::sin(kPi * h * duty) / std::sin(kPi * duty) * jspow(0.3 + brightness * 0.7, h - 1) / jspow(h, voice.slope),
                   0.45 + (1 - decay) * 2);
    } else if (instrument == 3) {
      addPartial(1, 0.8, 0.35 + (1 - decay) * 1.5);
      for (int h = 2; h <= 5; h++)
        addPartial(h, brightness * voice.color * 0.5 / jspow(h - 1, voice.slope), (0.35 + (1 - decay) * 1.5) * (1 + h * 0.15));
    } else if (instrument == 4) {
      // Hammered keys mix a warm body with short, ringing tine overtones.
      for (int h = 1; h <= 8; h++)
        addPartial(h, (h == 1 ? 0.85 : (0.2 + brightness * 0.7) * (h % 2 ? 0.55 : 1)) / jspow(h, voice.slope), (0.8 + (1 - decay) * 4) * (1 + h * 0.3));
      addPartial(4 + voice.color * 0.04, brightness * voice.hollow * 0.35, 12 + (1 - decay) * 12);
    } else if (instrument == 5) {
      // Reed character moves between hollow odd partials and a nasal full spectrum.
      for (int h = 1; h <= 12; h++) {
        const double resonance = 1 + voice.color * std::exp(-jspow((h - (2 + voice.hollow * 4)) / 2, 2)) * 2;
        const double even = h % 2 ? 1 : 0.1 + voice.hollow * 0.85;
        addPartial(h, 0.65 * resonance * even * jspow(0.35 + brightness * 0.65, h - 1) / jspow(h, voice.slope), 0.2 + (1 - decay) * 0.8);
      }
    } else if (instrument == 6) {
      // An unmodulated center holds the note underneath the changing FM spectrum.
      addPartial(1, 0.28, 0.5 + (1 - decay) * 3);
    } else {
      // Paired detuned partials make a bowed ensemble without moving its center pitch.
      for (int h = 1; h <= 10; h++) {
        const double gain = 0.32 * jspow(0.5 + brightness * 0.48, h - 1) / jspow(h, voice.slope);
        addPartial(h * (1 - voice.spread), gain, 0.15 + (1 - decay) * 0.6);
        addPartial(h * (1 + voice.spread), gain, 0.15 + (1 - decay) * 0.6, voice.color * 2);
      }
    }
    const double startPhase = instrument == 2 ? 0 : phase;
    const double attackLength = std::min(voice.attack, gate * 0.65) * rate;
    double breath = 0.005 * brightness * (0.3 + voice.hollow);
    const double breathFalloff = std::exp(-(0.5 + (1 - decay) * 2) * voice.damping / rate);
    const double cutoff = std::min(rate * 0.44, note.frequency * (voice.filter + brightness * 9));
    const double filter = 1 - std::exp(-kPi * 2 * cutoff / rate);
    double filtered = 0;
    const double fundamental = kPi * 2 * note.frequency / rate;
    // Reserve room for FM sidebands at high registers.
    const double fmIndex = std::min(voice.modulation * (0.15 + brightness), std::max(0.0, (rate * 0.4 / note.frequency - 1) / voice.modRatio));
    double fmAmount = fmIndex, fmGain = 0.62;
    const double fmFalloff = std::exp(-(2 + (1 - decay) * 8) * voice.damping / rate);
    const double fmGainFalloff = std::exp(-(0.6 + (1 - decay) * 3) * voice.damping / rate);
    // The JS loop body, one partial at a time over each block so the sines are batched.
    const int count = std::min(length, total - start);
    double arg[kBlock], sine[kBlock], samples[kBlock];
    for (int first = 0; first < count; first += kBlock) {
      const int n = std::min(kBlock, count - first);
      for (int k = 0; k < n; k++) samples[k] = 0;
      for (Partial& partial : partials) {
        for (int k = 0; k < n; k++) arg[k] = partial.step * (first + k) + startPhase + partial.offset;
        vsin(sine, arg, n);
        for (int k = 0; k < n; k++) { samples[k] += sine[k] * partial.gain; partial.gain *= partial.falloff; }
      }
      if (instrument == 3 || instrument == 5)
        for (int k = 0; k < n; k++) { samples[k] += (random() * 2 - 1) * breath; breath *= breathFalloff; }
      if (instrument == 6) {
        for (int k = 0; k < n; k++) arg[k] = fundamental * (first + k) * voice.modRatio;
        vsin(sine, arg, n);
        for (int k = 0; k < n; k++) {
          arg[k] = fundamental * (first + k) + startPhase + (fmIndex * 0.18 + fmAmount) * sine[k];
          fmAmount *= fmFalloff;
        }
        vsin(sine, arg, n);
        for (int k = 0; k < n; k++) { samples[k] += sine[k] * fmGain; fmGain *= fmGainFalloff; }
      }
      for (int k = 0; k < n; k++) {
        const int i = first + k;
        const double time = i / rate;
        const double attack = i < attackLength ? i / attackLength : 1;
        const double release = time > gate ? 1 - (time - gate) / tail : 1;
        filtered += (samples[k] - filtered) * filter;
        add(pcm[start + i], filtered * attack * release * strength);
      }
    }
  }
  if (echo > 0) {
    const std::vector<float> dry = pcm;
    for (int repeat = 1; repeat <= 3; repeat++) {
      const int offset = static_cast<int>(jsround(delay * repeat * rate));
      const double gain = jspow(echo * 0.58, repeat);
      for (int i = 0; i + offset < total; i++) add(pcm[i + offset], dry[i] * gain);
    }
  }
  finish(pcm, p.value("masterVolume", 0.5, 0, 1));
  return pcm;
}

MSN_ENGINE("Jinglr", render_jinglr);

}  // namespace msn
