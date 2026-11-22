"use client";

import { useRef } from "react";
import { TASKS } from "@/data/swarm";
import { mulberry32, useCanvasAnimation } from "./use-animation";

const COLORS = [
  "#2f6bff",
  "#2f6bff",
  "#3b82ff",
  "#19c9e6",
  "#1fd6a0",
  "#d35cff",
];

type Curve = {
  theta: number;
  reach: number;
  bend: number;
  width: number;
  color: string;
  phase: number;
  speed: number;
};
type Label = { y: number; text: string };

function makeCurves(seed: number, count: number): Curve[] {
  const r = mulberry32(seed);
  return Array.from({ length: count }, () => ({
    // Spread around the vertical, so most curves sweep up or down the strip.
    theta: (r() < 0.5 ? -1 : 1) * (Math.PI / 2) * (0.35 + r() * 0.75),
    reach: 0.6 + r() * 0.7,
    bend: (r() - 0.5) * 1.4,
    width: 0.6 + r() * 1.8,
    color: COLORS[Math.floor(r() * COLORS.length)],
    phase: r() * Math.PI * 2,
    speed: 0.25 + r() * 0.35,
  }));
}

const LEFT = makeCurves(7, 90);
const RIGHT = makeCurves(11, 90);

const fmt = (l: number) =>
  (l < 0 ? "−" : "") + (Math.round(Math.abs(l) * 100 + 1e-6) / 100).toFixed(2);
const kTokens = (t: number) => `${Math.round(t / 1e3)}K`;
const lastTokens = (id: string) => {
  const task = TASKS.find((x) => x.id === id)!;
  const big = [...task.series].sort((a, b) => b.agents - a.agents)[0];
  return { lambda: task.lambda, tokens: big.points[big.points.length - 1][0] };
};
const ATTACK = lastTokens("secbench");
const DEFENSE = lastTokens("soc");
// Left strip = attack (SEC-Bench Pro), right strip = defense (SOC pilot).
const LEFT_LABELS: Label[] = [
  { y: 0.27, text: `λ ${fmt(ATTACK.lambda)}` },
  { y: 0.76, text: kTokens(ATTACK.tokens) },
];
const RIGHT_LABELS: Label[] = [
  { y: 0.33, text: `λ ${fmt(DEFENSE.lambda)}` },
  { y: 0.68, text: kTokens(DEFENSE.tokens) },
];

function draw(ctx: CanvasRenderingContext2D, w: number, h: number, t: number) {
  const strip = Math.max(56, Math.min(w * 0.13, 220));
  const font = getComputedStyle(document.body).fontFamily;

  const side = (curves: Curve[], labels: Label[], dir: 1 | -1) => {
    const x0 = dir === 1 ? w - strip : 0;
    const fx = dir === 1 ? x0 + 4 : strip - 4; // focal point on the strip's inner edge
    const fy = h * 0.52;

    ctx.save();
    ctx.beginPath();
    ctx.rect(x0, 0, strip, h);
    ctx.clip();

    ctx.globalCompositeOperation = "lighter";
    for (const c of curves) {
      const wob = Math.sin(t * c.speed + c.phase);
      const th = c.theta + wob * 0.06;
      const R = h * c.reach;
      // Curves leave the focal point, run outward, then bend away.
      const ex = fx + dir * Math.abs(Math.cos(th)) * R * 0.9;
      const ey = fy + Math.sin(th) * R;
      const bend = c.bend + wob * 0.15;
      const cx = fx + dir * strip * (0.2 + Math.abs(bend));
      const cy = fy + Math.sin(th) * R * (0.35 + bend * 0.2);
      ctx.strokeStyle = c.color;
      ctx.globalAlpha = 0.55;
      ctx.lineWidth = c.width;
      ctx.beginPath();
      ctx.moveTo(fx, fy);
      ctx.quadraticCurveTo(cx, cy, ex, ey);
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;

    // Dashed guide arc, gently swaying.
    const gx = fx + dir * strip * (0.55 + 0.03 * Math.sin(t * 0.4));
    ctx.setLineDash([5, 6]);
    ctx.strokeStyle = "rgba(255,255,255,0.45)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(gx + dir * 14, 0);
    ctx.quadraticCurveTo(gx - dir * 10, h * 0.5, gx + dir * 14, h);
    ctx.stroke();
    ctx.setLineDash([]);

    // Data labels with square markers, sitting on the guide.
    ctx.font = `500 15px ${font}`;
    ctx.textBaseline = "middle";
    for (const l of labels) {
      const y = h * l.y;
      const u = l.y; // position along the guide (quadratic, ends at +14, control at -10)
      const lx = gx + dir * (14 * (1 - 2 * u * (1 - u)) - 20 * u * (1 - u));
      ctx.fillStyle = "#fff";
      ctx.fillRect(lx - 2, y + 5, 4, 4);
      ctx.fillText(l.text, lx + 6, y - 2);
    }
    ctx.restore();
  };

  side(LEFT, LEFT_LABELS, -1);
  side(RIGHT, RIGHT_LABELS, 1);
}

export function HeroFans() {
  const ref = useRef<HTMLCanvasElement>(null);
  useCanvasAnimation(ref, draw);

  return (
    <canvas ref={ref} aria-hidden className="absolute inset-0 h-full w-full" />
  );
}
