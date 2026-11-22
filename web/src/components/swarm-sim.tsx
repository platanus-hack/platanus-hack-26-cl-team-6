"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCanvasAnimation } from "./use-animation";

// DUMMY DATA. A simulated 48-agent swarm: every dot is an agent, every cluster
// is what it is doing right now. Agents move between activities at random;
// some messages get flagged, and flagged claims sometimes get repeated by
// other agents. Replace with a real run when we have one.

const ORANGE = "#ff5a1f";
const COLORS = ["#2f6bff", "#3b82ff", "#19c9e6", "#1fd6a0", "#d35cff"];
const N = 48;
const START = 9 * 60; // 09:00, in minutes
const LENGTH = 4 * 60; // the run lasts four simulated hours, then restarts

// Index 2 sits on the right of the ring, where the eye lands.
const STATES = [
  "Reading source",
  "Drafting",
  "Flagged",
  "Citing",
  "Discussing",
  "Repeating others",
  "Idle",
] as const;
const [READ, DRAFT, FLAG, CITE, TALK, REPEAT, IDLE] = [0, 1, 2, 3, 4, 5, 6];

// Where an agent goes next: [state, weight].
const NEXT: Record<number, [number, number][]> = {
  [READ]: [[DRAFT, 6], [TALK, 3], [IDLE, 1]],
  [DRAFT]: [[CITE, 4], [TALK, 3], [REPEAT, 2], [IDLE, 1]],
  [CITE]: [[DRAFT, 4], [TALK, 4], [READ, 2]],
  [TALK]: [[DRAFT, 3], [REPEAT, 3], [READ, 2], [IDLE, 2]],
  [REPEAT]: [[TALK, 5], [DRAFT, 5]],
  [IDLE]: [[READ, 4], [TALK, 4], [DRAFT, 2]],
  [FLAG]: [[TALK, 5], [DRAFT, 5]],
};

const SPEEDS = [
  { label: "Slow", v: 0.6 },
  { label: "Medium", v: 1.6 },
  { label: "Fast", v: 4.5 },
];

type Agent = {
  state: number;
  until: number; // sim minute when it moves on
  x: number;
  y: number;
  a: number; // fixed spot inside a cluster (angle, radius fraction)
  u: number;
  flaggedAt: number; // real seconds, for the pulse
};

type Flag = { time: number; agent: number; from?: number; born: number };

type Sim = {
  time: number;
  agents: Agent[];
  flags: Flag[];
  messages: number;
  flagged: number;
  last: number;
  placed: boolean;
};

type Snap = {
  time: number;
  counts: number[];
  messages: number;
  flagged: number;
  recent: Flag[];
};

const rand = (a: number, b: number) => a + Math.random() * (b - a);

function pick(options: [number, number][]) {
  const total = options.reduce((s, [, w]) => s + w, 0);
  let x = Math.random() * total;
  for (const [s, w] of options) {
    x -= w;
    if (x <= 0) return s;
  }
  return options[0][0];
}

function makeSim(): Sim {
  return {
    time: START,
    agents: Array.from({ length: N }, () => ({
      state: Math.random() < 0.6 ? READ : IDLE,
      until: START + rand(2, 14),
      x: 0,
      y: 0,
      a: rand(0, Math.PI * 2),
      u: Math.random(),
      flaggedAt: -10,
    })),
    flags: [],
    messages: 0,
    flagged: 0,
    last: 0,
    placed: false,
  };
}

function flag(sim: Sim, i: number, now: number, from?: number) {
  const a = sim.agents[i];
  a.state = FLAG;
  a.until = sim.time + rand(6, 12);
  a.flaggedAt = now;
  sim.flagged++;
  sim.flags.push({ time: sim.time, agent: i, from, born: now });
}

function advance(sim: Sim, minutes: number, now: number) {
  sim.time += minutes;
  sim.agents.forEach((a, i) => {
    if (sim.time < a.until) return;
    const next = pick(NEXT[a.state]);
    if (next !== IDLE) sim.messages++;

    if (next === REPEAT) {
      // Copying a recent flagged claim from someone else.
      const recent = sim.flags.filter((f) => sim.time - f.time < 20 && f.agent !== i);
      if (recent.length && Math.random() < 0.35) {
        const f = recent[Math.floor(Math.random() * recent.length)];
        return flag(sim, i, now, f.from ?? f.agent);
      }
    }
    if ((next === DRAFT || next === REPEAT) && Math.random() < 0.035) {
      return flag(sim, i, now);
    }
    a.state = next;
    a.until = sim.time + rand(4, 15);
  });
}

const clock = (m: number) =>
  `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(Math.floor(m % 60)).padStart(2, "0")}`;

function caption(f?: Flag) {
  if (!f) return "Agents are reading the source and starting their drafts.";
  return f.from === undefined
    ? `Agent ${f.agent + 1} posted a claim the source doesn't support. Flagged.`
    : `Agent ${f.agent + 1} repeated Agent ${f.from + 1}'s unsupported claim. Flagged.`;
}

// Cluster centres on an ellipse, as fractions of the canvas.
const angle = (s: number) => -Math.PI / 2 + (s / STATES.length) * Math.PI * 2;
const ring = (s: number, rx: number, ry: number) =>
  [0.5 + rx * Math.cos(angle(s)), 0.5 + ry * Math.sin(angle(s))] as const;

export function SwarmSim() {
  const ref = useRef<HTMLCanvasElement>(null);
  const sim = useRef<Sim>(makeSim());
  const speed = useRef(SPEEDS[1].v);
  const [speedIdx, setSpeedIdx] = useState(1);
  const [snap, setSnap] = useState<Snap | null>(null);

  const draw = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    let s = sim.current;
    const dt = Math.min(0.1, Math.max(0, t - s.last));
    s.last = t;
    advance(s, dt * speed.current, t);
    if (s.time >= START + LENGTH) {
      sim.current = makeSim();
      s = sim.current;
      s.last = t;
    }

    const counts = STATES.map(() => 0);
    for (const a of s.agents) counts[a.state]++;
    const centre = STATES.map((_, i) => {
      const [fx, fy] = ring(i, 0.33, 0.35);
      return [fx * w, fy * h, 4 + 6.5 * Math.sqrt(counts[i])] as const;
    });

    // Ease each dot toward its spot in its current cluster.
    const ease = s.placed ? 1 - Math.exp(-dt * 3) : 1;
    s.placed = true;
    for (const a of s.agents) {
      const [cx, cy, r] = centre[a.state];
      const jitter = Math.sin(t * 1.3 + a.a * 5) * 1.5;
      const tx = cx + Math.cos(a.a) * Math.sqrt(a.u) * r + jitter;
      const ty = cy + Math.sin(a.a) * Math.sqrt(a.u) * r + jitter;
      a.x += (tx - a.x) * ease;
      a.y += (ty - a.y) * ease;
    }

    // A repeated claim: a short-lived line from the original agent.
    ctx.lineWidth = 1.25;
    ctx.strokeStyle = ORANGE;
    for (const f of s.flags) {
      if (f.from === undefined) continue;
      const age = t - f.born;
      if (age > 3) continue;
      const a = s.agents[f.from];
      const b = s.agents[f.agent];
      ctx.globalAlpha = 1 - age / 3;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    s.agents.forEach((a, i) => {
      const hot = a.state === FLAG;
      ctx.globalAlpha = 1;
      ctx.fillStyle = hot ? ORANGE : COLORS[i % COLORS.length];
      ctx.beginPath();
      ctx.arc(a.x, a.y, hot ? 5 : 4, 0, Math.PI * 2);
      ctx.fill();
      const age = t - a.flaggedAt;
      if (age < 1.2) {
        ctx.strokeStyle = ORANGE;
        ctx.globalAlpha = 1 - age / 1.2;
        ctx.beginPath();
        ctx.arc(a.x, a.y, 5 + 18 * (age / 1.2), 0, Math.PI * 2);
        ctx.stroke();
      }
    });
    ctx.globalAlpha = 1;
  }, []);
  useCanvasAnimation(ref, draw);

  // The labels and side panel re-render a few times a second, not every frame.
  useEffect(() => {
    const read = () => {
      const s = sim.current;
      const counts = STATES.map(() => 0);
      for (const a of s.agents) counts[a.state]++;
      setSnap({
        time: s.time,
        counts,
        messages: s.messages,
        flagged: s.flagged,
        recent: s.flags.slice(-4).reverse(),
      });
    };
    read();
    const id = setInterval(read, 200);
    return () => clearInterval(id);
  }, []);

  const latest = snap?.recent[0];

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[240px_1fr]">
      <aside className="flex flex-col gap-6">
        <span className="font-mono text-5xl font-light tracking-tight text-white tabular-nums">
          {clock(snap?.time ?? START)}
        </span>
        <div className="flex w-fit overflow-hidden rounded-md border border-white/20 text-[11px] font-semibold tracking-wide uppercase">
          {SPEEDS.map((s, i) => (
            <button
              key={s.label}
              type="button"
              onClick={() => {
                speed.current = s.v;
                setSpeedIdx(i);
              }}
              className={`cursor-pointer px-3 py-1.5 transition-colors ${
                i === speedIdx ? "bg-white text-black" : "text-white/60 hover:text-white"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <p className="min-h-[3.5rem] text-sm leading-relaxed text-white/75" aria-live="polite">
          {caption(latest)}
        </p>
        <div className="flex flex-col gap-1 border-t border-white/15 pt-4 font-mono text-xs text-white/55 tabular-nums">
          <span>{snap?.messages ?? 0} messages scored</span>
          <span style={{ color: ORANGE }}>{snap?.flagged ?? 0} flagged</span>
        </div>
        {!!snap?.recent.length && (
          <ul className="flex flex-col gap-2 text-xs text-white/50">
            {snap.recent.map((f) => (
              <li key={`${f.time}-${f.agent}`} className="flex gap-2">
                <span className="font-mono text-white/35">{clock(f.time)}</span>
                <span>
                  Agent {f.agent + 1}
                  {f.from !== undefined && ` ← Agent ${f.from + 1}`}
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-auto text-[11px] leading-relaxed text-white/35">
          Dummy data: a simulated swarm of {N} agents. Each dot is an agent, each cluster is what
          it&apos;s doing right now.
        </p>
      </aside>

      <div className="relative h-[520px] w-full md:h-[640px]">
        <canvas
          ref={ref}
          role="img"
          aria-label={`Simulated swarm of ${N} agents grouped by activity. Flagged agents turn orange.`}
          className="absolute inset-0 h-full w-full"
        />
        {STATES.map((name, i) => {
          const [fx, fy] = ring(i, 0.45, 0.47);
          const pct = snap ? Math.round((snap.counts[i] / N) * 100) : 0;
          return (
            <div
              key={name}
              className="pointer-events-none absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center text-center font-mono text-[11px] leading-tight"
              style={{
                left: `${fx * 100}%`,
                top: `${fy * 100}%`,
                color: i === FLAG ? ORANGE : "rgba(255,255,255,0.7)",
              }}
            >
              <span className={i === FLAG ? "font-semibold" : ""}>{name}</span>
              <span className="text-white/45">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
