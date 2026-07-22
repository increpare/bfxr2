#pragma once

#include <string>
#include <unordered_map>
#include <vector>

namespace bfxr {

struct ParamMeta {
  std::string name;
  std::string type;  // "RANGE" or "BUTTONSELECT"
  double default_value = 0;
  double min_value = 0;
  double max_value = 1;
  std::vector<int> values;  // BUTTONSELECT only
};

struct WaveTypeMeta {
  std::string name;
  int value = 0;
};

struct ParamInfo {
  std::string version = "1.0.4";
  int sample_rate = 44100;
  std::vector<std::string> permalocked{"masterVolume"};
  std::vector<ParamMeta> params;
  std::vector<WaveTypeMeta> wave_types;
};

using ParamMap = std::unordered_map<std::string, double>;

ParamInfo make_param_info();
ParamMap default_params();
double param_min(const std::string& name);
double param_max(const std::string& name);

// Merge defaults with overrides; force masterVolume=0.5.
ParamMap merge_params(const ParamMap& overrides);

std::string dump_info_json();

}  // namespace bfxr
