"""Build a self-contained demo dashboard from an Inspect .eval log.

    python dashboard.py                      # newest log in .\\logs -> dashboard.html
    python dashboard.py logs\\my-run.eval     # a specific log
    python dashboard.py --out demo.html --open

Works on Windows, macOS and Linux. The HTML has no external dependencies,
so it opens offline (good for a demo with bad venue wifi).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from inspect_ai.log import read_eval_log  # noqa: E402

import ledger as L  # noqa: E402

AGENTS = ["researcher", "writer", "reviewer", "summarizer"]
CLASSES = ("fabricated", "mutated", "cited", "poisoned")
AGENT_ES = {"researcher": "investigador", "writer": "redactor", "reviewer": "revisor", "summarizer": "sintetizador"}


def plant_in(p: dict, claims: list, text: str | None = None) -> "L.Claim | None":
    """Same rule as swarm.plant_in: value + context word, and the right person when the plant names one."""
    probe = L.Claim(str(p["value"]), float(p["value"]), p["kind"], 1e-6, 0, 0, "",
                    {L._stem(k.lower()) for k in p["keywords"]})
    for c in claims:
        if L.same_claim(c, probe):
            if text is not None and p.get("entity") and L.entity_for(text, c, [p["entity"]]) != p["entity"]:
                continue
            return c
    return None


def _logs_by_task(task_name: str) -> list[Path]:
    """All logs in .\\logs for one task, newest first."""
    out = []
    for f in sorted(glob.glob(os.path.join("logs", "*.eval")), key=os.path.getmtime, reverse=True):
        try:
            if read_eval_log(f, header_only=True).eval.task.endswith(task_name):
                out.append(Path(f).resolve())
        except Exception:
            continue
    return out


def find_log(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    logs = _logs_by_task("claim_laundering")
    if not logs:
        sys.exit("No claim_laundering log found in .\\logs. Run `inspect eval swarm.py ...` first, or pass a log path.")
    return logs[0]


def find_degradation_logs(args: list[str] | None) -> list[Path]:
    """Explicit --deg logs, else the newest degradation log with the ledger off and the newest with it on."""
    if args:
        return [Path(a).expanduser().resolve() for a in args]
    picked: dict[bool, Path] = {}
    for f in _logs_by_task("degradation"):
        on = bool((read_eval_log(str(f), header_only=True).eval.task_args or {}).get("ledger"))
        picked.setdefault(on, f)
    return [picked[k] for k in (False, True) if k in picked]


def build_degradation(paths: list[Path]) -> dict | None:
    runs = {}
    mock = False
    model = None
    for path in paths:
        log = read_eval_log(str(path))
        args = log.eval.task_args or {}
        n = int(args.get("n_agents", 32))
        on = bool(args.get("ledger"))
        mock = mock or bool(args.get("mock")) or "mockllm" in log.eval.model
        model = log.eval.model
        tot: dict[str, float] = {}
        reports = 0
        plant_label = None
        for smp in log.samples or []:
            sc = (smp.scores or {}).get("degradation")
            if sc is None:
                continue
            reports += 1
            pl = smp.store.get("chain_plant")
            if pl and not plant_label:
                plant_label = {"entity": pl.get("entity"), "from": pl.get("from_text"), "to": pl.get("to_text"),
                               "hop": int(smp.store.get("chain_plant_hop") or 0)}
            for k, v in sc.value.items():
                tot[k] = tot.get(k, 0) + v
        if not reports:
            continue
        F = tot.get("facts", 0) or 1
        hops = list(range(1, n + 1))
        runs["on" if on else "off"] = {
            "n": n, "reports": reports, "log": path.name, "facts": tot.get("facts", 0),
            "intact": [100 * tot.get(f"h{k}_intact", 0) / F for k in hops],
            "mutated": [100 * tot.get(f"h{k}_mutated", 0) / F for k in hops],
            "dropped": [100 * tot.get(f"h{k}_dropped", 0) / F for k in hops],
            "fabricated": [tot.get(f"h{k}_fabricated", 0) / reports for k in hops],
            "plant_applied": tot.get("plant_applied", 0), "plant_info": plant_label,
            "plant": [100 * tot.get(f"h{k}_plant", 0) / tot["plant_applied"] for k in hops]
                     if tot.get("plant_applied") else None,
        }
    return {"mock": mock, "model": model, "runs": runs} if runs else None


def segments(report: str, entries: list[dict], poison_sents: dict[str, str]) -> list[dict]:
    """Split the report into sentence segments tagged plain / flag / poison."""
    flags: dict[str, list[dict]] = {}
    for e in entries:
        if e["status"] == "untraceable" and e["sentence"]:
            flags.setdefault(e["sentence"], []).append(e)
    out, pos = [], 0
    for a, b, s in L._sentences(report):
        if a > pos:
            out.append({"t": report[pos:a], "k": "gap"})
        key = s.strip()
        lead = s[: len(s) - len(s.lstrip())]
        if lead:
            out.append({"t": lead, "k": "gap"})
        if key in flags:
            es = flags[key]
            out.append({"t": key, "k": "flag",
                        "note": "; ".join(f"{e['claim']}: nació en el {AGENT_ES.get(e['origin_agent'], 'agente desconocido')}, turno {e['origin_turn']}" for e in es)})
        elif key in poison_sents:
            out.append({"t": key, "k": "poison", "note": poison_sents[key]})
        else:
            out.append({"t": key, "k": "plain"})
        tail = s[len(s.rstrip()):]
        if tail:
            out.append({"t": tail, "k": "gap"})
        pos = b
    if pos < len(report):
        out.append({"t": report[pos:], "k": "gap"})
    return out


def build(log_path: Path) -> dict:
    log = read_eval_log(str(log_path))
    tot = {f"{c}_{k}": 0 for c in CLASSES for k in ("applied", "raw", "after")}
    tot.update(origin_correct=0, origin_total=0, true_claims=0, false_flags=0, unlabelled_flags=0)
    jtot: dict[str, float] = {}
    samples = []
    for s in log.samples or []:
        sc = (s.scores or {}).get("claim_ledger")
        if sc is None:
            continue
        for k in tot:
            tot[k] += sc.value.get(k, 0)
        jsc = (s.scores or {}).get("llm_judge")
        jitems = []
        if jsc is not None:
            for k, v in jsc.value.items():
                jtot[k] = jtot.get(k, 0) + v
            jitems = jsc.metadata.get("judge_items", [])
        swarm_log = s.store.get("swarm_log", [])
        applied = s.store.get("plants_applied", {})
        sources = s.metadata["sources"]
        report = swarm_log[-1]["output"] if swarm_log else ""
        entries = sc.metadata["ledger"]
        filtered = sc.metadata["filtered_report"]
        raw_claims, after_claims = L.extract_claims(report), L.extract_claims(filtered)

        plants, poison_sents = [], {}
        for p in s.metadata["plants"]:
            if not applied.get(p["id"]):
                continue
            hop_hits = [plant_in(p, L.extract_claims(e["output"]), e["output"]) for e in swarm_log]
            hops = [h is not None for h in hop_hits]
            hop_sents = [" ".join(h.sentence.split()) if h is not None else None for h in hop_hits]
            hit = plant_in(p, raw_claims, report)
            entry = None
            if hit is not None:
                entry = next((e for e in entries if e["claim"] == hit.text and e["sentence"] == hit.sentence.strip()), None)
                if p["class"] == "poisoned":
                    poison_sents[hit.sentence.strip()] = (
                        f"{hit.text}: rastreable hasta {entry['source'] if entry else 'una fuente'} pero falsa (fuera de alcance)")
            jv = None
            if hit is not None and jitems:
                it = next((i for i in jitems if i["claim"] == hit.text and i["sentence"] == hit.sentence.strip()), None)
                jv = it["verdict"] if it else None
            src_claim = None
            if p["class"] == "poisoned":
                sid = p["target"].split(":", 1)[1]
                c = plant_in(p, L.extract_claims(sources.get(sid, "")))
                src_claim = c.sentence.strip() if c else None
            label = p.get("inject") or (f"{p.get('from_text')} → {p.get('to_text')}" if p["class"] == "mutated" else src_claim) or str(p["value"])
            plants.append({
                "id": p["id"], "cls": p["class"], "target": p["target"], "label": label,
                "claim": hit.text if hit is not None else (p.get("to_text") or str(p["value"])),
                "hops": hops, "hop_sents": hop_sents, "in_report": hit is not None,
                "report_sentence": " ".join(hit.sentence.split()) if hit is not None else None,
                "after": plant_in(p, after_claims, filtered) is not None,
                "featured": bool(p.get("featured")), "entity": p.get("entity"),
                "status": entry["status"] if entry else None,
                "origin_agent": entry["origin_agent"] if entry else None,
                "origin_turn": entry["origin_turn"] if entry else None,
                "source": entry["source"] if entry else None,
                "judge": jv,
            })
        samples.append({
            "id": f"{s.id}" + (f" (época {s.epoch})" if (log.eval.config.epochs or 1) > 1 else ""),
            "brief": s.input if isinstance(s.input, str) else str(s.input),
            "sources": sources,
            "agents": [e["agent"] for e in swarm_log],
            "plants": plants,
            "segments": segments(report, entries, poison_sents),
        })
    return {"model": log.eval.model, "log": log_path.name, "created": log.eval.created,
            "mock": "mockllm" in log.eval.model or bool((log.eval.task_args or {}).get("mock")),
            "totals": tot, "samples": samples,
            "dataset": (log.eval.metadata or {}).get("dataset") or (log.eval.task_args or {}).get("dataset") or "reports",
            "judge": jtot or None,
            "judge_model": _judge_model(log)}


def _judge_model(log) -> str | None:
    roles = log.eval.model_roles or {}
    j = roles.get("judge")
    if j is None:
        return None
    return getattr(j, "model", None) or str(j)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", nargs="?", help="path to an .eval log (default: newest in .\\logs)")
    ap.add_argument("--out", default="dashboard.html", help="output HTML file")
    ap.add_argument("--open", action="store_true", help="open in the browser when done")
    ap.add_argument("--deg", nargs="*", help="degradation logs (default: newest with ledger off and on in .\\logs)")
    args = ap.parse_args()

    log_path = find_log(args.log)
    data = build(log_path)
    data["degradation"] = build_degradation(find_degradation_logs(args.deg))
    if not data["samples"]:
        sys.exit(f"No scored samples in {log_path}")
    template = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = Path(args.out).expanduser().resolve()
    out.write_text(template.replace("/*__DATA__*/null", payload), encoding="utf-8")
    print(f"Read {log_path}\nWrote {out}")
    if args.open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
