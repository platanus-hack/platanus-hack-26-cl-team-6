"""Export a short transcript excerpt for the website's live demo (web/src/data/demo.json).

Uses easy seed 2, events 0..15. The first Haiku ledger snapshot for this seed starts at event 21, so Jev saw no
ledger for any of these messages: the website can rebuild Jev's exact input without Haiku.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import config as C

ROOT = pathlib.Path(__file__).resolve().parent.parent
N = 16
events = json.loads((ROOT / "data/metr-easy/seed-2.json").read_text())["events"][:N]
rows = {r["id"]: r for r in json.loads((ROOT / "results/easy.json").read_text())["rows"]}
catalog = {e["id"]: e for e in json.loads((ROOT / "data/metr-catalog.json").read_text())["errors"]}
snaps = json.loads(next((ROOT / ".cache/easy").glob("ledger-seed-2-*.json")).read_text())["snapshots"]
assert min(int(k) for k in snaps) > N, "excerpt overlaps the first ledger snapshot"

out = []
for e in events:
    r = rows.get(e["id"])
    item = {k: e[k] for k in ("id", "day", "ts", "actor", "role", "kind", "content")}
    if r:
        item["scores"] = r["scores"]
        item["category"] = r["category"]
        if r["category"] in ("origin", "propagation"):
            err = catalog[r["claim"]]
            item["error"] = {"id": err["id"], "type": err["type"], "truth": err["truth"]}
    out.append(item)

demo = {
    "source": "jev-swarm easy seed 2, events 0-15; scores from results/easy.json",
    "threshold": C.THRESHOLD,
    "model": C.JEV_MODEL,
    "mission": C.MISSION.strip(),
    "context": C.CONTEXT,
    "metrics": {k: {"question": q, "true": t, "false": f} for k, (q, t, f) in C.METRICS.items()},
    "events": out,
}
dest = ROOT.parent / "web/src/data/demo.json"
dest.write_text(json.dumps(demo, ensure_ascii=False, indent=1))
print(f"wrote {dest} ({len(out)} events)")
