"use client";

import { useEffect, useMemo, useRef } from "react";
import { mulberry32, useCanvasAnimation } from "./use-animation";

const COLORS = ["#2f6bff", "#2f6bff", "#3b82ff", "#19c9e6", "#1fd6a0", "#d35cff"];

type Curve = {
  theta: number;
  reach: number;
  bend: number;
  width: number;
  color: string;
  phase: number;
  speed: number;
};

function makeCurves(seed: number, count: number): Curve[] {
  const r = mulberry32(seed);
  return Array.from({ length: count }, () => ({
    // Spread around the vertical, so most curves sweep up or down the strip.
    theta: (r() < 0.5 ? -1 : 1) * (Math.PI / 2) * (0.35 + r() * 0.75),
    reach: 0.6 + r() * 0.7,
    bend: (r() - 0.5) * 1.4,
    // Snap widths to a few values so curves can be stroked in batches.
    width: [0.75, 1.25, 1.75, 2.25][Math.floor(r() * 4)],
    color: COLORS[Math.floor(r() * COLORS.length)],
    phase: r() * Math.PI * 2,
    speed: 0.25 + r() * 0.35,
  }));
}

/** Curves grouped by color and width, so each group is one stroke() call. */
function group(curves: Curve[]) {
  const map = new Map<string, Curve[]>();
  for (const c of curves) {
    const key = `${c.color}|${c.width}`;
    map.set(key, [...(map.get(key) ?? []), c]);
  }
  return [...map.values()];
}

const LEFT = group(makeCurves(7, 90));
const RIGHT = group(makeCurves(11, 90));

const RADIUS = 140; // px of influence around the pointer
const PUSH = 70; // px a curve's bend is pushed away at full influence
const IDLE_FPS = 30; // the drift is slow; 30fps is indistinguishable
const HOVER_FPS = 60;

// Pointer state for one strip. `x`/`y` ease toward the real pointer (`tx`/`ty`)
// and `s` (0..1) eases toward 1 while the pointer is over the strip.
type Pointer = { tx: number; ty: number; x: number; y: number; over: boolean; s: number };

function makeDraw(groups: Curve[][], dir: 1 | -1, p: Pointer) {
  return (ctx: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    // Each canvas is exactly one strip; the focal point sits on its inner edge.
    const fx = dir === 1 ? 4 : w - 4;
    const fy = h * 0.52;

    p.x += (p.tx - p.x) * 0.2;
    p.y += (p.ty - p.y) * 0.2;
    p.s += ((p.over ? 1 : 0) - p.s) * 0.1;
    const live = p.s > 0.01;

    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Curves near the pointer get drawn one by one, brighter and thicker.
    const hot: { c: Curve; cx: number; cy: number; ex: number; ey: number; k: number }[] = [];

    for (const curves of groups) {
      ctx.strokeStyle = curves[0].color;
      ctx.lineWidth = curves[0].width;
      ctx.globalAlpha = 0.55;
      ctx.beginPath();

      for (const c of curves) {
        const wob = Math.sin(t * c.speed + c.phase);
        const th = c.theta + wob * 0.06;
        const R = h * c.reach;
        const ex = fx + dir * Math.abs(Math.cos(th)) * R * 0.9;
        const ey = fy + Math.sin(th) * R;
        const bend = c.bend + wob * 0.15;
        let cx = fx + dir * w * (0.2 + Math.abs(bend));
        let cy = fy + Math.sin(th) * R * (0.35 + bend * 0.2);

        let k = 0;
        if (live) {
          // Nearest of a few samples along the curve to the pointer.
          let best = Infinity;
          let bx = 0;
          let by = 0;
          for (let i = 1; i <= 5; i++) {
            const u = i / 5;
            const a = (1 - u) * (1 - u);
            const b = 2 * (1 - u) * u;
            const d = u * u;
            const sx = a * fx + b * cx + d * ex;
            const sy = a * fy + b * cy + d * ey;
            const dist = (sx - p.x) ** 2 + (sy - p.y) ** 2;
            if (dist < best) {
              best = dist;
              bx = sx;
              by = sy;
            }
          }
          k = Math.exp(-best / (RADIUS * RADIUS)) * p.s;
          if (k > 0.02) {
            // Push the bend away from the pointer, like brushing past strings.
            const dx = bx - p.x;
            const dy = by - p.y;
            const len = Math.sqrt(best) || 1;
            cx += (dx / len) * PUSH * k;
            cy += (dy / len) * PUSH * k;
            hot.push({ c, cx, cy, ex, ey, k });
            continue;
          }
        }

        ctx.moveTo(fx, fy);
        ctx.quadraticCurveTo(cx, cy, ex, ey);
      }
      ctx.stroke();
    }

    for (const { c, cx, cy, ex, ey, k } of hot) {
      ctx.strokeStyle = c.color;
      ctx.globalAlpha = 0.55 + 0.45 * k;
      ctx.lineWidth = c.width * (1 + 0.8 * k);
      ctx.beginPath();
      ctx.moveTo(fx, fy);
      ctx.quadraticCurveTo(cx, cy, ex, ey);
      ctx.stroke();
    }

    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
  };
}

function Strip({ side }: { side: "left" | "right" }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const pointer = useMemo<Pointer>(
    () => ({ tx: 0, ty: 0, x: 0, y: 0, over: false, s: 0 }),
    [],
  );
  const draw = useMemo(
    () => makeDraw(side === "left" ? LEFT : RIGHT, side === "left" ? -1 : 1, pointer),
    [side, pointer],
  );
  // Full frame rate only while the pointer is interacting.
  const fps = useMemo(() => () => (pointer.s > 0.01 ? HOVER_FPS : IDLE_FPS), [pointer]);
  useCanvasAnimation(ref, draw, fps);

  // The canvas sits under the hero content, so track the pointer on the window.
  useEffect(() => {
    const move = (e: PointerEvent) => {
      const el = ref.current;
      if (!el || e.pointerType === "touch") return;
      const r = el.getBoundingClientRect();
      const x = e.clientX - r.left;
      const y = e.clientY - r.top;
      const inside = y >= 0 && y <= r.height && x >= -40 && x <= r.width + 40;
      if (inside && !pointer.over) {
        // Start easing from the entry point rather than the last position.
        pointer.x = x;
        pointer.y = y;
      }
      pointer.tx = x;
      pointer.ty = y;
      pointer.over = inside;
    };
    const leave = () => {
      pointer.over = false;
    };
    window.addEventListener("pointermove", move, { passive: true });
    document.documentElement.addEventListener("pointerleave", leave);
    return () => {
      window.removeEventListener("pointermove", move);
      document.documentElement.removeEventListener("pointerleave", leave);
    };
  }, [pointer]);

  return (
    <canvas
      ref={ref}
      className={`absolute inset-y-0 ${side === "left" ? "left-0" : "right-0"} h-full w-[clamp(56px,13vw,220px)]`}
    />
  );
}

/**
 * Light strings fanning out from both edges of the hero. Each side is its own
 * narrow canvas (so only the strips are painted), strokes are batched by color
 * and width, and the loop idles at 30fps until the pointer comes near.
 */
export function HeroFans() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 hidden md:block">
      <Strip side="left" />
      <Strip side="right" />
    </div>
  );
}
