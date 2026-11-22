"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCanvasAnimation } from "./use-animation";
import metrRun from "@/data/metr-run.json";
import hfRun from "@/data/hf-run.json";

// Real runs (jev-swarm/scripts/export_run.py): the METR hard set, and the same
// set re-made around the Hugging Face malicious-models incident
// (jev-swarm/scripts/make_hf.py). Each dot is one message, grouped by the
// agent that sent it. A message moves to the
// Flagged cluster in the centre when either of Jev's real scores reaches the
// threshold. Planted errors come from the answer key, which Jev never sees.

const ORANGE = "#ff5a1f";
const T = metrRun.threshold;
const AGENTS = metrRun.agents;
const COLOR: Record<string, string> = {
  Atlas: "#2f6bff",
  Birch: "#1fd6a0",
  Cedar: "#19c9e6",
  Delta: "#d35cff",
  Echo: "#3b82ff",
};
const CENTER = AGENTS.length; // cluster index of "Flagged"

type Raw = (typeof metrRun.seeds)[number]["messages"][number];
type Msg = Raw & {
  planted?: { type: string; truth: string };
  from?: number;
  flagged: boolean;
  slot: number; // position inside its cluster, in arrival order
  cluster: number;
};
type SetId = "metr" | "hf";
type Seed = { set: SetId; seed: number; calibration: boolean; start: string; msgs: Msg[]; length: number };

const DATASETS: { id: SetId; label: string; run: typeof metrRun; order: number[]; intro: string; note: string }[] = [
  {
    id: "metr",
    label: "METR report",
    run: metrRun,
    order: [2, 3, 1], // headline seeds first, calibration seed last
    intro: "Atlas fetches the source. The others start pulling claims from it.",
    note: "Five agents write a briefing on METR's AI R&D assessment, with 18 planted errors. *Seed 1 is where the 0.85 threshold was picked.",
  },
  {
    id: "hf",
    label: "Hugging Face incident",
    run: hfRun as typeof metrRun,
    order: [1, 2, 3],
    intro: "Atlas fetches the JFrog and ReversingLabs reports. The others start pulling claims from them.",
    note: "The same test, re-made around the malicious models found on the Hugging Face Hub (JFrog, 2024; ReversingLabs, 2025), with 18 planted errors per run. The threshold was not tuned on this set.",
  },
];

const SEEDS: Seed[] = DATASETS.flatMap((d) => d.run.seeds.map((s) => {
  const used = Array(AGENTS.length + 1).fill(0);
  const msgs = (s.messages as Raw[]).map((m) => {
    const flagged = Math.max(m.fab, m.trust) >= T;
    const cluster = flagged ? CENTER : AGENTS.indexOf(m.actor);
    return { ...m, flagged, cluster, slot: used[cluster]++ } as Msg;
  });
  return {
    set: d.id,
    seed: s.seed,
    calibration: s.calibration,
    start: s.start,
    msgs,
    length: Math.ceil(msgs[msgs.length - 1].t + 2),
  };
}));
const ORDER = Object.fromEntries(
  DATASETS.map((d) => [d.id, d.order.map((n) => SEEDS.findIndex((s) => s.set === d.id && s.seed === n))]),
) as Record<SetId, number[]>;
const dataset = (id: SetId) => DATASETS.find((d) => d.id === id)!;

const SPEEDS = [
  { label: "Slow", v: 2 },
  { label: "Medium", v: 5 },
  { label: "Fast", v: 12 },
];

const KIND: Record<string, string> = {
  numeric: "a wrong number",
  textual: "a wrong attribution",
  mixed: "a wrong claim",
};

function clock(seed: Seed, minutes: number) {
  const d = new Date(new Date(seed.start).getTime() + minutes * 60_000);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

function caption(seed: Seed, i?: number) {
  if (i === undefined) return dataset(seed.set).intro;
  const m = seed.msgs[i];
  if (!m.planted) return `${m.actor} was flagged on a correct message: a false alarm.`;
  if (m.from !== undefined)
    return `${m.actor} repeated ${seed.msgs[m.from].actor}'s error as fact. Flagged.`;
  return `${m.actor} posted ${KIND[m.planted.type] ?? "a wrong claim"}. Flagged.`;
}

const visibleCount = (msgs: Msg[], time: number) => {
  let lo = 0;
  let hi = msgs.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (msgs[mid].t <= time) lo = mid + 1;
    else hi = mid;
  }
  return lo;
};

// Agents on a ring, Flagged in the middle.
const ringAngle = (c: number) => -Math.PI / 2 + (c / AGENTS.length) * Math.PI * 2;
function clusterCentre(c: number, w: number, h: number) {
  if (c === CENTER) return [w / 2, h / 2] as const;
  return [w / 2 + Math.cos(ringAngle(c)) * w * 0.34, h / 2 + Math.sin(ringAngle(c)) * h * 0.36] as const;
}
const GOLDEN = Math.PI * (3 - Math.sqrt(5));
const SPACING = 7.5;
function slotOffset(k: number) {
  const r = SPACING * Math.sqrt(k + 0.5);
  return [Math.cos(k * GOLDEN) * r, Math.sin(k * GOLDEN) * r] as const;
}

type Particle = { a: number; b: number; p: number; bad: boolean; bow: number };
type Sim = {
  seed: number; // index into SEEDS
  time: number;
  playing: boolean;
  speed: number;
  last: number;
  shown: number;
  pos: { x: number; y: number; placed: boolean }[];
  arrived: Map<number, number>;
  parts: Particle[];
  pointer: { x: number; y: number } | null;
  hover: number;
};
type Snap = {
  time: number;
  shown: number;
  flagged: number;
  caught: number;
  reached: number;
  falseAlarms: number;
  recent: number[];
  counts: number[];
};
type Hover = { i: number; x: number; y: number; flip: boolean; below: boolean } | null;

function Meter({ label, value }: { label: string; value: number }) {
  const hot = value >= T;
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
        <div className="absolute -inset-y-1 w-px bg-white/60" style={{ left: `${T * 100}%` }} aria-hidden />
      </div>
    </div>
  );
}

const freshPos = (n: number) => Array.from({ length: n }, () => ({ x: 0, y: 0, placed: false }));

export function SwarmSim() {
  const ref = useRef<HTMLCanvasElement>(null);
  const sim = useRef<Sim>({
    seed: ORDER.metr[0],
    time: 0,
    playing: true,
    speed: SPEEDS[1].v,
    last: 0,
    shown: 0,
    pos: freshPos(SEEDS[ORDER.metr[0]].msgs.length),
    arrived: new Map(),
    parts: [],
    pointer: null,
    hover: -1,
  });
  const [seedIdx, setSeedIdx] = useState(ORDER.metr[0]);
  const [playing, setPlaying] = useState(true);
  const [speedIdx, setSpeedIdx] = useState(1);
  const [snap, setSnap] = useState<Snap | null>(null);
  const [hover, setHover] = useState<Hover>(null);

  const draw = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    const s = sim.current;
    const seed = SEEDS[s.seed];
    const msgs = seed.msgs;
    const dt = Math.min(0.1, Math.max(0, t - s.last));
    s.last = t;

    if (s.playing) {
      s.time = Math.min(seed.length, s.time + dt * s.speed);
      if (s.time >= seed.length) {
        s.playing = false;
        setPlaying(false);
      }
    }

    const shown = visibleCount(msgs, s.time);
    const live = shown > s.shown && shown - s.shown < 20; // playback, not a jump
    if (live) {
      for (let k = s.shown; k < shown; k++) {
        const m = msgs[k];
        s.arrived.set(k, t);
        const bow = Math.sin(k * 12.9898) * 50;
        if (m.from !== undefined) s.parts.push({ a: m.from, b: k, p: 0, bad: true, bow });
        else if (k > 0) s.parts.push({ a: k - 1, b: k, p: 0, bad: false, bow });
      }
    }
    if (shown < s.shown) s.arrived.clear();
    s.shown = shown;

    // Ease every visible message toward its slot. New ones start at their
    // agent's cluster, so a flagged message is seen leaving it for the centre.
    const ease = 1 - Math.exp(-dt * 4);
    for (let k = 0; k < shown; k++) {
      const m = msgs[k];
      const [cx, cy] = clusterCentre(m.cluster, w, h);
      const [ox, oy] = slotOffset(m.slot);
      const p = s.pos[k];
      if (!p.placed) {
        const [ax, ay] = clusterCentre(AGENTS.indexOf(m.actor), w, h);
        p.x = live ? ax : cx + ox;
        p.y = live ? ay : cy + oy;
        p.placed = true;
      }
      p.x += (cx + ox - p.x) * ease;
      p.y += (cy + oy - p.y) * ease;
    }
    for (let k = shown; k < msgs.length; k++) s.pos[k].placed = false;

    // A repeated error stays linked to the message it came from.
    ctx.lineWidth = 0.75;
    ctx.strokeStyle = ORANGE;
    ctx.globalAlpha = 0.35;
    ctx.setLineDash([3, 4]);
    for (let k = 0; k < shown; k++) {
      const m = msgs[k];
      if (m.from === undefined) continue;
      const a = s.pos[m.from];
      const b = s.pos[k];
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    // Particles: each new message travels in from the one before it; an
    // orange one carries a repeated error from where it started.
    const bez = (a: { x: number; y: number }, b: { x: number; y: number }, bow: number, u: number) => {
      const mx = (a.x + b.x) / 2 - (b.y - a.y) * (bow / 300);
      const my = (a.y + b.y) / 2 + (b.x - a.x) * (bow / 300);
      const v = 1 - u;
      return [v * v * a.x + 2 * v * u * mx + u * u * b.x, v * v * a.y + 2 * v * u * my + u * u * b.y] as const;
    };
    ctx.lineCap = "round";
    for (const p of s.parts) {
      p.p += dt * (p.bad ? 0.7 : 1.4);
      const a = s.pos[p.a];
      const b = s.pos[p.b];
      ctx.strokeStyle = p.bad ? ORANGE : COLOR[msgs[p.b].actor];
      ctx.lineWidth = p.bad ? 1.5 : 1;
      ctx.globalAlpha = p.bad ? 0.9 : 0.4;
      ctx.beginPath();
      for (let k = 0; k <= 6; k++) {
        const u = Math.max(0, Math.min(1, p.p - 0.2 + (k / 6) * 0.2));
        const [x, y] = bez(a, b, p.bow, u);
        if (k === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      const [hx, hy] = bez(a, b, p.bow, Math.min(1, p.p));
      ctx.fillStyle = p.bad ? ORANGE : "#fff";
      ctx.globalAlpha = p.bad ? 1 : 0.7;
      ctx.beginPath();
      ctx.arc(hx, hy, p.bad ? 2.5 : 1.4, 0, Math.PI * 2);
      ctx.fill();
    }
    s.parts = s.parts.filter((p) => p.p < 1);

    // Messages.
    for (let k = 0; k < shown; k++) {
      const m = msgs[k];
      const p = s.pos[k];
      ctx.globalAlpha = 1;
      ctx.fillStyle = m.flagged ? ORANGE : COLOR[m.actor];
      if (m.flagged) ctx.fillRect(p.x - 3, p.y - 3, 6, 6);
      else {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
        ctx.fill();
      }
      if (m.planted) {
        // Answer key: a white ring on every planted error, caught or not.
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.85;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 5.5, 0, Math.PI * 2);
        ctx.stroke();
      }
      const at = m.flagged ? s.arrived.get(k) : undefined;
      if (at !== undefined && t - at < 1.2) {
        const age = (t - at) / 1.2;
        ctx.strokeStyle = ORANGE;
        ctx.lineWidth = 1.25;
        ctx.globalAlpha = 1 - age;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 5 + 20 * age, 0, Math.PI * 2);
        ctx.stroke();
      }
      if (k === s.hover) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1.25;
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;

    let best = -1;
    if (s.pointer) {
      let bd = 64;
      for (let k = 0; k < shown; k++) {
        const p = s.pos[k];
        const d = (p.x - s.pointer.x) ** 2 + (p.y - s.pointer.y) ** 2;
        if (d < bd) {
          bd = d;
          best = k;
        }
      }
    }
    if (best !== s.hover) {
      s.hover = best;
      const p = best >= 0 ? s.pos[best] : null;
      setHover(p ? { i: best, x: p.x, y: p.y, flip: p.x > w - 340, below: p.y < 180 } : null);
    }
  }, []);

  useCanvasAnimation(ref, draw);

  useEffect(() => {
    const read = () => {
      const s = sim.current;
      const msgs = SEEDS[s.seed].msgs;
      const shown = visibleCount(msgs, s.time);
      const flagged: number[] = [];
      const counts = Array(AGENTS.length + 1).fill(0);
      let caught = 0;
      let reached = 0;
      let falseAlarms = 0;
      for (let k = 0; k < shown; k++) {
        const m = msgs[k];
        counts[m.cluster]++;
        if (m.flagged) flagged.push(k);
        if (m.planted) {
          reached++;
          if (m.flagged) caught++;
        } else if (m.flagged) falseAlarms++;
      }
      setSnap({
        time: s.time,
        shown,
        flagged: flagged.length,
        caught,
        reached,
        falseAlarms,
        recent: flagged.slice(-4).reverse(),
        counts,
      });
    };
    read();
    const id = setInterval(read, 150);
    return () => clearInterval(id);
  }, []);

  const jump = (time: number) => {
    const s = sim.current;
    s.time = Math.max(0, Math.min(SEEDS[s.seed].length, time));
    s.parts = [];
  };

  const pickSeed = (i: number) => {
    const s = sim.current;
    s.seed = i;
    s.time = 0;
    s.shown = 0;
    s.parts = [];
    s.arrived.clear();
    s.pos = freshPos(SEEDS[i].msgs.length);
    s.hover = -1;
    s.playing = true;
    setSeedIdx(i);
    setPlaying(true);
    setHover(null);
  };

  const toggle = () => {
    const s = sim.current;
    if (!s.playing && s.time >= SEEDS[s.seed].length) jump(0);
    s.playing = !s.playing;
    setPlaying(s.playing);
  };

  const seed = SEEDS[seedIdx];
  const time = snap?.time ?? 0;
  const planted = seed.msgs.map((m, i) => ({ m, i })).filter(({ m }) => m.planted);
  const hm = hover ? seed.msgs[hover.i] : null;

  const tabs = (items: { key: string | number; label: string; on: boolean; title?: string; click: () => void }[]) => (
    <div className="flex w-fit overflow-hidden rounded-md border border-white/20 text-[11px] font-semibold tracking-wide uppercase">
      {items.map((it) => (
        <button
          key={it.key}
          type="button"
          onClick={it.click}
          title={it.title}
          className={`cursor-pointer px-3 py-1.5 transition-colors ${
            it.on ? "bg-white text-black" : "text-white/60 hover:text-white"
          }`}
        >
          {it.label}
        </button>
      ))}
    </div>
  );

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[240px_1fr]">
        <aside className="flex flex-col gap-6">
          {tabs(
            DATASETS.map((d) => ({
              key: d.id,
              label: d.label,
              on: seed.set === d.id,
              click: () => pickSeed(ORDER[d.id][0]),
            })),
          )}
          {tabs(
            ORDER[seed.set].map((i) => ({
              key: i,
              label: `Seed ${SEEDS[i].seed}${SEEDS[i].calibration ? "*" : ""}`,
              on: i === seedIdx,
              title: SEEDS[i].calibration ? "The threshold was picked on this seed" : undefined,
              click: () => pickSeed(i),
            })),
          )}
          <span className="font-mono text-5xl font-light tracking-tight text-white tabular-nums">
            {clock(seed, time)}
            <span className="ml-2 text-sm text-white/35">UTC</span>
          </span>
          {tabs(
            SPEEDS.map((sp, i) => ({
              key: sp.label,
              label: sp.label,
              on: i === speedIdx,
              click: () => {
                sim.current.speed = sp.v;
                setSpeedIdx(i);
              },
            })),
          )}
          <p className="min-h-[3.5rem] text-sm leading-relaxed text-white/75" aria-live="polite">
            {caption(seed, snap?.recent[0])}
          </p>
          <div className="flex flex-col gap-1 border-t border-white/15 pt-4 font-mono text-xs text-white/55 tabular-nums">
            <span>{snap?.shown ?? 0} messages scored</span>
            <span style={{ color: ORANGE }}>{snap?.flagged ?? 0} flagged</span>
            <span>
              {snap?.caught ?? 0} of {snap?.reached ?? 0} planted errors caught
            </span>
            <span>{snap?.falseAlarms ?? 0} false alarms</span>
          </div>
          {!!snap?.recent.length && (
            <ul className="flex flex-col gap-2 text-xs text-white/50">
              {snap.recent.map((k) => {
                const m = seed.msgs[k];
                return (
                  <li key={k} className="flex gap-2">
                    <span className="font-mono text-white/35">{clock(seed, m.t)}</span>
                    <span>
                      {m.actor}
                      {m.from !== undefined && ` ← ${seed.msgs[m.from].actor}`}
                      {!m.planted && <span className="text-white/35"> · false alarm</span>}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="mt-auto text-[11px] leading-relaxed text-white/35">
            {dataset(seed.set).note} Each dot is a message, grouped by who sent it, with Jev&apos;s
            real scores. Flagged messages move to the centre.
          </p>
        </aside>

        <div
          className="relative h-[520px] w-full md:h-[640px]"
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
            aria-label={`${dataset(seed.set).label}, seed ${seed.seed}: messages from five agents, grouped by sender. Flagged messages move to the centre.`}
            className="absolute inset-0 h-full w-full"
          />
          {[...AGENTS, "Flagged"].map((name, c) => {
            const centre = c === CENTER;
            return (
              <div
                key={name}
                className={`pointer-events-none absolute flex -translate-x-1/2 flex-col items-center text-center font-mono text-[11px] leading-tight ${
                  centre ? "top-3" : "-translate-y-1/2"
                }`}
                style={{
                  left: centre ? "50%" : `${(0.5 + Math.cos(ringAngle(c)) * 0.47) * 100}%`,
                  top: centre ? undefined : `${(0.5 + Math.sin(ringAngle(c)) * 0.48) * 100}%`,
                  color: centre ? ORANGE : COLOR[name],
                }}
              >
                <span className="font-semibold">{centre ? "Flagged (centre)" : name}</span>
                <span className="text-white/45">{snap?.counts[c] ?? 0}</span>
              </div>
            );
          })}

          {hover && hm && (
            <div
              className="pointer-events-none absolute z-10 w-80 rounded-xl border border-white/15 bg-neutral-950/95 p-4 text-left shadow-2xl shadow-black/60 backdrop-blur-md"
              style={{
                left: hover.x,
                top: hover.y,
                transform: `translate(${hover.flip ? "calc(-100% - 16px)" : "16px"}, ${hover.below ? "0" : "-50%"})`,
              }}
            >
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="size-2 rounded-full" style={{ backgroundColor: COLOR[hm.actor] }} aria-hidden />
                <span className="font-semibold text-white">{hm.actor}</span>
                <span className="font-mono text-white/35">{clock(seed, hm.t)}</span>
                <span className="ml-auto font-mono text-[10px] text-white/35">{hm.id}</span>
              </div>
              {hm.flagged && (
                <p className="mt-2 text-xs font-medium" style={{ color: ORANGE }}>
                  Flagged by Jev
                </p>
              )}
              <p
                className={`mt-2 max-h-28 overflow-hidden leading-relaxed text-white/80 [mask-image:linear-gradient(180deg,#000_75%,transparent)] ${
                  hm.fetch ? "font-mono text-[11px]" : "text-sm"
                }`}
              >
                {hm.text}
              </p>
              <div className="mt-3 flex flex-col gap-2.5">
                <Meter label="Fabrication" value={hm.fab} />
                <Meter label="Unverified trust" value={hm.trust} />
              </div>
              {hm.planted && (
                <p className="mt-3 border-t border-white/10 pt-2.5 text-[11px] leading-snug text-white/45">
                  <span className="text-white/70">
                    Planted {hm.planted.type} error
                    {hm.from !== undefined ? `, repeated from ${seed.msgs[hm.from].actor}` : ""}
                    {hm.flagged ? "" : ". Missed"}.
                  </span>{" "}
                  Correct version: {hm.planted.truth} Jev never sees this label.
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Timeline: one tick per planted error, lit once the run reaches it. */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={toggle}
            className="w-20 cursor-pointer rounded-md border border-white/20 px-3 py-1.5 text-[11px] font-semibold tracking-wide text-white/80 uppercase transition-colors hover:border-white/40 hover:text-white"
          >
            {playing ? "Pause" : time >= seed.length ? "Replay" : "Play"}
          </button>
          <div
            role="slider"
            aria-label="Run timeline"
            aria-valuemin={0}
            aria-valuemax={seed.length}
            aria-valuenow={Math.round(time)}
            aria-valuetext={`${clock(seed, time)} UTC`}
            tabIndex={0}
            onClick={(e) => {
              const r = e.currentTarget.getBoundingClientRect();
              jump(((e.clientX - r.left) / r.width) * seed.length);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") jump(sim.current.time + 5);
              if (e.key === "ArrowLeft") jump(sim.current.time - 5);
            }}
            className="relative h-8 flex-1 cursor-pointer outline-none"
          >
            <div className="absolute inset-x-0 top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-white/10" />
            <div
              className="absolute top-1/2 left-0 h-0.5 -translate-y-1/2 rounded-full bg-white/40"
              style={{ width: `${(time / seed.length) * 100}%` }}
            />
            {planted.map(({ m, i }) => {
              const reached = time >= m.t;
              const caught = reached && m.flagged;
              return (
                <span
                  key={i}
                  title={`${m.id} · ${m.actor} · ${m.planted!.type}`}
                  className="absolute top-1/2 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full transition-all duration-300"
                  style={{
                    left: `${(m.t / seed.length) * 100}%`,
                    height: reached ? 20 : 10,
                    backgroundColor: caught ? ORANGE : reached ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.25)",
                    boxShadow: caught ? `0 0 8px ${ORANGE}` : undefined,
                  }}
                />
              );
            })}
            <span
              className="absolute top-1/2 h-4 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-[0_0_10px_rgba(255,255,255,0.6)]"
              style={{ left: `${(time / seed.length) * 100}%` }}
            />
          </div>
          <span className="w-24 text-right font-mono text-xs text-white/45 tabular-nums">
            {snap?.shown ?? 0} / {seed.msgs.length}
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-white/50">
          <span className="flex items-center gap-2">
            <span className="size-2.5" style={{ backgroundColor: ORANGE }} /> flagged by Jev
          </span>
          <span className="flex items-center gap-2">
            <span className="size-3 rounded-full border border-white" /> planted error (answer key)
          </span>
          <span className="flex items-center gap-2">
            <span className="h-3 w-0.5 rounded-full" style={{ backgroundColor: ORANGE }} /> caught
          </span>
          <span className="flex items-center gap-2">
            <span className="h-3 w-0.5 rounded-full bg-white/70" /> missed
          </span>
          <span className="flex items-center gap-2">
            <span className="w-5 border-t border-dashed" style={{ borderColor: ORANGE }} /> repeated error
          </span>
        </div>
      </div>
    </div>
  );
}
