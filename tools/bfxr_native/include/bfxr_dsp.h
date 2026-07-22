#pragma once

#include "params.h"
#include "prng.h"

#include <cstdint>
#include <vector>

namespace bfxr {

struct RenderResult {
  std::vector<float> samples;  // empty => failed / no buffer
  bool ok = false;
};

// Render with the given merged params and seeded PRNG (caller seeds rng).
RenderResult render_bfxr(ParamMap params, Mulberry32& rng);

// Convenience: set seed, merge overrides with defaults, render.
RenderResult render_bfxr(const ParamMap& overrides, uint32_t seed);

}  // namespace bfxr
