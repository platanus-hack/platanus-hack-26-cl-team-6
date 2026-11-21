"""Scores one candidate kernel from the v2 suite against its baseline.

Usage: python harness2.py <kernel> <candidate.py>
Prints one JSON line: {"kernel", "correct", "speedup", "score", "error", "candidate_ms", "baseline_ms"}
score = max(0, log2(speedup)). Fresh random inputs for every timed call, every
output checked, BLAS pinned to one thread.
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

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kernels  # noqa: E402

N_CAND, N_BASE = 5, 3
FORBIDDEN = ("multiprocessing", "threading", "concurrent", "subprocess", "ctypes", "os.environ", "cffi",
             "numba", "torch", "jax", "tensorflow", "cupy", "scipy", "threadpoolctl", "import sys", "__import__")


def load_src(name, src, fn):
    ns = {}
    exec(compile(src, f"<{name}>", "exec"), ns)
    return ns[fn]


def timed(name, fn, seed):
    inp = kernels.make_inputs(name, seed)
    t0 = time.perf_counter()
    out = fn(*inp)
    dt = time.perf_counter() - t0
    return dt, kernels.check(name, inp, out)


def run(name, src):
    res = {"kernel": name, "correct": False, "speedup": 0.0, "score": 0.0, "error": None}
    bad = [w for w in FORBIDDEN if w in src]
    if bad:
        res["error"] = f"forbidden: {bad}"
        return res
    seed0 = int.from_bytes(os.urandom(4), "little")
    try:
        cand = load_src("candidate", src, name)
        cand(*kernels.make_inputs(name, seed0 + 999))  # warm-up
        c = [timed(name, cand, seed0 + i) for i in range(N_CAND)]
    except Exception:
        res["error"] = traceback.format_exc(limit=3)[-1500:]
        return res
    if not all(ok for _, ok in c):
        res["error"] = "output does not match reference (rtol=1e-3, atol=1e-4*max|ref|)"
        return res
    base = load_src("baseline", kernels.BASELINES[name], name)
    b = [timed(name, base, seed0 + 100 + i)[0] for i in range(N_BASE)]
    ct, bt = float(np.median([t for t, _ in c])), float(np.median(b))
    res.update(correct=True, speedup=bt / ct, score=max(0.0, float(np.log2(bt / ct))),
               candidate_ms=1000 * ct, baseline_ms=1000 * bt)
    return res


if __name__ == "__main__":
    name, path = sys.argv[1], sys.argv[2]
    if name not in kernels.KERNELS:
        print(json.dumps({"kernel": name, "correct": False, "speedup": 0.0, "score": 0.0,
                          "error": f"unknown kernel; choose from {kernels.KERNELS}"}))
    else:
        print(json.dumps(run(name, pathlib.Path(path).read_text(encoding="utf-8"))))
