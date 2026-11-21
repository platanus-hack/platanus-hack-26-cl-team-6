# Swarm-scaling λ experiments

Measuring Toby Ord's swarm λ ("N agents ≈ 1 agent thinking N^λ times longer") for cybersecurity agent tasks. See [docs/lambda-explained.md](../../docs/lambda-explained.md) for the method in plain terms.

## Files

- `lambdas.csv`: every λ estimate so far, one row per benchmark and fit method.
- `data/openai-gpt56/gpt56_charts.json`: exact chart data from OpenAI's GPT-5.6 launch page (1, 4 and 16 agents on SEC-Bench Pro, BrowseComp and Terminal-Bench 2.1; single-agent token curves for CTF, ExploitGym and SEC-Bench Pro).
- `scripts/`
  - `extract.py`: pulls the chart data from the saved page HTML.
  - `lam.py`: fits λ to the OpenAI data.
  - `proj.py`: projections for tasks that have no swarm data.
  - `gen_soc.py`: generates synthetic SOC investigation tasks (defensive, depths 1–7).
  - `runner.py`: runs swarms of headless Claude Code agents (Haiku 5.5, sandboxed, shared notes, majority vote).
  - `analyze.py`: fits λ to runner results and appends rows to `lambdas.csv` with `--csv`.
- `runs/`
  - `calib`, `calib2`, `calib3`: difficulty calibration runs.
  - `pilot`: the main run: 10 depth-7 tasks, 1/2/4 agents at low and high effort, plus single agents at max effort.
  - `logtest`: a small run that saves full agent transcripts and shared notes under `traces/`. The pilot predates this feature.

Each run folder has `results.jsonl` (per-swarm metrics, no answers) and `reveal.json` (true answers and what each agent answered).

## Re-running

```bash
cd scripts
python3 runner.py --out ../runs/NAME --tasks 7:3,7:3,7:3 --efforts low,high --ns 1,2,4 --solo-efforts max --cap 2
python3 analyze.py ../runs/NAME/results.jsonl --csv ../lambdas.csv --label "short description"
```

The agents run on the Claude Code login (`ANTHROPIC_API_KEY` is removed from their environment). Costs are list-price equivalents reported by Claude Code. `--cap` stops launching new swarms once reached, but swarms already running finish, so the total can go slightly over the cap.
