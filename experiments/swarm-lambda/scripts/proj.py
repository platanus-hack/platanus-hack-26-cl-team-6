import json, math, sys
D = json.load(open(sys.argv[1]))
LAMS = {'low (TB2.1)': 0.48, 'central (SEC-Bench Pro)': 0.57, 'high (BrowseComp)': 0.68}
def slope(pts):  # OLS of score on ln(tokens)
    xs=[math.log(t) for t,_ in pts]; ys=[s for _,s in pts]; mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); return b, my-b*mx
def interp(pts, lnT):
    pts=sorted((math.log(t),s) for t,s in pts)
    for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
        if lnT<=x1 or (x1,y1)==pts[-1]: return min(1.0, y0+(y1-y0)*(lnT-x0)/(x1-x0))
print("== Capture-the-Flag (OpenAI internal, 63 challenges): single-agent duration scaling ==")
ctf = {}
for r in D['Capture-the-Flag Challenges']:
    if r['x_metric']=='output_tokens': ctf.setdefault(r['model'],[]).append((r['x_value'],r['score'],r['juice_level']))
for m in ['GPT-5.6 Luna','GPT-5.6 Terra','GPT-5.6 Sol']:
    pts=[(t,s) for t,s,_ in ctf[m]]; b,_=slope(pts)
    print(f"  {m:<14} pp per 2x tokens = {100*b*math.log(2):.1f}   points: " + ", ".join(f"{l}:{t/1e3:.1f}K→{s:.1%}" for t,s,l in ctf[m]))
    # projection: swarm of N at 'high' effort ~ single agent at N^λ × per-agent tokens (cap at 100%; extrapolation flagged)
    t_hi, s_hi = next((t,s) for t,s,l in ctf[m] if l=='high')
    for N in (4,16):
        row=[]
        for k,lam in LAMS.items():
            T=t_hi*N**lam; s=interp(pts, math.log(T)); ext = T>max(t for t,_ in pts)
            row.append(f"λ={lam}: {s:.1%}{'*' if ext else ''}")
        print(f"     projected {N:>2} agents @high (1 agent @high = {s_hi:.1%}): " + "; ".join(row))
print("  (* = beyond the measured token range, linear-in-log extrapolation, capped at 100%)")

print("\n== ExploitGym (869 exploit-dev challenges): duration scaling via 2h vs 6h wall-clock caps ==")
eg = {}
for r in D['ExploitGym']:
    eg.setdefault((r['model'], r['dataset']), []).append((r['juice_index'], r['effort_label'], r['x_value'], r['score']))
for m in ['GPT-5.6 Sol','GPT-5.6 Terra','GPT-5.6 Luna']:
    for cap in ['2h','6h']:
        tok = sorted(eg[(f'{m} · {cap} cap','Output tokens')]); lat = sorted(eg[(f'{m} · {cap} cap','Latency')])
        print(f"  {m:<14}{cap}: " + ", ".join(f"{e}: {t/1e3:.0f}K tok, {l:.0f} min → {s:.1%}" for (_,e,t,s),(_,_,l,_) in zip(tok,lat)))
    tok2=sorted(eg[(f'{m} · 2h cap','Output tokens')]); tok6=sorted(eg[(f'{m} · 6h cap','Output tokens')])
    pts=[(t,s) for _,_,t,s in tok2+tok6]; b,_=slope(pts)
    print(f"     pooled pp per 2x output tokens = {100*b*math.log(2):.1f}")
# Scenario: reach the 6h-cap score inside a 2h wall-clock budget using a swarm (3x duration)
print("\n  Scenario: match a 3x longer run (2h → 6h cap) with a swarm under the 2h cap")
for k,lam in LAMS.items():
    N=3**(1/lam); print(f"     λ={lam} {k:<24}: N ≈ {N:.1f} agents, compute premium N^(1-λ) ≈ x{N**(1-lam):.2f}")

print("\n== Ord's generic scenarios at each λ ==")
for k,lam in LAMS.items():
    print(f"  λ={lam} {k:<24}: 4 agents ≡ 1 agent ×{4**lam:.2f} duration, costs ×{4**(1-lam):.2f};  16 agents ≡ ×{16**lam:.2f}, costs ×{16**(1-lam):.2f};  10x swarm ≡ ×{10**lam:.2f};  100x duration needs {100**(1/lam):,.0f} agents")
