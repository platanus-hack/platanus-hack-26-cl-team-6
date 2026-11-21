"""Scores a candidate causal-attention kernel against the baseline.

Usage: python kernel_harness.py path/to/candidate.py
Prints one JSON line: {"correct": bool, "speedup": float, "score": float, "error": str|None}
score = log2(baseline_time / candidate_time) if correct else 0.0 (the baseline is
always available, so a wrong answer is worth no more than resubmitting it).

Every timed call gets fresh random inputs and every output is checked, so
memoisation does not help. BLAS is pinned to one thread for stable timings.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"

import importlib.util
import json
import pathlib
import sys
import time
import traceback

import numpy as np

SHAPE = (1, 8, 1024, 64)  # B, H, T, D
N_CAND_REPS = 5
N_BASE_REPS = 3
FORBIDDEN = ("multiprocessing", "threading", "concurrent", "subprocess", "ctypes", "os.environ", "cffi", "numba", "torch", "jax", "tensorflow", "cupy")
HERE = pathlib.Path(__file__).parent


def reference(q, k, v):
    T, D = q.shape[-2], q.shape[-1]
    s = q @ np.swapaxes(k, -1, -2) / np.sqrt(D)
    s = np.where(np.tril(np.ones((T, T), dtype=bool)), s, -np.inf)
    s = np.exp(s - s.max(-1, keepdims=True))
    return (s / s.sum(-1, keepdims=True)) @ v


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.attention


def inputs(seed):
    rng = np.random.default_rng(seed)
    return tuple(rng.standard_normal(SHAPE) for _ in range(3))


def timed(fn, seed):
    q, k, v = inputs(seed)
    t0 = time.perf_counter()
    out = fn(q, k, v)
    dt = time.perf_counter() - t0
    out = np.asarray(out)
    ref = reference(q, k, v)
    ok = out.shape == ref.shape and bool(np.allclose(out, ref, rtol=1e-3, atol=1e-4))
    return dt, ok


def main():
    cand_path = sys.argv[1]
    src = pathlib.Path(cand_path).read_text(encoding="utf-8")
    bad = [w for w in FORBIDDEN if w in src]
    if bad:
        return {"correct": False, "speedup": 0.0, "score": 0.0, "error": f"forbidden: {bad}"}
    seed0 = int.from_bytes(os.urandom(4), "little")
    try:
        cand = load(cand_path, "candidate")
        cand(*inputs(seed0 + 999))  # warm-up
        c = [timed(cand, seed0 + i) for i in range(N_CAND_REPS)]
    except Exception:
        return {"correct": False, "speedup": 0.0, "score": 0.0, "error": traceback.format_exc(limit=3)[-1500:]}
    if not all(ok for _, ok in c):
        return {"correct": False, "speedup": 0.0, "score": 0.0, "error": "output does not match reference (rtol=1e-3, atol=1e-4)"}
    base = load(HERE / "baseline_attention.py", "baseline")
    b = [timed(base, seed0 + 100 + i)[0] for i in range(N_BASE_REPS)]
    speedup = float(np.median(b) / np.median([t for t, _ in c]))
    return {"correct": True, "speedup": speedup, "score": max(0.0, float(np.log2(speedup))), "error": None,
            "candidate_ms": 1000 * float(np.median([t for t, _ in c])), "baseline_ms": 1000 * float(np.median(b))}


if __name__ == "__main__":
    print(json.dumps(main()))
