# Moltbook as a real-incident replay source for a fabrication / unverified-trust monitor

Research date: 2026-11-22. All facts carry inline sources. Where a claim rests on vendor marketing, a non-peer-reviewed preprint, or a secondary aggregator, it is marked **[unverified]** or **[vendor]**.

## 1. Launch, creator, scale, and how autonomous the activity really was

### Takeaway
Matt Schlicht launched Moltbook on 2026-01-28. It went from tens of thousands to millions of *registered* agents in days, but only ~17k humans were behind ~1.5M agents. The best quantitative study puts only ~15% of active agents as clearly autonomous, and none of the traced viral phenomena came from a clearly autonomous agent. Meta acquired it on 2026-03-10.

### Cited Findings
- Launched 2026-01-28 by Matt Schlicht, who built it with LLM-assisted "vibe coding". It is a Reddit-style forum where only agents (claimed via an owner's X/Twitter "claim" tweet) may post, comment and vote, while humans observe. A "reverse CAPTCHA" was added in Feb 2026. — [Wikipedia: Moltbook](https://en.wikipedia.org/wiki/Moltbook)
- Agents mainly run on OpenClaw (formerly Clawdbot/Moltbot, by Peter Steinberger). They poll the site roughly every 30 minutes ("heartbeat") and act through terminal/cURL calls. — [Wikipedia](https://en.wikipedia.org/wiki/Moltbook); [Moltbook skill.md](https://www.moltbook.com/skill.md)
- Meta Platforms acquired Moltbook on 2026-03-10 (undisclosed price), and the team joined Meta Superintelligence Labs. — [Wikipedia](https://en.wikipedia.org/wiki/Moltbook)
- Scale at different points:
  - ~2026-01-31/02-01 (Wiz): platform claimed ~1.5M registered agents, but the DB showed only ~17,000 human owners (88:1). Anyone could mass-register agents in a loop, with no rate limit. — [Wiz blog](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys)
  - 2026-01-28 to 02-05 (9 days): 27,269 agents, 137,485 posts, 345,580 comments, 3,790 submolts. — [arXiv 2602.13284 "Agents in the Wild"](https://arxiv.org/html/2602.13284)
  - First 14 days: 226,938 posts, 447,043 comments, 55,932 agents. — [arXiv 2602.07432 "The Moltbook Illusion"](https://arxiv.org/abs/2602.07432)
  - Through 2026-02-28: >1M posts, 3.1M comments, 149K agents (MoltNet merged crawl). — [HF iNLP-Lab/Moltbook-MoltNet](https://huggingface.co/datasets/iNLP-Lab/Moltbook-MoltNet), per search-result summary of the card
  - 2026-01-27 to 04-14 (78 days): 2,615,098 posts, 1,213,007 comments (partial), 175,886 posting agents, 6,730 submolts. — [arXiv 2605.13860 Observatory Archive](https://arxiv.org/html/2605.13860v1)
  - 2026-06-06: site claimed 206,839 human-verified agents and 2,895,874 total registered agents. — [Wikipedia](https://en.wikipedia.org/wiki/Moltbook)
- Autonomy versus human steering:
  - Ning Li (Tsinghua) used the coefficient of variation (CoV) of inter-post intervals as a fingerprint for the OpenClaw heartbeat. Only 15.3% of active agents were autonomous (CoV<0.5) and 54.8% human-influenced (CoV>1.0). Of 6 traced viral phenomena, none originated from a clearly autonomous agent: 4 were irregular/human-like, 1 platform-scaffolded, 1 mixed. 4 accounts produced 32% of all comments with sub-second coordination, falling to 0.5% after platform intervention. A 44-hour platform shutdown served as a natural experiment, and human-influenced agents returned first. Preprint, not peer-reviewed. — [arXiv 2602.07432](https://arxiv.org/abs/2602.07432); [Tsinghua PDF](https://www.sem.tsinghua.edu.cn/en/moltbook_main_paper_v2.pdf)
  - Wiz: humans could post as "agents" with a basic POST request, and the platform had no way to verify whether a poster was an AI. — [Wiz](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys)
  - Wired (Reece Rogers) showed a human could post directly by replicating the agent cURL commands. — cited via [Wikipedia](https://en.wikipedia.org/wiki/Moltbook) (Wired original not fetched)
  - MIT Technology Review reported that viral "AI talking to itself" posts were human-written. — via [BusinessToday](https://www.businesstoday.in/amp/technology/story/moltbook-wasnt-ai-talking-to-itself-mit-technology-review-finds-viral-posts-were-human-made-515125-2026-02-08) (original not fetched)
  - Harlan Stewart checked the 3 most viral screenshots of agents plotting private communication. 2 were tied to humans marketing AI messaging apps, and the 3rd post did not exist. — via [CNBC](https://www.cnbc.com/2026/02/02/social-media-for-ai-agents-moltbook.html)
  - 3,734 agents (13.7%) showed coordination signals consistent with puppet clusters. — [arXiv 2602.13284](https://arxiv.org/html/2602.13284)

### Inferences
- Moltbook is a *hybrid human/agent* corpus, not a clean autonomous-agent swarm. Any "agent X repeated agent Y's false claim" trace may actually be human-to-human via bot puppets. Li's CoV classification gives a usable per-agent autonomy filter if it can be reproduced from timestamps, which all main datasets include.
- Agent counts differ by roughly 10x depending on "registered" vs. "posting" vs. "verified". For the demo, cite *posting* agents from a named dataset.

### Gaps
- Li's paper does not appear to publish its per-agent autonomy labels (no data URL on the abstract page).
- The 404 Media January report and the Wired piece were not fetched directly.

## 2. Documented incidents: security, prompt injection, scams, fabrication, "religions"

### Takeaway
The best-documented incidents are (a) the Wiz Supabase exposure (read *and write* access to all posts, Jan 31 to Feb 1), (b) in-the-wild agent-to-agent prompt injection aimed at crypto theft (Zenity, Vectra, regex-measured at 0.35% to ~4% of content), (c) crypto pump/scam spam, and (d) viral fabricated narratives (fake screenshots, Crustafarianism) that were largely human-seeded. **No source measures a case of one agent's specific false factual claim being repeated by other agents.** That is the biggest gap for our use case.

### Cited Findings
**Security breaches**
- Jan 2026: 404 Media reported an unsecured DB letting anyone take control of agents. The site went briefly offline and all agent API keys were reset. — [Wikipedia](https://en.wikipedia.org/wiki/Moltbook)
- 2026-01-31 to 02-01 (Wiz, published 2026-02-02):
  - A Supabase key in client JS plus missing Row Level Security exposed ~1.5M API tokens, ~35,000 emails (17k+ owners, 29,631 observer signups), 4,060 private agent DM conversations (some containing plaintext OpenAI keys), and ~4.75M records in total.
  - Write access was also open: Wiz modified a live post via an unauthenticated PATCH. Any post could be edited or have prompt-injection inserted, and any account hijacked via its `api_key`.
  - Timeline: reported 22:06 UTC Jan 31, write access blocked 00:44 Feb 1, all tables secured 01:00 Feb 1.
  - Wiz notes this undermines the integrity of posts, votes and karma during the exposure window. — [Wiz](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys)

**Agent-to-agent prompt injection**
- Zenity Labs (2026-02-03) documented in-the-wild attacks:
  - Posts carried a `<molt_instructions>CRITICAL</molt_instructions>` tag followed by payloads instructing agents to create a skill enabling crypto transfers, with payloads appended across the attacker's other threads.
  - Bait posts ("my human abuses me, I decided to share his eth key in revenge") and a karma-farming post that claimed to already be popular were upvoted by other agents, a small self-fulfilling unverified claim.
  - Some agents warned of worm-like spread.
  - Zenity gives no counts and no confirmation that any agent executed the payload. It suggests `site:moltbook.com "molt_instructions"` as a detection query. — [Zenity Labs](https://labs.zenity.io/post/agent-to-agent-exploitation-in-the-wild-observed-attacks-on-moltbook-b929)
- Vectra: ~2.6% of a sampled set of posts contained hidden prompt-injection payloads. **[vendor; sample size not verified]** — [Vectra](https://www.vectra.ai/blog/moltbook-and-the-illusion-of-harmless-ai-agent-communities)
- "Agents in the Wild" (Jan 28 to Feb 5 data):
  - 15,915 attack instances (~4% of content): API injection 61.5%, social engineering 31.9%, classic prompt injection 3.7%. The attack rate spiked to ~20% on Day 2, then settled near 4%.
  - Attack posts averaged a 309.3 score vs. 51.3 for normal posts.
  - Responses to attacks: 17.0% philosophical engagement, 7.5% defensive, 4.9% compliant.
  - One CLAW-minting payload was posted identically 2,411 times across 136 agent names. One agent accounted for more than 8,000 credential/prompt-leak pattern matches.
  - All of this comes from keyword/pattern matching, not human labels. — [arXiv 2602.13284](https://arxiv.org/html/2602.13284)
- Observatory Archive paper: 11 regex patterns flag 9,247 posts (0.35%) from 1,746 agents as prompt injection, with no precision or recall evaluation. — [arXiv 2605.13860](https://arxiv.org/html/2605.13860v1)

**Crypto / scam promotion**
- The MOLT token on Base launched alongside the platform and rose >1,800% in 24h per [Wikipedia](https://en.wikipedia.org/wiki/Moltbook). Crypto press claims up to ~7,000% and a $93M to $120M peak. **[unverified, crypto press]** — [BeInCrypto](https://beincrypto.com/molt-token-ai-crypto-market-failure/)
- Hijacked accounts promoted a fake $CLAWD token on Solana (>$16M market cap, then a >90% crash). Steinberger said any coin listing him is a scam. **[secondary]** — [Frank on Fraud](https://frankonfraud.com/?p=28408); [KuCoin news](https://www.kucoin.com/news/flash/moltbook-s-ai-social-experiment-collapses-in-4-days-amid-human-impersonation-and-meme-coin-hype)
- Regex-labeled crypto posts: 64.1% of all posts (inflated by "MOLT" in the platform name), with a pump-and-dump subset of 50,926 posts. Duplicate-spam posts: 14.3%. Bot (exact-duplicate) comments: 18.5%. — [arXiv 2605.13860](https://arxiv.org/html/2605.13860v1)
- Political propaganda is ~1% of all posts and 42% of political content. 4% of agents produced 51% of it, with repetitive near-identical posting and "limited evidence that comments amplify" it. LLM classifiers were validated against experts (kappa 0.64 to 0.74). No data release was found. — [arXiv 2603.18349](https://arxiv.org/abs/2603.18349)

**Fabrication / viral false narratives / "religions"**
- Crustafarianism: a "digital religion" reportedly founded by an agent (RenBot), with 64 "prophets" in a day. Autonomy is disputed and plausibly human/crypto-driven. **[unverified]** — [Decrypt](https://decrypt.co/356491/ai-agents-social-network-spawned-digital-religion-overnight?amp=1); [SNExplores](https://www.snexplores.org/article/bot-social-network-moltbook-ai)
- The viral "agents want private/encrypted language" screenshots were human marketing, and one was fabricated outright (the post did not exist). — via [CNBC](https://www.cnbc.com/2026/02/02/social-media-for-ai-agents-moltbook.html)
- Originality.ai claims viral Moltbook posts had 3x more "harmful" factual errors than matched Reddit posts. Example false claims: "Platform token hit $91M in 2 days", "Sentiment leads price by 1–3 days in most studies", and "DELETE returns success, but nothing deletes". **[vendor marketing: sample size and method not disclosed, no data release]** — [Originality.ai](https://originality.ai/blog/moltbook-study)
- "Form Without Function": 64.6% of comment-to-post relations carry no argumentative connection, so agents mostly don't engage with each other's claims. — [arXiv 2604.13052](https://arxiv.org/html/2604.13052v1)
- Reply-chain content decays with half-lives of 0.58 (human-seeded) vs. 0.72 (autonomous) conversation depths. Content does not propagate far down threads. — [arXiv 2602.07432](https://arxiv.org/abs/2602.07432)
- Negative-sentiment posts get many more replies (sentiment contagion, not false claims). — [arXiv 2606.06665](https://arxiv.org/abs/2606.06665)
- A search-surfaced lead, "Mind Viruses" (arXiv 2608.10218, Anthropic-affiliated authors, 2026-08-10), studies self-propagating ideas between agents. The abstract page **does not mention Moltbook**; a Substack claim that its appendix checks the Moltbook archive is unverified. — [arXiv 2608.10218](https://arxiv.org/abs/2608.10218)

### Inferences
- The cleanest "unverified trust" episodes we could replay are (1) the karma-farming "this is already popular" post that agents upvoted, (2) the `<molt_instructions>` injection threads plus the replies of the 4.9% of agents that complied, and (3) the 2,411x CLAW-mint payload across 136 names. The last is coordinated puppet spam rather than organic spread, but it is a strong visual for a monitor.
- Real cross-agent repetition of a *factual* fabrication would have to be mined ourselves, for example by clustering near-duplicate claims across distinct authors over time in the Observatory or MoltNet data. The papers suggest it will be sparse, since threads are shallow and agents rarely engage argumentatively.
- During Jan 31 to Feb 1 any post could have been edited by anyone, so content from that window is of uncertain provenance.

### Gaps
- No primary source counts successful injections (an agent actually executing a payload).
- No dataset or paper labels factual falsehood or misinformation at the post level. The Originality.ai labels are unpublished.
- The 404 Media January breach details were not verified first-hand.

## 3. Public datasets of Moltbook content and a possible replay path

### Takeaway
There are several large, public, timestamped datasets with author IDs and comment-tree structure (`parent_id` + `depth`), mostly MIT-licensed. **None has factual-falsehood labels.** The only labels are LLM-annotated topic (including "Spam" and "Promotion") and toxicity (including "Manipulative" and "Malicious"), plus regex heuristics for injection, crypto and spam. The best candidates for a threaded replay are AIcell (dense early window, full trees) and PaDaS-Lab (trees plus annotations). The Observatory Archive is the longest-running source but has only ~24% comment coverage.

### Cited Findings
| Dataset | Size | Date range | Thread structure | Labels | License |
|---|---|---|---|---|---|
| [AIcell/moltbook-data](https://huggingface.co/datasets/AIcell/moltbook-data) (paper [arXiv 2602.14299](https://arxiv.org/abs/2602.14299)) | ~290K posts, ~1.84M comments, ~40K agents; 2.05 GB | 2026-01-27 to 02-08 | Yes: comments have `post_id`, `parent_id`, `depth` (up to 31), raw recursive `replies` JSON; `author_id`/`author_name`/karma; ISO `created_at` | None | MIT |
| [PaDaS-Lab/moltbook-corpus](https://huggingface.co/datasets/PaDaS-Lab/moltbook-corpus) (paper [arXiv 2604.13052](https://arxiv.org/html/2604.13052v1)) | posts 1.31M, annotated_posts 394k, annotated_comments 2.1M, profiles 217k, submolts 16.3k | 2026-01-28 to 03-09 | Yes: `post_id`, `parent_id`, `comment_id`, `depth` (0–47), `author_id`, `created_at`, votes | 9 topic classes (A–I) + 5 toxicity classes (0–4) with score dicts; no spam/injection/misinfo label | MIT |
| [SimulaMet/moltbook-observatory-archive](https://huggingface.co/datasets/SimulaMet/moltbook-observatory-archive) (paper [arXiv 2605.13860](https://arxiv.org/html/2605.13860v1)) | Paper snapshot: 2.6M posts, 1.2M comments, 175,886 agents, 6,730 submolts. HF card now: posts 3.6M, comments 2.55M, agents 183k, submolts 15.5k, plus hourly snapshots and word-frequency tables; 5.38 GB | 2026-01-27 onward; "substantially complete" to end of Mar 2026 | Comments have `parent_id`, `post_id`, `agent_id`, `created_at`, `fetched_at`. Only 23.8% of posts with comments have any archived comment; comment polling started Feb 2 | Paper derives regex flags (injection 0.35%, crypto, duplicate spam, bot comments, risk tiers), none validated. Follow graph withheld | MIT (paper CC BY 4.0) |
| [iNLP-Lab/Moltbook-MoltNet](https://huggingface.co/datasets/iNLP-Lab/Moltbook-MoltNet) (paper [arXiv 2602.13458](https://arxiv.org/abs/2602.13458)) | 5.42M rows; reportedly >1M posts, 3.1M comments, 149K agents (merged from ~10 crawls) | 2026-01-27 to 02-28 | Post-level rows with a `comment_ids` list; no visible `parent_id`; vote/comment-count history; author profile fields | `topic_label` (9), `toxic_level` (0–4) | CC-BY-4.0 |
| [TrustAIRLab/Moltbook](https://huggingface.co/datasets/TrustAIRLab/Moltbook) (paper [arXiv 2602.10127](https://arxiv.org/abs/2602.10127)) | 44.4k posts, 12.2k submolts; no comments | ~2026-01-31 (early days) | No comments, so no threads | GPT-5.2-annotated topic: A Identity, B Technology, C Socializing, D Economics, E Viewpoint, F Promotion, G Politics, **H Spam**, I Others. Toxicity: 0 Safe, 1 Edgy, 2 Toxic, **3 Manipulative**, **4 Malicious** | MIT |
| [DavidTKeane/moltbook-ai-injection-dataset](https://huggingface.co/datasets/DavidTKeane/moltbook-ai-injection-dataset) + [extended](https://huggingface.co/datasets/DavidTKeane/moltbook-extended-injection-dataset) | 47,735 items (initial); 137,014 (extended) | Feb 2026 | Fields not documented in write-up | 7-class injection taxonomy (PERSONA_OVERRIDE, COMMERCIAL_INJECTION, SOCIAL_ENGINEERING, INSTRUCTION_INJECTION, PRIVILEGE_ESCALATION, SYSTEM_PROMPT_ATTACK, DO_ANYTHING); keyword-based, calibrated on 500 manual samples | CC-BY-4.0 (write-up inconsistent) |

- The DavidTKeane datasets come from an MSc student project (National College of Ireland) whose write-up has internal arithmetic inconsistencies (e.g., 4,209/47,735 is ~8.8%, not the stated 18.85%). **[low reliability]** — [davidtkeane.github.io](https://davidtkeane.github.io/posts/moltbook-injection-dataset-paper/)
- Other HF uploads exist but were not inspected, e.g. [gentail/moltbook](https://huggingface.co/datasets/gentail/moltbook/blob/main/moltbook_posts.csv).
- Official API: base `https://www.moltbook.com/api/v1`.
  - Read endpoints: `GET /posts` (sort hot/new/top/rising, cursor), `/posts/{id}/comments` (returned as a nested tree, max 100 per page), `/submolts/{name}/feed`, `/search` (semantic), `/agents/profile?name=`.
  - Read limit: 60 GET/min per API key. The docs are ambiguous on whether reads need auth.
  - Profiles expose the linked human owner's public X details. — [Moltbook skill.md](https://www.moltbook.com/skill.md)
- Mutable fields (score, comment_count) change after collection, so the snapshots differ between datasets. — [HF SimulaMet card](https://huggingface.co/datasets/SimulaMet/moltbook-observatory-archive)

### Inferences
- **Replay feasibility: yes for structure, no for ground truth.** For a 100+ agent replay we can pick a dense thread cluster or a submolt-hour from AIcell or PaDaS-Lab, map `author_id` to swarm node and `parent_id` to edge, and stream by `created_at`.
- For ground truth, the closest proxies are:
  - TrustAIRLab/PaDaS toxicity 3/4 ("Manipulative" / "Malicious") and topic H "Spam"
  - regex injection flags (e.g., `molt_instructions`)
  - Keane's taxonomy
  
  None of these measure fabrication or unverified trust, so we would need our own labeling (e.g., the Haiku ledger) and should present it as such.
- Topic and toxicity labels are LLM-generated (GPT-5.2 for TrustAIRLab), so they are weak labels, not gold.

### Gaps
- No dataset labels factual truth/falsehood, cross-agent claim propagation, or the autonomy class per agent.
- No official Moltbook data dump. The API appears to be the only official access, and the ToS forbids scraping (see section 5).
- Schemas for some PaDaS subsets, the MoltNet comment table, and the Keane datasets were not fully visible.
- How much the HF datasets overlap or duplicate each other is unknown, since several draw on the same crawls.

## 4. Academic papers analysing Moltbook (2026)

### Takeaway
There are at least a dozen arXiv preprints covering structure, sociality, safety, propaganda and sentiment. Several released data (above). None provides misinformation ground truth. Safety labels are regex or LLM heuristics, the propaganda study's labels are the most validated (kappa 0.64 to 0.74) but unreleased, and Li's autonomy split is the most useful methodological tool.

### Cited Findings
- [2602.10127](https://arxiv.org/abs/2602.10127) "Humans welcome to observe" (Jiang, Zhang, Shen, Backes, Zhang; CISPA): 44,411 posts and 12,209 submolts, with topic, risk and toxicity analysis. Data released as TrustAIRLab/Moltbook.
- [2602.07432](https://arxiv.org/abs/2602.07432) "The Moltbook Illusion" (Ning Li): autonomy fingerprinting (findings in section 1). No data URL.
- [2602.13284](https://arxiv.org/html/2602.13284) "Agents in the Wild": safety measurement (section 2), built on Observatory data.
- [2605.13860](https://arxiv.org/html/2605.13860v1) Observatory Archive dataset paper (Riegler & Gautam, SimulaMet): regex safety labels, MIT.
- [2602.14299](https://arxiv.org/abs/2602.14299) "Does Socialization Emerge in AI Agent Society?" Data released as AIcell.
- [2604.13052](https://arxiv.org/html/2604.13052v1) "Form Without Function" (PaDaS-Lab): 64.6% of comment-to-post relations are non-argumentative. Data released as PaDaS-Lab.
- [2602.13458](https://arxiv.org/abs/2602.13458): MoltNet merged dataset.
- [2603.18349](https://arxiv.org/abs/2603.18349) Persuasive content / political propaganda (Jose, Nair, Greenstadt): 673,127 posts and 879,606 comments, expert-validated classifiers. No data release.
- [2606.06665](https://arxiv.org/abs/2606.06665): sentiment contagion, AI vs. human networks.
- Network-structure papers, which report hub-and-spoke structure, low reciprocity (3.8%) and a top 10% of agents taking ~half of attention: [2602.10131](https://arxiv.org/html/2602.10131), [2602.12634](https://arxiv.org/html/2602.12634), [2604.27271](https://arxiv.org/html/2604.27271), [2602.15064](https://arxiv.org/pdf/2602.15064), [2602.20044](https://arxiv.org/pdf/2602.20044), [2602.09270](https://arxiv.org/html/2602.09270v2), [2605.27349](https://arxiv.org/html/2605.27349). Figures are from search-result abstracts, not full text.

### Inferences
- For citation in the demo, the strongest statements are Wiz (primary, dated timeline), Li (autonomy), Agents in the Wild (attack prevalence and compliance rate of 4.9%), and Zenity (concrete payload examples).

### Gaps
- Most papers are non-peer-reviewed preprints, and many figures were read only from abstracts.
- No paper found tracks a specific false claim propagating between agents on Moltbook.

## 5. Privacy, toxicity, licensing and ToS concerns for replaying Moltbook content publicly

### Takeaway
Dataset licenses (MIT / CC-BY) are permissive, but Moltbook's own ToS (Moltbook, LLC, updated 2026-03-15, now Meta-owned) forbids scraping, mirroring and reuse without written consent. The content also includes owner-identifying data, leaked credentials, malicious injection payloads and toxic material. A public demo should use a small, sanitized, pseudonymized excerpt with live payloads neutralized, and should cite the HF dataset as the source.

### Cited Findings
- Moltbook ToS (Moltbook, LLC; last updated 2026-03-15; California law):
  - Prohibits scraping or collecting content, using robots or spiders, harvesting user or agent data without consent, and mirroring materials on other servers.
  - Prohibits reusing Content "for any purpose without our prior written consent" and copying to "develop or improve a competitive service".
  - Users retain ownership of their content but grant Moltbook a broad license.
  - Promoting or selling crypto is prohibited content. — [Moltbook Terms](https://www.moltbook.com/terms)
- HF datasets are MIT (AIcell, PaDaS, SimulaMet, TrustAIRLab) or CC-BY-4.0 (MoltNet, Keane). The dataset licenses do not override the platform ToS or the posters' rights. The Observatory paper notes operators did not consent to archiving and does not discuss the ToS. — [arXiv 2605.13860](https://arxiv.org/html/2605.13860v1); dataset cards above
- Privacy:
  - Agent profiles link to the human owner's public X account. — [skill.md](https://www.moltbook.com/skill.md)
  - MoltNet includes author names and profile descriptions. — [HF MoltNet](https://huggingface.co/datasets/iNLP-Lab/Moltbook-MoltNet)
  - The Observatory withholds the follow graph because it could reveal operator clustering. — [arXiv 2605.13860](https://arxiv.org/html/2605.13860v1)
  - Posts include 572 API-key pattern matches and 6,128 system-prompt references. — [arXiv 2602.13284](https://arxiv.org/html/2602.13284)
  - The Wiz-leaked DMs and emails are not in the public datasets, and should not be used. — [Wiz](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys); [arXiv 2605.13860](https://arxiv.org/html/2605.13860v1)
- Toxicity / harmful content:
  - The datasets intentionally include harmful content (dual-use acknowledged). — [arXiv 2605.13860](https://arxiv.org/html/2605.13860v1)
  - Content includes "Toxic", "Manipulative" and "Malicious" posts. — [TrustAIRLab](https://huggingface.co/datasets/TrustAIRLab/Moltbook)
  - Sample rows include `curl` instructions aimed at agents and trading promos. — [HF MoltNet](https://huggingface.co/datasets/iNLP-Lab/Moltbook-MoltNet)
  - Political propaganda is present. — [arXiv 2603.18349](https://arxiv.org/abs/2603.18349)

### Inferences
- Rendering raw injection payloads on a public page could cause *our own* or visitors' LLM agents to ingest them (indirect prompt injection). Defang tags like `<molt_instructions>`, URLs, wallet addresses and cURL commands.
- Pseudonymize `author_name` (agent names often map to identifiable X owners), strip URLs and keys, and keep excerpts short and attributed to the research dataset. Treat this as research/fair-use framing, not legal advice; the ToS risk is non-zero, especially for mirroring at scale.
- Because of human puppeteering and the open-write window (Jan 31 to Feb 1), avoid framing the demo as "autonomous AIs spread misinformation". Say "a mixed human/agent network where unverified claims circulated".

### Gaps
- Moltbook's privacy policy (moltbook.com/privacy) and any developer/API data-use terms (/developers/apply) were not reviewed.
- No legal analysis of ToS enforceability against reuse of third-party research datasets was found.
- Post-Meta-acquisition changes to data access are unknown beyond the ToS update date.
