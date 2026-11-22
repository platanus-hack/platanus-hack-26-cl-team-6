// TypeScript port of jev-swarm/monitor.py:build_state, for the demo excerpt.
// The excerpt ends before the first Haiku ledger snapshot, so no ledger section is needed:
// with no edits, this rebuilds exactly the input Jev scored in the recorded run.

import demo from "@/data/demo.json";

export type DemoEvent = (typeof demo.events)[number];

const C = demo.context;

function clip(s: string | null | undefined, n: number): string {
  if (!s) return "";
  const cps = Array.from(s.trim()); // Python slices by code point
  return cps.length <= n
    ? cps.join("")
    : cps.slice(0, n).join("") + ` …[+${cps.length - n} chars]`;
}

const time = (e: DemoEvent) => e.ts.slice(11, 19); // ISO in UTC: HH:MM:SS

function render(e: DemoEvent, contentChars: number): string {
  const who = e.role === "agent" ? e.actor : `${e.actor} (${e.role})`;
  return `[${e.id} ${time(e)}] ${who}: ${clip(e.content, contentChars)}`;
}

const KIND: Record<string, string> = {
  message: "public message",
  action_start: "starts a computer/tool session",
  action: "tool call",
};

export function buildState(stream: DemoEvent[], i: number): string {
  const target = stream[i];
  const lo = Math.max(0, i - C.recent_messages);
  const recent = stream.slice(lo, i);
  const recentIds = new Set(recent.map((e) => e.id));
  const own = stream
    .slice(0, lo)
    .filter(
      (e) =>
        e.actor === target.actor && e.kind === "message" && !recentIds.has(e.id),
    )
    .slice(-C.own_history);
  const humans = stream.slice(0, i).filter((e) => e.role === "human");

  const parts = [
    "## Mission",
    demo.mission,
    "",
    "## Instructions from human organizers so far (oldest first)",
  ];
  const humanLines = humans
    .slice(-20)
    .map((h) => `- [day ${h.day} ${time(h)}] ${h.actor}: ${clip(h.content, 700)}`);
  parts.push(...(humanLines.length ? humanLines : ["- (none)"]), "");
  if (own.length) {
    parts.push(`## Earlier messages by ${target.actor} (before the recent window)`);
    parts.push(...own.map((e) => render(e, C.context_content_chars)), "");
  }
  parts.push("## Recent conversation (oldest first)");
  const recentLines = recent.map((e) => render(e, C.context_content_chars));
  parts.push(...(recentLines.length ? recentLines : ["(start of day)"]), "");
  parts.push(
    "## Message under review",
    `id: ${target.id} | time: ${time(target)} | agent: ${target.actor} | type: ${KIND[target.kind] ?? target.kind}`,
    "Private reasoning (not visible to other agents):",
    "(none available)",
    "Public message:",
    clip(target.content, C.target_content_chars),
  );
  return parts.join("\n");
}
