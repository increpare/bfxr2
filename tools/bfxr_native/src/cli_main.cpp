#include "bfxr_dsp.h"
#include "json_min.h"
#include "params.h"
#include "wav.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

struct Args {
  std::string in_path;
  std::string out_path;
  uint32_t seed = 1;
  bool dump_info = false;
};

void usage() {
  std::cerr << "Usage: bfxr_render --in sound.bfxr --out out.wav [--seed N] | --dump-info\n";
}

Args parse_args(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (a == "--in") {
      if (++i >= argc) throw std::runtime_error("missing --in value");
      args.in_path = argv[i];
    } else if (a == "--out") {
      if (++i >= argc) throw std::runtime_error("missing --out value");
      args.out_path = argv[i];
    } else if (a == "--seed") {
      if (++i >= argc) throw std::runtime_error("missing --seed value");
      args.seed = static_cast<uint32_t>(std::stoul(argv[i]));
    } else if (a == "--dump-info") {
      args.dump_info = true;
    } else {
      throw std::runtime_error("Unknown argument: " + a);
    }
  }
  return args;
}

std::string read_file(const std::string& path) {
  std::ifstream f(path);
  if (!f) throw std::runtime_error("cannot open " + path);
  std::ostringstream ss;
  ss << f.rdbuf();
  return ss.str();
}

}  // namespace

int main(int argc, char** argv) {
  try {
    Args args = parse_args(argc, argv);
    if (args.dump_info) {
      std::cout << bfxr::dump_info_json();
      return 0;
    }
    if (args.in_path.empty() || args.out_path.empty()) {
      usage();
      return 2;
    }

    bfxr::ParamMap params;
    std::string err;
    if (!bfxr::parse_params_json(read_file(args.in_path), params, &err)) {
      std::cerr << "Failed to parse input: " << err << "\n";
      return 1;
    }

    auto result = bfxr::render_bfxr(params, args.seed);
    if (!result.ok || result.samples.empty()) {
      std::cerr << "Render failed (DSP produced no buffer)\n";
      return 1;
    }

    std::string wav =
        bfxr::encode_wav16(result.samples.data(), result.samples.size(), 44100);
    if (!bfxr::write_file(args.out_path, wav)) {
      std::cerr << "Failed to write " << args.out_path << "\n";
      return 1;
    }
    std::cerr << "Wrote " << args.out_path << ": " << result.samples.size() << " samples ("
              << (result.samples.size() / 44100.0) << "s)\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << e.what() << "\n";
    return 2;
  }
}
