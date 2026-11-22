// Measured swarm-scaling data. Sources:
// - OpenAI GPT-5.6 launch charts (experiments/swarm-lambda/data/openai-gpt56/gpt56_charts.json)
// - Our SOC pilot (experiments/swarm-lambda/runs/pilot/results.jsonl), averaged per (N, effort)
// λ values are the "linear score fit (pooled)" rows of experiments/swarm-lambda/lambdas.csv.
// Each point is [total output tokens across all agents, score 0..1], one per effort level.

export type Point = [tokens: number, score: number];

export type Series = { agents: number; points: Point[] };

export type SwarmTask = {
  id: string;
  side: "offensive" | "defensive" | "general";
  task: string;
  benchmark: string;
  model: string;
  nTasks: number;
  lambda: number;
  ci: [number, number];
  source: string;
  series: Series[];
};

export const TASKS: SwarmTask[] = [
  {
    id: "secbench",
    side: "offensive",
    task: "Proof-of-concept generation",
    benchmark: "SEC-Bench Pro",
    model: "GPT-5.6 Sol",
    nTasks: 183,
    lambda: 0.565,
    ci: [0.5, 0.63],
    source: "OpenAI GPT-5.6 charts",
    series: [
      { agents: 1, points: [[4791, 0.1708], [15324, 0.373], [27030, 0.5314], [52908, 0.6407], [76557, 0.7145]] },
      { agents: 4, points: [[11061, 0.2036], [29577, 0.3893], [54213, 0.5014], [89934, 0.653], [159006, 0.7432]] },
      { agents: 16, points: [[17485, 0.224], [68568, 0.4563], [153117, 0.6148], [232577, 0.6667], [357363, 0.7623]] },
    ],
  },
  {
    id: "soc",
    side: "defensive",
    task: "SOC incident investigation",
    benchmark: "Synthetic SOC logs, depth 7 (pilot)",
    model: "Claude Haiku 5.5",
    nTasks: 10,
    lambda: -0.05,
    ci: [-0.67, 0.39],
    source: "Our swarm pilot, 69 runs",
    series: [
      { agents: 1, points: [[9065, 0.4], [20874, 0.7], [70848, 1.0]] },
      { agents: 2, points: [[19877, 0.2], [39954, 0.8]] },
      { agents: 4, points: [[39337, 0.3], [87564, 0.7]] },
    ],
  },
  {
    id: "browsecomp",
    side: "general",
    task: "Web research",
    benchmark: "BrowseComp",
    model: "GPT-5.6 Sol",
    nTasks: 1266,
    lambda: 0.65,
    ci: [0.59, 0.71],
    source: "OpenAI GPT-5.6 charts",
    series: [
      { agents: 1, points: [[1957, 0.6904], [6095, 0.846], [10887, 0.8823], [14839, 0.8942], [22001, 0.9084]] },
      { agents: 4, points: [[7418, 0.8175], [14791, 0.8918], [24355, 0.9076], [33558, 0.9115], [54138, 0.9218]] },
      { agents: 16, points: [[22851, 0.8641], [45366, 0.9107], [71458, 0.9218], [97726, 0.9336], [144146, 0.9329]] },
    ],
  },
  {
    id: "terminalbench",
    side: "general",
    task: "Terminal tasks",
    benchmark: "Terminal-Bench 2.1",
    model: "GPT-5.6 Sol",
    nTasks: 89,
    lambda: 0.481,
    ci: [0.17, 0.98],
    source: "OpenAI GPT-5.6 charts",
    series: [
      { agents: 1, points: [[3828, 0.764], [5553, 0.818], [7229, 0.8472], [9515, 0.8494], [12796, 0.8876]] },
      { agents: 4, points: [[10448, 0.7978], [16387, 0.8539], [21618, 0.8674], [27710, 0.8921], [39275, 0.9191]] },
    ],
  },
];
