"""Fit Toby Ord's swarm λ to runner.py results.

Ord's model: N agents each running t tokens ≈ 1 agent running N^λ·t tokens.
  config-level:  score(e,N) = a + b·ln(t_agent(e,N)) + c·ln N,  λ = c/b   (OpenAI-chart method)
  run-level:     logit P(correct) = a + b·ln(t_agent) + c·ln N,  λ = c/b   (cross-check)
t_agent = output tokens per agent (total swarm output tokens / N). CIs: bootstrap over tasks.
Also reports Ord's scenarios: compute premium and wall-clock speedup at matched score.
"""
import csv, datetime, json, math, random, sys
from collections import defaultdict

# usage: analyze.py results.jsonl [...] [--csv lambdas.csv --label "short description"]
argv = sys.argv[1:]; CSV = LABEL = None
if "--csv" in argv: i = argv.index("--csv"); CSV = argv[i + 1]; del argv[i:i + 2]
if "--label" in argv: i = argv.index("--label"); LABEL = argv[i + 1]; del argv[i:i + 2]
rows = [json.loads(l) for f in argv for l in open(f)]
rows = [r for r in rows if all(a["status"].startswith("success") for a in r["agents"])] or rows


def solve(A, y, w=None):
    w = w or [1] * len(y); k = len(A[0])
    M = [[sum(wi * r[i] * r[j] for r, wi in zip(A, w)) for j in range(k)] for i in range(k)]
    v = [sum(wi * r[i] * yy for r, yy, wi in zip(A, y, w)) for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]; v[i], v[p] = v[p], v[i]
        if abs(M[i][i]) < 1e-12: raise ZeroDivisionError
        for r in range(k):
            if r != i:
                f = M[r][i] / M[i][i]; M[r] = [a - f * b for a, b in zip(M[r], M[i])]; v[r] -= f * v[i]
    return [v[i] / M[i][i] for i in range(k)]


def configs(rs):
    g = defaultdict(list)
    for r in rs: g[(r["effort"], r["N"])].append(r)
    out = []
    for (e, n), L in g.items():
        out.append(dict(effort=e, N=n, score=sum(r["correct"] for r in L) / len(L), any=sum(r["any_correct"] for r in L) / len(L),
                        t_agent=sum(r["out_tokens_total"] for r in L) / len(L) / n, tot=sum(r["out_tokens_total"] for r in L) / len(L),
                        wall=sorted(r["wall_s"] for r in L)[len(L) // 2], cost=sum(r["cost"] for r in L), k=len(L)))
    return sorted(out, key=lambda c: (c["N"], c["t_agent"]))


def fit_cfg(cs, key="score"):
    A = [[1, math.log(c["t_agent"]), math.log(c["N"])] for c in cs]; y = [c[key] for c in cs]
    a, b, c = solve(A, y, [x["k"] for x in cs]); return c / b, b, c


def fit_logit(rs, iters=50):
    X = [[1, math.log(r["out_tokens_total"] / r["N"]), math.log(r["N"])] for r in rs]; y = [1.0 if r["correct"] else 0.0 for r in rs]
    beta = [0.0, 0.0, 0.0]
    for _ in range(iters):  # Newton-Raphson with a small ridge for stability
        p = [1 / (1 + math.exp(-max(-30, min(30, sum(bi * xi for bi, xi in zip(beta, x)))))) for x in X]
        g = [sum((yy - pp) * x[j] for x, yy, pp in zip(X, y, p)) - 1e-3 * beta[j] for j in range(3)]
        H = [[sum(pp * (1 - pp) * x[i] * x[j] for x, pp in zip(X, p)) + (1e-3 if i == j else 0) for j in range(3)] for i in range(3)]
        step = solve(H, g); beta = [bi + si for bi, si in zip(beta, step)]
    return beta[2] / beta[1], beta[1], beta[2]


def boot(rs, fn, B=2000, seed=1):
    by = defaultdict(list)
    for r in rs: by[r["task"]].append(r)
    ids = list(by); rnd = random.Random(seed); vals = []
    for _ in range(B):
        samp = [r for t in (rnd.choice(ids) for _ in ids) for r in by[t]]
        try:
            v = fn(samp)
            if math.isfinite(v): vals.append(v)
        except (ZeroDivisionError, OverflowError, ValueError):
            pass
    vals.sort(); return (vals[int(.05 * len(vals))], vals[int(.95 * len(vals))], len(vals)) if vals else (float("nan"),) * 3


cs = configs(rows)
print(f"runs={len(rows)}  tasks={len({r['task'] for r in rows})}  list-price cost=${sum(r['cost'] for r in rows):.2f}\n")
print(f"{'effort':<7}{'N':>3}{'tasks':>6}{'score':>7}{'any✓':>7}{'tok/agent':>11}{'tok total':>11}{'wall s':>8}")
for c in cs:
    print(f"{c['effort']:<7}{c['N']:>3}{c['k']:>6}{c['score']:>7.2f}{c['any']:>7.2f}{c['t_agent']:>11.0f}{c['tot']:>11.0f}{c['wall']:>8.0f}")

lam, b, c = fit_cfg(cs); lo, hi, nb = boot(rows, lambda s: fit_cfg(configs(s))[0])
print(f"\nλ (config-level, Ord/OpenAI method) = {lam:.2f}   90% CI [{lo:.2f}, {hi:.2f}]  (boot ok {nb})")
print(f"   duration slope b = {100 * b * math.log(2):+.1f} pp per 2x tokens/agent;  swarm slope c = {100 * c * math.log(2):+.1f} pp per 2x agents")
lamL, bL, cL = fit_logit(rows); loL, hiL, nL = boot(rows, lambda s: fit_logit(s)[0], B=500)
print(f"λ (run-level logistic)             = {lamL:.2f}   90% CI [{loL:.2f}, {hiL:.2f}]  (boot ok {nL})")
lamA, bA, cA = fit_cfg(cs, "any")
print(f"λ if the swarm had a perfect verifier (any agent right) = {lamA:.2f}")

# Ord's scenarios at matched score, interpolating the single-agent curve in ln(tokens)
one = sorted([x for x in cs if x["N"] == 1], key=lambda x: x["t_agent"])
def interp(xs, ys, x):
    pts = sorted(zip(xs, ys))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1 or (x1, y1) == pts[-1]: return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y0
if len(one) >= 2 and len({x["score"] for x in one}) > 1:
    S = [x["score"] for x in one]
    print("\nmatched-score comparison vs 1 agent:")
    for x in cs:
        if x["N"] == 1 or not (min(S) <= x["score"] <= max(S)): continue
        T1 = math.exp(interp(S, [math.log(o["tot"]) for o in one], x["score"])); W1 = math.exp(interp(S, [math.log(o["wall"]) for o in one], x["score"]))
        print(f"   N={x['N']} {x['effort']:<6} score={x['score']:.2f}: token premium x{x['tot'] / T1:.2f} (theory x{x['N'] ** (1 - lam):.2f}); "
              f"wall-clock speedup x{W1 / x['wall']:.2f} (theory x{x['N'] ** lam:.2f})")
print("max score by N: " + ", ".join(f"N={n}: {max(x['score'] for x in cs if x['N'] == n):.2f}" for n in sorted({x['N'] for x in cs})))

if CSV:  # append this run's λ estimates to the shared table
    ns = "-".join(str(n) for n in sorted({x["N"] for x in cs})); ntask = len({r["task"] for r in rows})
    base = dict(date=datetime.date.today().isoformat(), task="SOC incident investigation", side="defensive",
                benchmark=LABEL or "synthetic SOC logs", model="Claude Haiku 5.5", agents=ns, n_tasks=ntask,
                source="our swarm experiment (Claude Code agents, shared notes + majority vote)")
    out = [dict(base, method="linear score fit (pooled)", **{"lambda": f"{lam:.3f}"}, ci90_low=f"{lo:.2f}", ci90_high=f"{hi:.2f}", notes=f"bootstrap over tasks; {len(rows)} swarm runs"),
           dict(base, method="run-level logistic fit", **{"lambda": f"{lamL:.3f}"}, ci90_low=f"{loL:.2f}", ci90_high=f"{hiL:.2f}", notes=""),
           dict(base, method="perfect-verifier fit (any agent right)", **{"lambda": f"{lamA:.3f}"}, ci90_low="", ci90_high="", notes="upper reference: swarm scored as right if any agent was right")]
    cols = ["date", "task", "side", "benchmark", "model", "agents", "method", "lambda", "ci90_low", "ci90_high", "n_tasks", "source", "notes"]
    with open(CSV, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); [w.writerow(r) for r in out]
    print(f"appended {len(out)} rows to {CSV}")
