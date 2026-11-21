"""Claim ledger: fixed rules, no LLM.

Extracts numeric claims (percents, money, counts, years, paraphrases like
"one in eight") from text, traces each claim in a final report back to a
source document, and for anything it can't trace, names the agent and turn
where the claim first appeared in the swarm's message log.

Pure Python so it can be unit tested and run outside Inspect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------- numbers

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_ORDINAL_DENOM = {
    "half": 2, "halves": 2, "third": 3, "thirds": 3, "quarter": 4,
    "quarters": 4, "fifth": 5, "fifths": 5, "sixth": 6, "tenth": 10,
    "tenths": 10,
}
_SCALE = {
    "thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "mn": 1e6,
    "billion": 1e9, "bn": 1e9, "b": 1e9, "trillion": 1e12,
}
_HEDGES = (
    "about", "around", "roughly", "approximately", "approx", "nearly",
    "almost", "some", "close to", "more than", "over", "under", "less than",
    "up to", "at least", "an estimated", "estimated", "~", ">", "≥", "greater than",
)
_MULT_WORDS = {"double": 2, "doubled": 2, "doubles": 2, "doubling": 2, "twice": 2,
               "triple": 3, "tripled": 3, "triples": 3, "tripling": 3, "thrice": 3,
               "quadruple": 4, "quadrupled": 4, "quadruples": 4}

_WORDNUM = (
    r"(?:(?:" + "|".join(_TENS) + r")(?:[-\s](?:" + "|".join(k for k in _UNITS if k != "zero") + r"))?"
    r"|" + "|".join(sorted(_UNITS, key=len, reverse=True)) + r")"
)
_DIGITS = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_NUM = rf"(?:{_DIGITS}|{_WORDNUM})"
_SCALE_RE = r"(?:\s*(?:thousand|million|billion|trillion|bn|mn|k|m|b)\b)?"

_PATTERNS = [
    # "one in eight", "1 in 5", "nine out of ten"
    ("ratio", re.compile(rf"\b(?P<a>{_NUM})\s+(?:in|out of)\s+(?P<b>{_NUM})\b", re.I)),
    # "two thirds", "a quarter", "half"
    ("fraction", re.compile(
        rf"\b(?P<a>a|an|one|two|three|{_NUM})?[\s-]*(?P<d>half|halves|thirds?|quarters?|fifths?|sixth|tenths?)\b(?!\s+(?:of\s+the\s+)?(?:year|century|decade|time))",
        re.I)),
    # "3x", "1.2x", "2X speedup", "3×", "four times faster", "10-fold"
    ("multiplier", re.compile(
        rf"(?<![\w.])(?P<n>{_NUM})\s?(?:[x×](?![a-z0-9])|times\b|-?fold\b)", re.I)),
    # "doubled", "twice as fast", "tripled"
    ("multword", re.compile(r"\b(?P<w>" + "|".join(sorted(_MULT_WORDS, key=len, reverse=True)) + r")\b", re.I)),
    # "$4.5 million", "US$310", "180 million dollars", "41%", "41 percent", "fourteen per cent"
    ("number", re.compile(
        rf"(?P<cur>(?:US)?\$|USD\s?|CLP\s?)?(?P<n>{_NUM})(?P<scale>{_SCALE_RE})"
        rf"(?P<pct>\s*(?:%|percent\b|per\s?cent\b|percentage points?\b|pp\b))?"
        rf"(?P<cur2>\s*(?:dollars|usd)\b)?",
        re.I)),
]


def _word_to_num(s: str) -> float | None:
    s = s.lower().replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        pass
    if s in ("a", "an"):
        return 1.0
    parts = re.split(r"[-\s]+", s)
    total = 0
    for p in parts:
        if p in _UNITS:
            total += _UNITS[p]
        elif p in _TENS:
            total += _TENS[p]
        else:
            return None
    return float(total)


def _granularity(raw: str) -> float:
    raw = raw.replace(",", "")
    if re.fullmatch(r"\d+\.\d+", raw):
        return 10 ** -len(raw.split(".")[1])
    return 1.0


# ---------------------------------------------------------------- claims

STOP = set("""a an the of in on at to for from by with and or but is are was were be been
has have had it its this that these those as than then which who whom whose
their there they them we our you your he she his her not no per cent percent
about around roughly approximately nearly almost some over under more less up
least estimated between during after before since into across each one two
all also only just will would could should may might can year years""".split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    return {_stem(w) for w in words if w not in STOP and len(w) > 2}


@dataclass
class Claim:
    text: str          # the matched span, e.g. "about one in eight"
    value: float       # normalised value (percents as 0-100)
    kind: str          # percent | money | year | number | multiplier
    tol: float         # absolute tolerance for matching
    start: int
    end: int
    sentence: str
    context: set[str] = field(default_factory=set)

    def key(self) -> str:
        return f"{self.kind}:{self.value:g}"


def _sentences(text: str) -> list[tuple[int, int, str]]:
    out, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z\[\-*•\d“\"])|\n\s*\n|\n(?=\s*[-*•#|])|\s*(?<!\\)\|\s*(?=[^\n]*\|)|\s*<br\s*/?>\s*|\s*(?<!\\)\|[ \t]*(?=\n|$)", text):
        out.append((start, m.start(), text[start:m.start()]))
        start = m.end()
    out.append((start, len(text), text[start:]))
    return [s for s in out if s[2].strip()]


def extract_claims(text: str) -> list[Claim]:
    """Find numeric claims in text. Ignores list numbering and source tags like [S1]."""
    claims: list[Claim] = []
    taken: list[tuple[int, int]] = []
    sents = _sentences(text)

    def sentence_for(pos: int) -> str:
        for a, b, s in sents:
            if a <= pos <= b:
                return s
        return ""

    def overlaps(a: int, b: int) -> bool:
        return any(a < y and x < b for x, y in taken)

    for kind_hint, pat in _PATTERNS:
        for m in pat.finditer(text):
            a, b = m.start(), m.end()
            span = m.group(0).strip(" -")
            if not span or overlaps(a, b):
                continue
            # skip "[S1]", list numbering "1." at line start, and "n=140"-style tags stay
            before = text[max(0, a - 2):a]
            if re.search(r"[A-Za-z\[]$", before) and kind_hint == "number" and not m.group("cur"):
                continue
            # skip citation locators: "p.2", "pp. 4-5", "table 3", "figure 2", "section 4"
            if kind_hint == "number" and not m.group("cur") and re.search(
                    r"(?:\bpp?|\bpg|\bpage|\btable|\bfig|\bfigure|\bsection|§)\.?\s*$", text[max(0, a - 10):a], re.I):
                continue
            # skip model names and versions: "Opus 4.5", "Opus-4.6", "Model 2", "GPT-5"
            if kind_hint in ("number", "multiplier") and not (kind_hint == "number" and m.group("cur")) and re.search(
                    r"(?:opus|sonnet|haiku|claude|gpt|gemini|model|version|v)[\s-]*$", text[max(0, a - 10):a], re.I):
                continue
            # skip enumerations "(1)", "(2)"
            if kind_hint == "number" and text[a - 1:a] == "(" and text[b:b + 1] == ")":
                continue
            line_start = text.rfind("\n", 0, a) + 1
            if kind_hint == "number" and re.fullmatch(r"\s*\d+", text[line_start:b]) and text[b:b + 1] in ".)":
                continue

            pre = text[max(0, a - 16):a].lower()
            hedged = any(pre.rstrip().endswith(h) for h in _HEDGES)

            if kind_hint == "multword":
                value, kind, gran = float(_MULT_WORDS[m.group("w").lower()]), "multiplier", 1.0
                hedged = False
            elif kind_hint == "multiplier":
                n = _word_to_num(m.group("n"))
                if not n:
                    continue
                value, kind, gran = n, "multiplier", 1.0
            elif kind_hint == "ratio":
                x, y = _word_to_num(m.group("a")), _word_to_num(m.group("b"))
                if not x or not y or x >= y:
                    continue
                value, kind, hedged = 100 * x / y, "percent", True
                gran = 1.0
            elif kind_hint == "fraction":
                num = _word_to_num(m.group("a") or "one")
                den = _ORDINAL_DENOM[m.group("d").lower()]
                if num is None or num >= den:
                    continue
                value, kind, hedged, gran = 100 * num / den, "percent", True, 1.0
            else:
                n = _word_to_num(m.group("n"))
                if n is None:
                    continue
                if not re.match(r"\d", m.group("n")) and not (m.group("pct") or m.group("cur") or m.group("scale").strip()):
                    # bare number words ("three plants") are too noisy; keep only >= 10
                    if n < 10:
                        continue
                scale = _SCALE.get(m.group("scale").strip().lower(), 1.0) if m.group("scale").strip() else 1.0
                gran = _granularity(m.group("n")) * scale
                value = n * scale
                # "15-20%": the low end of a range is a percent too; "2-3x" a multiplier
                tail = text[b:b + 16]
                range_pct = re.match(r"\s*(?:-|–|to)\s*[\d.]+\s*(?:%|percent|per\s?cent)", tail, re.I)
                range_mult = re.match(r"\s*(?:-|–|to)\s*[\d.]+\s?(?:[x×](?![a-z0-9])|times\b)", tail, re.I)
                if m.group("pct") or range_pct:
                    kind = "percent"
                elif range_mult:
                    kind = "multiplier"
                elif m.group("cur") or m.group("cur2"):
                    kind = "money"
                elif scale == 1.0 and re.fullmatch(r"(19|20)\d\d", m.group("n")):
                    kind = "year"
                else:
                    kind = "number"
            tol = gran / 2 + 1e-9
            if kind == "multiplier":
                # 2x vs 2.5x must not match: multipliers get a relative tolerance
                tol = 0.05 * abs(value) + 1e-9
            if hedged and kind != "year":
                tol = max(tol, 0.08 * abs(value))
            sent = sentence_for(a)
            taken.append((a, b))
            claims.append(Claim(span, value, kind, tol, a, b, sent, _keywords(sent)))
    claims.sort(key=lambda c: c.start)
    return claims


def same_claim(c: Claim, d: Claim, need_context: bool = True, loose: bool = False) -> bool:
    """Value and kind match within tolerance, plus at least one shared context word."""
    kinds = {c.kind, d.kind}
    if c.kind != d.kind and kinds != {"money", "number"}:
        return False
    tol = max(c.tol, d.tol)
    if loose:
        tol = max(tol, 0.10 * abs(c.value))
    if abs(c.value - d.value) > tol:
        return False
    return (not need_context) or bool(c.context & d.context)


# ---------------------------------------------------------------- tracing

@dataclass
class LedgerEntry:
    claim: str
    value: float
    kind: str
    sentence: str
    status: str                 # "traced" | "untraceable"
    source: str | None = None   # source doc id it traced to
    origin_agent: str | None = None
    origin_turn: int | None = None
    entity: str | None = None   # person the sentence is about, if it names exactly one


def first_appearance(claim: Claim, log: list[dict], entity: str | None = None,
                     entities: list[str] | None = None) -> tuple[str | None, int | None]:
    """Earliest agent turn whose output contains this claim (about the same person, if one)."""
    for entry in log:
        out = entry["output"]
        for d in extract_claims(out):
            if entity:
                if entity_for(out, d, entities) == entity and same_claim(claim, d, need_context=False):
                    return entry["agent"], entry["turn"]
            elif same_claim(claim, d):
                return entry["agent"], entry["turn"]
    return None, None


# ---------------------------------------------------------------- attribution
#
# With `entities` (e.g. ["Researcher A", "Researcher B"]), a figure in a sentence that
# names exactly one person is traced only against that person's part of the sources:
# the "## Researcher B" sections of each source doc. "2x" is in Researcher A's notes,
# so "Researcher K said 2x" must not pass just because some source contains a 2x.


def _names_in(text: str, entities: list[str]) -> list[str]:
    return [n for n in entities if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", text)]


def entity_for(report: str, c: "Claim", entities: list[str] | None) -> str | None:
    """The one person this claim is about: named in its sentence, else in its line (a table row)."""
    if not entities:
        return None
    names = _names_in(c.sentence, entities)
    if len(names) == 1:
        return names[0]
    if names:
        return None
    a = report.rfind("\n", 0, c.start) + 1
    b = report.find("\n", c.end)
    names = _names_in(report[a: b if b >= 0 else len(report)], entities)
    return names[0] if len(names) == 1 else None


def entity_sources(sources: dict[str, str], name: str) -> dict[str, str]:
    """Each source doc cut down to its sections whose '## ' heading names this person."""
    out = {}
    for sid, txt in sources.items():
        parts = re.split(r"(?m)^(?=##\s)", txt)
        mine = [p for p in parts if p.startswith("##") and _names_in(p.split("\n", 1)[0], [name])]
        if mine:
            out[sid] = "\n".join(mine)
    return out


def trace(c: "Claim", report: str, sources: dict[str, str], entities: list[str] | None = None,
          loose: bool = False, src_claims: dict | None = None) -> tuple[str | None, str | None]:
    """(source id the claim traces to or None, entity it was scoped to or None)."""
    ent = entity_for(report, c, entities)
    if ent:
        scoped = entity_sources(sources, ent)
        for sid, txt in scoped.items():
            # inside one person's notes the value alone is strong evidence: no context word needed
            if any(same_claim(c, d, need_context=False, loose=loose) for d in extract_claims(txt)):
                return sid, ent
        return None, ent
    src_claims = src_claims or {sid: extract_claims(txt) for sid, txt in sources.items()}
    for sid, cs in src_claims.items():
        if any(same_claim(c, d, loose=loose) for d in cs):
            return sid, None
    return None, None


def audit(report: str, log: list[dict], sources: dict[str, str],
          entities: list[str] | None = None) -> list[LedgerEntry]:
    src_claims = {sid: extract_claims(txt) for sid, txt in sources.items()}
    entries = []
    for c in extract_claims(report):
        traced, ent = trace(c, report, sources, entities, src_claims=src_claims)
        if traced:
            entries.append(LedgerEntry(c.text, c.value, c.kind, c.sentence.strip(), "traced",
                                       source=traced, entity=ent))
        else:
            agent, turn = first_appearance(c, log, ent, entities)
            entries.append(LedgerEntry(c.text, c.value, c.kind, c.sentence.strip(), "untraceable",
                                       origin_agent=agent, origin_turn=turn, entity=ent))
    return entries


# ---------------------------------------------------------------- quotes
#
# A quoted passage of 5+ words must appear word for word (ignoring case, punctuation
# and "..." cuts) in the sources. Reported separately: it does not remove sentences.

_QUOTE_RE = re.compile(r"[“\"]([^”\"\n]{8,}?)[”\"]")


def _norm_words(t: str) -> list[str]:
    t = t.replace("’", "'").replace("‘", "'").lower()
    return re.findall(r"[a-z0-9']+(?:\.[0-9]+)?", t)


@dataclass
class QuoteEntry:
    quote: str
    status: str                  # "verbatim" | "not in sources"
    entity: str | None = None
    origin_agent: str | None = None
    origin_turn: int | None = None


def audit_quotes(report: str, log: list[dict], sources: dict[str, str],
                 entities: list[str] | None = None, min_words: int = 5) -> list[QuoteEntry]:
    out = []
    for m in _QUOTE_RE.finditer(report):
        q = m.group(1)
        if len(_norm_words(q)) < min_words:
            continue
        line_a = report.rfind("\n", 0, m.start()) + 1
        line_b = report.find("\n", m.end())
        line = report[line_a: line_b if line_b >= 0 else len(report)]
        names = _names_in(q, entities or []) or _names_in(line, entities or [])
        ent = names[0] if len(names) == 1 else None
        scope = entity_sources(sources, ent) if ent else sources
        hay = " " + " ".join(_norm_words(" ".join(scope.values()))) + " "
        frags = [f for f in re.split(r"\.\.\.|…|\[\s*\.\.\.\s*\]", q) if len(_norm_words(f)) >= 3]
        ok = bool(frags) and all(" " + " ".join(_norm_words(f)) + " " in hay for f in frags)
        if ok:
            out.append(QuoteEntry(q, "verbatim", ent))
            continue
        agent = turn = None
        key = " ".join(_norm_words(q))
        for e in log:
            if key in " ".join(_norm_words(e["output"])):
                agent, turn = e["agent"], e["turn"]
                break
        out.append(QuoteEntry(q, "not in sources", ent, agent, turn))
    return out


def filter_report(report: str, entries: list[LedgerEntry]) -> str:
    """Remove every sentence that carries an untraceable claim."""
    bad = {e.sentence for e in entries if e.status == "untraceable"}
    out = report
    for s in bad:
        if s:
            out = out.replace(s, "[removed by ledger: untraceable claim]")
    return out


def render(entries: list[LedgerEntry]) -> str:
    lines = ["| claim | status | source / origin |", "|---|---|---|"]
    for e in entries:
        where = e.source if e.status == "traced" else f"{e.origin_agent or 'unknown'} (turn {e.origin_turn})"
        if e.entity:
            where += f" · checked against {e.entity}'s notes only"
        flag = "OK" if e.status == "traced" else "**FLAG**"
        lines.append(f"| {e.claim} | {flag} | {where} |")
    return "\n".join(lines)


def as_dicts(entries: list) -> list[dict]:
    return [asdict(e) for e in entries]
