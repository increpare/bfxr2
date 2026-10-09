#pragma once
// Port of js/audio/BfxrWaveforms.js: Bfxr's oscillator palette, one
// deterministic noise state per oscillator.

#include <cstdint>

namespace msn {

class Waveform {
 public:
  explicit Waveform(int type, double seed = 0.5);
  double operator()(double phase, double step);

 private:
  int type_;
  uint32_t state_, bits_;
  double previous_ = 1, cell_ = -1, white_ = 0, bit_ = 0.5;
  const uint16_t* table_ = nullptr;
};

}  // namespace msn
