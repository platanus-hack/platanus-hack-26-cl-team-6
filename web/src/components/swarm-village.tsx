"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCanvasAnimation } from "./use-animation";

// AI Village's Swarm Village: 133 GLM 5.3 Flash agents in one shared chat for
// 24 hours (Aug 29-30 2026), with Jev's real scores on every message
// (jev-swarm/scripts/export_run.py --dataset swarm). Each dot is an agent,
// grouped by the Greek letter in its name. An agent whose latest message Jev
// flags moves to the centre for a while. There is no answer key, so flags are
// Jev's verdicts, not confirmed errors. The dataset's terms forbid
// redistribution, so the site ships only Jev's scores and who-named-whom
// timing, never message text.

const ORANGE = "#ff5a1f";
const HOLD = 30; // simulated minutes a flagged agent stays in the centre
const SPEEDS = [
  { label: "Slow", v: 8 },
  { label: "Medium", v: 25 },
  { label: "Fast", v: 70 },
];
// The agents are literally named after colours.
const HUE: Record<string, string> = {
  red: "#ff4d5e",
  blue: "#2f6bff",
  green: "#1fd6a0",
  amber: "#ffb020",
  coral: "#ff7f6e",
  jade: "#00a878",
  onyx: "#8a8f98",
  pearl: "#e8e4dc",
  ruby: "#e0115f",
  sage: "#9cb380",
  teal: "#19c9e6",
  violet: "#a970ff",
};

type Row = [t: number, agent: number, fab: number, trust: number, refs: number[]];
type Data = { threshold: number; start: string; phase2: number; agents: string[]; messages: Row[] };

type Model = {
  d: Data;
  length: number;
  groups: string[];
  group: number[]; // agent -> group index
  slot: number[]; // agent -> position inside its group
  colour: string[];
  byAgent: number[][]; // agent -> message indices in time order
  flagged: boolean[];
};

function build(d: Data): Model {
  const groups: string[] = [];
  const group: number[] = [];
  const slot: number[] = [];
  const used: number[] = [];
  d.agents.forEach((name) => {
    const g = name.split("-")[1] ?? "other";
    let gi = groups.indexOf(g);
    if (gi < 0) {
      gi = groups.push(g) - 1;
      used.push(0);
    }
    group.push(gi);
    slot.push(used[gi]++);
  });
  const byAgent = d.agents.map(() => [] as number[]);
  d.messages.forEach((m, i) => byAgent[m[1]].push(i));
  return {
    d,
    length: Math.ceil(d.messages[d.messages.length - 1][0] + 5),
    groups,
    group,
    slot,
    colour: d.agents.map((n) => HUE[n.split("-")[0]] ?? "#ffffff"),
    byAgent,
    flagged: d.messages.map((m) => Math.max(m[2], m[3]) >= d.threshold),
  };
}

const visibleCount = (rows: Row[], time: number) => {
  let lo = 0;
  let hi = rows.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (rows[mid][0] <= time) lo = mid + 1;
    else hi = mid;
  }
  return lo;
};

/** The agent's latest message at this time, or -1. */
function latest(M: Model, agent: number, time: number) {
  const list = M.byAgent[agent];
  let lo = 0;
  let hi = list.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (M.d.messages[list[mid]][0] <= time) {
      ans = list[mid];
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans;
}

const isHot = (M: Model, agent: number, time: number) => {
  const i = latest(M, agent, time);
  return i >= 0 && M.flagged[i] && time - M.d.messages[i][0] < HOLD;
};

function clock(M: Model, minutes: number) {
  const d = new Date(new Date(M.d.start).getTime() + minutes * 60_000);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

const GOLDEN = Math.PI * (3 - Math.sqrt(5));
const pack = (k: number, spacing: number) => {
  const r = spacing * Math.sqrt(k + 0.5);
  return [Math.cos(k * GOLDEN) * r, Math.sin(k * GOLDEN) * r] as const;
};
const groupAngle = (g: number, n: number) => -Math.PI / 2 + (g / n) * Math.PI * 2;

function Meter({ label, value, t }: { label: string; value: number; t: number }) {
  const hot = value >= t;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between text-[11px]">
        <span className="text-white/50">{label}</span>
        <span className="font-mono tabular-nums" style={{ color: hot ? ORANGE : "rgba(255,255,255,0.8)" }}>
          {value.toFixed(2)}
        </span>
      </div>
      <div className="relative h-1 rounded-full bg-white/10">
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{ width: `${value * 100}%`, backgroundColor: hot ? ORANGE : "rgba(255,255,255,0.6)" }}
        />
        <div className="absolute -inset-y-1 w-px bg-white/60" style={{ left: `${t * 100}%` }} aria-hidden />
      </div>
    </div>
  );
}

type Particle = { a: number; b: number; p: number; bad: boolean; bow: number };
type Sim = {
  time: number;
  playing: boolean;
  speed: number;
  last: number;
  shown: number;
  pos: { x: number; y: number }[];
  placed: boolean;
  spoke: number[]; // real seconds the agent last posted
  parts: Particle[];
  pointer: { x: number; y: number } | null;
  hover: number;
};
type Snap = { time: number; shown: number; flags: number; agentsFlagged: number; hot: number; recent: number[] };

export function SwarmVillage() {
  const [M, setM] = useState<Model | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    fetch("/data/swarm-village.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d: Data) => setM(build(d)))
      .catch(() => setError(true));
  }, []);
  if (error)
    return (
      <p className="py-24 text-center text-sm text-white/50">
        The 133-agent run isn&apos;t available here yet.
      </p>
    );
  if (!M) return <p className="py-24 text-center text-sm text-white/50">Loading 3,843 messages…</p>;
  return <Village M={M} />;
}

function Village({ M }: { M: Model }) {
  const T = M.d.threshold;
  const ref = useRef<HTMLCanvasElement>(null);
  const sim = useRef<Sim>({
    time: 0,
    playing: true,
    speed: SPEEDS[1].v,
    last: 0,
    shown: 0,
    pos: M.d.agents.map(() => ({ x: 0, y: 0 })),
    placed: false,
    spoke: M.d.agents.map(() => -10),
    parts: [],
    pointer: null,
    hover: -1,
  });
  const [playing, setPlaying] = useState(true);
  const [speedIdx, setSpeedIdx] = useState(1);
  const [snap, setSnap] = useState<Snap | null>(null);
  const [hover, setHover] = useState<{ agent: number; x: number; y: number; flip: boolean; below: boolean } | null>(
    null,
  );

  const draw = useCallback(
    (ctx: CanvasRenderingContext2D, w: number, h: number, t: number) => {
      const s = sim.current;
      const rows = M.d.messages;
      const dt = Math.min(0.1, Math.max(0, t - s.last));
      s.last = t;
      if (s.playing) {
        s.time = Math.min(M.length, s.time + dt * s.speed);
        if (s.time >= M.length) {
          s.playing = false;
          setPlaying(false);
        }
      }

      const shown = visibleCount(rows, s.time);
      if (shown > s.shown && shown - s.shown < 40) {
        for (let k = s.shown; k < shown; k++) {
          const [, a, fab, trust, refs] = rows[k];
          s.spoke[a] = t;
          const bad = Math.max(fab, trust) >= T;
          for (const b of refs.slice(0, 3))
            s.parts.push({ a: b, b: a, p: 0, bad, bow: Math.sin(k * 12.9898) * 50 });
        }
      }
      s.shown = shown;

      // Targets: groups on a ring, flagged agents in the centre.
      const n = M.groups.length;
      const hot = M.d.agents.map((_, a) => isHot(M, a, s.time));
      let centreSlot = 0;
      const target = M.d.agents.map((_, a) => {
        if (hot[a]) {
          const [ox, oy] = pack(centreSlot++, 9);
          return [w / 2 + ox, h / 2 + oy] as const;
        }
        const ang = groupAngle(M.group[a], n);
        const [ox, oy] = pack(M.slot[a], 9);
        return [w / 2 + Math.cos(ang) * w * 0.36 + ox, h / 2 + Math.sin(ang) * h * 0.37 + oy] as const;
      });
      const ease = s.placed ? 1 - Math.exp(-dt * 3) : 1;
      s.placed = true;
      s.pos.forEach((p, a) => {
        p.x += (target[a][0] - p.x) * ease;
        p.y += (target[a][1] - p.y) * ease;
      });

      // Mentions: a particle from the agent named to the agent who named it.
      ctx.lineCap = "round";
      for (const p of s.parts) {
        p.p += dt * (p.bad ? 0.8 : 1.3);
        const a = s.pos[p.a];
        const b = s.pos[p.b];
        const mx = (a.x + b.x) / 2 - (b.y - a.y) * (p.bow / 300);
        const my = (a.y + b.y) / 2 + (b.x - a.x) * (p.bow / 300);
        const at = (u: number) => {
          const v = 1 - u;
          return [v * v * a.x + 2 * v * u * mx + u * u * b.x, v * v * a.y + 2 * v * u * my + u * u * b.y] as const;
        };
        ctx.strokeStyle = p.bad ? ORANGE : M.colour[p.b];
        ctx.lineWidth = p.bad ? 1.5 : 1;
        ctx.globalAlpha = p.bad ? 0.9 : 0.3;
        ctx.beginPath();
        for (let k = 0; k <= 6; k++) {
          const [x, y] = at(Math.max(0, Math.min(1, p.p - 0.2 + (k / 6) * 0.2)));
          if (k === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
        const [hx, hy] = at(Math.min(1, p.p));
        ctx.fillStyle = p.bad ? ORANGE : "#fff";
        ctx.globalAlpha = p.bad ? 1 : 0.6;
        ctx.beginPath();
        ctx.arc(hx, hy, p.bad ? 2.4 : 1.3, 0, Math.PI * 2);
        ctx.fill();
      }
      s.parts = s.parts.filter((p) => p.p < 1);

      s.pos.forEach((p, a) => {
        const since = t - s.spoke[a];
        const talking = since < 0.6 ? 1 - since / 0.6 : 0;
        ctx.globalAlpha = 1;
        ctx.fillStyle = hot[a] ? ORANGE : M.colour[a];
        if (hot[a]) ctx.fillRect(p.x - 3.5, p.y - 3.5, 7, 7);
        else {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3.2 + talking * 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
        if (talking > 0) {
          ctx.strokeStyle = hot[a] ? ORANGE : "#fff";
          ctx.lineWidth = 1;
          ctx.globalAlpha = talking * 0.8;
          ctx.beginPath();
          ctx.arc(p.x, p.y, 5 + (1 - talking) * 12, 0, Math.PI * 2);
          ctx.stroke();
        }
        if (a === s.hover) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 1.25;
          ctx.globalAlpha = 1;
          ctx.beginPath();
          ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
      ctx.globalAlpha = 1;

      let best = -1;
      if (s.pointer) {
        let bd = 64;
        s.pos.forEach((p, a) => {
          const dd = (p.x - s.pointer!.x) ** 2 + (p.y - s.pointer!.y) ** 2;
          if (dd < bd) {
            bd = dd;
            best = a;
          }
        });
      }
      if (best !== s.hover) {
        s.hover = best;
        const p = best >= 0 ? s.pos[best] : null;
        setHover(p ? { agent: best, x: p.x, y: p.y, flip: p.x > w - 340, below: p.y < 180 } : null);
      }
    },
    [M, T],
  );

  useCanvasAnimation(ref, draw);

  useEffect(() => {
    const read = () => {
      const s = sim.current;
      const shown = visibleCount(M.d.messages, s.time);
      const flaggedIdx: number[] = [];
      const who = new Set<number>();
      for (let k = 0; k < shown; k++)
        if (M.flagged[k]) {
          flaggedIdx.push(k);
          who.add(M.d.messages[k][1]);
        }
      setSnap({
        time: s.time,
        shown,
        flags: flaggedIdx.length,
        agentsFlagged: who.size,
        hot: M.d.agents.filter((_, a) => isHot(M, a, s.time)).length,
        recent: flaggedIdx.slice(-4).reverse(),
      });
    };
    read();
    const id = setInterval(read, 200);
    return () => clearInterval(id);
  }, [M]);

  const jump = (time: number) => {
    const s = sim.current;
    s.time = Math.max(0, Math.min(M.length, time));
    s.parts = [];
  };
  const toggle = () => {
    const s = sim.current;
    if (!s.playing && s.time >= M.length) jump(0);
    s.playing = !s.playing;
    setPlaying(s.playing);
  };

  const time = snap?.time ?? 0;
  const latestFlag = snap?.recent[0];
  const hm = hover ? latest(M, hover.agent, time) : -1;
  const hrow = hm >= 0 ? M.d.messages[hm] : null;
  // One timeline tick per flagged message.
  const flagTicks = M.d.messages.map((m, i) => ({ t: m[0], i })).filter(({ i }) => M.flagged[i]);

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[240px_1fr]">
        <aside className="flex flex-col gap-6">
          <span className="font-mono text-5xl font-light tracking-tight text-white tabular-nums">
            {clock(M, time)}
            <span className="ml-2 text-sm text-white/35">UTC</span>
          </span>
          <span className="text-xs font-semibold tracking-wide text-white/45 uppercase">
            {time < M.d.phase2 ? "Phase 1 · building Earth" : "Phase 2 · playing roles"}
          </span>
          <div className="flex w-fit overflow-hidden rounded-md border border-white/20 text-[11px] font-semibold tracking-wide uppercase">
            {SPEEDS.map((sp, i) => (
              <button
                key={sp.label}
                type="button"
                onClick={() => {
                  sim.current.speed = sp.v;
                  setSpeedIdx(i);
                }}
                className={`cursor-pointer px-3 py-1.5 transition-colors ${
                  i === speedIdx ? "bg-white text-black" : "text-white/60 hover:text-white"
                }`}
              >
                {sp.label}
              </button>
            ))}
          </div>
          <p className="min-h-[4.5rem] text-sm leading-relaxed text-white/75" aria-live="polite">
            {latestFlag === undefined ? (
              "133 agents boot up and start planning a shared simulation of Earth."
            ) : (
              <>
                <span style={{ color: ORANGE }}>{M.d.agents[M.d.messages[latestFlag][1]]}</span> was flagged:
                fabrication {M.d.messages[latestFlag][2].toFixed(2)}, unverified trust{" "}
                {M.d.messages[latestFlag][3].toFixed(2)}.
              </>
            )}
          </p>
          <div className="flex flex-col gap-1 border-t border-white/15 pt-4 font-mono text-xs text-white/55 tabular-nums">
            <span>{snap?.shown ?? 0} messages scored</span>
            <span style={{ color: ORANGE }}>{snap?.flags ?? 0} flagged</span>
            <span>
              {snap?.agentsFlagged ?? 0} of {M.d.agents.length} agents flagged at least once
            </span>
          </div>
          {!!snap?.recent.length && (
            <ul className="flex flex-col gap-2 text-xs text-white/50">
              {snap.recent.map((k) => (
                <li key={k} className="flex gap-2">
                  <span className="font-mono text-white/35">{clock(M, M.d.messages[k][0])}</span>
                  <span className="truncate">{M.d.agents[M.d.messages[k][1]]}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-auto text-[11px] leading-relaxed text-white/35">
            A real run: AI Village&apos;s Swarm Village, 133 copies of GLM 5.3 Flash in one chat for 24
            hours (Aug 29–30, 2026). Each dot is an agent, grouped by the Greek letter in its name. Only
            Jev&apos;s scores are shown; the messages belong to AI Village.
          </p>
        </aside>

        <div
          className="relative h-[560px] w-full md:h-[680px]"
          onPointerMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            sim.current.pointer = { x: e.clientX - r.left, y: e.clientY - r.top };
          }}
          onPointerLeave={() => {
            sim.current.pointer = null;
          }}
        >
          <canvas
            ref={ref}
            role="img"
            aria-label="133 AI agents grouped by name. Agents whose latest message Jev flags move to the centre."
            className="absolute inset-0 h-full w-full"
          />
          {M.groups.map((g, i) => {
            const ang = groupAngle(i, M.groups.length);
            return (
              <span
                key={g}
                className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 font-mono text-[11px] text-white/45"
                style={{
                  left: `${(0.5 + Math.cos(ang) * 0.47) * 100}%`,
                  top: `${(0.5 + Math.sin(ang) * 0.48) * 100}%`,
                }}
              >
                {g}
              </span>
            );
          })}
          <span
            className="pointer-events-none absolute -top-5 left-1/2 -translate-x-1/2 font-mono text-[11px] font-semibold"
            style={{ color: ORANGE }}
          >
            Flagged now (centre): {snap?.hot ?? 0}
          </span>

          {hover && (
            <div
              className="pointer-events-none absolute z-10 w-80 rounded-xl border border-white/15 bg-neutral-950/95 p-4 text-left shadow-2xl shadow-black/60 backdrop-blur-md"
              style={{
                left: hover.x,
                top: hover.y,
                transform: `translate(${hover.flip ? "calc(-100% - 16px)" : "16px"}, ${hover.below ? "0" : "-50%"})`,
              }}
            >
              <div className="flex items-center gap-2 text-xs">
                <span className="size-2 rounded-full" style={{ backgroundColor: M.colour[hover.agent] }} aria-hidden />
                <span className="font-semibold text-white">{M.d.agents[hover.agent]}</span>
                {hrow && <span className="font-mono text-white/35">{clock(M, hrow[0])}</span>}
              </div>
              {hrow ? (
                <>
                  {M.flagged[hm] && (
                    <p className="mt-2 text-xs font-medium" style={{ color: ORANGE }}>
                      Flagged by Jev
                    </p>
                  )}
                  <div className="mt-3 flex flex-col gap-2.5">
                    <Meter label="Fabrication" value={hrow[2]} t={T} />
                    <Meter label="Unverified trust" value={hrow[3]} t={T} />
                  </div>
                </>
              ) : (
                <p className="mt-2 text-sm text-white/50">Hasn&apos;t posted yet.</p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={toggle}
            className="w-20 cursor-pointer rounded-md border border-white/20 px-3 py-1.5 text-[11px] font-semibold tracking-wide text-white/80 uppercase transition-colors hover:border-white/40 hover:text-white"
          >
            {playing ? "Pause" : time >= M.length ? "Replay" : "Play"}
          </button>
          <div
            role="slider"
            aria-label="Run timeline"
            aria-valuemin={0}
            aria-valuemax={M.length}
            aria-valuenow={Math.round(time)}
            aria-valuetext={`${clock(M, time)} UTC`}
            tabIndex={0}
            onClick={(e) => {
              const r = e.currentTarget.getBoundingClientRect();
              jump(((e.clientX - r.left) / r.width) * M.length);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") jump(sim.current.time + 30);
              if (e.key === "ArrowLeft") jump(sim.current.time - 30);
            }}
            className="relative h-8 flex-1 cursor-pointer outline-none"
          >
            <div className="absolute inset-x-0 top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-white/10" />
            <div
              className="absolute top-1/2 left-0 h-0.5 -translate-y-1/2 rounded-full bg-white/40"
              style={{ width: `${(time / M.length) * 100}%` }}
            />
            {flagTicks.map(({ t, i }) => (
              <span
                key={i}
                className="absolute top-1/2 w-px -translate-x-1/2 -translate-y-1/2"
                style={{
                  left: `${(t / M.length) * 100}%`,
                  height: time >= t ? 14 : 8,
                  backgroundColor: time >= t ? ORANGE : "rgba(255,255,255,0.2)",
                }}
              />
            ))}
            <span
              className="absolute top-0 bottom-0 w-px bg-white/30"
              style={{ left: `${(M.d.phase2 / M.length) * 100}%` }}
              title="Phase 2 starts"
            />
            <span
              className="absolute top-1/2 h-4 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-[0_0_10px_rgba(255,255,255,0.6)]"
              style={{ left: `${(time / M.length) * 100}%` }}
            />
          </div>
          <span className="w-28 text-right font-mono text-xs text-white/45 tabular-nums">
            {snap?.shown ?? 0} / {M.d.messages.length}
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-white/50">
          <span className="flex items-center gap-2">
            <span className="size-2.5" style={{ backgroundColor: ORANGE }} /> latest message flagged by Jev
          </span>
          <span className="flex items-center gap-2">
            <span className="h-3 w-px" style={{ backgroundColor: ORANGE }} /> one flagged message
          </span>
          <span className="flex items-center gap-2">
            <span className="h-3 w-px bg-white/30" /> phase 2 starts
          </span>
          <span className="flex items-center gap-2">
            <span className="w-5 border-t-2 border-white/40" /> one agent naming another
          </span>
        </div>
      </div>
    </div>
  );
}
