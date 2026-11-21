"""Ord's lambda with tokens (not experiments) as the budget unit.

Reads data/tokens_run2.csv (one row per sample, extracted from the run 2 Inspect logs)
and treats each agent's budget as the tokens it actually used:
N agents using t tokens each ~ one agent using t * N**lambda tokens.

    python fit_lambda_tokens.py [data/tokens_run2.csv] [--unit output_tokens|total_tokens]
"""
import argparse, csv
from collections import defaultdict
import numpy as np


def load(path, unit):
    rows = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["combine"]].append((int(r["n_agents"]), int(r["budget_per_agent"]), float(r["score"]), float(r[unit])))
    return rows


def interp(runs):
    g = defaultdict(list)
    for n, b, y, t in runs:
        g[(n, b)].append((y, t))
    single = sorted((np.log2(np.mean([t for _, t in v])), np.mean([y for y, _ in v])) for (n, b), v in g.items() if n == 1)
    xs = np.array([x for x, _ in single]); fs = np.maximum.accumulate([f for _, f in single]) + 1e-9 * np.arange(len(single))
    num = den = 0.0; used = cens = 0
    for (n, b), v in g.items():
        if n == 1:
            continue
        m = np.mean([y for y, _ in v]); per_agent = np.mean([t for _, t in v]) / n
        if m <= fs[0] or m >= fs[-1]:
            cens += 1; continue
        ln = np.log2(n); num += ln * (np.interp(m, fs, xs) - np.log2(per_agent)); den += ln * ln; used += 1
    return num / den, used, cens


def slope_ratio(runs):
    g = defaultdict(list)
    for n, b, y, t in runs:
        g[(n, b)].append((y, t))
    mean = {k: (np.mean([y for y, _ in v]), np.mean([t for _, t in v])) for k, v in g.items()}
    one = [(np.log2(t), y) for (n, b), (y, t) in mean.items() if n == 1]
    sw = [(np.log2(t), y) for (n, b), (y, t) in mean.items() if b == 1]
    s1 = np.polyfit(*zip(*one), 1)[0]; s2 = np.polyfit(*zip(*sw), 1)[0]
    return s1, s2


def boot(runs, n=2000, seed=0):
    rng = np.random.default_rng(seed); g = defaultdict(list)
    for r in runs:
        g[(r[0], r[1])].append(r)
    out = []
    for _ in range(n):
        rs = [v[i] for v in g.values() for i in rng.integers(0, len(v), len(v))]
        out.append(interp(rs)[0])
    return np.nanpercentile(out, [5, 95])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("csv", nargs="?", default="data/tokens_run2.csv")
    ap.add_argument("--unit", default="output_tokens", choices=["output_tokens", "total_tokens"]); a = ap.parse_args()
    for combine, runs in load(a.csv, a.unit).items():
        lam, used, cens = interp(runs); lo, hi = boot(runs); s1, s2 = slope_ratio(runs)
        print(f"{combine:8s} [{a.unit}] Ord interpolation lambda = {lam:.2f}  90% CI [{lo:.2f}, {hi:.2f}]  ({used} used, {cens} censored)"
              f"   slope ratio: duration {s1:.2f}, swarm {s2:.2f} per doubling of tokens")
