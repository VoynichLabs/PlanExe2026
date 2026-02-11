---
title: "Monte Carlo Plan Success Probability Engine (10,000 Runs)"
date: 2026-02-10
status: proposal
author: PlanExe Team
---

# Monte Carlo Plan Success Probability Engine (10,000 Runs)

**Author:** PlanExe Team  
**Date:** 2026-02-10  
**Status:** Proposal  
**Tags:** `monte-carlo`, `risk`, `forecasting`, `planning`, `simulation`

## Pitch
Add a Monte Carlo simulation layer that runs 10,000 stochastic scenarios per plan to estimate probability of success/failure, budget overrun risk, and schedule slippage.

## Why
Single-point estimates hide uncertainty. Decision-makers need distribution-level answers, not only one "expected" outcome.

## Problem

- Plans are evaluated on deterministic timelines and budgets.
- Dependencies and risk events are not modeled probabilistically.
- Decision-makers lack a quantified view of downside risk.

## Proposed Solution
Implement a simulation engine that:

1. Extracts uncertain variables from the plan.
2. Defines distributions for duration, cost, and risk events.
3. Runs 10,000 scenarios.
4. Outputs probability distributions and risk-adjusted guidance.

## Model Inputs

### Uncertain Variables

- Task durations
- Cost drivers
- Dependency delay probabilities
- Funding variability
- Regulatory delay risk

### Distributions

- Duration: triangular or lognormal per task
- Cost: lognormal or PERT per bucket
- Risk events: Bernoulli with impact distributions

## Simulation Workflow

1. Build baseline schedule and budget.
2. Sample durations and costs from distributions.
3. Propagate delays through dependencies.
4. Evaluate success/failure criteria.

## Outputs

- Probability of on-time delivery
- Probability of budget overrun
- Probability of failure criteria being triggered
- P10 / P50 / P90 schedule and cost outcomes
- Tornado chart of top uncertainty drivers

## Output Schema

```json
{
  "prob_on_time": 0.42,
  "prob_budget_overrun": 0.55,
  "p50_cost": 4200000,
  "p90_cost": 6100000,
  "top_drivers": ["regulatory_delay", "materials_cost_volatility"]
}
```

## Integration Points

- Feeds into risk propagation network.
- Used in funding stress Monte Carlo.
- Updates investor matching confidence scores.

## Success Metrics

- Calibration against historical project outcomes.
- Reduction in high-confidence but wrong forecasts.
- Improved decision quality for go/no-go gates.

## Risks

- Poor distribution assumptions skew outputs.
- Complexity may reduce interpretability.
- Limited data for early-stage plans.

## Future Enhancements

- Dynamic updating with real execution data.
- Domain-specific priors for distributions.
- Automated sensitivity and scenario generation.
