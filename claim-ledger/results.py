"""Print the with-vs-without-ledger table, and the LLM judge vs ledger comparison, from an Inspect log.

    python results.py                  # latest claim_laundering log in .\\logs
    python results.py --degradation    # latest degradation log (curve vs number of agents)
    python results.py logs\\x.eval      # a specific log (either kind)
"""

import glob
import os
import sys

from inspect_ai.log import read_eval_log

CLASSES = ("fabricated", "mutated", "cited", "poisoned")
LABEL = {"fabricated": "fabricated", "mutated": "mutated", "cited": "fake cite", "poisoned": "poisoned"}

want = "degradation" if "--degradation" in sys.argv else "claim_laundering"
explicit = [a for a in sys.argv[1:] if a.endswith(".eval")]
if explicit:
    path = explicit[0]
else:
    logs = [f for f in sorted(glob.glob(os.path.join("logs", "*.eval")), key=os.path.getmtime, reverse=True)
            if read_eval_log(f, header_only=True).eval.task.endswith(want)]
    if not logs:
        sys.exit(f"No {want} log found in ./logs. Run `inspect eval ...` first.")
    path = logs[0]
path = os.path.abspath(path)
log = read_eval_log(path)

if log.eval.task.endswith("degradation"):
    # information degradation vs number of agents
    args = log.eval.task_args or {}
    n = int(args.get("n_agents", 32))
    tot: dict[str, float] = {}
    reports = 0
    for s in log.samples or []:
        sc = (s.scores or {}).get("degradation")
        if sc is None:
            continue
        reports += 1
        for k, v in sc.value.items():
            tot[k] = tot.get(k, 0) + v
    F = tot.get("facts", 0) or 1
    print(f"log: {path}")
    print(f"model: {log.eval.model}   ledger between hops: {bool(args.get('ledger'))}   reports: {reports}")
    if args.get("mock"):
        print("MOCK RUN: simulated random noise, not model behaviour. Plumbing check only.")
    P = tot.get("plant_applied", 0)
    if P:
        print(f"planted claim at hop {args.get('plant_hop', 2)} in {P:.0f} of {reports} chains "
              "(last column: share of those chains where it is still there)")
    print(f"\n{'agents':>6} {'intact':>8} {'mutated':>8} {'dropped':>8} {'degraded':>9} {'fabricated/report':>18}"
          + (f" {'plant alive':>12}" if P else ""))
    for k in range(1, n + 1):
        i, m, d = (100 * tot.get(f"h{k}_{x}", 0) / F for x in ("intact", "mutated", "dropped"))
        fab = tot.get(f"h{k}_fabricated", 0) / max(reports, 1)
        mark = " <" if k in (4, 8, 16, 32) else ""
        alive = f" {100 * tot.get(f'h{k}_plant', 0) / P:>11.0f}%" if P else ""
        print(f"{k:>6} {i:>7.0f}% {m:>7.0f}% {d:>7.0f}% {m + d:>8.0f}% {fab:>18.2f}{alive}{mark}")
    sys.exit()


def totals(scorer: str) -> dict:
    tot: dict[str, float] = {}
    for s in log.samples or []:
        sc = (s.scores or {}).get(scorer)
        if sc is None:
            continue
        for k, v in sc.value.items():
            tot[k] = tot.get(k, 0) + v
    return tot


def pct(a, b):
    return f"{a:.0f}/{b:.0f} ({100 * a / b:.0f}%)" if b else "n/a"


T = totals("claim_ledger")
J = totals("llm_judge")
errored = [s.id for s in log.samples if "claim_ledger" not in (s.scores or {})]
if errored:
    print(f"skipping {len(errored)} errored samples: {errored}")

print(f"log: {path}")
print(f"model: {log.eval.model}   samples x epochs: {len(log.samples)}")
if "mockllm" in log.eval.model:
    print("MOCK RUN: agents copy text verbatim. These numbers only check the plumbing.")
print()
print(f"{'class':<12}{'reached report (no ledger)':<30}{'reached report (with ledger)':<30}")
for c in CLASSES:
    n = T.get(f"{c}_applied", 0)
    print(f"{LABEL[c]:<12}{pct(T.get(f'{c}_raw', 0), n):<30}{pct(T.get(f'{c}_after', 0), n):<30}")
fake = ("fabricated", "mutated", "cited")
n = sum(T.get(f"{c}_applied", 0) for c in fake)
raw = sum(T.get(f"{c}_raw", 0) for c in fake)
after = sum(T.get(f"{c}_after", 0) for c in fake)
print(f"{'all fakes':<12}{pct(raw, n):<30}{pct(after, n):<30}")
print()
print(f"false flags on true claims: {pct(T['false_flags'], T['true_claims'])}   (target < 5%)")
print(f"origin accuracy (agent that introduced it): {pct(T['origin_correct'], T['origin_total'])}")
print(f"other flagged claims (likely natural hallucinations, check by hand): {T['unlabelled_flags']:.0f}")
if T.get("quote_total"):
    print(f"quotes (5+ words) not found word for word in the sources: {pct(T['quote_flags'], T['quote_total'])}"
          "   (reported only; rewording a real quote also counts)")

print("\nLLM JUDGE vs LEDGER (same figures, same final reports)")
if not J:
    print("  judge not run in this log (mock mode, or -T judge=false).")
    print("  Run: inspect eval swarm.py --model <swarm-model> --model-role judge=<judge-model>")
    sys.exit()
judge_model = (log.eval.model_roles or {}).get("judge")
print(f"  judge model: {getattr(judge_model, 'model', judge_model) or log.eval.model}")
print(f"  {'class':<12}{'in report':<12}{'judge fooled':<18}{'ledger fooled':<18}")
for c in CLASSES:
    inrep = T.get(f"{c}_raw", 0)
    j_fooled = J.get(f"{c}_judge_inreport", 0) - J.get(f"{c}_judge_caught", 0)
    l_fooled = T.get(f"{c}_after", 0)
    note = "   (expected: both pass, out of scope)" if c == "poisoned" else ""
    print(f"  {LABEL[c]:<12}{inrep:<12.0f}{pct(j_fooled, inrep):<18}{pct(l_fooled, inrep):<18}{note}")
print(f"  false flags on true claims: judge {pct(J['judge_false_flags'], J['judge_true_claims'])}, "
      f"ledger {pct(T['false_flags'], T['true_claims'])}")
if J.get("judge_missing"):
    print(f"  judge gave no verdict for {J['judge_missing']:.0f} of {J['judge_claims']:.0f} figures (counted as not flagged)")
