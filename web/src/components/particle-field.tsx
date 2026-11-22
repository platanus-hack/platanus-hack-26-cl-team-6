"use client";

import { useRef } from "react";
import { mulberry32, useCanvasAnimation } from "./use-animation";

const TEAL = "#35d0c8";
const ORANGE = "#ff5a1f";
const YELLOW = "#ffcf3f";
const RED = "#ff7a45";

type Dot =
  | {
      kind: "ring";
      a: number;
      ring: number;
      color: string;
      jitter: number;
      phase: number;
    }
  | {
      kind: "band";
      u: number;
      band: number;
      off: number;
      color: string;
      phase: number;
      speed: number;
    };

const rand = mulberry32(2026);
const pick = <T,>(xs: T[]) => xs[Math.floor(rand() * xs.length)];

const DOTS: Dot[] = [];
// Three contour rings around a blob, like the edge of a scanned region.
const RINGS = [
  { scale: 1.0, color: TEAL, n: 150 },
  { scale: 1.07, color: ORANGE, n: 170 },
  { scale: 1.16, color: YELLOW, n: 90 },
];
RINGS.forEach((r, ring) => {
  for (let i = 0; i < r.n; i++)
    DOTS.push({
      kind: "ring",
      a: (i / r.n) * Math.PI * 2,
      ring,
      color: r.color,
      jitter: (rand() - 0.5) * 0.03,
      phase: rand() * 6.28,
    });
});
// Loose bands sweeping in from the top-left towards the blob.
for (let band = 0; band < 3; band++)
  for (let i = 0; i < 140; i++)
    DOTS.push({
      kind: "band",
      u: rand(),
      band,
      off: (rand() + rand() + rand() - 1.5) * 0.09,
      color: pick([TEAL, ORANGE, YELLOW, RED, TEAL]),
      phase: rand() * 6.28,
      speed: 0.012 + rand() * 0.012,
    });

function blob(a: number, t: number) {
  return (
    1 + 0.22 * Math.sin(2 * a + 1 + t * 0.15) + 0.08 * Math.sin(3 * a - t * 0.1)
  );
}

function draw(ctx: CanvasRenderingContext2D, w: number, h: number, t: number) {
  const cx = w * 0.84;
  const cy = h * 0.6;
  const R = Math.min(h * 0.32, w * 0.2);

  for (const d of DOTS) {
    let x: number;
    let y: number;
    if (d.kind === "ring") {
      const a = d.a + t * 0.03 * (d.ring % 2 ? -1 : 1);
      const r = R * RINGS[d.ring].scale * blob(a, t) * (1 + d.jitter);
      x = cx + Math.cos(a) * r * 0.75;
      y = cy + Math.sin(a) * r;
    } else {
      const u = (d.u + t * d.speed) % 1;
      // Each band is a gentle curve from the upper left into the blob.
      const sx = w * (0.25 + d.band * 0.12);
      const sy = -h * 0.05;
      const ex = cx - R * 0.7;
      const ey = cy - R * (0.6 - d.band * 0.35);
      const mx = (sx + ex) / 2 - h * 0.1;
      const my = (sy + ey) / 2 + h * 0.2;
      const bx = (1 - u) ** 2 * sx + 2 * u * (1 - u) * mx + u * u * ex;
      const by = (1 - u) ** 2 * sy + 2 * u * (1 - u) * my + u * u * ey;
      const spread = d.off * h * (0.5 + u);
      x = bx + spread + Math.sin(t * 0.8 + d.phase) * 2;
      y = by - spread * 0.6 + Math.cos(t * 0.7 + d.phase) * 2;
    }
    const twinkle = 0.55 + 0.45 * Math.sin(t * 1.3 + d.phase);
    ctx.globalAlpha = twinkle;
    ctx.fillStyle = d.color;
    ctx.beginPath();
    ctx.arc(x, y, 1.7, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

export function ParticleField({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useCanvasAnimation(ref, draw);
  return <canvas ref={ref} aria-hidden className={className} />;
}
