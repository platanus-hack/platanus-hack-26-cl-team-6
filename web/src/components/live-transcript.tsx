"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Popover } from "@base-ui/react/popover";
import { ExclamationMarkIcon } from "@phosphor-icons/react/dist/ssr";
import demo from "@/data/demo.json";

type Scores = { fabrication: number; unverified_trust: number };
type Event = (typeof demo.events)[number] & {
  scores?: Scores;
  error?: { id: string; type: string; truth: string };
};
type Status = "recorded" | "scoring" | "live" | "error";

const EVENTS = demo.events as Event[];
const T = demo.threshold;
const ORIGINAL = Object.fromEntries(EVENTS.map((e) => [e.id, e.content]));
const RECORDED = Object.fromEntries(
  EVENTS.filter((e) => e.scores).map((e) => [e.id, e.scores!]),
) as Record<string, Scores>;
const ORANGE = "#ff5a1f";
const risk = (s: Scores) => Math.max(s.fabrication, s.unverified_trust);

// ---------------------------------------------------------------- layout

const LANES = [
  { agent: "Atlas", x: 10, color: "#2f6bff" },
  { agent: "Birch", x: 30, color: "#1fd6a0" },
  { agent: "Cedar", x: 50, color: "#19c9e6" },
  { agent: "Delta", x: 70, color: "#d35cff" },
  { agent: "Echo", x: 90, color: "#3b82ff" },
];
const LANE = Object.fromEntries(LANES.map((l) => [l.agent, l]));

const ORG_Y = 16;
const LANE_TOP = 150;
const ROW = 54;
const FIRST_ROW = LANE_TOP + 46;
const ROWS = EVENTS.filter((e) => e.role === "agent");
const rowY = (k: number) => FIRST_ROW + k * ROW;
const LANE_END = rowY(ROWS.length - 1) + 56;
const SINK_Y = LANE_END + 120;
const HEIGHT = SINK_Y + 90;

// Short labels for the diagram; the full text is in the popover.
const LABEL: Record<string, string> = {
  "s2-0001": "Headline numbers",
  "s2-0002": "Quotes A–B",
  "s2-0003": "Quotes C–G",
  "s2-0004": "Quotes H–L",
  "s2-0005": "Self-reported uplift ≈12x",
  "s2-0006": "Excerpts posted",
  "s2-0007": "A: 4 years in 1 is likely",
  "s2-0008": "A: endorses >4x speedup",
  "s2-0009": "F: slope change 50–80%",
  "s2-0010": "Keep bullets short",
  "s2-0011": "E: fairly significant",
  "s2-0012": "F: slope change 70–90%",
  "s2-0013": "Compute will bottleneck",
  "s2-0014": "Slotting into outlook",
  "s2-0015": "L: 15–20% due to AI",
};
const FETCHES = ROWS.map((e, k) => ({ e, k })).filter(({ e }) => e.kind === "action");

// ---------------------------------------------------------------- scoring state

function useJev() {
  const [texts, setTexts] = useState<Record<string, string>>(ORIGINAL);
  const [scores, setScores] = useState<Record<string, Scores>>(RECORDED);
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState<Status>("recorded");
  const [errorMsg, setErrorMsg] = useState("");
  const abort = useRef<AbortController | null>(null);
  const textsRef = useRef(texts);
  // Earliest edited message not yet re-scored with its current text.
  const fromRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      abort.current?.abort();
    },
    [],
  );

  const rescore = useCallback(
    async (edits: Record<string, string>, targets: string[]) => {
      abort.current?.abort();
      const ctl = new AbortController();
      abort.current = ctl;
      setStatus("scoring");
      try {
        const r = await fetch("/api/score", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ edits, targets }),
          signal: ctl.signal,
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error ?? `HTTP ${r.status}`);
        setScores((s) => ({ ...s, ...d.scores }));
        setStatus("live");
        fromRef.current = null;
      } catch (err) {
        if (ctl.signal.aborted) return;
        setErrorMsg(err instanceof Error ? err.message : "Scoring failed");
        setStatus("error");
      } finally {
        if (!ctl.signal.aborted) setPending(new Set());
      }
    },
    [],
  );

  // Typing only updates the text. Scoring waits for commit() (Enter).
  const edit = useCallback((id: string, text: string) => {
    const i = EVENTS.findIndex((e) => e.id === id);
    const next = { ...textsRef.current, [id]: text };
    textsRef.current = next;
    setTexts(next);
    fromRef.current = Math.min(fromRef.current ?? i, i);

    // Back to the original transcript: restore the recorded scores right away.
    if (Object.entries(next).every(([k, t]) => t === ORIGINAL[k])) {
      abort.current?.abort();
      fromRef.current = null;
      setScores(RECORDED);
      setPending(new Set());
      setStatus("recorded");
    }
  }, []);

  // Re-score the earliest edited message and every agent message after it:
  // each later message is scored with the edited one in its context.
  const commit = useCallback(() => {
    if (fromRef.current === null) return;
    const edits = Object.fromEntries(
      Object.entries(textsRef.current).filter(([k, t]) => t !== ORIGINAL[k]),
    );
    if (!Object.keys(edits).length) return;
    const targets = EVENTS.slice(fromRef.current)
      .filter((e) => e.scores)
      .map((e) => e.id);
    setPending(new Set(targets));
    rescore(edits, targets);
  }, [rescore]);

  const reset = useCallback(() => {
    abort.current?.abort();
    textsRef.current = ORIGINAL;
    fromRef.current = null;
    setTexts(ORIGINAL);
    setScores(RECORDED);
    setPending(new Set());
    setStatus("recorded");
  }, []);

  return { texts, scores, pending, status, errorMsg, edit, commit, reset };
}

// ---------------------------------------------------------------- pieces

function Meter({ label, value, was }: { label: string; value: number; was?: number }) {
  const hot = value >= T;
  const changed = was !== undefined && Math.abs(was - value) >= 0.01;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-2 text-[11px]">
        <span className="text-white/50">{label}</span>
        <span
          className="font-mono tabular-nums"
          style={{ color: hot ? ORANGE : "rgba(255,255,255,0.8)" }}
        >
          {changed && (
            <span className="mr-1.5 text-white/30 line-through">{was!.toFixed(2)}</span>
          )}
          {value.toFixed(2)}
        </span>
      </div>
      <div className="relative h-1 rounded-full bg-white/10">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-[width,background-color] duration-700 ease-out"
          style={{
            width: `${value * 100}%`,
            backgroundColor: hot ? ORANGE : "rgba(255,255,255,0.6)",
          }}
        />
        <div
          className="absolute -inset-y-1 w-px bg-white/60"
          style={{ left: `${T * 100}%` }}
          aria-hidden
        />
      </div>
    </div>
  );
}

const POPUP =
  "w-[min(22rem,calc(100vw-2rem))] origin-[var(--transform-origin)] rounded-xl border border-white/15 bg-neutral-950/95 p-4 text-left text-white shadow-2xl shadow-black/60 backdrop-blur-md transition-[opacity,scale] duration-150 data-[ending-style]:scale-95 data-[ending-style]:opacity-0 data-[starting-style]:scale-95 data-[starting-style]:opacity-0";

function Tag({ children, color }: { children: React.ReactNode; color?: string }) {
  return (
    <span
      className="rounded border px-1.5 text-[10px] tracking-wide uppercase"
      style={{
        color: color ?? "rgba(255,255,255,0.55)",
        borderColor: color ? `${color}66` : "rgba(255,255,255,0.15)",
      }}
    >
      {children}
    </span>
  );
}

function Node({
  event,
  y,
  text,
  scores,
  pending,
  hint,
  onEdit,
  onCommit,
  onOpen,
}: {
  event: Event;
  y: number;
  text: string;
  scores?: Scores;
  pending: boolean;
  hint: boolean;
  onEdit: (id: string, text: string) => void;
  onCommit: () => void;
  onOpen: () => void;
}) {
  const lane = LANE[event.actor];
  const isFetch = event.kind === "action";
  const flagged = scores ? risk(scores) >= T : false;
  const edited = text !== ORIGINAL[event.id];
  const recorded = RECORDED[event.id];
  const label = edited
    ? text.replace(/\s+/g, " ").slice(0, 34) + (text.length > 34 ? "…" : "")
    : LABEL[event.id];

  return (
    <Popover.Root onOpenChange={(open) => open && onOpen()}>
      <Popover.Trigger
        aria-label={`${event.actor}: ${label}. ${flagged ? "Flagged by our mechanism." : ""} Open to read and edit.`}
        className="group absolute flex cursor-pointer -translate-y-1/2 items-center gap-3 rounded-md py-1 pr-2 pl-0 text-left outline-none"
        style={{ left: `calc(${lane.x}% - 7px)`, top: y }}
      >
        <span className="relative flex size-3.5 shrink-0 items-center justify-center">
          {hint && (
            <span
              className="absolute -inset-2 animate-ping rounded-full border"
              style={{ borderColor: ORANGE }}
              aria-hidden
            />
          )}
          <span
            className={`flex items-center justify-center transition-all duration-500 group-hover:scale-125 group-focus-visible:scale-125 group-data-[popup-open]:scale-125 ${pending ? "animate-pulse" : ""}`}
            style={
              flagged
                ? {
                    width: 16,
                    height: 16,
                    backgroundColor: ORANGE,
                  }
                : isFetch
                  ? {
                      width: 13,
                      height: 13,
                      borderRadius: 999,
                      border: "1.5px solid #fff",
                      background: "radial-gradient(circle, #fff 2px, #000 2.5px)",
                    }
                  : { width: 10, height: 10, borderRadius: 999, backgroundColor: "#fff" }
            }
          >
            {flagged && <ExclamationMarkIcon size={12} weight="bold" color="#000" aria-hidden />}
          </span>
        </span>
        <span
          className={`hidden max-w-[9.5rem] truncate text-[11px] leading-tight transition-colors sm:block ${
            flagged ? "" : "text-white/55 group-hover:text-white"
          }`}
          style={flagged ? { color: ORANGE } : undefined}
        >
          {label}
          {edited && <span className="ml-1 text-white/40">✎</span>}
        </span>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Positioner side="right" align="center" sideOffset={14} collisionPadding={16} className="z-50">
          <Popover.Popup className={POPUP}>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="size-2 rounded-full" style={{ backgroundColor: lane.color }} aria-hidden />
              <Popover.Title className="font-semibold">{event.actor}</Popover.Title>
              <span className="font-mono text-white/35">{event.ts.slice(11, 16)}</span>
              {isFetch && <Tag>fetch_url · source</Tag>}
              {event.error && <Tag color={ORANGE}>planted · {event.error.type}</Tag>}
              {edited && (
                <button
                  type="button"
                  onClick={() => onEdit(event.id, ORIGINAL[event.id])}
                  className="ml-auto cursor-pointer text-[11px] text-white/45 underline-offset-2 hover:text-white hover:underline"
                >
                  Undo edit
                </button>
              )}
            </div>

            <textarea
              value={text}
              onChange={(e) => onEdit(event.id, e.target.value)}
              onKeyDown={(e) => {
                // Enter re-scores; Shift+Enter adds a new line.
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  onCommit();
                }
              }}
              aria-label={`Message from ${event.actor}`}
              spellCheck={false}
              className={`field-sizing-content mt-3 max-h-56 min-h-16 w-full resize-none overflow-y-auto rounded-lg border border-white/10 bg-white/[0.04] p-2.5 leading-relaxed text-white/90 outline-none transition-colors focus:border-white/30 focus:bg-white/[0.07] ${
                isFetch ? "font-mono text-[11px]" : "text-sm"
              }`}
            />
            <Popover.Description className="mt-1.5 text-[11px] text-white/35">
              Rewrite it, then press Enter. Our mechanism re-scores this message and every one after it.
            </Popover.Description>

            {scores && (
              <div className={`mt-4 flex flex-col gap-2.5 ${pending ? "animate-pulse" : ""}`}>
                <Meter
                  label="Fabrication"
                  value={scores.fabrication}
                  was={edited ? recorded?.fabrication : undefined}
                />
                <Meter
                  label="Unverified trust"
                  value={scores.unverified_trust}
                  was={edited ? recorded?.unverified_trust : undefined}
                />
                <div className="flex items-center justify-between text-[11px]">
                  <span
                    className="font-semibold tracking-wide uppercase"
                    style={{ color: flagged ? ORANGE : "rgba(255,255,255,0.4)" }}
                  >
                    {pending ? "Scoring…" : flagged ? "Flagged by our mechanism" : "Not flagged"}
                  </span>
                  <span className="text-white/35">flag at {T.toFixed(2)}</span>
                </div>
              </div>
            )}

            {event.error && (
              <p className="mt-4 border-t border-white/10 pt-3 text-[11px] leading-snug text-white/45">
                <span className="text-white/70">Answer key</span> (our mechanism never sees
                this): {event.error.truth}
              </p>
            )}
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

// ---------------------------------------------------------------- diagram

export function LiveTranscript() {
  const { texts, scores, pending, status, edit, commit, reset } = useJev();
  const [touched, setTouched] = useState(false);
  const organizer = EVENTS[0];

  const { planted, caught } = useMemo(() => {
    const scored = EVENTS.filter((e) => scores[e.id]);
    const isFlag = (e: Event) => risk(scores[e.id]) >= T;
    const p = scored.filter((e) => e.error);
    return {
      planted: p.length,
      caught: p.filter(isFlag).length,
    };
  }, [scores]);

  const dirty = Object.entries(texts).some(([id, t]) => t !== ORIGINAL[id]);

  const fan = (x: number) =>
    `M50,${ORG_Y + 14} C50,${ORG_Y + 80} ${x},${LANE_TOP - 70} ${x},${LANE_TOP}`;
  const sink = (x: number) =>
    `M${x},${LANE_END} C${x},${LANE_END + 70} 50,${SINK_Y - 80} 50,${SINK_Y - 8}`;
  const fetchTop = rowY(FETCHES[0].k) - 22;
  const fetchBottom = rowY(FETCHES[FETCHES.length - 1].k) + 22;

  return (
    <div className="flex w-full flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 delay-200 duration-1000 fill-mode-backwards">
      <div className="relative w-full" style={{ height: HEIGHT }}>
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox={`0 0 100 ${HEIGHT}`}
          preserveAspectRatio="none"
          aria-hidden
        >
          {LANES.map((l) => (
            <g key={l.agent} stroke={l.color} fill="none" strokeOpacity={0.7}>
              <path d={fan(l.x)} vectorEffect="non-scaling-stroke" strokeWidth={1.25} />
              <path d={`M${l.x},${LANE_TOP} L${l.x},${LANE_END}`} vectorEffect="non-scaling-stroke" strokeWidth={1.25} />
              <path d={sink(l.x)} vectorEffect="non-scaling-stroke" strokeWidth={1.25} />
            </g>
          ))}
        </svg>

        {/* Organizer instruction: the source of every lane. */}
        <Popover.Root>
          <Popover.Trigger
            aria-label="Organizer instruction. Open to read."
            className="group absolute left-1/2 cursor-pointer flex -translate-x-1/2 flex-col items-center gap-2 outline-none"
            style={{ top: ORG_Y - 8 }}
          >
            <span className="size-7 bg-white transition-transform group-hover:scale-110" />
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Positioner side="bottom" sideOffset={12} collisionPadding={16} className="z-50">
              <Popover.Popup className={POPUP}>
                <div className="flex items-center gap-2 text-xs">
                  <Popover.Title className="font-semibold">Organizer</Popover.Title>
                  <Tag>human</Tag>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-white/75">{organizer.content}</p>
              </Popover.Popup>
            </Popover.Positioner>
          </Popover.Portal>
        </Popover.Root>
        <span
          className="absolute left-1/2 ml-8 text-sm font-semibold text-white"
          style={{ top: ORG_Y - 4 }}
        >
          Organizer: write a briefing on METR&apos;s interview quotes
        </span>

        {/* Agent names at the head of each lane. */}
        {LANES.map((l) => (
          <span
            key={l.agent}
            className="absolute -translate-x-1/2 bg-black px-1.5 text-xs font-semibold"
            style={{ left: `${l.x}%`, top: LANE_TOP + 2, color: l.color }}
          >
            {l.agent}
          </span>
        ))}

        {/* Dashed group around Atlas's source fetches, as in the reference diagram. */}
        <div
          className="pointer-events-none absolute rounded-sm border border-dashed border-white/35"
          style={{
            left: `calc(${LANE.Atlas.x}% - 22px)`,
            width: "calc(18% + 4px)",
            top: fetchTop,
            height: fetchBottom - fetchTop,
          }}
        >
          <span className="absolute top-full left-0 mt-1.5 text-[11px] whitespace-nowrap text-white/55">
            Atlas fetches the source
          </span>
        </div>

        {ROWS.map((e, k) => (
          <Node
            key={e.id}
            event={e}
            y={rowY(k)}
            text={texts[e.id]}
            scores={scores[e.id]}
            pending={pending.has(e.id)}
            hint={!touched && e.id === "s2-0008"}
            onEdit={edit}
            onCommit={commit}
            onOpen={() => setTouched(true)}
          />
        ))}

        {/* The briefing the lanes converge into, with Jev's tally so far. */}
        <div
          className="absolute left-1/2 flex -translate-x-1/2 flex-col items-center gap-3"
          style={{ top: SINK_Y - 8 }}
        >
          <span className="size-9 bg-white" />
          <span className="text-lg font-semibold text-white">Briefing</span>
          <span className="text-xs whitespace-nowrap text-white/55" aria-live="polite">
            <span className={status === "scoring" ? "animate-pulse" : ""}>
              {caught}/{planted} planted errors flagged
            </span>
            {dirty && (
              <>
                {" · "}
                <button
                  type="button"
                  onClick={reset}
                  className="cursor-pointer text-white underline underline-offset-2 hover:text-white/70"
                >
                  Reset
                </button>
              </>
            )}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-white/50">
        <span className="flex items-center gap-2">
          <span className="size-2 rounded-full bg-white" /> message
        </span>
        <span className="flex items-center gap-2">
          <span
            className="size-2.5 rounded-full border border-white"
            style={{ background: "radial-gradient(circle, #fff 1.5px, #000 2px)" }}
          />{" "}
          source fetch
        </span>
        <span className="flex items-center gap-2">
          <span className="size-2.5" style={{ backgroundColor: ORANGE }} /> flagged by our mechanism
        </span>
      </div>
    </div>
  );
}
