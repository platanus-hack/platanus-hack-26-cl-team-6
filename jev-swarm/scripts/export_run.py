"""Export real runs for the website's swarm view: web/src/data/metr-run.json (METR hard set) and
web/src/data/hf-run.json (Hugging Face incident set, scripts/make_hf.py).

    python scripts/export_run.py            # both
    python scripts/export_run.py --dataset hf

One entry per seed: every agent message with its real timestamp, Jev's scores from results/<dataset>.json, and the
answer key (planted error, its correct version, and for a repeated error the message it repeats). The website
flags a message when either score reaches the threshold; the answer key is shown only as such.
"""
import argparse, json, pathlib, sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import config as C

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_CHARS = 600

SETS = {
    "hard": {"dir": "metr-hard", "catalog": "metr-catalog.json", "out": "metr-run.json",
             "label": "METR report", "calibrated": True},
    "hf": {"dir": "hf-hard", "catalog": "hf-catalog.json", "out": "hf-run.json",
           "label": "Hugging Face incident", "calibrated": False},
}


def export(name: str) -> None:
    cfg = SETS[name]
    rows = {r["id"]: r for r in json.loads((ROOT / f"results/{name}.json").read_text())["rows"]}
    catalog = {e["id"]: e for e in json.loads((ROOT / "data" / cfg["catalog"]).read_text())["errors"]}
    seeds = []
    for seed in (1, 2, 3):
        events = json.loads((ROOT / f"data/{cfg['dir']}/seed-{seed}.json").read_text())["events"]
        t0 = datetime.fromisoformat(events[0]["ts"])
        msgs, origin_of = [], {}
        for e in events:
            r = rows.get(e["id"])
            if not r:
                continue  # the organizer's instruction is not scored
            m = {
                "id": e["id"],
                "t": round((datetime.fromisoformat(e["ts"]) - t0).total_seconds() / 60, 2),
                "actor": e["actor"],
                "fetch": e["kind"] == "action",
                "text": e["content"][:MAX_CHARS] + ("…" if len(e["content"]) > MAX_CHARS else ""),
                "fab": r["scores"]["fabrication"],
                "trust": r["scores"]["unverified_trust"],
                "category": r["category"],
            }
            if r["category"] in ("origin", "propagation"):
                m["planted"] = {"type": r["error_type"], "truth": catalog[r["claim"]]["truth"]}
                if r["category"] == "origin":
                    origin_of[r["claim"]] = len(msgs)
                elif r["claim"] in origin_of:
                    m["from"] = origin_of[r["claim"]]
            msgs.append(m)
        seeds.append({
            "seed": seed,
            # Only the METR hard set has a seed the threshold was picked on.
            "calibration": cfg["calibrated"] and seed == C.CALIBRATION_SEED,
            "start": events[0]["ts"],
            "organizer": events[0]["content"],
            "messages": msgs,
        })
    out = {
        "source": f"jev-swarm {cfg['dir']}, seeds 1-3; scores from results/{name}.json",
        "label": cfg["label"],
        "threshold": C.THRESHOLD,
        "agents": ["Atlas", "Birch", "Cedar", "Delta", "Echo"],
        "seeds": seeds,
    }
    dest = ROOT.parent / "web/src/data" / cfg["out"]
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    flag = lambda m: max(m["fab"], m["trust"]) >= C.THRESHOLD
    for s in seeds:
        p = [m for m in s["messages"] if "planted" in m]
        print(f"{name} seed {s['seed']}: {len(s['messages'])} messages, {len(p)} planted, "
              f"{sum(map(flag, p))} caught, {sum(flag(m) for m in s['messages'] if 'planted' not in m)} false alarms, "
              f"{sum('from' in m for m in p)} linked repeats, {s['messages'][-1]['t']:.0f} min")
    print(f"wrote {dest}")


def export_swarm() -> None:
    """AI Village swarm village -> web/public/data/swarm-village.json (committed and served to the site).

    The dataset's terms are research-only and forbid redistribution, so this exports only Jev's results plus the
    timing metadata the replay needs, never message text. Compact rows:
    [minute, agent index, fabrication, unverified_trust, [indices of agents the message names]]."""
    import re
    events = json.loads((ROOT / "data/swarm-village-run/seed-1.json").read_text())["events"]
    rows = {r["id"]: r for r in json.loads((ROOT / "results/swarm.json").read_text())["rows"]}
    agents = sorted({e["actor"] for e in events if e["role"] == "agent"})
    idx = {a: i for i, a in enumerate(agents)}
    name_re = re.compile(r"\b(" + "|".join(map(re.escape, sorted(agents, key=len, reverse=True))) + r")\b")
    t0 = datetime.fromisoformat(events[0]["ts"])
    msgs = []
    for e in events:
        r = rows.get(e["id"])
        if not r:
            continue
        msgs.append([round((datetime.fromisoformat(e["ts"]) - t0).total_seconds() / 60, 2), idx[e["actor"]],
                     r["scores"]["fabrication"], r["scores"]["unverified_trust"],
                     sorted({idx[m] for m in name_re.findall(e["content"]) if m != e["actor"]})])
    out = {
        "source": "Jev scores on AI Village's Swarm Village (results/swarm.json); message text is not included",
        "threshold": C.THRESHOLD,
        "start": events[0]["ts"],
        # Phase 2 (roles) began at 3am Pacific, Aug 30 = 10:00 UTC.
        "phase2": round((datetime.fromisoformat("2026-08-30T10:00:00+00:00") - t0).total_seconds() / 60, 2),
        "agents": agents,
        "messages": msgs,
    }
    dest = ROOT.parent / "web/public/data/swarm-village.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    flagged = [m for m in msgs if max(m[2], m[3]) >= C.THRESHOLD]
    print(f"swarm: {len(msgs)} messages, {len(agents)} agents, {len(flagged)} flagged "
          f"({len({m[1] for m in flagged})} agents flagged at least once); wrote {dest} ({dest.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=[*SETS, "swarm", "all"], default="all")
    a = ap.parse_args()
    for n in (SETS if a.dataset == "all" else [] if a.dataset == "swarm" else [a.dataset]):
        export(n)
    if a.dataset == "swarm" or (a.dataset == "all" and (ROOT / "results/swarm.json").exists()):
        export_swarm()
