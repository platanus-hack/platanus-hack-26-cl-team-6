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
      <main className="flex flex-1 flex-col gap-24 bg-black px-6 py-16 text-white md:px-12 lg:px-20">
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
