#include "dsp.h"
#include "vmath.h"

#include <cstdlib>
#include <stdexcept>

namespace msn {

double jspow(double x, double y) {
  if (y == 2.0) return x * x;
  if (y == 0.5) return std::sqrt(x);
  return std::pow(x, y);
}

Rng::Rng(double seed) {
  // Math.floor(seed * 4294967295) >>> 0
  double v = std::floor(seed * 4294967295.0);
  if (!std::isfinite(v)) v = 0;
  v = std::fmod(v, 4294967296.0);
  if (v < 0) v += 4294967296.0;
  s_ = static_cast<uint32_t>(v);
}

double Params::value(const char* name, double fallback, double lo, double hi) const {
  auto it = numbers.find(name);
  return it == numbers.end() ? fallback : clamp(it->second, lo, hi);
}

double Params::number(const char* name) const {
  auto it = numbers.find(name);
  if (it == numbers.end()) throw std::runtime_error(std::string("missing parameter: ") + name);
  return it->second;
}

const Transition* Params::transition(const char* name) const {
  auto it = transitions.find(name);
  return it == transitions.end() ? nullptr : &it->second;
}

void finish(std::vector<float>& buffer, double volume, bool loop) {
  const size_t n = buffer.size();
  double mean = 0;
  for (float v : buffer) mean += std::isfinite(v) ? static_cast<double>(v) : 0.0;
  mean /= std::max<double>(1, static_cast<double>(n));
  const double fade_length = std::max(1.0, std::min(220.0, std::floor(static_cast<double>(n) / 2)));
  const double level = clamp(volume, 0, 1);
  double centred[kBlock], shaped[kBlock];
  for (size_t first = 0; first < n; first += kBlock) {
    const int count = static_cast<int>(std::min<size_t>(kBlock, n - first));
    for (int k = 0; k < count; k++)
      centred[k] = std::isfinite(buffer[first + k]) ? static_cast<double>(buffer[first + k]) - mean : 0.0;
    vtanh(shaped, centred, count);
    for (int k = 0; k < count; k++) {
      const double i = static_cast<double>(first + k);
      const double fade = loop ? 1.0 : min3(1.0, i / fade_length, (static_cast<double>(n) - 1 - i) / fade_length);
      buffer[first + k] = static_cast<float>(shaped[k] * level * 0.95 * fade);
    }
  }
}

// ---- Minimal JSON reader for worker requests --------------------------------

namespace {

struct Reader {
  const char* p;
  const char* end;
  std::string error;

  void ws() { while (p < end && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) ++p; }
  bool fail(const char* message) { if (error.empty()) error = message; return false; }
  bool eat(char c) { ws(); if (p < end && *p == c) { ++p; return true; } return false; }
  char peek() { ws(); return p < end ? *p : '\0'; }

  bool string(std::string& out) {
    if (!eat('"')) return fail("expected string");
    out.clear();
    while (p < end && *p != '"') {
      char c = *p++;
      if (c != '\\') { out.push_back(c); continue; }
      if (p >= end) return fail("bad escape");
      char e = *p++;
      switch (e) {
        case 'n': out.push_back('\n'); break;
        case 't': out.push_back('\t'); break;
        case 'r': out.push_back('\r'); break;
        case 'b': out.push_back('\b'); break;
        case 'f': out.push_back('\f'); break;
        case 'u': {
          if (end - p < 4) return fail("bad unicode escape");
          unsigned code = static_cast<unsigned>(std::strtoul(std::string(p, 4).c_str(), nullptr, 16));
          p += 4;
          // Controls are ASCII in practice; encode the BMP code unit as UTF-8.
          if (code < 0x80) out.push_back(static_cast<char>(code));
          else if (code < 0x800) { out.push_back(static_cast<char>(0xC0 | (code >> 6))); out.push_back(static_cast<char>(0x80 | (code & 0x3F))); }
          else { out.push_back(static_cast<char>(0xE0 | (code >> 12))); out.push_back(static_cast<char>(0x80 | ((code >> 6) & 0x3F))); out.push_back(static_cast<char>(0x80 | (code & 0x3F))); }
          break;
        }
        default: out.push_back(e);
      }
    }
    if (p >= end) return fail("unterminated string");
    ++p;
    return true;
  }

  bool number(double& out) {
    ws();
    char* stop = nullptr;
    out = std::strtod(p, &stop);
    if (stop == p) return fail("expected number");
    p = stop;
    return true;
  }

  // Skip any value (arrays, nested objects, literals) we have no use for.
  bool skip() {
    char c = peek();
    if (c == '"') { std::string s; return string(s); }
    if (c == '{' || c == '[') {
      const char close = c == '{' ? '}' : ']';
      ++p;
      if (eat(close)) return true;
      do {
        if (c == '{') { std::string key; if (!string(key) || !eat(':')) return fail("bad object"); }
        if (!skip()) return false;
      } while (eat(','));
      return eat(close) || fail("unterminated container");
    }
    if (c == 't' || c == 'f' || c == 'n') { while (p < end && *p >= 'a' && *p <= 'z') ++p; return true; }
    double ignored;
    return number(ignored);
  }

  template <class Member>
  bool object(Member member) {
    if (!eat('{')) return fail("expected object");
    if (eat('}')) return true;
    do {
      std::string key;
      if (!string(key) || !eat(':')) return fail("bad object");
      if (!member(key)) return false;
    } while (eat(','));
    return eat('}') || fail("unterminated object");
  }
};

}  // namespace

bool parse_request(const std::string& line, Request& out, std::string& error) {
  Reader r{line.data(), line.data() + line.size(), {}};
  bool has_id = false;
  auto is_number = [&] { char c = r.peek(); return c == '-' || (c >= '0' && c <= '9'); };
  bool ok = r.object([&](const std::string& key) {
    double v;
    if (key == "id") { if (!r.number(v)) return false; out.id = static_cast<uint32_t>(v); has_id = true; return true; }
    if (key == "seed") { if (!r.number(v)) return false; out.seed = static_cast<uint32_t>(v); return true; }
    if (key == "synth") return r.string(out.synth);
    if (key != "params") return r.skip();
    return r.object([&](const std::string& name) {
      if (is_number()) return r.number(out.params.numbers[name]);
      if (r.peek() == '"') return r.string(out.params.strings[name]);
      if (r.peek() != '{') return r.skip();
      Transition& transition = out.params.transitions[name];
      return r.object([&](const std::string& field) {
        if (field == "start" && is_number()) return r.number(transition.start);
        if (field == "end" && is_number()) return r.number(transition.end);
        if (field == "curve" && r.peek() == '"') return r.string(transition.curve);
        return r.skip();
      });
    });
  });
  if (ok && !has_id) ok = r.fail("missing id");
  if (ok && out.synth.empty()) ok = r.fail("missing synth");
  if (!ok) error = r.error;
  return ok;
}

}  // namespace msn
