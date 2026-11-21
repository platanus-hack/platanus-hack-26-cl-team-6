"""Fit Ord's lambda from lambda_task.py logs.

Model (Ord 2026): N agents with budget b each perform like one agent with
budget b * N**lambda. With log-linear returns to budget (Ord's observation):

    score(N, b) = a + s * (log2 b + lambda * log2 N)

We fit a, s, lambda jointly by least squares over every run and get a 90% CI
by bootstrapping runs within each (N, b) config. We also report the two
"one-line" estimators so you can see whether they agree:

  * Ord-style:     lambda = slope(score vs log2 N at fixed b) / slope(score vs log2 b at N=1)
  * Iso-compute:   lambda = 1 + slope(score vs log2 N at fixed N*b) / slope(duration)
                  (this is Sam's 1x100 / 10x10 / 100x1 design; it needs the
                   duration slope to be interpretable.)

Usage:
    python fit_lambda.py logs/*.eval [--plot out.png]
    python fit_lambda.py --simulate 0.6       # check the fitter recovers a known lambda
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

import numpy as np
from scipy.optimize import least_squares


def load_runs(paths):
    from inspect_ai.log import read_eval_log

    runs = []
    for p in paths:
        log = read_eval_log(p)
        for s in log.samples or []:
            sc = s.scores.get("swarm_score")
            if sc is None or s.error:
                continue
            runs.append((s.metadata["n_agents"], s.metadata["budget_per_agent"], float(sc.value)))
    return runs


def fit(runs):
    N = np.array([r[0] for r in runs], float)
    B = np.array([r[1] for r in runs], float)
    y = np.array([r[2] for r in runs], float)

    def resid(p):
        a, s, lam = p
        return a + s * (np.log2(B) + lam * np.log2(N)) - y

    r = least_squares(resid, x0=[y.mean(), 0.3, 0.5])
    return r.x


def slope(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if len(set(xs)) < 2:
        return np.nan
    return np.polyfit(xs, ys, 1)[0]


def one_line_estimates(runs):
    dur = [(np.log2(b), y) for n, b, y in runs if n == 1]
    s_dur = slope(*zip(*dur)) if dur else np.nan
    out = {"duration_slope": s_dur}
    # iso-compute: most common total with >=3 distinct N
    by_total = defaultdict(list)
    for n, b, y in runs:
        by_total[n * b].append((np.log2(n), y))
    iso = [t for t, v in by_total.items() if len({x for x, _ in v}) >= 3]
    if iso:
        t = max(iso, key=lambda t: len(by_total[t]))
        s_iso = slope(*zip(*by_total[t]))
        out.update(iso_total=t, iso_slope=s_iso, lambda_iso=1 + s_iso / s_dur)
    by_b = defaultdict(list)
    for n, b, y in runs:
        by_b[b].append((np.log2(n), y))
    sw = [b for b, v in by_b.items() if len({x for x, _ in v}) >= 3]
    if sw:
        b = max(sw, key=lambda b: len(by_b[b]))
        s_sw = slope(*zip(*by_b[b]))
        out.update(swarm_b=b, swarm_slope=s_sw, lambda_swarm=s_sw / s_dur)
    return out


def interp_lambda(runs):
    """Ord's own method, without assuming log-linear returns.

    The single-agent curve f(log2 b) (config means, made monotone) is inverted
    for each multi-agent config: the effective single-agent budget b_eff with
    f(log2 b_eff) = score(N, b). Then log2 b_eff = log2 b + lambda * log2 N.
    Configs scoring above the single-agent maximum or below its minimum are
    censored (can't be placed on the curve) and are counted, not used.
    """
    g = defaultdict(list)
    for n, b, y in runs:
        g[(n, b)].append(y)
    single = sorted((np.log2(b), np.mean(ys)) for (n, b), ys in g.items() if n == 1)
    if len(single) < 2:
        return np.nan, 0, 0
    xs = np.array([x for x, _ in single])
    fs = np.maximum.accumulate(np.array([f for _, f in single]))
    fs = fs + 1e-9 * np.arange(len(fs))  # strictly increasing for inversion
    num = den = 0.0
    used = censored = 0
    for (n, b), ys in g.items():
        if n == 1:
            continue
        m = np.mean(ys)
        if m <= fs[0] or m >= fs[-1]:
            censored += 1
            continue
        x_eff = np.interp(m, fs, xs)
        ln = np.log2(n)
        num += ln * (x_eff - np.log2(b))
        den += ln * ln
        used += 1
    return (num / den if den else np.nan), used, censored


def bootstrap(runs, n_boot=2000, seed=0):
    rng = np.random.default_rng(seed)
    groups = defaultdict(list)
    for r in runs:
        groups[(r[0], r[1])].append(r)
    lams, isos, sws, ints = [], [], [], []
    for _ in range(n_boot):
        rs = [g[i] for g in groups.values() for i in rng.integers(0, len(g), len(g))]
        lams.append(fit(rs)[2])
        o = one_line_estimates(rs)
        isos.append(o.get("lambda_iso", np.nan))
        sws.append(o.get("lambda_swarm", np.nan))
        ints.append(interp_lambda(rs)[0])
    ci = lambda v: np.nanpercentile(v, [5, 95]) if np.isfinite(v).any() else np.array([np.nan, np.nan])
    return ci(lams), ci(isos), ci(sws), ci(ints)


def simulate(lam, sd=0.6, reps=5, seed=1):
    """Fake v2-style data: concave, saturating returns to effective budget b * N**lam."""
    from lambda_task2 import DESIGNS

    rng = np.random.default_rng(seed)
    f = lambda eff: 20 * (1 - np.exp(-eff / 12))
    return [(n, b, f(b * n ** lam) + rng.normal(0, sd)) for n, b in DESIGNS["core"] for _ in range(reps)]


def report(runs, plot=None):
    a, s, lam = fit(runs)
    ci_lam, ci_iso, ci_sw, ci_int = bootstrap(runs, n_boot=1000)
    o = one_line_estimates(runs)
    lam_int, used, cens = interp_lambda(runs)
    print(f"runs: {len(runs)}   configs: {len({(n, b) for n, b, _ in runs})}")
    print("\nmean score by config (N agents x b per agent):")
    g = defaultdict(list)
    for n, b, y in runs:
        g[(n, b)].append(y)
    for (n, b), ys in sorted(g.items()):
        print(f"  N={n:3d} b={b:3d} total={n*b:4d}  score={np.mean(ys):.3f} ± {np.std(ys, ddof=1)/np.sqrt(len(ys)) if len(ys)>1 else 0:.3f}  (n={len(ys)})")
    print(f"\nOrd interpolation (no functional form): lambda = {lam_int:.2f}   90% CI [{ci_int[0]:.2f}, {ci_int[1]:.2f}]"
          f"   ({used} multi-agent configs used, {cens} censored outside the single-agent curve)")
    print(f"\njoint fit: score = {a:.3f} + {s:.3f} * (log2 b + lambda * log2 N)")
    print(f"  lambda = {lam:.2f}   90% CI [{ci_lam[0]:.2f}, {ci_lam[1]:.2f}]")
    if "lambda_iso" in o:
        print(f"  iso-compute (total={o['iso_total']}) lambda = {o['lambda_iso']:.2f}  90% CI [{ci_iso[0]:.2f}, {ci_iso[1]:.2f}]")
    if "lambda_swarm" in o:
        print(f"  Ord-style swarm line (b={o['swarm_b']}) lambda = {o['lambda_swarm']:.2f}  90% CI [{ci_sw[0]:.2f}, {ci_sw[1]:.2f}]")
    print(f"  duration slope (N=1) = {o['duration_slope']:.3f} score per doubling of budget")
    if plot:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
        ns = sorted({n for n, _, _ in runs})
        cmap = plt.get_cmap("viridis", len(ns) + 1)
        for i, n in enumerate(ns):
            pts = sorted((b, np.mean(ys), np.std(ys, ddof=1) / np.sqrt(len(ys)) if len(ys) > 1 else 0) for (nn, b), ys in g.items() if nn == n)
            x = [n * b for b, _, _ in pts]
            ax.errorbar(x, [m for _, m, _ in pts], yerr=[e for _, _, e in pts], marker="o", capsize=3, color=cmap(i), label=f"N={n}")
        xs = np.logspace(0, np.log2(max(n * b for n, b, _ in runs)), 50, base=2)
        ax.plot(xs, a + s * np.log2(xs), "k--", lw=1, label="1 agent (fit)")
        ax.set_xscale("log", base=2)
        ax.set_xlabel("total compute (experiments, N × b)")
        ax.set_ylabel("score = log2 speedup of best kernel")
        ax.set_title(f"lambda = {lam:.2f} [{ci_lam[0]:.2f}, {ci_lam[1]:.2f}]")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(plot)
        print(f"\nplot -> {plot}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="*")
    ap.add_argument("--simulate", type=float)
    ap.add_argument("--plot")
    a = ap.parse_args()
    if a.simulate is not None:
        sys.path.insert(0, __file__.rsplit("/", 1)[0])
        print(f"[simulated data, true lambda = {a.simulate}]")
        report(simulate(a.simulate), a.plot)
    else:
        report(load_runs(a.logs), a.plot)
