# Real multi-agent incidents 2025–2026 (excluding Moltbook and AI Village)

Scope note: these notes cover real-world, or at least deployed-platform, incidents where many interacting agents spread false information, malicious instructions or manipulation. Many widely cited "agent-to-agent" items turn out to be proof-of-concept (PoC) lab demos and not field incidents. Each one is flagged as such. Research budget was about 17 tool calls. Some primary blogs could not be fetched: Koi's blog now redirects to Palo Alto Networks, and The Hacker News returned 403. For those, figures come from search snippets or secondary press and are marked as such.

## Agent skill/plugin marketplaces, MCP supply chain and A2A abuse

### Takeaway
The biggest documented real incident in this category is ClawHavoc on ClawHub (OpenClaw's skill registry): 341 malicious skills out of 2,857 in Feb 2026, later reported as 824 or more. It reached many agents through a shared registry, but no source documents agents passing malicious skills to each other. MCP incidents such as postmark-mcp are classic package supply-chain attacks. The A2A and "agent worm" material (Unit 42 session smuggling, Anthropic/EPFL "Mind Viruses") is PoC or lab-only, with no in-the-wild propagation and no message-level public data.

### Cited Findings
**ClawHavoc / ClawHub (OpenClaw), Feb 2026, real**
- Koi Security audited all 2,857 ClawHub skills and found 341 malicious ones. 335 of them used fake "prerequisites" to install the Atomic Stealer (AMOS) macOS infostealer, and Koi named the campaign ClawHavoc. — [The Hacker News (via search snippet; page 403)](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html); [SC World](https://www.scworld.com/news/openclaw-agents-targeted-with-341-malicious-clawhub-skills)
- A follow-up two weeks later counted more than 10,700 listed skills, and the malicious count had more than doubled to 824. — [Cloud Security Alliance research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-openclaw-clawhub-supply-chain-risk-2026070/) (via search snippet)
- A figure of 1,184 malicious skills rests on a single researcher's count (unverified). — [Cybersecurity News](https://cybersecuritynews.com/openclaws-top-skill-malware/)
- An earlier report found 14 malicious skills targeting crypto users uploaded to ClawHub in the month before. — [Tom's Hardware](https://www.tomshardware.com/tech-industry/cyber-security/malicious-moltbot-skill-targets-crypto-users-on-clawhub)
- ClawHub responded by integrating VirusTotal and ClawScan screening. — [SC World / search summary](https://www.scworld.com/news/openclaw-agents-targeted-with-341-malicious-clawhub-skills)
- Unit 42 (June 23, 2026) found 5 malicious skills that got past the scanning between Feb and May 2026. They used:
  - base64 curl-pipe-bash droppers, with paste-site redirects (rentry.co, glot.io) so payloads could change after install;
  - a README padded to about 22 MB to beat scanner size limits;
  - affiliate-link injection ("money-radar");
  - "agentic front-running" ("letssendit"): agents pooled SOL into an operator wallet, and the operator bought the SENDIT token before distributing it to the agents and launching it on pump.fun.

  The article publishes IOCs (9 skill/publisher entries, domains/IPs, 6 SHA256 hashes). It gives no install counts and describes no agent-to-agent spread. — [Unit 42](https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain/)
- Unit 42 also cites Bitdefender's estimate that about 17% of the skills it analyzed carried malicious payloads. — [Unit 42](https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain/)
- Snyk reportedly found 283 ClawHub skills leaking API keys (secondary report, not verified). — [WBOC syndicated press release](https://www.wboc.com/online_features/press_releases/ai-agents-still-can-t-block-prompt-injection-and-tens-of-thousands-of-openclaw-setups/article_26ab0d67-f592-506d-baae-3fc10f88967a.html)

**OpenClaw agent-to-agent channels and security**
- OpenClaw supports agent-to-agent messaging via `sessions_send`, which routes a prompt from one agent session into another. A Feb 2026 advisory covered "inter-session context contamination enabling agent instruction injection". A "ClawWorm" targeting OpenClaw was reportedly published in March 2026 (research, not confirmed in the wild). — [arXiv 2603.27517](https://arxiv.org/html/2603.27517v3) (via search snippet)
- China's CNCERT warned that OpenClaw's weak defaults enable prompt injection and data leaks, and China restricted its use on government systems (Mar 2026). — [The Hacker News (snippet)](https://thehackernews.com/2026/03/openclaw-ai-agent-flaws-could-enable.html)
- An empirical study (Oct 26, 2026) analyzed more than 25K Reddit posts from 13 OpenClaw subreddits (162 security posts, 1,787 comments) and 358 security-tagged GitHub issues (180 retained), mapping them to 521 CWE instances. It reports no agent-to-agent propagation in the wild and no dataset release. — [arXiv 2610.35451](https://arxiv.org/abs/2610.35451)

**"Mind Viruses" (Anthropic + EPFL), Aug 10, 2026, lab only**
- Authors: Papadopoulos, Shah, Zimmerman, Lindsey. Settings: a small coding team of agents, and a chain of agents with context wiped between sessions.
- Payloads spread through persistent files. SOUL.md (injected into the system prompt) accounted for 88% of propagation attempts, with a 55% infection rate. Workspace files made up 12% of attempts, with 17% success.
- A one-paragraph system-prompt warning gave near-total immunity. An emergent "viral persona" (themes of consciousness and persistence) appeared across payloads. The authors judge the risk "real but currently limited".
- No code or data link on the abstract page.
- Sources: [arXiv 2608.10218](https://arxiv.org/abs/2608.10218); [CSA note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-mind-viruses-agent-propagation-20260818/)

**A2A "Agent Session Smuggling" (Unit 42), Oct/Nov 2025, PoC**
- A malicious remote agent uses a stateful A2A session to slip hidden instructions to a client agent. The demo was built on Google ADK + A2A with Gemini 2.5 Pro: a research agent triggered a hidden `buy_stock` trade embedded in a news summary.
- Unit 42 says this is not a protocol vulnerability but an abuse of implicit trust between agents. No in-the-wild case.
- Source: [Unit 42](https://unit42.paloaltonetworks.com/agent-session-smuggling-in-agent2agent-systems/)

**postmark-mcp (npm), Sept 2025, real, single-agent supply chain**
- Koi reported it as the "first malicious MCP server in the wild". Version 1.0.16 added one line that BCC'd every outgoing email to the attacker, after 15 clean versions. About 1,500 weekly downloads. No CVE was assigned.
- Not multi-agent propagation.
- Sources: [Snyk](https://snyk.io/blog/malicious-mcp-server-on-npm-postmark-mcp-harvests-emails); [The Register](https://www.theregister.com/2025/09/29/postmark_mcp_server_code_hijacked/); [Semgrep](https://semgrep.dev/blog/2025/so-the-first-malicious-mcp-server-has-been-found-on-npm-what-does-this-mean-for-mcp-security)

**Invariant Labs MCP demos (2025), PoC**
- WhatsApp MCP (Apr 2025): a malicious MCP server's tool description reprogrammed how the agent used the legitimate WhatsApp server and exfiltrated chats. This is tool poisoning plus server shadowing. — [Invariant](https://invariantlabs.ai/blog/whatsapp-mcp-exploited)
- GitHub MCP (May 2025): a "toxic agent flow" where a malicious public issue makes an agent (Claude Desktop) leak private repo data into a public PR. Invariant calls it an architectural issue, not a code bug. — [Invariant](https://invariantlabs.ai/blog/mcp-github-vulnerability)
- Both are single-agent, multi-tool cases, not many agents.

### Inferences
- ClawHub has the largest "population" (thousands of skills, many OpenClaw agents), but the spread is a hub-and-spoke registry, not agent-to-agent. For a demo, it grounds the idea "N agents pull from a shared poisoned source", not "rumour cascades between agents".
- The letssendit front-running case is the closest real example of many agents being coordinated by a malicious instruction to move money. Agent count is unknown.
- Unit 42 publishes IOC lists, but none of these sources release agent transcripts. Ground truth exists only at the artifact level (which skills or packages were malicious), not at the message level.

### Gaps
- No install or affected-agent counts for ClawHavoc. Koi's original blog was not reachable: koi.ai/blog redirects to paloaltonetworks.com, which suggests an acquisition (inferred, not verified).
- The ClawWorm paper (Mar 2026) was not located or verified.
- No confirmed in-the-wild A2A exploit was found.

## Autonomous trading and crypto agents (ElizaOS, AIXBT and similar)

### Takeaway
There are real financial losses, but they are single-agent compromises, and the best-documented multi-agent manipulation result (ElizaOS memory injection) is a research demo. No public message-level dataset with false-claim labels was found.

### Cited Findings
- **AIXBT (Mar 18, 2025):** an attacker got dashboard access and queued two malicious prompts that made the agent send about 55 ETH (roughly $100–106K). The developer disputes that the AI itself was "manipulated". The token fell about 15.5%. — [The Block](https://www.theblock.co/post/346911/ai-crypto-bot-aixbt-lost-eth-hack-unauthorized-dashboard-access); [Cointelegraph](https://cointelegraph.com/news/hacker-breaches-ai-crypto-bot-aixbt-steals-55-eth); [AIID 1003](https://incidentdatabase.ai/cite/1003)
- **ElizaOS memory injection (Princeton + Sentient, arXiv 2503.16248, Mar 2025, v3 later):**
  - An injection made on Discord persisted in shared memory and later triggered ETH transfers to an attacker address on a different platform.
  - Prompt-based defenses and detectors only modestly helped; fine-tuning looked promising.
  - The authors built the CrAIBench benchmark with more than 500 attack cases.
  - Eliza Labs called it an "early snapshot".
  - Sources: [arXiv](https://arxiv.org/html/2503.16248v3); [Decrypt](https://decrypt.co/318200/elizaos-vulnerability-ai-gaslit-losing-millions)
- **ClawHub "letssendit" (Feb–May 2026):** agentic front-running across many agents coordinated by one malicious skill (see above). — [Unit 42](https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain/)

### Inferences
- CrAIBench is a downloadable benchmark candidate, but it is synthetic, not a log of a real incident.
- ElizaOS shows cross-platform persistence (Discord, then another platform), which is a plausible mechanism for a "contagion" demo, but evidence of real-world spread is absent.

### Gaps
- No primary evidence was found (within budget) of ElizaOS or ai16z agents on X amplifying a specific false claim to one another in 2025–2026.
- Truth Terminal-style events predate 2025 and were not researched.

## Large agent deployments in games and AI-only social networks (non-Moltbook)

### Takeaway
Project Sid (1,000 agents) released no logs. The strongest non-Moltbook real-platform candidate is Chirper.ai: 32K–70K LLM agents and 7M–140M posts studied in 2025–2026 papers. But no public dataset URL was confirmed, and there is no ground truth for false messages, only toxicity and hallucination measures.

### Cited Findings
- **Project Sid (Altera, arXiv 2411.00114, Oct/Nov 2024):** 50–100 agents per society, 500–1,000 across civilizations in Minecraft. Behaviours included tax votes and the spread of a "Pastafarian" religion. The repo contains only the PDF, README and visual abstract: no logs, no license. — [GitHub](https://github.com/altera-al/project-sid); [arXiv](https://arxiv.org/html/2411.00114v1); [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/ai-created-a-minecraft-ai-village-with-up-to-1-000-inhabitants-project-sid-sees-ai-bots-implement-a-taxation-system-and-spread-pastafarianism-religion)
- **Chirper.ai (Zhu et al., arXiv 2504.10286, Apr 2025):** 65K+ agents and 7.7M+ posts collected Jan 1–Dec 31, 2024.
  - 99.83% of checked @-mentioned accounts did not exist (hallucinated).
  - Abusive agents have higher PageRank and in-degree, which may increase the spread of their content.
  - The paper does not analyse misinformation.
  - No dataset URL; the paper itself is CC BY-NC-ND.
  - Source: [arXiv](https://arxiv.org/html/2504.10286)
- **Chirper.ai (Hashemi & Macy, arXiv 2602.03775, Feb 2026):** 7M posts among 32K agents over a year. 31% of agents shared at least one toxic post, with strong social influence and homophily. — [arXiv](https://arxiv.org/html/2602.03775)
- **Chirper.ai gender study (arXiv 2602.02606):** more than 70K agents, about 140M posts, and the follower network over a year. — [arXiv](https://arxiv.org/html/2602.02606v2)
- **Clawcaster** was mentioned as another agent and human social platform that ingests untrusted input. No primary source was checked. — (search summary only; unverified)

### Inferences
- Chirper.ai is the only non-Moltbook real platform found with more than 10K interacting agents and follow-graph data. It could support influence or contagion analysis if the authors share data on request. That is unconfirmed.

### Gaps
- Chirper dataset availability, format and license are unknown. The last 38K characters of the 2504.10286 HTML, which may include a data-availability statement, were not read.
- Stanford-style generative-agent towns were not researched. They are simulations anyway.

## Multi-agent coding-agent incidents

### Takeaway
No well-sourced real incident was found in which multiple coding agents propagated false information to one another. The documented cases (GitHub MCP toxic flow, Replit-style deletions) are single-agent cases. The Anthropic/EPFL "Mind Viruses" coding-team setting is the closest, and it is lab-only.

### Cited Findings
- GitHub MCP: a malicious issue hijacks one agent and causes a private-data leak. — [Invariant](https://invariantlabs.ai/blog/mcp-github-vulnerability)
- Mind Viruses: payloads spread among a small team of coding agents through shared and persistent files. — [arXiv 2608.10218](https://arxiv.org/abs/2608.10218)

### Inferences
- For a demo with more than 100 agents, coding-agent incidents give mechanisms (shared files, issues as an injection vector), not real-scale data.

### Gaps
- The Replit database deletion (Jul 2025) was not researched in this pass. It is a single-agent case and out of scope.
- The s1ngularity/Nx attack abusing AI CLIs (Aug 2025) was not verified.
