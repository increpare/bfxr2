#pragma once

#include <cstdint>

namespace bfxr {

// Mulberry32 — identical to tools/render/bfxr_context.js __setSeed.
class Mulberry32 {
 public:
  explicit Mulberry32(uint32_t seed = 0) : state_(seed) {}

  void set_seed(uint32_t seed) { state_ = seed; }

  double next() {
    uint32_t a = state_;
    a = static_cast<uint32_t>(a + 0x6D2B79F5u);
    state_ = a;
    uint32_t t = (a ^ (a >> 15)) * (1u | a);
    t = (t + ((t ^ (t >> 7)) * 61u)) ^ t;
    return static_cast<double>((t ^ (t >> 14)) >> 0) / 4294967296.0;
  }

 private:
  uint32_t state_;
};

}  // namespace bfxr
