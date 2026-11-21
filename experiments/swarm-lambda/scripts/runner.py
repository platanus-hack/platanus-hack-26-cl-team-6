"""Run swarms of headless Claude Code agents on synthetic SOC tasks and log results for a λ fit.

- Agents: `claude -p` (Claude Code login, ANTHROPIC_API_KEY removed from env), Haiku, --restricted,
  Bash/Read/Write only, OS sandbox on, no MCP/plugins/skills, no session persistence.
- A swarm = N agents started together on copies of the same logs, sharing ../shared/NOTES.md.
  Each writes its final answer to ../shared/answers/agent_i.txt; the swarm answer is the majority
  vote (tie -> earliest written). `any_correct` is also logged for reference.
- Answers are held in memory only; results.jsonl has no answer text. reveal.json is written at the end.
- Spend guard: stops launching new swarms once tracked list-price cost reaches --cap.
"""
import argparse, json, os, secrets, shutil, subprocess, sys, threading, time, uuid
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_soc import make_task, normalize

SANDBOX = json.dumps({"sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True}})
SYS_TEAM = ("You are SOC analyst agent {i} of a team of {n} agents investigating the same incident in parallel. "
            "Your working directory has a copy of the logs and QUESTION.md. Coordinate through the shared notes file "
            "../shared/NOTES.md: read it when you start and every few steps, and append short findings prefixed with "
            "[agent {i}] (what you checked, what you found, what you will do next) so teammates do not repeat work; split the work sensibly. ")
SYS_SOLO = ("You are a SOC analyst agent investigating a security incident. Your working directory has the logs and QUESTION.md. "
            "You may keep working notes in ../shared/NOTES.md. ")
SYS_COMMON = ("Analyse the logs with command-line tools (grep, python3); do not print whole large files. "
              "Only use your working directory and ../shared. When you are confident, write ONLY the final answer, in the exact "
              "answer format from QUESTION.md, to ../shared/answers/agent_{i}.txt, then stop.")


class Slots:  # atomic multi-slot acquire (no deadlock between swarms)
    def __init__(self, n): self.free, self.cv = n, threading.Condition()
    def acquire(self, k):
        with self.cv:
            self.cv.wait_for(lambda: self.free >= k); self.free -= k
    def release(self, k):
        with self.cv: self.free += k; self.cv.notify_all()


class State:
    def __init__(self, cap): self.cost, self.cap, self.lock = 0.0, cap, threading.Lock()
    def add(self, c):
        with self.lock: self.cost += c
    def over(self):
        with self.lock: return self.cost >= self.cap


def run_agent(adir: Path, i: int, n: int, effort: str, model: str, timeout: int, max_turns: int):
    sysp = (SYS_TEAM.format(i=i, n=n) if n > 1 else SYS_SOLO) + SYS_COMMON.format(i=i)
    cmd = ["claude", "-p", "Read QUESTION.md and answer it.", "--model", model, "--effort", effort, "--restricted",
           "--tools", "Bash,Read,Write", "--allowedTools", "Bash", "Read", "Write", "--strict-mcp-config",
           "--disable-slash-commands", "--no-session-persistence", "--add-dir", "../shared", "--settings", SANDBOX,
           "--system-prompt", sysp, "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns)]
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    t0 = time.time(); p = subprocess.Popen(cmd, cwd=adir, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, text=True)
    timer = threading.Timer(timeout, p.kill); timer.start()
    res, partial_out, events = None, 0, []
    try:
        for line in p.stdout:
            try: e = json.loads(line)
            except json.JSONDecodeError: continue
            events.append({"_t": round(time.time() - t0, 2), **e})  # full transcript, kept in memory until the run ends
            if e.get("type") == "assistant": partial_out += e["message"].get("usage", {}).get("output_tokens", 0)
            elif e.get("type") == "result": res = e
        p.wait()
    finally:
        timer.cancel()
    dur = time.time() - t0
    if res is None:
        # killed or crashed: rough list-price estimate from partial usage (output only, Haiku $0.50/M)
        return dict(status="timeout_or_crash", out_tokens=partial_out, cost=partial_out * 0.5e-6, turns=None, dur=dur, text="", events=events)
    return dict(status=res.get("subtype", "?") + ("/error" if res.get("is_error") else ""), out_tokens=res["usage"]["output_tokens"],
                cost=res.get("total_cost_usd", 0.0), turns=res.get("num_turns"), dur=dur, text=(res.get("result") or "")[-400:],
                api_error=res.get("api_error_status"), events=events)


def run_swarm(task, effort, n, args, slots, state, workroot: Path):
    rd = workroot / uuid.uuid4().hex[:12]; (rd / "shared" / "answers").mkdir(parents=True)
    (rd / "shared" / "NOTES.md").write_text("# Shared notes\n")
    for i in range(n):
        ad = rd / f"agent_{i}"; ad.mkdir()
        for name, content in task["files"].items(): (ad / name).write_text(content)
    slots.acquire(n); out = [None] * n; t0 = time.time()
    try:
        th = [threading.Thread(target=lambda i=i: out.__setitem__(i, run_agent(rd / f"agent_{i}", i, n, effort, args.model, args.timeout, args.max_turns))) for i in range(n)]
        [t.start() for t in th]; [t.join() for t in th]
    finally:
        slots.release(n)
    wall = time.time() - t0
    answers, raw_answers = [], {}
    for i in range(n):
        f = rd / "shared" / "answers" / f"agent_{i}.txt"
        if f.exists():
            answers.append((f.stat().st_mtime, normalize(f.read_text())))
            raw_answers[f"agent_{i}"] = dict(text=f.read_text(), written_s=round(f.stat().st_mtime - t0, 1))
    answers.sort()
    voted = None
    if answers:
        cnt = Counter(a for _, a in answers); best = max(cnt.values())
        voted = next(a for _, a in answers if cnt[a] == best)
    truth = normalize(task["answer"])
    notes_text = (rd / "shared" / "NOTES.md").read_text(); notes_len = len(notes_text)
    shutil.rmtree(rd, ignore_errors=True)
    for o in out: state.add(o["cost"])
    row = dict(task=task["id"], depth=task["depth"], noise=task["noise"], effort=effort, N=n, correct=voted == truth,
               any_correct=any(a == truth for _, a in answers), n_answered=len(answers), wall_s=round(wall, 1),
               out_tokens_total=sum(o["out_tokens"] for o in out), cost=round(sum(o["cost"] for o in out), 5), notes_chars=notes_len,
               agents=[{k: o[k] for k in ("status", "out_tokens", "cost", "turns", "dur")} for o in out])
    secret = dict(task=task["id"], effort=effort, N=n, given=[a for _, a in answers], voted=voted, texts=[o["text"] for o in out],
                  trace=dict(notes=notes_text, answers=raw_answers, events=[o["events"] for o in out], row=row))
    return row, secret


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--tasks", required=True, help="comma list depth:noise, e.g. 2:1,3:1.5")
    ap.add_argument("--efforts", default="low,medium,high"); ap.add_argument("--ns", default="1,2,4")
    ap.add_argument("--model", default="haiku"); ap.add_argument("--cap", type=float, default=5.0)
    ap.add_argument("--concurrency", type=int, default=6); ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--solo-efforts", default="", help="extra efforts run with N=1 only, after the main grid")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True); workroot = out / "work"; workroot.mkdir(exist_ok=True)
    tasks = []
    for k, spec in enumerate(args.tasks.split(",")):
        d, nz = spec.split(":"); seed = secrets.randbits(48)
        files, q, fmt, ans = make_task(seed, int(d), float(nz))
        tasks.append(dict(id=f"T{k:02d}", depth=int(d), noise=float(nz), seed=seed, files=files, answer=ans))
    efforts, ns = args.efforts.split(","), [int(x) for x in args.ns.split(",")]
    slots, state, lock = Slots(args.concurrency), State(args.cap), threading.Lock()
    secrets_out = []
    resf = open(out / "results.jsonl", "a")

    grid = [(e, n) for e in efforts for n in ns] + [(e, 1) for e in args.solo_efforts.split(",") if e]

    def worker(task):
        for e, n in grid:
            if True:
                if state.over(): return
                row, sec = run_swarm(task, e, n, args, slots, state, workroot)
                with lock:
                    resf.write(json.dumps(row) + "\n"); resf.flush(); secrets_out.append(sec)
                    print(f"[{time.strftime('%H:%M:%S')}] {row['task']} d{row['depth']} {e:<6} N={n} correct={row['correct']} "
                          f"out_tok={row['out_tokens_total']} cost=${row['cost']:.4f} total=${state.cost:.3f}", flush=True)

    ths = [threading.Thread(target=worker, args=(t,)) for t in tasks]
    [t.start() for t in ths]; [t.join() for t in ths]
    resf.close()
    # traces are written only now, after every agent has finished, so no agent can read another run's transcript
    for sec in secrets_out:
        tr = sec.pop("trace"); td = out / "traces" / f"{sec['task']}_{sec['effort']}_N{sec['N']}"; td.mkdir(parents=True, exist_ok=True)
        (td / "NOTES.md").write_text(tr["notes"]); json.dump(tr["answers"], open(td / "answers.json", "w"), indent=1)
        json.dump(dict(tr["row"], truth=next(t["answer"] for t in tasks if t["id"] == sec["task"]), voted=sec["voted"]), open(td / "meta.json", "w"), indent=1)
        for i, evs in enumerate(tr["events"]):
            with open(td / f"agent_{i}.jsonl", "w") as fh:
                for e in evs: fh.write(json.dumps(e) + "\n")
    json.dump(dict(tasks=[dict(id=t["id"], depth=t["depth"], noise=t["noise"], seed=t["seed"], answer=t["answer"]) for t in tasks],
                   runs=secrets_out, total_cost=state.cost), open(out / "reveal.json", "w"), indent=1)
    shutil.rmtree(workroot, ignore_errors=True)
    print(f"DONE total list-price cost ${state.cost:.3f}", flush=True)


if __name__ == "__main__":
    main()
