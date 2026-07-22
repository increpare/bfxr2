#include "wav.h"

#include <fstream>

namespace bfxr {

std::string encode_wav16(const float* samples, size_t n, int sample_rate) {
  const uint32_t data_bytes = static_cast<uint32_t>(n * 2);
  std::string buf(44 + data_bytes, '\0');
  auto* p = reinterpret_cast<unsigned char*>(&buf[0]);

  auto wr_u16 = [&](size_t off, uint16_t v) {
    p[off] = static_cast<unsigned char>(v & 0xff);
    p[off + 1] = static_cast<unsigned char>((v >> 8) & 0xff);
  };
  auto wr_u32 = [&](size_t off, uint32_t v) {
    p[off] = static_cast<unsigned char>(v & 0xff);
    p[off + 1] = static_cast<unsigned char>((v >> 8) & 0xff);
    p[off + 2] = static_cast<unsigned char>((v >> 16) & 0xff);
    p[off + 3] = static_cast<unsigned char>((v >> 24) & 0xff);
  };
  auto wr_str = [&](size_t off, const char* s) {
    for (int k = 0; s[k]; ++k) p[off + k] = static_cast<unsigned char>(s[k]);
  };

  wr_str(0, "RIFF");
  wr_u32(4, 36 + data_bytes);
  wr_str(8, "WAVE");
  wr_str(12, "fmt ");
  wr_u32(16, 16);
  wr_u16(20, 1);
  wr_u16(22, 1);
  wr_u32(24, static_cast<uint32_t>(sample_rate));
  wr_u32(28, static_cast<uint32_t>(sample_rate * 2));
  wr_u16(32, 2);
  wr_u16(34, 16);
  wr_str(36, "data");
  wr_u32(40, data_bytes);

  for (size_t i = 0; i < n; ++i) {
    float v = samples[i];
    if (v > 1.f) v = 1.f;
    else if (v < -1.f) v = -1.f;
    int16_t sample = static_cast<int16_t>(static_cast<int>(v * 32767.f));
    wr_u16(44 + i * 2, static_cast<uint16_t>(sample));
  }
  return buf;
}

bool write_file(const std::string& path, const std::string& bytes) {
  std::ofstream f(path, std::ios::binary);
  if (!f) return false;
  f.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
  return static_cast<bool>(f);
}

}  // namespace bfxr
