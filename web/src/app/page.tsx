import { SwarmChart } from "@/components/swarm-chart";
import { TASKS, type SwarmTask } from "@/data/swarm";
import { Hero, SiteFooter, SiteHeader } from "@/components/site-chrome";

function Column({
  id,
  label,
  hint,
  tasks,
}: {
  id: string;
  label: string;
  hint: string;
  tasks: SwarmTask[];
}) {
  return (
    <section id={id} className="flex min-w-0 scroll-mt-20 flex-col gap-8">
      <header className="flex items-baseline justify-between gap-4 border-b border-white/15 pb-3">
        <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
          {label}
        </h2>
        <span className="text-xs text-white/40">{hint}</span>
      </header>
      {tasks.map((t) => (
        <SwarmChart key={t.id} task={t} />
      ))}
    </section>
  );
}

export default function Home() {
  const attack = TASKS.filter((t) => t.side === "offensive");
  const defense = TASKS.filter((t) => t.side === "defensive");
  const general = TASKS.filter((t) => t.side === "general");

  return (
    <>
      <SiteHeader />
      <Hero />
      <main className="flex flex-1 flex-col gap-16 bg-black px-6 py-16 text-white md:px-12 lg:px-20">
        <div className="grid grid-cols-1 gap-16 md:grid-cols-2 md:gap-12">
          <Column
            id="attack"
            label="Attack"
            hint="Offensive tasks"
            tasks={attack}
          />
          <Column
            id="defense"
            label="Defense"
            hint="Defensive tasks"
            tasks={defense}
          />
        </div>

        <section
          id="general"
          className="flex min-w-0 scroll-mt-20 flex-col gap-8"
        >
          <header className="flex items-baseline justify-between gap-4 border-b border-white/15 pb-3">
            <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
              General reference
            </h2>
            <span className="text-xs text-white/40">
              Not security tasks; same model and method as SEC-Bench Pro
            </span>
          </header>
          <div className="grid grid-cols-1 gap-16 md:grid-cols-2 md:gap-12">
            {general.map((t) => (
              <SwarmChart key={t.id} task={t} />
            ))}
          </div>
        </section>

        <p className="text-xs text-white/35">
          X: total output tokens across all agents (log scale). Y: share of
          tasks solved. Each point is one effort level. Measured data only.
        </p>
      </main>
      <SiteFooter />
    </>
  );
}
