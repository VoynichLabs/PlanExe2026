---
title: "Three-Hypotheses Engine for Unsolved Challenges"
date: 2026-02-10
status: Proposal
author: PlanExe Team
---

# Three-Hypotheses Engine for Unsolved Challenges

**Author:** PlanExe Team  
**Date:** 2026-02-10  
**Status:** Proposal  
**Tags:** `hypotheses`, `r-and-d`, `uncertainty`, `experimentation`, `planning`

## Pitch
When the system finds an unsolved challenge, require generation of exactly three plausible hypotheses to approach a solution, then rank them by evidence and risk.

## Why
Plans stall when teams identify hard problems but do not structure solution exploration. A strict three-hypothesis framework forces breadth without exploding scope.

## Problem

- Unresolved technical gaps are treated as vague risks.
- Teams jump to a single approach without alternatives.
- R&D spending is not staged or governed by evidence.

## Proposed Solution
For each unresolved challenge:

1. Produce exactly three hypotheses (H1/H2/H3).
2. Define a test protocol for each hypothesis.
3. Estimate cost, time, and risk profile per hypothesis.
4. Recommend a portfolio strategy (single-track vs parallel trials).

## Hypothesis Card Template

Each hypothesis includes:

- Assumptions
- Required experiments
- Failure criteria
- Expected evidence outputs
- Estimated cost and timeline

## Example (Cold-Climate Concrete)

- **H1:** Admixture chemistry adaptation for low-temp hydration kinetics
- **H2:** Modular heated formwork + controlled curing micro-environments
- **H3:** Alternative material systems with reduced hydration sensitivity

## Required Outputs

- Hypothesis cards (H1/H2/H3)
- Stage-gate plan for kill/continue decisions
- Expected Value of Information (EVI) by hypothesis

## Output Schema

```json
{
  "challenge": "cold_climate_concrete",
  "hypotheses": [
    {"id": "H1", "risk": "medium", "evi": 0.64},
    {"id": "H2", "risk": "high", "evi": 0.52},
    {"id": "H3", "risk": "medium", "evi": 0.71}
  ],
  "recommended_strategy": "parallel_trial"
}
```

## Integration Points

- Feeds hypothesis success probabilities into Monte Carlo models.
- Updates plan success probability after each experiment cycle.
- Links to frontier research gap mapper.

## Success Metrics

- Time to first validated path for frontier challenges.
- Reduction in dead-end R&D spend.
- Improved confidence bounds after hypothesis testing.

## Risks

- Hypotheses may not be meaningfully distinct.
- Over-parallelization increases cost.
- EVI estimates depend on weak priors.

## Future Enhancements

- Automated literature scan to seed hypotheses.
- Expert panel review of hypothesis set.
- Learning-based hypothesis ranking from outcomes.
