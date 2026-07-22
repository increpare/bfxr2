#pragma once

#include <cstdint>

namespace bfxr {

// Mulberry32 — identical to tools/render/bfxr_context.js __setSeed.
// Uses int32_t / unsigned shifts to match JS ToInt32, |0, >>>, and Math.imul.
class Mulberry32 {
 public:
  explicit Mulberry32(uint32_t seed = 0) : state_(static_cast<int32_t>(seed)) {}

  void set_seed(uint32_t seed) { state_ = static_cast<int32_t>(seed); }

  double next() {
    int32_t a = state_;
    a = static_cast<int32_t>(static_cast<uint32_t>(a) + 0x6D2B79F5u);
    state_ = a;

    auto imul = [](int32_t x, int32_t y) -> int32_t {
      return static_cast<int32_t>(static_cast<uint32_t>(x) * static_cast<uint32_t>(y));
    };
    auto usr = [](int32_t x, int shift) -> int32_t {
      return static_cast<int32_t>(static_cast<uint32_t>(x) >> shift);
    };

    int32_t t = imul(a ^ usr(a, 15), 1 | a);
    t = static_cast<int32_t>(static_cast<uint32_t>(t) +
                             static_cast<uint32_t>(imul(t ^ usr(t, 7), 61 | t))) ^
        t;
    return static_cast<double>(static_cast<uint32_t>(t ^ usr(t, 14))) / 4294967296.0;
  }

 private:
  int32_t state_;
};

}  // namespace bfxr
