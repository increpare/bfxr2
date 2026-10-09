"""Parity and speed of the native engines against the Node renderer.

    uv run python -m multisynth_native.bench [--cases 36] [--repeats 3] [Synth ...]

Each case is a preset sample rendered by both backends from the same canonical
controls. Timings are the best of --repeats per case, interleaved so that
background load affects both backends alike.
"""
import argparse
import time

import numpy as np

from sfxmatch.render import FastRenderer as NodeRenderer

from .client import NativeWorker


def cases(node, synth, count):
    """Canonical (params, seed) pairs cycling through every preset of a synth."""
    presets = node.specs[synth]['presets']
    return [(node.sample(synth, presets[k % len(presets)], 1000+k), 7+k) for k in range(count)]


def compare(node, native, synth, count=36, repeats=1):
    """Return (max |difference|, bit-exact cases, node seconds, native seconds)."""
    worst, exact, node_time, native_time = 0.0, 0, 0.0, 0.0
    for params, seed in cases(node, synth, count):
        best = [float('inf'), float('inf')]
        for _ in range(repeats):
            start = time.perf_counter()
            canonical, expected = node.render(synth, params, seed)
            best[0] = min(best[0], time.perf_counter()-start)
            start = time.perf_counter()
            actual = native.render(synth, canonical)
            best[1] = min(best[1], time.perf_counter()-start)
        if len(actual) != len(expected):
            raise AssertionError(f'{synth}: {len(actual)} samples, expected {len(expected)} for {canonical}')
        difference = float(np.max(np.abs(actual-expected)))
        worst, exact = max(worst, difference), exact+(difference == 0)
        node_time, native_time = node_time+best[0], native_time+best[1]
    return worst, exact, node_time, native_time


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('synths', nargs='*')
    parser.add_argument('--cases', type=int, default=36)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    with NodeRenderer() as node, NativeWorker() as native:
        print(f'{"synth":10s} {"max |diff|":>10s} {"exact":>7s} {"node ms":>8s} {"native ms":>9s} {"speedup":>7s}')
        for synth in args.synths or sorted(native.synths):
            compare(node, native, synth, 2)  # warm both backends
            worst, exact, node_time, native_time = compare(node, native, synth, args.cases, args.repeats)
            print(f'{synth:10s} {worst:10.1e} {exact:4d}/{args.cases:<2d} {node_time/args.cases*1e3:8.1f} '
                  f'{native_time/args.cases*1e3:9.1f} {node_time/native_time:6.1f}x', flush=True)


if __name__ == '__main__':
    main()
