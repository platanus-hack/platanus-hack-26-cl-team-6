"""Lambda experiment, v2: an 8-kernel ML optimisation suite.

Why v2: in v1 (one attention kernel) every config with >= 4 experiments hit the
same ~4.6x ceiling, so lambda was unidentifiable. Here:
  * there are 8 kernels (attention, layernorm, softmax-xent, depthwise conv1d,
    top-k, pairwise distances, segment sum, EMA scan), so the ceiling is far higher;
  * each experiment submits ONE kernel, so total progress needs many experiments,
    and work can be split across agents (or duplicated: stepping on toes);
  * the team's score is the sum over kernels of log2(speedup) of its best
    version of each kernel ("merge the best version of each file"), and those
    best versions are re-timed fresh at the end, to remove winner's-curse bias
    from picking the luckiest noisy timing.

Run:
    inspect eval lambda_task2.py --model anthropic/claude-haiku-5-5 --epochs 5 -T combine=best_of
    inspect eval lambda_task2.py --model anthropic/claude-haiku-5-5 --epochs 5 -T combine=shared
    python fit_lambda.py logs/<file>.eval --plot out.png
"""

from __future__ import annotations

import json
import pathlib
import random
import sys
import tempfile
import zlib

import anyio

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, execute_tools, get_model
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.tool import tool
from inspect_ai.util import concurrency, subprocess

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from kernels import BASELINES, KERNELS  # noqa: E402

HARNESS = HERE / "harness2.py"

DESIGNS = {
    "core": sorted({
        (1, 1), (1, 2), (1, 4), (1, 8), (1, 16), (1, 32),   # duration curve
        (2, 8), (4, 4), (8, 2), (16, 1),                     # iso-compute, total 16
        (2, 2), (4, 2),                                      # swarm line at b=2 (with 8x2)
        (2, 1), (4, 1), (8, 1),                              # swarm line at b=1 (with 16x1)
    }),
    "isocompute": [(1, 16), (2, 8), (4, 4), (8, 2), (16, 1)],
    "smoke": [(1, 2), (2, 1)],
}

SYSTEM = """You are an expert performance engineer doing ML-systems research.
You optimise numpy kernels. You can only test ideas through the `evaluate`
tool, and every call costs one unit of a strictly limited experiment budget,
so think carefully before each call."""

PROMPT = """Make these {n_k} numpy ML kernels as fast as possible on CPU.

Scoring: for each kernel, your team's best correct version earns
log2(speedup over its baseline) (minimum 0). The team's score is the SUM over
all kernels. So improving a kernel nobody has improved yet is usually worth
more than squeezing an already-fast one.

Rules
- Each `evaluate` call submits ONE kernel: give the kernel name and a complete
  Python module defining a function with that same name and signature.
- numpy only. BLAS runs single-threaded; threading, multiprocessing, scipy,
  numba, ctypes etc. are forbidden.
- Inputs are float64 (ints where stated), fresh random values on every call, with the
  shapes used in the benchmark: {shapes}.
- Outputs must match the exact result to rtol=1e-3 (lower precision internally is fine).

Budget: you have {budget} for `evaluate`. When it is spent you are done.{team_note}

The baselines (you are timed against these):

{baselines}"""

SHAPES = ("attention q,k,v (1,4,512,64); layernorm x (8192,256); xent logits (2048,1000), "
          "labels (2048,); conv1d x (256,4096), w (256,32); topk x (4096,1024), k=16; "
          "sqdist a,b (1024,64); segsum values (8_000_000,), n_seg 200_000; ema x (64,8192)")

TEAM_SHARED = """

You are one of {n} agents working on this in parallel as a team. The free
`leaderboard` tool shows the team's current best score per kernel and who got
it; `leaderboard(kernel=...)` shows that best code. Coordinate through it:
avoid duplicating work, and build on teammates' best versions."""

TEAM_INDEPENDENT = """

(Other agents are working on the same suite independently; you cannot see
their work. The team keeps the best version of each kernel from anyone.)"""


class Board:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def add(self, agent: int, code: str, res: dict) -> None:
        self.entries.append({"agent": agent, "code": code, **res})

    def best(self, kernel: str) -> dict | None:
        ok = [e for e in self.entries if e["kernel"] == kernel and e["correct"]]
        return max(ok, key=lambda e: e["score"]) if ok else None

    def total(self, agent: int | None = None) -> float:
        tot = 0.0
        for k in KERNELS:
            ok = [e["score"] for e in self.entries if e["kernel"] == k and e["correct"] and (agent is None or e["agent"] == agent)]
            tot += max(ok, default=0.0)
        return tot

    def table(self) -> str:
        rows = []
        for k in KERNELS:
            b = self.best(k)
            n = sum(e["kernel"] == k for e in self.entries)
            rows.append(f"{k:10s} " + (f"best {b['score']:.2f} ({b['speedup']:.1f}x, agent {b['agent']})" if b else "not improved yet") + f", {n} attempts")
        return "\n".join(rows) + f"\nTEAM TOTAL {self.total():.2f}"


async def run_harness(kernel: str, code: str) -> dict:
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "candidate.py"
        p.write_text(code, encoding="utf-8")
        async with concurrency("kernel-timing", 1):
            r = await subprocess([sys.executable, str(HARNESS), kernel, str(p)], timeout=180)
    if not r.success:
        return {"kernel": kernel, "correct": False, "speedup": 0.0, "score": 0.0, "error": (r.stderr or "timeout/crash")[-1500:]}
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"kernel": kernel, "correct": False, "speedup": 0.0, "score": 0.0, "error": "harness output unparseable"}


def make_tools(agent: int, board: Board, budget: dict, shared: bool):
    @tool
    def evaluate():
        async def execute(kernel: str, code: str) -> str:
            """Benchmark one candidate kernel. Costs one experiment.

            Args:
                kernel: Kernel name, one of attention, layernorm, xent, conv1d, topk, sqdist, segsum, ema.
                code: Full Python module defining a function with that name.
            """
            if budget["left"] <= 0:
                return "Experiment budget exhausted. Stop now."
            budget["left"] -= 1
            res = await run_harness(kernel, code)
            if res.get("kernel") in KERNELS:
                board.add(agent, code, res)
            keep = {k: res.get(k) for k in ("kernel", "correct", "speedup", "score", "error", "candidate_ms", "baseline_ms")}
            return json.dumps(keep) + f"\nYour own total so far: {board.total(agent):.2f}. Experiments left: {budget['left']}."

        return execute

    @tool
    def leaderboard():
        async def execute(kernel: str = "") -> str:
            """Team progress (free). With no kernel: best score per kernel. With a kernel name: that best code.

            Args:
                kernel: Optional kernel name to see the team's best code for it.
            """
            if not kernel:
                return board.table()
            b = board.best(kernel)
            return f"No correct {kernel} yet." if b is None else f"{kernel} best {b['score']:.2f} by agent {b['agent']}:\n```python\n{b['code']}\n```"

        return execute

    return [evaluate(), leaderboard()] if shared else [evaluate()]


async def run_agent(agent: int, n: int, b: int, board: Board, combine: str, seed: int) -> dict:
    model = get_model()
    shared = combine == "shared" and n > 1
    budget = {"left": b}
    tools = make_tools(agent, board, budget, shared)
    order = KERNELS[:]
    random.Random(seed * 1000 + agent).shuffle(order)  # per-agent presentation order (cheap diversity)
    note = TEAM_SHARED.format(n=n) if shared else (TEAM_INDEPENDENT if n > 1 else "")
    prompt = PROMPT.format(
        n_k=len(KERNELS), shapes=SHAPES, budget=f"{b} experiment{'s' if b > 1 else ''}", team_note=note,
        baselines="\n\n".join(f"### {k}\n```python\n{BASELINES[k]}```" for k in order),
    )
    messages = [ChatMessageSystem(content=SYSTEM), ChatMessageUser(content=prompt)]
    nudges, out_tokens = 0, 0
    for _ in range(3 * b + 6):
        out = await model.generate(messages, tools=tools)
        if out.usage:
            out_tokens += out.usage.output_tokens
        messages.append(out.message)
        if out.message.tool_calls:
            messages.extend((await execute_tools(messages, tools)).messages)
        else:
            nudges += 1
            if nudges > 2:
                break
            messages.append(ChatMessageUser(content="Use the evaluate tool to submit a kernel. Only evaluated kernels count."))
        if budget["left"] <= 0:
            break
    return {"agent": agent, "evals_used": b - budget["left"], "output_tokens": out_tokens, "own_total": board.total(agent)}


@solver
def swarm(combine: str = "best_of"):
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        n, b = state.metadata["n_agents"], state.metadata["budget_per_agent"]
        seed = zlib.crc32(f"{state.sample_id}-{state.epoch}".encode()) % 10_000
        board = Board()
        results: list = [None] * n

        async def one(i: int) -> None:
            results[i] = await run_agent(i, n, b, board, combine, seed)

        async with anyio.create_task_group() as tg:
            for i in range(n):
                tg.start_soon(one, i)
        # Re-time the team's best version of each kernel (removes winner's-curse bias).
        final = {}
        for k in KERNELS:
            best = board.best(k)
            if best is None:
                final[k] = 0.0
            else:
                r = await run_harness(k, best["code"])
                final[k] = float(r["score"]) if r.get("correct") else 0.0
        state.store.set("final", final)
        state.store.set("selected_total", board.total())
        state.store.set("agents", results)
        state.store.set("attempts", {k: sum(e["kernel"] == k for e in board.entries) for k in KERNELS})
        return state

    return solve


@scorer(metrics=[mean(), stderr()])
def swarm_score():
    async def score(state: TaskState, target: Target) -> Score:
        md, final = state.metadata, state.store.get("final") or {}
        agents = state.store.get("agents") or []
        return Score(
            value=float(sum(final.values())),
            metadata={
                "n_agents": md["n_agents"], "budget_per_agent": md["budget_per_agent"],
                "total_budget": md["n_agents"] * md["budget_per_agent"],
                "per_kernel": final, "selected_total": state.store.get("selected_total"),
                "attempts": state.store.get("attempts"),
                "kernels_improved": sum(v > 0 for v in final.values()),
                "evals_used": sum(a["evals_used"] for a in agents if a),
                "output_tokens": sum(a["output_tokens"] for a in agents if a),
            },
        )

    return score


@task
def lambda_suite(design: str = "core", combine: str = "best_of") -> Task:
    samples = [
        Sample(id=f"N{n:02d}_b{b:02d}", input=f"{n} agents x {b} experiments",
               metadata={"n_agents": n, "budget_per_agent": b, "combine": combine})
        for n, b in DESIGNS[design]
    ]
    return Task(dataset=samples, solver=swarm(combine), scorer=swarm_score())
