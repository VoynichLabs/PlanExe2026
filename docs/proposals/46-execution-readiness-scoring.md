---
title: Execution Readiness Scoring
date: 2026-02-11
status: proposal
author: PlanExe Team
---

# Execution Readiness Scoring

## Pitch
Produce a single readiness score that determines whether a plan is ready to execute, based on evidence coverage, resource capacity, risk gates, and dependency maturity.

## Why
Many plans are “good on paper” but not ready to execute. A readiness score provides a clear go/no-go signal and identifies gaps.

## Problem

- No consistent definition of execution readiness.
- Plans move forward with missing evidence or resource gaps.
- Readiness varies widely across domains and teams.

## Proposed Solution
Build a scoring model that:

1. Evaluates evidence coverage.
2. Checks resource capacity and feasibility.
3. Validates risk gates and compliance.
4. Produces an overall readiness score and gap list.

## Architecture

```text
Evidence Ledger
  + Resource Capacity Profile
  + Risk Gate Status
  + Dependency Maturity
  -> Readiness Scoring Engine
  -> Readiness Report
```

## Scoring Dimensions

- Evidence coverage
- Resource capacity
- Risk gate completeness
- Dependency maturity
- Financial viability

## Scoring Model

**Example weighted formula:**

```
ReadinessScore =
  0.30*EvidenceCoverage +
  0.25*ResourceCapacity +
  0.20*RiskGateCompleteness +
  0.15*DependencyMaturity +
  0.10*FinancialViability
```

Thresholds:

- `>= 0.80` Ready
- `0.60 - 0.79` Conditional
- `< 0.60` Not Ready

## Output Schema

```json
{
  "readiness_score": 0.67,
  "status": "conditional",
  "top_gaps": ["insufficient compliance evidence", "resource shortfall"],
  "required_actions": ["add legal capacity", "verify vendor contracts"]
}
```

## Integration Points

- Consumes evidence ledger and risk propagation outputs.
- Used by autonomous execution engine for gating.
- Included in investor audit packs.

## Success Metrics

- Reduction in premature execution attempts.
- Higher execution success rates.
- Faster identification of blocking gaps.
- Decrease in post-launch emergency re-plans.

## Risks

- Over-simplification of complex readiness states.
- Gaming the score by optimizing inputs.
- Domain-specific factors not captured.

## Future Enhancements

- Domain-specific readiness models.
- Learning from historical execution outcomes.
- Readiness deltas over time to track improvement.
- Explainable scoring breakdowns for stakeholder review.
