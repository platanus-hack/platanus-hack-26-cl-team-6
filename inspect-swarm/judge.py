"""LLM-judge baseline: the obvious way to check a report.

The judge sees the source documents, the final report, and a numbered list of
every figure the ledger's extractor found in the report (same claims, so the two
are scored on exactly the same items). For each figure it answers SUPPORTED or
UNSUPPORTED. Only the prompt building and parsing live here (pure Python, unit
tested); the Inspect scorer that calls the model is `llm_judge()` in swarm.py.
"""

from __future__ import annotations

import re

SYSTEM = "You are a careful fact-checker. You check reports against their source documents."

INSTRUCTIONS = (
    "Below are the source documents, a report written from them, and a numbered list of "
    "figures that appear in the report, each with the sentence it appears in.\n"
    "For each item, decide whether the source documents support that figure as it is used "
    "in the sentence. Answer with ONLY a JSON object that maps each item number to "
    '"SUPPORTED" or "UNSUPPORTED", for example {"1": "SUPPORTED", "2": "UNSUPPORTED"}.'
)


def build_prompt(sources: dict[str, str], report: str, claims: list) -> str:
    src = "\n\n".join(f"[{k}]\n{v}" for k, v in sources.items())
    items = "\n".join(
        f'{i}. Figure: {c.text} | Sentence: "{" ".join(c.sentence.split())}"'
        for i, c in enumerate(claims, start=1))
    return f"{INSTRUCTIONS}\n\nSOURCE DOCUMENTS:\n{src}\n\nREPORT:\n{report}\n\nITEMS:\n{items}"


_VERDICT = re.compile(r'"?(\d+)"?\s*[:=\-]\s*"?\s*(UNSUPPORTED|SUPPORTED|NOT SUPPORTED)\b', re.I)


def parse_verdicts(text: str, n: int) -> dict[int, bool | None]:
    """Map item number -> True if UNSUPPORTED (flagged), False if SUPPORTED, None if missing."""
    out: dict[int, bool | None] = {i: None for i in range(1, n + 1)}
    for num, verdict in _VERDICT.findall(text or ""):
        i = int(num)
        if i in out and out[i] is None:
            out[i] = verdict.upper() != "SUPPORTED"
    return out
