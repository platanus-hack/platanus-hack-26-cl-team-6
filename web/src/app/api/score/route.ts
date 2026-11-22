// Live Jev scoring for the hero demo.
// The client sends only its edits ({event id: new text}) and which events to re-score.
// The transcript, mission and questions stay server-side, so this endpoint can only score the demo excerpt.

import demo from "@/data/demo.json";
import { buildState, type DemoEvent } from "@/lib/jev-state";

const ENDPOINT = "https://api.typesafe.ai/v1/systemone";
const MAX_EDIT_CHARS = 4000;

const QUESTIONS = Object.fromEntries(
  Object.entries(demo.metrics).map(([k, m]) => [
    k,
    { type: "noul", instructions: m.question, criteria: { true: m.true, false: m.false } },
  ]),
);

const SCORED = new Set(
  demo.events.filter((e) => e.role === "agent").map((e) => e.id),
);

async function score(key: string, state: string) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await fetch(ENDPOINT, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: demo.model, state, questions: QUESTIONS }),
    });
    if (r.status === 429 || r.status >= 500) {
      await new Promise((ok) => setTimeout(ok, 500 * 2 ** attempt));
      continue;
    }
    if (!r.ok) throw new Error(`Jev HTTP ${r.status}`);
    const d = (await r.json()) as {
      answers?: Record<string, { type: string; noul: number }>;
    };
    return Object.fromEntries(
      Object.entries(d.answers ?? {})
        .filter(([, v]) => v.type === "noul")
        .map(([k, v]) => [k, Number(v.noul)]),
    ) as Record<string, number>;
  }
  throw new Error("Jev unavailable");
}

export async function POST(req: Request) {
  const key = process.env.TYPESAFE_API_KEY;
  if (!key) {
    return Response.json({ error: "TYPESAFE_API_KEY is not set" }, { status: 503 });
  }

  let body: { edits?: unknown; targets?: unknown };
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Bad JSON" }, { status: 400 });
  }

  const edits: Record<string, string> = {};
  if (body.edits && typeof body.edits === "object") {
    for (const [id, text] of Object.entries(body.edits)) {
      if (SCORED.has(id) && typeof text === "string") {
        edits[id] = text.slice(0, MAX_EDIT_CHARS);
      }
    }
  }
  const targets = Array.isArray(body.targets)
    ? [...new Set(body.targets.filter((t): t is string => typeof t === "string" && SCORED.has(t)))]
    : [];
  if (!targets.length) {
    return Response.json({ error: "No targets" }, { status: 400 });
  }

  const stream: DemoEvent[] = demo.events.map((e) =>
    e.id in edits ? { ...e, content: edits[e.id] } : e,
  );

  try {
    const results = await Promise.all(
      targets.map(async (id) => {
        const i = stream.findIndex((e) => e.id === id);
        return [id, await score(key, buildState(stream, i))] as const;
      }),
    );
    return Response.json({ scores: Object.fromEntries(results) });
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "Scoring failed" },
      { status: 502 },
    );
  }
}
