#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace bfxr {

// Mono 16-bit PCM WAV, matching tools/render/wav.js encodeWav16.
std::string encode_wav16(const float* samples, size_t n, int sample_rate);

bool write_file(const std::string& path, const std::string& bytes);

}  // namespace bfxr
