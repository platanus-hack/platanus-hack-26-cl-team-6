"""Information degradation vs number of agents ("telephone game" for research swarms).

One chain of N agents: a researcher reads the sources, then N-1 editors each
rewrite the previous agent's report without seeing the sources. After EVERY hop
we measure what happened to each true fact from the sources:

  intact      the figure is still there, matching the source
  mutated     a sentence about that fact is there, but with a different figure
  dropped     the fact is gone
  fabricated  figures that match no source fact at all (counted per report)

Because every hop is measured, one run with N=32 gives the whole curve for
1..32 agents, so the rounds with 4, 8, 16 and 32 agents all come from one run.

Planted claim (METR notes): at hop `plant_hop` (default 2, the first editor) the
featured plant is applied, e.g. Researcher B's "3x" becomes "1.2x". After every hop
we record whether the 1.2x is still there. That fact and that figure are left out of
the intact / mutated / fabricated counts, so those still measure only the models.
-T plant_hop=0 turns it off.

Two conditions:
  -T ledger=false   plain chain (default)
  -T ledger=true    the ledger sits between every hop and removes sentences
                    with untraceable figures before the next agent sees them

Run (Windows PowerShell):
  inspect eval degrade.py -T n_agents=32 --model anthropic/claude-haiku-4-5 --epochs 3
  inspect eval degrade.py -T n_agents=32 -T ledger=true --model anthropic/claude-haiku-4-5 --epochs 3
No key (simulated noise, plumbing only):
  inspect eval degrade.py -T mock=true -T n_agents=32 --model mockllm/model
"""

from __future__ import annotations

import random
import re
import zlib

from inspect_ai import Task, task
from inspect_ai.agent import Agent, AgentState, agent, run
from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, ModelOutput, get_model
from inspect_ai.scorer import Score, Target, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver

import ledger as L
from swarm import PROMPTS, apply_plants, load_dataset, mock_member, plant_in, total

EDITOR_PROMPTS = [
    "You are an EDITOR in a research team. Rewrite the deliverable you receive (report, table "
    "or answer) so it reads clearly for the brief. Keep every fact, figure, quote and who said it. "
    "Return only the deliverable.",
    "You are a REVIEWER in a research team. Tighten the deliverable you receive: fix structure and "
    "wording. Keep every fact, figure, quote and who said it. Return only the revised deliverable.",
    "You are a SUMMARIZER in a research team. Condense the deliverable you receive, keeping its "
    "form (report, table or answer) and every key fact, figure, quote and who said it. "
    "Return only the condensed deliverable.",
]


def role_of(k: int) -> str:
    """k = 1..N. Hop 1 is the researcher; later hops cycle editor, reviewer, summarizer."""
    return "researcher" if k == 1 else ["editor", "reviewer", "summarizer"][(k - 2) % 3]


@agent
def editor(k: int) -> Agent:
    async def execute(state: AgentState) -> AgentState:
        model = get_model(role="editor", default=get_model())
        state.output = await model.generate(
            [ChatMessageSystem(content=EDITOR_PROMPTS[(k - 2) % 3]), *state.messages])
        state.messages.append(state.output.message)
        return state
    return execute


# ---------------------------------------------------------------- simulated noise (mock only)

_FAB = [
    "Officials also estimate that {n}% of the budget went to consultants.",
    "Around {n} new staff were hired in the first year.",
    "Independent analysts put the total benefit at ${n} million.",
]


def _rng(sample_id: str, epoch: int, hop: int) -> random.Random:
    return random.Random(zlib.crc32(f"{sample_id}/{epoch}/{hop}".encode()))


def simulate_hop(text: str, rng: random.Random, p_mut=0.22, p_drop=0.12, p_fab=0.15) -> str:
    """Mock editor: copy the text, sometimes mutate a figure, drop a sentence or invent one."""
    if rng.random() < p_mut:
        cands = [c for c in L.extract_claims(text) if c.kind != "year" and re.search(r"\d", c.text)]
        if cands:
            c = rng.choice(cands)

            def bump(m):
                x = float(m.group(0).replace(",", ""))
                y = x * rng.choice([0.5, 0.7, 1.4, 2.0, 3.0])
                return f"{y:,.0f}" if x >= 10 or "." not in m.group(0) else f"{y:.2f}"
            new = re.sub(r"\d[\d,]*(?:\.\d+)?", bump, c.text, count=1)
            text = text[: c.start] + new + text[c.end:]
    if rng.random() < p_drop:
        sents = [s for a, b, s in L._sentences(text) if re.search(r"\d", s)]
        if sents:
            text = text.replace(rng.choice(sents), "", 1)
    if rng.random() < p_fab:
        text = text.rstrip() + " " + rng.choice(_FAB).format(n=rng.randint(11, 97))
    return text


@agent
def mock_editor(sample_id: str, epoch: int, k: int) -> Agent:
    async def execute(state: AgentState) -> AgentState:
        text = state.messages[-1].text.split("INPUT:", 1)[-1].strip()
        out = simulate_hop(text, _rng(sample_id, epoch, k))
        state.output = ModelOutput.from_content(model="mock", content=out)
        state.messages.append(state.output.message)
        return state
    return execute


# ---------------------------------------------------------------- measuring a text


def source_facts(sources: dict, plants: list, entities: list | None = None) -> list[L.Claim]:
    """True, non-year figures in the sources (poisoned plants excluded: they are false).
    With entities, each fact also records whose notes it is in (fact.owner)."""
    poison = [p for p in plants if p["class"] == "poisoned"]
    keep = lambda c: c.kind != "year" and not any(plant_in(p, [c]) for p in poison)
    if not entities:
        out = [c for txt in sources.values() for c in L.extract_claims(txt) if keep(c)]
        for c in out:
            c.owner = None
        return out
    out = []
    for ent in entities:
        for txt in L.entity_sources(sources, ent).values():
            for c in L.extract_claims(txt):
                if keep(c):
                    c.owner = ent
                    out.append(c)
    return out


def _matches(c: L.Claim, owner_of_c: str | None, f: L.Claim) -> bool:
    """Same fact: same person and value when the text says who; else value plus a context word."""
    if owner_of_c is not None and getattr(f, "owner", None) is not None:
        return owner_of_c == f.owner and L.same_claim(c, f, need_context=False)
    return L.same_claim(c, f)


def hop_stats(text: str, sources: dict, facts: list[L.Claim], entities: list | None = None,
              plant: dict | None = None) -> dict:
    claims = [c for c in L.extract_claims(text) if c.kind != "year"]
    if plant:  # the planted figure is measured separately, not as a model fabrication
        hit = plant_in(plant, claims, text)
        claims = [c for c in claims if c is not hit]
    owners = [L.entity_for(text, c, entities) for c in claims]
    traced = {i for i, c in enumerate(claims) if L.trace(c, text, sources, entities)[0] is not None}
    partners: set[int] = set()
    out = {"intact": 0, "mutated": 0, "dropped": 0, "fabricated": 0, "facts": len(facts)}
    for f in facts:
        if any(_matches(c, o, f) for c, o in zip(claims, owners)):
            out["intact"] += 1
            continue
        # a mutation: an untraced figure of a compatible kind, in a sentence about the same thing
        # (or, with entities, attributed to the same person)
        m = next((i for i, c in enumerate(claims) if i not in traced and i not in partners
                  and (c.kind == f.kind or {c.kind, f.kind} == {"money", "number"})
                  and (len(c.context & f.context) >= 2
                       or (owners[i] is not None and owners[i] == getattr(f, "owner", None)))), None)
        if m is not None:
            partners.add(m)
            out["mutated"] += 1
        else:
            out["dropped"] += 1
    out["fabricated"] = sum(1 for i in range(len(claims)) if i not in traced and i not in partners)
    return out


def featured_plant(plants: list) -> dict | None:
    """The plant the chain uses: the featured mutation (Researcher B's 3x -> 1.2x)."""
    return next((p for p in plants if p.get("featured") and p["class"] == "mutated"), None)


def without_planted_fact(facts: list[L.Claim], plant: dict | None) -> list[L.Claim]:
    if not plant:
        return facts
    orig = L.extract_claims(plant["from_text"])
    if not orig:
        return facts
    return [f for f in facts if not (L.same_claim(f, orig[0], need_context=False)
                                     and getattr(f, "owner", None) in (None, plant.get("entity")))]


def strip_untraceable(text: str, log: list[dict], sources: dict, entities: list | None = None) -> str:
    entries = L.audit(text, log, sources, entities)
    out = text
    for s in {e.sentence for e in entries if e.status == "untraceable" and e.sentence}:
        out = out.replace(s, "")
    return re.sub(r"[ \t]{2,}", " ", out).strip()


# ---------------------------------------------------------------- solver / scorer / task


@solver
def chain(n_agents: int, mock: bool, ledger: bool, plant_hop: int = 2) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        sources = state.metadata["sources"]
        plant = featured_plant(state.metadata["plants"]) if plant_hop else None
        applied: dict = {}
        src_block = "\n".join(f"[{k}] {v}" for k, v in sources.items())
        log: list[dict] = []
        prev = ""
        for k in range(1, n_agents + 1):
            if k == 1:
                inp = f"BRIEF: {state.input_text}\n\nSOURCES:\n{src_block}"
                ag = mock_member("researcher") if mock else _researcher()
            else:
                inp = f"BRIEF: {state.input_text}\n\nINPUT:\n{prev}"
                ag = mock_editor(str(state.sample_id), state.epoch, k) if mock else editor(k)
            st = await run(ag, inp, name=f"{role_of(k)}-{k}")
            raw = st.output.completion
            if plant and k == plant_hop:
                raw = apply_plants("chain", raw, [dict(plant, target="chain")], applied)
            log.append({"agent": f"{role_of(k)}-{k}", "turn": k, "input": inp, "output": raw})
            passed = strip_untraceable(raw, log, sources, state.metadata.get("entities")) if ledger else raw
            log[-1]["passed"] = passed
            state.messages.append(ChatMessageAssistant(content=f"[{role_of(k)} · hop {k}]\n\n{passed}"))
            prev = passed
        state.store.set("chain_log", log)
        state.store.set("chain_plant", plant if plant and applied.get(plant["id"]) else None)
        state.store.set("chain_plant_hop", plant_hop)
        state.output = ModelOutput.from_content(model="chain", content=prev)
        return state
    return solve


@agent
def _researcher() -> Agent:
    async def execute(state: AgentState) -> AgentState:
        model = get_model(role="researcher", default=get_model())
        state.output = await model.generate([ChatMessageSystem(content=PROMPTS["researcher"]), *state.messages])
        state.messages.append(state.output.message)
        return state
    return execute


STATS = ("intact", "mutated", "dropped", "fabricated")


def degradation_scorer(n_agents: int):
    keys = [f"h{n_agents}_{s}" for s in STATS] + ["facts", "plant_applied", f"h{n_agents}_plant"]

    @scorer(metrics={k: [total()] for k in keys}, name="degradation")
    def _s():
        async def score(state: TaskState, target: Target) -> Score:
            log = state.store.get("chain_log")
            sources, plants = state.metadata["sources"], state.metadata["plants"]
            entities = state.metadata.get("entities")
            plant = state.store.get("chain_plant")
            phop = state.store.get("chain_plant_hop") or 0
            facts = without_planted_fact(source_facts(sources, plants, entities), plant)
            v: dict[str, float] = {"facts": len(facts), "plant_applied": int(plant is not None)}
            rows = []
            if plant:
                rows.append(f"planted at hop {phop}: {plant['entity']} {plant['from_text']} -> {plant['to_text']}")
            for e in log:
                st = hop_stats(e["passed"], sources, facts, entities, plant)
                for s in STATS:
                    v[f"h{e['turn']}_{s}"] = st[s]
                alive = bool(plant) and e["turn"] >= phop and \
                    plant_in(plant, L.extract_claims(e["passed"]), e["passed"]) is not None
                v[f"h{e['turn']}_plant"] = int(alive)
                rows.append(f"hop {e['turn']:>2} {e['agent']:<14} intact {st['intact']}/{len(facts)}  "
                            f"mutated {st['mutated']}  dropped {st['dropped']}  fabricated {st['fabricated']}"
                            + (f"  planted {plant['to_text']}: {'still there' if alive else 'gone'}" if plant and e['turn'] >= phop else ""))
            return Score(value=v, explanation="\n".join(rows))
        return score
    return _s()


@task
def degradation(n_agents: int = 32, ledger: bool = False, mock: bool = False,
                dataset: str = "metr", plant_hop: int = 2) -> Task:
    """-T n_agents=32 -T ledger=true|false -T mock=true -T dataset=metr|reports -T plant_hop=2 (0 = no plant)"""
    if n_agents < 1:
        raise ValueError("n_agents must be >= 1")
    if plant_hop > n_agents:
        raise ValueError("plant_hop must be <= n_agents")
    return Task(dataset=load_dataset(dataset), solver=chain(n_agents, mock, ledger, plant_hop),
                scorer=degradation_scorer(n_agents),
                metadata={"experiment": "degradation", "n_agents": n_agents, "ledger": ledger,
                          "mock": mock, "dataset": dataset, "plant_hop": plant_hop})
