#include "params.h"

#include <sstream>
#include <utility>

namespace bfxr {
namespace {

const ParamMeta kRangeParams[] = {
    {"masterVolume", "RANGE", 0.5, 0, 1, {}},
    {"attackTime", "RANGE", 0, 0, 1, {}},
    {"sustainTime", "RANGE", 0.3, 0, 1, {}},
    {"sustainPunch", "RANGE", 0, 0, 1, {}},
    {"decayTime", "RANGE", 0.4, 0.03, 1, {}},
    {"compressionAmount", "RANGE", 0, 0, 1, {}},
    {"frequency_start", "RANGE", 0.3, 0, 1, {}},
    {"frequency_slide", "RANGE", 0, -0.5, 0.5, {}},
    {"frequency_acceleration", "RANGE", 0, -1, 1, {}},
    {"min_frequency_relative_to_starting_frequency", "RANGE", 0, 0, 0.99, {}},
    {"vibratoDepth", "RANGE", 0, 0, 1, {}},
    {"vibratoSpeed", "RANGE", 0, 0, 1, {}},
    {"pitch_jump_repeat_speed", "RANGE", 0, 0, 1, {}},
    {"pitch_jump_amount", "RANGE", 0, -1, 1, {}},
    {"pitch_jump_onset_percent", "RANGE", 0, 0, 1, {}},
    {"pitch_jump_2_amount", "RANGE", 0, -1, 1, {}},
    {"pitch_jump_onset2_percent", "RANGE", 0, 0, 1, {}},
    {"overtones", "RANGE", 0, 0, 1, {}},
    {"overtoneFalloff", "RANGE", 0, 0, 1, {}},
    {"squareDuty", "RANGE", 0, 0, 0.99, {}},
    {"dutySweep", "RANGE", 0, -1, 1, {}},
    {"repeatSpeed", "RANGE", 0, 0, 1, {}},
    {"flangerOffset", "RANGE", 0, -1, 1, {}},
    {"flangerSweep", "RANGE", 0, -1, 1, {}},
    {"lpFilterCutoff", "RANGE", 1, 0.01, 1, {}},
    {"lpFilterCutoffSweep", "RANGE", 0, -1, 1, {}},
    {"lpFilterResonance", "RANGE", 0, 0, 1, {}},
    {"hpFilterCutoff", "RANGE", 0, 0, 1, {}},
    {"hpFilterCutoffSweep", "RANGE", 0, -1, 1, {}},
    {"bitCrush", "RANGE", 0, 0, 1, {}},
    {"bitCrushSweep", "RANGE", 0, -1, 1, {}},
};

constexpr size_t kNumRangeParams = sizeof(kRangeParams) / sizeof(kRangeParams[0]);

const WaveTypeMeta kWaveTypes[] = {
    {"Triangle", 4}, {"Sin", 2},      {"Square", 0}, {"Saw", 1},
    {"Breaker", 8},  {"Tan", 6},      {"Whistle", 7}, {"White", 3},
    {"Voice", 11},   {"Bitnoise", 9}, {"Rasp", 5},   {"FMSyn", 10},
};

constexpr size_t kNumWaveTypes = sizeof(kWaveTypes) / sizeof(kWaveTypes[0]);

std::string json_escape(const std::string& s) {
  std::string out;
  out.reserve(s.size() + 8);
  for (char c : s) {
    if (c == '"' || c == '\\') {
      out.push_back('\\');
      out.push_back(c);
    } else {
      out.push_back(c);
    }
  }
  return out;
}

std::string json_number(double v) {
  std::ostringstream oss;
  oss.precision(17);
  oss << v;
  return oss.str();
}

}  // namespace

ParamInfo make_param_info() {
  ParamInfo info;
  ParamMeta wave;
  wave.name = "waveType";
  wave.type = "BUTTONSELECT";
  wave.default_value = 0;
  for (size_t i = 0; i < kNumWaveTypes; ++i) wave.values.push_back(kWaveTypes[i].value);

  info.params.push_back(kRangeParams[0]);
  info.params.push_back(wave);
  for (size_t i = 1; i < kNumRangeParams; ++i) info.params.push_back(kRangeParams[i]);
  for (size_t i = 0; i < kNumWaveTypes; ++i) info.wave_types.push_back(kWaveTypes[i]);
  return info;
}

ParamMap default_params() {
  ParamMap p;
  for (size_t i = 0; i < kNumRangeParams; ++i) {
    p[kRangeParams[i].name] = kRangeParams[i].default_value;
  }
  p["waveType"] = 0;
  return p;
}

double param_min(const std::string& name) {
  for (size_t i = 0; i < kNumRangeParams; ++i) {
    if (kRangeParams[i].name == name) return kRangeParams[i].min_value;
  }
  return 0;
}

double param_max(const std::string& name) {
  for (size_t i = 0; i < kNumRangeParams; ++i) {
    if (kRangeParams[i].name == name) return kRangeParams[i].max_value;
  }
  return 1;
}

ParamMap merge_params(const ParamMap& overrides) {
  ParamMap merged = default_params();
  for (const auto& kv : overrides) merged[kv.first] = kv.second;
  merged["masterVolume"] = 0.5;
  return merged;
}

std::string dump_info_json() {
  ParamInfo info = make_param_info();
  std::ostringstream out;
  out << "{\n  \"version\": \"" << json_escape(info.version) << "\",\n"
      << "  \"sampleRate\": " << info.sample_rate << ",\n"
      << "  \"permalocked\": [\n";
  for (size_t i = 0; i < info.permalocked.size(); ++i) {
    out << "    \"" << json_escape(info.permalocked[i]) << "\"";
    if (i + 1 < info.permalocked.size()) out << ",";
    out << "\n";
  }
  out << "  ],\n  \"params\": [\n";
  for (size_t i = 0; i < info.params.size(); ++i) {
    const auto& p = info.params[i];
    out << "    {\n      \"name\": \"" << json_escape(p.name) << "\",\n"
        << "      \"type\": \"" << p.type << "\",\n"
        << "      \"default\": " << json_number(p.default_value);
    if (p.type == "BUTTONSELECT") {
      out << ",\n      \"values\": [\n";
      for (size_t j = 0; j < p.values.size(); ++j) {
        out << "        " << p.values[j];
        if (j + 1 < p.values.size()) out << ",";
        out << "\n";
      }
      out << "      ]\n";
    } else {
      out << ",\n      \"min\": " << json_number(p.min_value)
          << ",\n      \"max\": " << json_number(p.max_value) << "\n";
    }
    out << "    }";
    if (i + 1 < info.params.size()) out << ",";
    out << "\n";
  }
  out << "  ],\n  \"waveTypes\": [\n";
  for (size_t i = 0; i < info.wave_types.size(); ++i) {
    const auto& w = info.wave_types[i];
    out << "    {\n      \"name\": \"" << json_escape(w.name) << "\",\n"
        << "      \"value\": " << w.value << "\n    }";
    if (i + 1 < info.wave_types.size()) out << ",";
    out << "\n";
  }
  out << "  ]\n}\n";
  return out.str();
}

}  // namespace bfxr
