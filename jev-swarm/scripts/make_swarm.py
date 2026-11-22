"""Convert AI Village's Swarm Village (133 agents, Aug 29-30 2026) into the transcript format run.py scores.

Input: data/swarm-village/village-transcript.json from the gated Hugging Face dataset aidigestorg/ai-village
(research-only terms: do not commit or redistribute; the folder is gitignored).

Kept: the organizers' messages (USER_TALK, role human) and every agent chat message (AGENT_TALK) with the agent's
private reasoning, in time order. Dropped: SEARCH_HISTORY (a model's private summary of the transcript, not a chat
message), PAUSE and CONSOLIDATE (memory bookkeeping). Almost all chat is in one room, so it is one stream.

There is no answer key: every message is labelled "unlabelled", so run.py reports where Jev's flags fall but no
recall or precision.

    python scripts/make_swarm.py    # writes data/swarm-village-run/seed-1.json and labels-seed-1.json
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data/swarm-village/village-transcript.json"
OUT = ROOT / "data/swarm-village-run"

d = json.loads(SRC.read_text())
raw = [e for day in d["days"] for e in day["events"] if e["type"] in ("USER_TALK", "AGENT_TALK")]
raw.sort(key=lambda e: e["timestamp"])
start = raw[0]["timestamp"][:10]

events, labels = [], []
for k, e in enumerate(raw, 1):
    human = e["type"] == "USER_TALK"
    ev = {
        "id": f"sv-{k:04d}",
        "day": 1 if e["timestamp"][:10] == start else 2,
        "ts": e["timestamp"].replace("Z", "+00:00"),
        "actor": e["speakerName"],
        "role": "human" if human else "agent",
        "kind": "message",
        "content": e.get("content") or "",
        "thinking": None if human else e.get("thinking"),
    }
    events.append(ev)
    if not human:
        labels.append({"id": ev["id"], "actor": ev["actor"], "category": "unlabelled", "positive": False,
                       "expected_metrics": []})

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "seed-1.json").write_text(json.dumps(
    {"seed": 1, "date": start, "agents": sorted({e["actor"] for e in events if e["role"] == "agent"}),
     "source": "AI Village swarm village (aidigestorg/ai-village on Hugging Face), research-only terms",
     "events": events}, ensure_ascii=False))
(OUT / "labels-seed-1.json").write_text(json.dumps(
    {"label": "unlabelled", "source": "No answer key exists for Swarm Village.", "messages": labels}, ensure_ascii=False))
agents = {e["actor"] for e in events if e["role"] == "agent"}
print(f"wrote {len(events)} events ({len(labels)} agent messages from {len(agents)} agents, "
      f"{len(events) - len(labels)} organizer messages), {events[0]['ts'][:16]} -> {events[-1]['ts'][:16]}")
