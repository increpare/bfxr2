#include "bfxr_dsp.h"
#include "json_min.h"
#include "params.h"

#include <cstdint>
#include <cstdio>
#include <iostream>
#include <string>

namespace {

constexpr int32_t STATUS_OK = 0;
constexpr int32_t STATUS_RENDER_FAILED = 1;
constexpr int32_t STATUS_BAD_REQUEST = 2;
constexpr uint32_t UNKNOWN_ID = 0xFFFFFFFFu;

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
  if (n > 0) {
    if (std::fwrite(samples, 4, n, stdout) != n) return false;
  }
  std::fflush(stdout);
  return true;
}

void trim_inplace(std::string& line) {
  while (!line.empty() &&
         (line.back() == '\r' || line.back() == ' ' || line.back() == '\t'))
    line.pop_back();
  size_t start = 0;
  while (start < line.size() &&
         (line[start] == ' ' || line[start] == '\t' || line[start] == '\r'))
    ++start;
  if (start > 0) line.erase(0, start);
}

bool handle_line(const std::string& raw) {
  std::string line = raw;
  trim_inplace(line);
  if (line.empty()) return true;
  bfxr::RenderRequest req;
  std::string err;
  if (!bfxr::parse_render_request(line, req, &err) || !req.ok) {
    return write_frame(UNKNOWN_ID, STATUS_BAD_REQUEST, nullptr, 0);
  }
  auto result = bfxr::render_bfxr(req.params, req.seed);
  if (!result.ok) {
    return write_frame(req.id, STATUS_RENDER_FAILED, nullptr, 0);
  }
  return write_frame(req.id, STATUS_OK, result.samples.data(),
                     static_cast<uint32_t>(result.samples.size()));
}

}  // namespace

int main() {
  // Binary stdout must not be line-buffered; NDJSON stdin is line-oriented.
  std::setvbuf(stdout, nullptr, _IONBF, 0);

  std::cerr << "{\"ready\":true,\"version\":\"" << bfxr::make_param_info().version
            << "\",\"sampleRate\":" << 44100 << "}\n";
  std::cerr.flush();

  // getline returns as soon as a newline arrives — critical for the persistent
  // worker protocol (a bulk cin.read would block until the buffer fills / EOF).
  std::string line;
  while (std::getline(std::cin, line)) {
    handle_line(line);
  }
  return 0;
}
