// Headline results from jev-swarm/results/{hard,easy}.md.
// Threshold 0.85, picked on seed 1; numbers below are seeds 2–3.

export type JevSet = {
  id: "hard" | "easy";
  label: string;
  hint: string;
  caught: number;
  errors: number;
  falseAlarms: number;
  clean: number;
  recall: number;
  precision: number;
  f1: number;
  costPer100: number;
  charts: { title: string; kicker: string }[];
};

const CHARTS = [
  { kicker: "Recall by error type", title: "Numeric, textual, mixed" },
  { kicker: "Threshold sweep", title: "Recall vs. precision" },
];

export const SETS: JevSet[] = [
  {
    id: "hard",
    label: "Hard set",
    hint: "Errors inside multi-claim drafts, ~165 messages per transcript",
    caught: 30,
    errors: 36,
    falseAlarms: 8,
    clean: 289,
    recall: 0.83,
    precision: 0.79,
    f1: 0.81,
    costPer100: 0.027,
    charts: CHARTS,
  },
  {
    id: "easy",
    label: "Easy set",
    hint: "One claim per message, ~58 messages per transcript",
    caught: 32,
    errors: 36,
    falseAlarms: 0,
    clean: 81,
    recall: 0.89,
    precision: 1,
    f1: 0.94,
    costPer100: 0.029,
    charts: CHARTS,
  },
];
