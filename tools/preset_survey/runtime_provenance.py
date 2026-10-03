"""Fingerprint the sources that select, apply and render preset states."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def runtime_fingerprint():
    sources = json.loads((Path(__file__).parent/'runtime_sources.json').read_text())
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}

def require_current_runtime(record):
    if record.get('runtime_sha256') != runtime_fingerprint():
        raise ValueError('Render and validate again: preset sampler or renderer sources have changed')
