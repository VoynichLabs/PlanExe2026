---
title: Counterfactual Scenario Explorer
date: 2026-02-11
status: proposal
author: PlanExe Team
---

# Counterfactual Scenario Explorer

## Pitch
Generate alternative plan scenarios under adverse or unexpected conditions and rank plan resilience across scenarios.

## Why
Plans optimized for a single baseline are fragile. Counterfactual exploration reveals how the plan behaves when reality deviates.

## Problem

- Plans assume a single future state.
- Stakeholders lack resilience comparisons.
- Risk planning is reactive instead of proactive.

## Proposed Solution
Build a scenario explorer that:

1. Creates adverse, neutral, and optimistic variants.
2. Recomputes schedules, costs, and success probabilities.
3. Ranks resilience and highlights weak points.

## Architecture

```text
Baseline Plan
  -> Scenario Generator
  -> Recompute Schedule + Cost
  -> Risk + Success Simulation
  -> Resilience Scoring
  -> Scenario Report
```

## Scenario Types

- Regulatory delay
- Funding shock
- Supplier failure
- Demand drop
- FX volatility (multi-currency)

## Scenario Generation

- Start from baseline plan.
- Apply parameter shocks (cost, time, demand, FX) within bounded ranges.
- Generate at least 5 scenarios per plan (1 base, 2 adverse, 2 optimistic).

## Resilience Scoring

Compute a resilience score using:

- Probability of success under scenario
- Maximum budget overrun
- Maximum schedule slip
- Failure mode count

**Example formula:**

```
ResilienceScore =
  0.40*(1 - BudgetOverrunProb) +
  0.30*(1 - ScheduleSlipProb) +
  0.30*SuccessProb
```

## Output Schema

```json
{
  "scenario": "funding_shock",
  "success_prob": 0.28,
  "budget_overrun_prob": 0.72,
  "key_failure_modes": ["liquidity_gap"],
  "resilience_score": 0.22
}
```

## Integration Points

- Feeds into Monte Carlo engines and risk propagation.
- Used by investor matching to assess downside tolerance.
- Adds resilience score to execution readiness.
- Included in investor audit packs.

## Success Metrics

- Increased identification of high-risk dependencies.
- Improved resilience scores across iterations.
- Fewer surprises in execution.

## Risks

- Scenario selection bias.
- Over-reliance on synthetic stress conditions.
- Increased computation cost.

## Future Enhancements

- User-defined scenario libraries.
- Scenario auto-generation from live signals.
- Benchmark resilience across similar plans.
- Adaptive scenario severity based on domain.
