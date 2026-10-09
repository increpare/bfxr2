CXX ?= c++
# No -ffast-math, and no FMA contraction: both change results against the JS oracle.
CXXFLAGS ?= -std=c++17 -O3 -ffp-contract=off -Wall -Wextra -Wpedantic
CPPFLAGS += -Iinclude -I../bfxr_native/include
LDFLAGS ?=
# vmath.h batches sin/pow/tanh through Accelerate on macOS (SCALAR=1 opts out).
ifeq ($(shell uname -s),Darwin)
ifndef SCALAR
LDFLAGS += -framework Accelerate
endif
endif
ifdef SCALAR
CPPFLAGS += -DMSN_SCALAR_MATH
endif

BUILD ?= build
ENGINE_SRCS ?= $(wildcard src/engines/*.cpp)
SRCS := $(wildcard src/*.cpp) $(ENGINE_SRCS)
OBJS := $(patsubst src/%.cpp,$(BUILD)/%.o,$(SRCS)) $(BUILD)/akwf_tables.o
HEADERS := $(wildcard include/*.h)

.PHONY: all clean

all: $(BUILD)/multisynth_worker

$(BUILD)/%.o: src/%.cpp $(HEADERS)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

# Transfxr's wavetable oscillators share the tables extracted for Bfxr.
$(BUILD)/akwf_tables.o: ../bfxr_native/src/akwf_tables.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

$(BUILD)/multisynth_worker: $(OBJS)
	$(CXX) $(CXXFLAGS) $(OBJS) -o $@ $(LDFLAGS)

clean:
	rm -rf $(BUILD)
