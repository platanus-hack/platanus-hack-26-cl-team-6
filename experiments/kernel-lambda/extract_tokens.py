"""Extract per-sample token usage from run 2 Inspect logs into tokens_run2.csv.

Usage: python extract_tokens.py [log.eval ...]   (defaults to the run 2 logs)
Read-only: logs are opened with read_eval_log and never modified.
"""
import csv
import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log

DEFAULT_LOGS = [
    "logs2_best_of/2026-11-21T21-15-20-00-00_lambda-suite_9GsPogqDprq5pdaXwnEBR9.eval",
    "logs2_shared/2026-11-21T21-38-26-00-00_lambda-suite_FNdALwLUJeq3EhTSwLvuSe.eval",
]
FIELDS = ["input_tokens", "output_tokens", "input_tokens_cache_read",
          "input_tokens_cache_write", "total_tokens", "reasoning_tokens"]
COLS = ["combine", "n_agents", "budget_per_agent", "epoch", "score",
        "input_tokens", "output_tokens", "cache_read", "cache_write",
        "total_tokens", "reasoning_tokens", "evaluate_calls", "evals_used",
        "usage_source"]


def sum_usage(usages):
    tot = dict.fromkeys(FIELDS, 0)
    for u in usages:
        for f in FIELDS:
            tot[f] += getattr(u, f, None) or 0
    return tot


def main(paths):
    rows = []
    for path in paths:
        log = read_eval_log(path)
        print(f"{path}: status={log.status} args={log.eval.task_args} "
              f"epochs={log.eval.config.epochs} samples={len(log.samples)}",
              file=sys.stderr)
        for s in log.samples:
            if s.error:
                continue
            md = s.metadata or {}
            if s.model_usage:
                tot, src = sum_usage(s.model_usage.values()), "model_usage"
            else:
                tot = sum_usage(e.output.usage for e in s.events
                                if type(e).__name__ == "ModelEvent"
                                and e.output and e.output.usage)
                src = "model_events"
            sc = s.scores["swarm_score"]
            rows.append({
                "combine": md.get("combine", log.eval.task_args.get("combine")),
                "n_agents": md.get("n_agents"),
                "budget_per_agent": md.get("budget_per_agent"),
                "epoch": s.epoch,
                "score": sc.value,
                "input_tokens": tot["input_tokens"],
                "output_tokens": tot["output_tokens"],
                "cache_read": tot["input_tokens_cache_read"],
                "cache_write": tot["input_tokens_cache_write"],
                "total_tokens": tot["total_tokens"],
                "reasoning_tokens": tot["reasoning_tokens"],
                "evaluate_calls": sum(1 for e in s.events
                                      if type(e).__name__ == "ToolEvent"
                                      and e.function == "evaluate"),
                "evals_used": (sc.metadata or {}).get("evals_used"),
                "usage_source": src,
            })
    rows.sort(key=lambda r: (r["combine"], r["n_agents"], r["budget_per_agent"], r["epoch"]))
    with open("tokens_run2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    groups = defaultdict(list)
    for r in rows:
        groups[(r["combine"], r["n_agents"], r["budget_per_agent"])].append(r)
    print("combine,n_agents,budget_per_agent,n,mean_total_tokens,mean_output_tokens,mean_evaluate_calls")
    for k, g in sorted(groups.items()):
        n = len(g)
        print(f"{k[0]},{k[1]},{k[2]},{n},"
              f"{sum(r['total_tokens'] for r in g)/n:.0f},"
              f"{sum(r['output_tokens'] for r in g)/n:.0f},"
              f"{sum(r['evaluate_calls'] for r in g)/n:.2f}")
    print(f"rows={len(rows)} sources={set(r['usage_source'] for r in rows)}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_LOGS)
