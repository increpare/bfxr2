#include "dsp.h"

#include <algorithm>
#include <cstring>

namespace msn {

namespace {

std::vector<Engine>& registry() {
  static std::vector<Engine> list;
  return list;
}

}  // namespace

Registration::Registration(const char* name, RenderFn render) {
  std::vector<Engine>& list = registry();
  list.insert(std::upper_bound(list.begin(), list.end(), name,
                               [](const char* a, const Engine& b) { return std::strcmp(a, b.name) < 0; }),
              Engine{name, render});
}

const std::vector<Engine>& engines() { return registry(); }

}  // namespace msn
