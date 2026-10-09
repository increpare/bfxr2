#pragma once
// Batched transcendental functions for loops that libm calls dominate.
// With Accelerate (the default on macOS) they are several times faster than
// scalar libm and agree with it to a few ulp, far below a float32 sample.
// Build with -DMSN_SCALAR_MATH for plain loops over the scalar calls.

#include "dsp.h"

#if defined(__APPLE__) && !defined(MSN_SCALAR_MATH)
#include <Accelerate/Accelerate.h>
#define MSN_VFORCE 1
#endif

namespace msn {

constexpr int kBlock = 256;  // samples per batch; small enough to stay in L1

// out and in must be distinct arrays of at most kBlock elements.
#ifdef MSN_VFORCE
#define MSN_BATCH(name, vforce, scalar) \
  inline void name(double* out, const double* in, int n) { vforce(out, in, &n); }
#else
#define MSN_BATCH(name, vforce, scalar) \
  inline void name(double* out, const double* in, int n) { for (int i = 0; i < n; i++) out[i] = scalar(in[i]); }
#endif
MSN_BATCH(vsin, vvsin, std::sin)
MSN_BATCH(vcos, vvcos, std::cos)
MSN_BATCH(vtan, vvtan, std::tan)
MSN_BATCH(vexp, vvexp, std::exp)
MSN_BATCH(vtanh, vvtanh, std::tanh)
#undef MSN_BATCH

// Math.pow(base[i], exponent) with V8's exact cases for squares and roots.
inline void vpow(double* out, const double* base, double exponent, int n) {
  if (exponent == 2.0) { for (int i = 0; i < n; i++) out[i] = base[i] * base[i]; return; }
  if (exponent == 0.5) { for (int i = 0; i < n; i++) out[i] = std::sqrt(base[i]); return; }
#ifdef MSN_VFORCE
  double exponents[kBlock];
  for (int i = 0; i < n; i++) exponents[i] = exponent;
  vvpow(out, exponents, base, &n);
#else
  for (int i = 0; i < n; i++) out[i] = std::pow(base[i], exponent);
#endif
}

// Math.pow(base, exponent[i]) for one base.
inline void vpow(double* out, double base, const double* exponent, int n) {
#ifdef MSN_VFORCE
  double bases[kBlock];
  for (int i = 0; i < n; i++) bases[i] = base;
  vvpow(out, exponent, bases, &n);
  for (int i = 0; i < n; i++) {
    if (exponent[i] == 2.0) out[i] = base * base;
    else if (exponent[i] == 0.5) out[i] = std::sqrt(base);
  }
#else
  for (int i = 0; i < n; i++) out[i] = jspow(base, exponent[i]);
#endif
}

}  // namespace msn
