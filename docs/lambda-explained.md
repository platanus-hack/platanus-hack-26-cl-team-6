# How λ (lambda) is calculated, in simple terms

λ comes from Toby Ord's post [Swarm Scaling](https://www.tobyord.com/writing/swarm-scaling). It measures how much a team of AI agents is worth compared with a single agent that gets more time to think.

## The idea

There are two ways to spend more compute on a task:

1. **Let one agent think longer**, for example at a higher effort level or with more tokens.
2. **Use a team of N agents** working on the task together.

λ answers one question:

> A team of N agents is as good as one agent thinking **N^λ times longer**.

| λ | What it means | 4 agents equal… |
|---|---|---|
| 1 | Teamwork is free: no overlap or coordination cost | 1 agent with 4× the time |
| 0.5 | Half the benefit is lost to overlap and coordination | 1 agent with 2× the time (4^0.5) |
| 0 | Extra agents add nothing | 1 agent with the same time |

In practice λ falls between 0 and 1.

## How we calculate it, in three steps

### Step 1: measure how much extra thinking time helps

Run **one agent** at several effort levels (low, medium, high, max). Record its score and the tokens it used. Plot score against tokens on a log scale and fit a straight line.

The slope of that line is the **time slope**, for example:

> +13 points every time the agent's tokens double.

### Step 2: measure how much extra agents help

Keep each agent's effort fixed and run teams of **1, 4 and 16 agents**. Fit a second line: score against the number of agents, also on a log scale.

The slope of that line is the **agent slope**, for example:

> +7.5 points every time the team size doubles.

### Step 3: divide the two slopes

```
λ = agent slope ÷ time slope
```

Steps 1 to 3 can be done in one fit:

```
score = a + b · ln(tokens per agent) + c · ln(number of agents)
λ = c / b
```

Here `b` is the time slope and `c` is the agent slope.

## Worked example: SEC-Bench Pro (writing proof-of-concept inputs for known bugs)

This uses the data from OpenAI's GPT-5.6 launch charts.

- **One agent:** the score rose by about **13 points** each time its tokens doubled.
- **Teams:** at the same tokens per agent, the score rose by about **7.5 points** each time the team size doubled.
- **λ ≈ 7.5 / 13 ≈ 0.57**

To check this on one data point:

- One agent at about 2.8K tokens scored 20.4%.
- The 4-agent team matched that score at only 2.8K tokens per agent.
- That data point gives λ ≈ 0.53. Averaged over all data points, λ ≈ 0.57.

## What λ tells you

With N agents:

- **Speed:** the team is like one agent thinking **N^λ** times longer, so in theory you get the answer that much sooner.
- **Cost:** you pay for N agents to get N^λ worth of thinking, so the bill is **N^(1−λ)** times higher for the same result.

| | 4 agents | 16 agents |
|---|---|---|
| Equivalent extra thinking time (N^λ) | ×2.2 | ×4.9 |
| Extra cost for the same result (N^(1−λ)) | ×1.8 | ×3.3 |

These numbers use λ = 0.57.

**In short:** a team buys **speed** at a **cost premium**. A higher λ means a smaller premium. In the real data, the speedup was smaller than this theory predicts, because coordinating the agents takes time too.

## Measured values so far

| Task | λ | Source |
|---|---|---|
| SEC-Bench Pro (proof-of-concept generation) | 0.57 | OpenAI GPT-5.6 charts (matches Ord's 0.57) |
| BrowseComp (web research) | 0.65–0.68 | OpenAI GPT-5.6 charts (matches Ord's 0.68) |
| Terminal-Bench 2.1 (terminal tasks) | 0.48 | OpenAI GPT-5.6 charts (matches Ord's 0.48) |
| SOC incident investigation (our own experiment) | in progress | Haiku 5.5 agents on synthetic logs |

## Caveats

- λ depends on the task. Some tasks split up well across agents and others don't.
- λ can change with team size. Going from 1 to 4 agents may differ from going from 1,000 to 4,000.
- λ can only be measured when extra thinking time actually helps. If scores are stuck at 0% or 100%, neither slope can be measured.
