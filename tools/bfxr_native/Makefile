CXX ?= c++
CXXFLAGS ?= -std=c++17 -O3 -Wall -Wextra -Wpedantic -Iinclude
LDFLAGS ?=

BUILD := build
LIB_SRCS := \
	src/bfxr_dsp.cpp \
	src/params.cpp \
	src/json_min.cpp \
	src/wav.cpp \
	src/akwf_tables.cpp

LIB_OBJS := $(patsubst src/%.cpp,$(BUILD)/%.o,$(LIB_SRCS))

.PHONY: all clean

all: $(BUILD)/bfxr_render $(BUILD)/bfxr_worker

$(BUILD):
	mkdir -p $(BUILD)

HEADERS := $(wildcard include/*.h)

$(BUILD)/%.o: src/%.cpp $(HEADERS) | $(BUILD)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(BUILD)/bfxr_render: src/cli_main.cpp $(LIB_OBJS) $(HEADERS) | $(BUILD)
	$(CXX) $(CXXFLAGS) $< $(LIB_OBJS) -o $@ $(LDFLAGS)

$(BUILD)/bfxr_worker: src/worker_main.cpp $(LIB_OBJS) $(HEADERS) | $(BUILD)
	$(CXX) $(CXXFLAGS) $< $(LIB_OBJS) -o $@ $(LDFLAGS)

clean:
	rm -rf $(BUILD)
