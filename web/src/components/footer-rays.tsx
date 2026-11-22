"use client";

import { useEffect, useMemo, useRef } from "react";
import { mulberry32, useCanvasAnimation } from "./use-animation";

// Same palette as the hero fans.
const COLORS = ["#2f6bff", "#2f6bff", "#3b82ff", "#19c9e6", "#1fd6a0", "#d35cff"];

type Ray = {
  theta: number; // angle from the focal point, PI = left, 1.5*PI = up
  reach: number;
  bend: number;
  width: number;
  color: string;
  phase: number;
  speed: number;
  pulse: boolean; // carries a travelling spark, like a message being scored
  pulseSpeed: number;
};

function makeRays(seed: number, count: number): Ray[] {
  const r = mulberry32(seed);
  return Array.from({ length: count }, () => ({
    // Fan from pointing left (PI) to pointing up (1.5 PI), biased toward the
    // diagonal so the sweep reads as one bloom.
    theta: Math.PI + (Math.PI / 2) * (0.04 + 0.92 * Math.pow(r(), 0.85)),
    reach: 0.75 + r() * 0.6,
    bend: (r() - 0.5) * 0.9,
    width: [0.75, 1.25, 1.75, 2.25][Math.floor(r() * 4)],
    color: COLORS[Math.floor(r() * COLORS.length)],
    phase: r() * Math.PI * 2,
    speed: 0.2 + r() * 0.3,
    pulse: r() < 0.14,
    pulseSpeed: 0.12 + r() * 0.14,
  }));
}

const RAYS = makeRays(23, 140);

const RADIUS = 150;
const PUSH = 80;
const IDLE_FPS = 30;
const HOVER_FPS = 60;

type Pointer = { tx: number; ty: number; x: number; y: number; over: boolean; s: number };

function point(fx: number, fy: number, cx: number, cy: number, ex: number, ey: number, u: number) {
  const a = (1 - u) * (1 - u);
  const b = 2 * (1 - u) * u;
  const d = u * u;
  return [a * fx + b * cx + d * ex, a * fy + b * cy + d * ey] as const;
}

function makeDraw(p: Pointer) {
  return (ctx: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    // Focal point just past the bottom-right corner: the rays bloom up and
    // across the band, away from the text in the bottom-left.
    const fx = w + 20;
    const fy = h + 30;
    const scale = Math.hypot(w, h);

    p.x += (p.tx - p.x) * 0.2;
    p.y += (p.ty - p.y) * 0.2;
    p.s += ((p.over ? 1 : 0) - p.s) * 0.1;
    const live = p.s > 0.01;

    // Soft glow at the source.
    const glow = ctx.createRadialGradient(fx, fy, 0, fx, fy, h * 0.9);
    glow.addColorStop(0, "rgba(47,107,255,0.28)");
    glow.addColorStop(0.5, "rgba(25,201,230,0.07)");
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);

    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (const c of RAYS) {
      const wob = Math.sin(t * c.speed + c.phase);
      const th = c.theta + wob * 0.025;
      const R = scale * c.reach * 0.75;
      const ex = fx + Math.cos(th) * R;
      const ey = fy + Math.sin(th) * R;
      // Control point off the straight line, so each ray arcs gently.
      const mid = 0.5;
      const nx = -Math.sin(th);
      const ny = Math.cos(th);
      const off = (c.bend + wob * 0.08) * R * 0.35;
      let cx = fx + Math.cos(th) * R * mid + nx * off;
      let cy = fy + Math.sin(th) * R * mid + ny * off;

      let k = 0;
      if (live) {
        let best = Infinity;
        let bx = 0;
        let by = 0;
        for (let i = 2; i <= 8; i++) {
          const [sx, sy] = point(fx, fy, cx, cy, ex, ey, i / 8);
          const dist = (sx - p.x) ** 2 + (sy - p.y) ** 2;
          if (dist < best) {
            best = dist;
            bx = sx;
            by = sy;
          }
        }
        k = Math.exp(-best / (RADIUS * RADIUS)) * p.s;
        if (k > 0.02) {
          const len = Math.sqrt(best) || 1;
          cx += ((bx - p.x) / len) * PUSH * k;
          cy += ((by - p.y) / len) * PUSH * k;
        }
      }

      ctx.strokeStyle = c.color;
      ctx.globalAlpha = 0.32 + 0.5 * k;
      ctx.lineWidth = c.width * (1 + 0.8 * k);
      ctx.beginPath();
      ctx.moveTo(fx, fy);
      ctx.quadraticCurveTo(cx, cy, ex, ey);
      ctx.stroke();

      if (c.pulse) {
        // A short bright spark running outward along the ray.
        const u = (t * c.pulseSpeed + c.phase) % 1;
        const [sx, sy] = point(fx, fy, cx, cy, ex, ey, u);
        const [qx, qy] = point(fx, fy, cx, cy, ex, ey, Math.max(0, u - 0.05));
        const fade = Math.sin(Math.PI * u);
        ctx.globalAlpha = 0.9 * fade;
        ctx.lineWidth = c.width + 1.5;
        ctx.beginPath();
        ctx.moveTo(qx, qy);
        ctx.lineTo(sx, sy);
        ctx.stroke();
        ctx.globalAlpha = 0.25 * fade;
        ctx.fillStyle = c.color;
        ctx.beginPath();
        ctx.arc(sx, sy, 5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
  };
}

/**
 * The hero's light strings, re-staged for the footer: one fan blooming from
 * the bottom-right corner, with a few sparks travelling outward along it.
 * Strings bend away from the pointer, as in the hero.
 */
export function FooterRays({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const pointer = useMemo<Pointer>(
    () => ({ tx: 0, ty: 0, x: 0, y: 0, over: false, s: 0 }),
    [],
  );
  const draw = useMemo(() => makeDraw(pointer), [pointer]);
  const fps = useMemo(() => () => (pointer.s > 0.01 ? HOVER_FPS : IDLE_FPS), [pointer]);
  useCanvasAnimation(ref, draw, fps);

  useEffect(() => {
    const move = (e: PointerEvent) => {
      const el = ref.current;
      if (!el || e.pointerType === "touch") return;
      const r = el.getBoundingClientRect();
      const x = e.clientX - r.left;
      const y = e.clientY - r.top;
      const inside = x >= 0 && x <= r.width && y >= 0 && y <= r.height;
      if (inside && !pointer.over) {
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

  return <canvas ref={ref} aria-hidden className={className} />;
}
