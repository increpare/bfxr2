#pragma once
// Shared pieces of the JS synth runtime, ported with JS number semantics:
// every value is a double, Float32Array stores round to float, and
// expressions keep the source's operator order (build with -ffp-contract=off).

#include <cmath>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace msn {

constexpr double kRate = 44100.0;       // SoundDSP.rate
constexpr double kPi = 3.141592653589793;  // Math.PI
constexpr double kTau = 2 * kPi;

// Math.pow as V8 computes it: x*x for y==2, sqrt for y==0.5, libm otherwise.
// Defined out of line so the compiler cannot rewrite constant-base calls.
[[gnu::const]] double jspow(double x, double y);

// Math.round: ties go towards +Infinity.
inline double jsround(double x) {
  double r = std::ceil(x);
  return r - 0.5 > x ? r - 1.0 : r;
}

// x % 1 without the libm call: the fractional part is exact, and takes x's sign.
inline double mod1(double x) { return std::copysign(x - std::trunc(x), x); }

inline double clamp(double v, double lo, double hi) { return std::max(lo, std::min(hi, v)); }
inline double min3(double a, double b, double c) { return std::min(a, std::min(b, c)); }

// SoundDSP.rng: mulberry32 seeded from a 0..1 control value.
class Rng {
 public:
  explicit Rng(double seed);
  double operator()() {
    s_ += 0x6D2B79F5u;
    uint32_t t = (s_ ^ (s_ >> 15)) * (1u | s_);
    t = (t + (t ^ (t >> 7)) * (61u | t)) ^ t;
    return static_cast<double>(t ^ (t >> 14)) / 4294967296.0;
  }

 private:
  uint32_t s_;
};

struct Transition {
  double start = 0, end = 0;
  std::string curve;
};

struct Params {
  std::unordered_map<std::string, double> numbers;
  std::unordered_map<std::string, Transition> transitions;
  std::unordered_map<std::string, std::string> strings;

  // The DSP files' value(): clamp a finite control, else use the fallback.
  double value(const char* name, double fallback, double lo = 0, double hi = 1) const;
  // A control the JS reads without a fallback; throws when absent.
  double number(const char* name) const;
  const Transition* transition(const char* name) const;
};

struct Request {
  uint32_t id = 0xFFFFFFFFu;
  uint32_t seed = 0;
  std::string synth;
  Params params;
};

// Parse one worker NDJSON line. Returns false (with a message) on bad input.
bool parse_request(const std::string& line, Request& out, std::string& error);

// Float32Array "+=": the sum is formed in double, then rounded to float.
inline void add(float& slot, double x) { slot = static_cast<float>(static_cast<double>(slot) + x); }

// SoundDSP.finish: remove DC, soft-clip, scale and fade the ends.
void finish(std::vector<float>& buffer, double volume, bool loop = false);

using RenderFn = std::vector<float> (*)(const Params&);
struct Engine {
  const char* name;
  RenderFn render;
};
// Every engine, sorted by name.
const std::vector<Engine>& engines();

// Each engine file registers itself: MSN_ENGINE("Boomr", render_boomr);
struct Registration {
  Registration(const char* name, RenderFn render);
};
#define MSN_ENGINE(name, function) static const ::msn::Registration registration_##function(name, function)

}  // namespace msn
