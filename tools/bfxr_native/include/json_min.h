#pragma once

#include "params.h"

#include <cstdint>
#include <optional>
#include <string>

namespace bfxr {

struct RenderRequest {
  uint32_t id = 0xFFFFFFFFu;
  uint32_t seed = 0;
  ParamMap params;
  bool ok = false;
};

// Parse a worker NDJSON line or a .bfxr / bare-params JSON document.
// For documents with a top-level "params" object, that object is used;
// otherwise the top-level object itself is treated as params.
bool parse_params_json(const std::string& text, ParamMap& out, std::string* err = nullptr);

bool parse_render_request(const std::string& line, RenderRequest& out, std::string* err = nullptr);

}  // namespace bfxr
