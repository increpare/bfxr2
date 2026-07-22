"""Python client for the persistent Node render worker(s).

Protocol (see render/render_worker.js):
  request:  NDJSON line {"id", "seed", "params"}
  response: uint32LE id | int32LE status | uint32LE n_samples | float32LE data

A single render is CPU-bound at ~45 ms per second of audio, so batches are
fanned out across several worker processes.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import threading

import numpy as np

from .bfxr_io import RENDER_WORKER

STATUS_OK = 0

_FRAME_HEADER = struct.Struct("<IiI")


class RenderError(RuntimeError):
    pass


def default_jobs() -> int:
    return max(1, (os.cpu_count() or 4) - 2)


class _Worker:
    def __init__(self):
        self.proc = subprocess.Popen(
            ["node", str(RENDER_WORKER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def run_queue(
        self,
        queue: list[tuple[int, int, dict]],
        lock: threading.Lock,
        results: dict[int, np.ndarray | None],
    ) -> None:
        """Pull (id, seed, params) requests off the shared queue one at a
        time. Render costs vary ~10x with params, so request-level dispatch
        balances far better than pre-sharding; the per-request pipe round
        trip is negligible next to render time."""
        if self.proc.poll() is not None:
            raise RenderError("render worker has exited")
        while True:
            with lock:
                if not queue:
                    return
                req_id, seed, params = queue.pop()
            line = json.dumps(
                {"id": req_id, "seed": seed, "params": params},
                separators=(",", ":"),
            )
            self._write(line.encode() + b"\n")
            frame_id, status, samples = self._read_frame()
            results[frame_id] = samples if status == STATUS_OK else None

    def _write(self, payload: bytes) -> None:
        try:
            self.proc.stdin.write(payload)
            self.proc.stdin.flush()
        except BrokenPipeError as e:
            raise RenderError("render worker closed stdin") from e

    def _read_exact(self, n: int) -> bytes:
        chunks = []
        remaining = n
        while remaining > 0:
            chunk = self.proc.stdout.read(remaining)
            if not chunk:
                raise RenderError("render worker closed stdout mid-frame")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _read_frame(self) -> tuple[int, int, np.ndarray | None]:
        frame_id, status, n_samples = _FRAME_HEADER.unpack(self._read_exact(12))
        samples = None
        if n_samples > 0:
            samples = np.frombuffer(self._read_exact(4 * n_samples), dtype="<f4")
        return frame_id, status, samples

    def close(self) -> None:
        if self.proc.poll() is None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
            self.proc.wait(timeout=5)


class BfxrRenderer:
    """Owns a pool of render workers. Not thread-safe; one batch at a time."""

    def __init__(self, jobs: int | None = None):
        self.jobs = jobs if jobs is not None else default_jobs()
        self._workers = [_Worker() for _ in range(self.jobs)]
        self._next_id = 0

    def render_batch(
        self,
        params_list: list[dict],
        seeds: list[int] | int = 1,
    ) -> list[np.ndarray | None]:
        """Render many param dicts. Returns float32 arrays in input order,
        None for failed renders."""
        n = len(params_list)
        if isinstance(seeds, int):
            seeds = [seeds] * n
        ids = list(range(self._next_id, self._next_id + n))
        self._next_id += n

        queue = list(zip(ids, seeds, params_list))
        lock = threading.Lock()
        results: dict[int, np.ndarray | None] = {}
        errors: list[Exception] = []

        def run(worker: _Worker):
            try:
                worker.run_queue(queue, lock, results)
            except Exception as e:  # surfaced after join
                errors.append(e)

        threads = [
            threading.Thread(target=run, args=(w,))
            for w in self._workers[: min(self.jobs, n)]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if errors:
            raise errors[0]
        return [results.get(i) for i in ids]

    def render(self, params: dict, seed: int = 1) -> np.ndarray | None:
        return self.render_batch([params], seeds=seed)[0]

    def close(self) -> None:
        for w in self._workers:
            w.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
