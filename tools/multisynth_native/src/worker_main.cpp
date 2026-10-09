// Persistent worker, same framing as bfxr_native/src/worker_main.cpp.
//   stdin  NDJSON: {"id":0,"synth":"Boomr","params":{...}}
//   stdout frames: uint32 id | int32 status | uint32 n | n x float32LE
#include "dsp.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int32_t STATUS_OK = 0;
constexpr int32_t STATUS_RENDER_FAILED = 1;
constexpr int32_t STATUS_BAD_REQUEST = 2;
constexpr int32_t STATUS_UNSUPPORTED_SYNTH = 3;

bool write_frame(uint32_t id, int32_t status, const float* samples, uint32_t n) {
  unsigned char header[12];
  auto put_u32 = [](unsigned char* p, uint32_t v) {
    p[0] = static_cast<unsigned char>(v & 0xff);
    p[1] = static_cast<unsigned char>((v >> 8) & 0xff);
    p[2] = static_cast<unsigned char>((v >> 16) & 0xff);
    p[3] = static_cast<unsigned char>((v >> 24) & 0xff);
  };
  put_u32(header + 0, id);
  put_u32(header + 4, static_cast<uint32_t>(status));
  put_u32(header + 8, n);
  if (std::fwrite(header, 1, 12, stdout) != 12) return false;
  if (n > 0 && std::fwrite(samples, 4, n, stdout) != n) return false;
  std::fflush(stdout);
  return true;
}

bool handle_line(const std::string& line) {
  if (line.find_first_not_of(" \t\r") == std::string::npos) return true;
  msn::Request request;
  std::string error;
  if (!msn::parse_request(line, request, error))
    return write_frame(request.id, STATUS_BAD_REQUEST, nullptr, 0);
  for (const msn::Engine& engine : msn::engines()) {
    if (request.synth != engine.name) continue;
    try {
      const std::vector<float> pcm = engine.render(request.params);
      for (float sample : pcm) if (!std::isfinite(sample)) throw std::runtime_error("nonfinite audio");
      if (pcm.empty()) throw std::runtime_error("no audio");
      return write_frame(request.id, STATUS_OK, pcm.data(), static_cast<uint32_t>(pcm.size()));
    } catch (const std::exception&) {
      return write_frame(request.id, STATUS_RENDER_FAILED, nullptr, 0);
    }
  }
  return write_frame(request.id, STATUS_UNSUPPORTED_SYNTH, nullptr, 0);
}

}  // namespace

int main() {
  // A full buffer per frame; write_frame flushes after each one.
  static char buffer[1 << 16];
  std::setvbuf(stdout, buffer, _IOFBF, sizeof buffer);

  std::string ready = "{\"ready\":true,\"sampleRate\":44100,\"synths\":[";
  for (const msn::Engine& engine : msn::engines()) {
    if (ready.back() != '[') ready += ',';
    ready += std::string("\"") + engine.name + "\"";
  }
  std::cerr << ready << "]}\n";
  std::cerr.flush();

  // getline returns as soon as a newline arrives, which the persistent
  // request/response protocol relies on.
  std::string line;
  while (std::getline(std::cin, line)) handle_line(line);
  return 0;
}
