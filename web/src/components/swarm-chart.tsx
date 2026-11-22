import type { SwarmTask } from "@/data/swarm";

const W = 560;
const H = 300;
const PAD = { top: 56, right: 72, bottom: 44, left: 40 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

const ORANGE = "#ff5a1f";
const LIGHT = "#bdbdbd";
const DIM = "#5f5f5f";

const TICKS = [1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6];

function fmtTokens(t: number) {
  return t >= 1e6 ? `${+(t / 1e6).toFixed(1)}M` : `${Math.round(t / 1e3)}K`;
}

function fmtLambda(l: number) {
  return (l < 0 ? "−" : "") + (Math.round(Math.abs(l) * 100 + 1e-6) / 100).toFixed(2);
}

export function SwarmChart({ task }: { task: SwarmTask }) {
  const all = task.series.flatMap((s) => s.points);
  const lo = Math.log10(Math.min(...all.map((p) => p[0])) / 1.4);
  const hi = Math.log10(Math.max(...all.map((p) => p[0])) * 1.25);
  const x = (t: number) => PAD.left + ((Math.log10(t) - lo) / (hi - lo)) * PLOT_W;
  const y = (s: number) => PAD.top + (1 - s) * PLOT_H;

  const sorted = [...task.series].sort((a, b) => a.agents - b.agents);
  const solo = sorted[0];
  const swarm = sorted[sorted.length - 1];
  const middle = sorted.slice(1, -1);
  const colorFor = (agents: number) =>
    agents === swarm.agents ? ORANGE : agents === solo.agents ? LIGHT : DIM;

  const soloEnd = solo.points[solo.points.length - 1];
  const swarmEnd = swarm.points[swarm.points.length - 1];
  const ticks = TICKS.filter(
    (t) =>
      Math.log10(t) > lo &&
      Math.log10(t) < hi &&
      Math.abs(x(t) - x(swarm.points[swarm.points.length - 1][0])) > 44,
  );
  const path = (pts: [number, number][]) =>
    pts.map(([t, s], i) => `${i ? "L" : "M"}${x(t).toFixed(1)},${y(s).toFixed(1)}`).join("");

  const sx = x(swarmEnd[0]);
  const ciLabel = `90% CI ${fmtLambda(task.ci[0])} – ${fmtLambda(task.ci[1])}`;

  return (
    <figure className="flex min-w-0 flex-col gap-4">
      <figcaption className="flex flex-col gap-1">
        <span className="text-xs font-medium tracking-wide text-white/45 uppercase">
          {task.benchmark}
        </span>
        <span className="text-lg font-semibold text-white">{task.task}</span>
        <span className="text-xs text-white/45">
          {task.model} · {task.nTasks} tasks · {task.source}
        </span>
      </figcaption>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full overflow-visible"
        role="img"
        aria-label={`${task.task}: score against total output tokens for ${sorted
          .map((s) => `${s.agents} agent${s.agents > 1 ? "s" : ""}`)
          .join(", ")}. Swarm lambda ${fmtLambda(task.lambda)}, ${ciLabel}.`}
      >
        {/* Faint score guides */}
        {[0, 0.5, 1].map((s) => (
          <g key={s}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(s)} y2={y(s)} stroke="#fff" strokeOpacity={s === 0 ? 0 : 0.06} />
            <text x={PAD.left - 10} y={y(s) + 4} textAnchor="end" fontSize={11} fill="#6b6b6b">
              {s * 100}%
            </text>
          </g>
        ))}

        {/* Baseline + x ticks */}
        <line x1={PAD.left - 4} x2={W - PAD.right + 24} y1={y(0) + 8} y2={y(0) + 8} stroke="#3a3a3a" />
        {ticks.map((t) => (
          <text key={t} x={x(t)} y={H - 10} textAnchor="middle" fontSize={12} fill="#8a8a8a">
            {fmtTokens(t)}
          </text>
        ))}

        {/* Highlight marker at the biggest swarm's top effort */}
        <line x1={sx} x2={sx} y1={30} y2={y(0) + 8} stroke="#fff" strokeOpacity={0.35} strokeDasharray="1.5 3" />
        <text x={sx} y={22} textAnchor="end" fontSize={17} fontWeight={700} fill="#fff">
          λ {fmtLambda(task.lambda)}
        </text>
        <g transform={`translate(${sx + 6}, 4)`}>
          <rect width={64} height={18} rx={9} fill="#fff" />
          <text x={32} y={12.5} textAnchor="middle" fontSize={10} fontWeight={700} fill="#000">
            {swarm.agents} agents
          </text>
        </g>
        <text x={sx} y={H - 10} textAnchor="middle" fontSize={12} fontWeight={700} fill="#fff">
          {fmtTokens(swarmEnd[0])}
        </text>

        {/* Lines: dim middle swarms first, then solo, then the biggest swarm on top */}
        {[...middle, solo, swarm].map((s) => (
          <path
            key={s.agents}
            d={path(s.points)}
            fill="none"
            stroke={colorFor(s.agents)}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
        {[...middle, solo, swarm].flatMap((s) =>
          s.points.map(([t, sc], i) => (
            <circle
              key={`${s.agents}-${i}`}
              cx={x(t)}
              cy={y(sc)}
              r={i === s.points.length - 1 ? 4.5 : 2.5}
              fill={colorFor(s.agents)}
            />
          )),
        )}

        {/* Dashed callouts on the end points being compared */}
        <circle cx={x(soloEnd[0])} cy={y(soloEnd[1])} r={13} fill="none" stroke={ORANGE} strokeWidth={1.2} strokeDasharray="3 3" />
        <circle cx={sx} cy={y(swarmEnd[1])} r={24} fill="none" stroke={ORANGE} strokeWidth={1.2} strokeDasharray="3 3" />

        {/* End-point score labels */}
        <text x={x(soloEnd[0])} y={y(soloEnd[1]) - 19} textAnchor="middle" fontSize={11} fill={LIGHT}>
          {Math.round(soloEnd[1] * 100)}%
        </text>
        <text x={sx + 30} y={y(swarmEnd[1]) + 4} fontSize={12} fontWeight={700} fill={ORANGE}>
          {Math.round(swarmEnd[1] * 100)}%
        </text>
      </svg>

      <ul className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-white/70">
        {sorted.map((s) => (
          <li key={s.agents} className="flex items-center gap-2">
            <span className="size-2.5 rounded-full" style={{ background: colorFor(s.agents) }} />
            {s.agents === 1 ? "1 agent" : `${s.agents} agents`}
          </li>
        ))}
        <li className="text-white/40">{ciLabel}</li>
      </ul>
    </figure>
  );
}
