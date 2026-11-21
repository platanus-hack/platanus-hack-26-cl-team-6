# Estimate Toby Ord's swarm-scaling lambda from OpenAI GPT-5.6 multi-agent chart data.
# Model: score = a + b*ln(tokens_per_agent) + c*ln(N)   ->  lambda = c/b
# (N agents each running t tokens  ==  1 agent running N^lambda * t tokens)
import json, math, random, sys
D = json.load(open(sys.argv[1]))
NTASKS = {'SEC-Bench Pro (Multi-Agent)': 183, 'BrowseComp (Multi-Agent)': 1266, 'Terminal-Bench 2.1 (Multi-Agent)': 89}

def solve(A, y):  # least squares via normal equations, small k
    k = len(A[0]); M = [[sum(r[i]*r[j] for r in A) for j in range(k)] for i in range(k)]
    v = [sum(r[i]*yy for r, yy in zip(A, y)) for i in range(k)]
    for i in range(k):  # gaussian elimination
        p = max(range(i, k), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]; v[i], v[p] = v[p], v[i]
        for r in range(k):
            if r != i:
                f = M[r][i]/M[i][i]; M[r] = [a-f*b for a, b in zip(M[r], M[i])]; v[r] -= f*v[i]
    return [v[i]/M[i][i] for i in range(k)]

def logit(p): p = min(max(p, 1e-3), 1-1e-3); return math.log(p/(1-p))

def rows(title):
    out = []
    for r in D[title]:
        if r['x_metric'] != 'output_tokens' or 'Sol ·' not in r['model']: continue
        n = int(r['model'].split('·')[1].split()[0])
        lat = next(x['x_value'] for x in D[title] if x['model'] == r['model'] and x['juice_level'] == r['juice_level'] and x['x_metric'] == 'latency_s')
        out.append(dict(N=n, lvl=r['juice_level'], tot=r['x_value'], per=r['x_value']/n, s=r['score'], lat=lat))
    return out

def fit(R, link=lambda s: s, split=False):
    A, y = [], []
    for r in R:
        x = [1, math.log(r['per'])]
        x += [math.log(4) if r['N'] >= 4 else 0, math.log(4) if r['N'] >= 16 else 0] if split else [math.log(r['N'])]
        A.append(x); y.append(link(r['s']))
    if split and not any(r['N'] >= 16 for r in R): A = [a[:3] for a in A]
    co = solve(A, y)
    return [c/co[1] for c in co[2:]], co

def boot(R, n, link, split=False, B=4000, seed=0):
    rnd = random.Random(seed); out = []
    for _ in range(B):
        RR = [dict(r, s=sum(rnd.random() < r['s'] for _ in range(n))/n) for r in R]
        try: out.append(fit(RR, link, split)[0])
        except ZeroDivisionError: pass
    res = []
    for j in range(len(out[0])):
        v = sorted(o[j] for o in out); res.append((v[int(.05*len(v))], v[int(.95*len(v))]))
    return res

def interp(xs, ys, x):  # piecewise linear, linear extrapolation at ends
    pts = sorted(zip(xs, ys))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1 or (x1, y1) == pts[-1]:
            return y0 + (y1-y0)*(x-x0)/(x1-x0)

summary = {}
for title, n in NTASKS.items():
    R = rows(title)
    print(f"\n==== {title}  (n_tasks={n}) ====")
    for link, nm in [(lambda s: s, 'linear score'), (logit, 'logit score')]:
        lam, co = fit(R, link); ci = boot(R, n, link)
        print(f"  pooled λ [{nm}] = {lam[0]:.3f}  90% CI [{ci[0][0]:.2f}, {ci[0][1]:.2f}]   (duration slope b={co[1]:.4f}/ln-token)")
        if nm == 'linear score': summary[title] = dict(lam=lam[0], ci=ci[0])
        ls, _ = fit(R, link, split=True); cis = boot(R, n, link, split=True, B=2000)
        print(f"     by step: λ(1→4)={ls[0]:.3f} [{cis[0][0]:.2f},{cis[0][1]:.2f}]" + (f"   λ(4→16)={ls[1]:.3f} [{cis[1][0]:.2f},{cis[1][1]:.2f}]" if len(ls) > 1 else ''))
    # pointwise: invert the 1-agent curve (score vs ln tokens) for each swarm point
    one = [r for r in R if r['N'] == 1]
    lnT = [math.log(r['tot']) for r in one]; S = [r['s'] for r in one]
    print("  pointwise (N agents at effort e  ->  equivalent single-agent tokens):")
    for r in R:
        if r['N'] == 1: continue
        Tstar = math.exp(interp(S, lnT, r['s']))
        lam_p = math.log(Tstar/r['per'])/math.log(r['N'])
        flag = ' (extrapolated)' if not (min(S) <= r['s'] <= max(S)) else ''
        print(f"     N={r['N']:>2} {r['lvl']:<6} score={r['s']:.3f} per-agent={r['per']/1e3:6.1f}K  ≡ 1 agent @ {Tstar/1e3:6.1f}K  λ={lam_p:.2f}{flag}")
    # Scenario: speed & cost at matched score (measured, not theoretical)
    print("  matched-score comparison vs 1 agent (interpolating the 1-agent curve on ln scale):")
    lnL = [math.log(r['lat']) for r in one]
    for r in R:
        if r['N'] == 1 or not (min(S) <= r['s'] <= max(S)): continue
        T1 = math.exp(interp(S, lnT, r['s'])); L1 = math.exp(interp(S, lnL, r['s']))
        print(f"     N={r['N']:>2} {r['lvl']:<6} score={r['s']:.3f}: total-token premium x{r['tot']/T1:.2f} (theory N^(1-λ)=x{r['N']**(1-summary[title]['lam']):.2f}); "
              f"wall-clock speedup x{L1/r['lat']:.2f} (theory N^λ=x{r['N']**summary[title]['lam']:.2f})")
    print("  max score: " + ", ".join(f"N={N}: {max(r['s'] for r in R if r['N']==N):.3f}" for N in sorted({r['N'] for r in R})))
json.dump(summary, open('data/lambda_summary.json', 'w'), indent=1)
