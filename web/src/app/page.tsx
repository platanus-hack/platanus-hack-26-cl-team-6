import { SwarmVillage } from "@/components/swarm-village";
import { Hero, SiteFooter, SiteHeader } from "@/components/site-chrome";

function SectionHeader({ label, hint }: { label: string; hint: string }) {
  return (
    <header className="flex items-baseline justify-between gap-4 border-b border-white/15 pb-3">
      <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
        {label}
      </h2>
      <span className="text-right text-xs text-white/40">{hint}</span>
    </header>
  );
}

// Hard set, threshold 0.85, seeds 2–3 (jev-swarm/results/hard.md).
// Scalable: Jev's 1.87M input tokens priced at Sonnet 5.5 ($2/M input, output
// not counted) = $3.75 vs our $0.134 for the same 493 messages. Jev's context is
// capped (last 30 messages + a ledger of at most 9,000 chars), so cost per
// message does not grow with the swarm.
// Real time: scored causally as each message arrives.
const PILLARS = [
  {
    kicker: "Scalable",
    value: "28×",
    unit: "cheaper than a Sonnet judge",
    body: "Built for big swarms: a flat cost per message, no frontier model on every message.",
  },
  {
    kicker: "Real time",
    value: "Live",
    unit: "with the same precision as comparable alternatives",
    body: "Errors are flagged as they're posted, before other agents can repeat them.",
  },
];

function Pillars() {
  return (
    <section
      id="why"
      aria-label="Why Jev"
      className="grid scroll-mt-20 grid-cols-1 border-b border-white/15 md:grid-cols-2"
    >
      {PILLARS.map((p, i) => (
        <div
          key={p.kicker}
          className={`flex flex-col gap-5 py-10 md:px-8 md:py-12 ${
            i > 0 ? "border-t border-white/15 md:border-t-0 md:border-l" : ""
          } ${i === 0 ? "md:pl-0" : ""} ${i === PILLARS.length - 1 ? "md:pr-0" : ""}`}
        >
          <span className="text-xs font-semibold tracking-wide text-white/45 uppercase">
            {p.kicker}
          </span>
          <div className="flex flex-col gap-1">
            <span className="text-5xl font-light tracking-[-0.04em] text-white md:text-6xl">
              {p.value}
            </span>
            <span className="text-sm text-white/55">{p.unit}</span>
          </div>
          <p className="max-w-sm text-sm leading-relaxed text-white/60">
            {p.body}
          </p>
        </div>
      ))}
    </section>
  );
}

const STEPS = [
  {
    title: "A small hallucination can multiply",
    body: "When AI agents work together, usually only one reads the source and the others trust it. If it gets a number or a quote wrong, the others repeat it, and the hallucination ends up in the final result.",
  },
  {
    title: "Two models watch the conversation",
    body: "We add two models that follow the chat as it happens. Every 20 messages, a language model takes notes on who said what and what the source actually says. Only the source counts as true; anything an agent claims is marked as not yet checked. A decision model uses these notes to review each new message. It asks: is this message making something up? Is it treating something unchecked as true? If it's confident the answer is yes, it flags the message.",
  },
  {
    title: "Hallucinations are caught before they spread",
    body: "The decision model flags a hallucination as soon as it appears, so it can be fixed before other agents repeat it. We tested it two ways. First, on conversations where we planted hallucinations ourselves: changed numbers, quotes credited to the wrong person and quotes with invented endings. Because we know where each one is, we can check which ones get caught. Then we ran it unchanged on a real swarm: 133 agents from AI Village talking for 24 hours, where it flagged 113 of 3,843 messages.",
  },
];

export default function Home() {
  return (
    <>
      <SiteHeader />
      <Hero />
      <main className="flex flex-1 flex-col gap-24 border-t border-white/15 bg-black px-6 py-16 text-white md:px-12 lg:px-20">
        <Pillars />

        <section id="method" className="flex scroll-mt-20 flex-col gap-8">
          <SectionHeader label="How it works" hint="For every message" />
          <ol className="grid grid-cols-1 gap-10 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="flex flex-col gap-3">
                <span className="font-mono text-xs text-white/35">
                  0{i + 1}
                </span>
                <span className="text-lg font-semibold">{s.title}</span>
                <p className="text-sm leading-relaxed text-white/60">
                  {s.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section id="swarm" className="flex scroll-mt-20 flex-col gap-8">
          <SectionHeader label="A real swarm" hint="AI Village Swarm · 133 agents" />
          <SwarmVillage />
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
