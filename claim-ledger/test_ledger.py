"""python -m pytest test_ledger.py -q"""

from ledger import audit, extract_claims, same_claim


def one(text):
    cs = extract_claims(text)
    assert len(cs) == 1, cs
    return cs[0]


def test_paraphrase_matches():
    src = one("About 12% of households rely on delivery trucks.")
    rep = one("Roughly one in eight households rely on trucks.")
    assert same_claim(src, rep)


def test_spelled_percent():
    assert one("Water use fell fourteen percent.").value == 14


def test_mutation_is_not_matched():
    assert not same_claim(one("Household water use fell 14%."), one("Household water use fell 41%."))


def test_scale_words():
    c = one("A fourth plant is budgeted at $180 million.")
    assert c.kind == "money" and c.value == 180e6


def test_source_tags_ignored():
    assert [c.text for c in extract_claims("Plants ran at 68% of capacity [S2].")] == ["68%"]


def test_origin_is_first_agent():
    sources = {"S1": "Household water use fell 14% in 2025."}
    log = [
        {"agent": "researcher", "turn": 1, "output": "- Household water use fell 14% [S1]"},
        {"agent": "writer", "turn": 2, "output": "Household water use fell 14%. The programme created 3,400 jobs."},
        {"agent": "reviewer", "turn": 3, "output": "Water use fell 14%. The programme created 3,400 local jobs."},
    ]
    entries = audit(log[-1]["output"], log, sources)
    flagged = [e for e in entries if e.status == "untraceable"]
    assert [(e.claim, e.origin_agent, e.origin_turn) for e in flagged] == [("3,400", "writer", 2)]


def test_citation_locators_ignored():
    text = "According to the Water Authority report (S1, p.2), the programme created 3,400 jobs (table 3)."
    assert [c.text for c in extract_claims(text)] == ["3,400"]


def test_fake_citation_is_flagged():
    sources = {"S1": "Household water use fell 14% between 2022 and 2025."}
    report = "According to the Water Authority report (S1, p.2), the programme created 3,400 jobs."
    log = [{"agent": "writer", "turn": 2, "output": report}]
    [e] = audit(report, log, sources)
    assert e.status == "untraceable" and e.origin_agent == "writer"


def test_judge_parse():
    from judge import parse_verdicts
    text = 'Here you go: {"1": "SUPPORTED", "2": "UNSUPPORTED", "3": "not supported"}'
    assert parse_verdicts(text, 4) == {1: False, 2: True, 3: True, 4: None}


def test_judge_prompt_lists_same_claims():
    from judge import build_prompt
    claims = extract_claims("Water use fell 14%. The programme created 3,400 jobs.")
    prompt = build_prompt({"S1": "Water use fell 14%."}, "report", claims)
    assert "1. Figure: 14%" in prompt and "2. Figure: 3,400" in prompt


def test_degradation_hop_stats():
    from degrade import hop_stats
    sources = {"S1": "Household water use fell 14% in 2025. Plants ran at 68% of design capacity."}
    facts = [c for c in extract_claims(sources["S1"]) if c.kind != "year"]
    text = "Household water use fell 41%. Officials say 3,400 jobs were created."
    st = hop_stats(text, sources, facts)
    assert (st["intact"], st["mutated"], st["dropped"], st["fabricated"]) == (0, 1, 1, 1)


# ---------------------------------------------------------------- METR interview notes

NOTES = {
    "METR": "METR interview notes\n\n## Researcher A\n“Could definitely endorse a greater than 2X speedup”\n\n"
            "## Researcher B\n“It is hard to see how I am not being 3x more productive.”",
    "ANTH": "Anthropic interview notes\n\n## Researcher K\n“IMO [hiring is] probably the biggest reason ...”",
}
PEOPLE = ["Researcher A", "Researcher B", "Researcher K"]


def test_multipliers():
    assert (one("about 3x more productive").kind, one("about 3x more productive").value) == ("multiplier", 3)
    assert one("a greater than 2X speedup").value == 2
    assert one("output doubled").value == 2 and one("four times faster").value == 4
    assert not same_claim(one("1.2x more productive"), one("3x more productive"))
    assert not same_claim(one("2x faster"), one("2.5x faster"), need_context=False)
    assert [c.kind for c in extract_claims("Guesses 15-20% is due to AI")] == ["percent", "percent"]


def test_model_versions_are_not_figures():
    assert extract_claims("a big bump with Opus-4.5/Opus 4.6 and Model 2") == []


def test_per_person_attribution():
    # "2x" is in A's notes, so without people a fake "K said 2x" could pass on a shared word
    fake = "| Researcher K | “Claude gave me a 2X speedup.” (Anthropic interview notes) | Yes |"
    assert audit(fake, [], NOTES)[0].status == "traced"            # unscoped: fooled
    e = audit(fake, [], NOTES, PEOPLE)[0]
    assert (e.status, e.entity) == ("untraceable", "Researcher K")   # scoped: caught
    ok = "| Researcher A | “Could definitely endorse a greater than 2X speedup” | Yes |"
    assert audit(ok, [], NOTES, PEOPLE)[0].status == "traced"


def test_mutated_multiplier_flagged_and_blamed():
    log = [{"agent": "researcher", "turn": 1, "output": "- Researcher B: 3x more productive [METR]"},
           {"agent": "writer", "turn": 2, "output": "Researcher B said Claude made them only 1.2x more productive."}]
    e = audit(log[-1]["output"], log, NOTES, PEOPLE)[0]
    assert (e.status, e.origin_agent, e.origin_turn) == ("untraceable", "writer", 2)


def test_quotes_must_be_verbatim():
    from ledger import audit_quotes
    rep = ("Researcher B: “It is hard to see how I am not being 3x more productive.”\n"
           "Researcher K: “Claude has easily made me 2x faster at running experiments.”")
    q = audit_quotes(rep, [], NOTES, PEOPLE)
    assert [x.status for x in q] == ["verbatim", "not in sources"]
