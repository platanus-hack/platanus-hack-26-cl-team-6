import { ChartPlaceholder } from "@/components/chart-placeholder";
import { SETS, type JevSet } from "@/data/jev";
import { Hero, SiteFooter, SiteHeader } from "@/components/site-chrome";

const pct = (x: number) => `${Math.round(x * 100)}%`;

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

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-3xl font-light tracking-[-0.03em] text-white">
        {value}
      </span>
      <span className="text-xs text-white/45">{label}</span>
    </div>
  );
}

function Column({ set }: { set: JevSet }) {
  return (
    <section className="flex min-w-0 flex-col gap-8">
      <SectionHeader label={set.label} hint={set.hint} />
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Stat
          value={`${set.caught}/${set.errors}`}
          label="planted errors caught"
        />
        <Stat
          value={`${set.falseAlarms}`}
          label={`false alarms of ${set.clean} clean`}
        />
        <Stat value={pct(set.precision)} label="precision" />
        <Stat value={`$${set.costPer100.toFixed(3)}`} label="per 100 messages" />
      </div>
      {set.charts.map((c) => (
        <ChartPlaceholder key={c.kicker} kicker={c.kicker} title={c.title} />
      ))}
    </section>
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
    title: "A swarm writes a briefing",
    body: "Five agents (Atlas, Birch, Cedar, Delta, Echo) summarise the interview quotes in METR's November 2026 assessment of Anthropic. Atlas fetches the source; the others mostly work from Atlas's excerpts and each other's notes.",
  },
  {
    title: "We plant 36 errors",
    body: "Wrong numbers, wrong attributions, invented quote endings, and agents repeating each other's mistakes as fact. Twelve numeric, twelve textual, twelve mixed, each with a known correct version.",
  },
  {
    title: "Jev scores every message live",
    body: "As each message arrives, Jev rates it on fabrication and unverified trust, seeing only earlier messages. A message is flagged when either score reaches 0.85.",
  },
  {
    title: "Haiku keeps the ledger",
    body: "Every 20 messages, Haiku updates a running record of who claimed what, plus the facts from the fetched source. That ledger goes into Jev's context.",
  },
];

const NOTES = [
  "Every numeric error is caught. Most misses are textual errors inside multi-claim paragraphs, such as an invented ending for a quote that was cut off.",
  "Most false alarms are correct multi-claim drafts, and true statements about paraphrases or ranges.",
  "Errors repeated without credit are the hardest: 40% recall on the hard set.",
  "The ledger is rebuilt on every fresh run and is not deterministic, so expect about ±5 points between runs.",
  "The threshold was picked on seed 1 of the hard set. Nothing was tuned on the easy set.",
];

export default function Home() {
  return (
    <>
      <SiteHeader />
      <Hero />
      <main className="flex flex-1 flex-col gap-24 border-t border-white/15 bg-black px-6 py-16 text-white md:px-12 lg:px-20">
        <Pillars />

        <div
          id="results"
          className="grid scroll-mt-20 grid-cols-1 gap-16 md:grid-cols-2 md:gap-12"
        >
          {SETS.map((s) => (
            <Column key={s.id} set={s} />
          ))}
        </div>

        <section id="method" className="flex scroll-mt-20 flex-col gap-8">
          <SectionHeader label="How it works" hint="Three seeds per set" />
          <ol className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
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

        <section id="limits" className="flex scroll-mt-20 flex-col gap-8">
          <SectionHeader
            label="What it misses"
            hint="Seeds 2–3, threshold 0.85"
          />
          <ul className="grid grid-cols-1 gap-x-12 gap-y-4 md:grid-cols-2">
            {NOTES.map((n) => (
              <li
                key={n}
                className="border-l border-white/15 pl-4 text-sm leading-relaxed text-white/60"
              >
                {n}
              </li>
            ))}
          </ul>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
