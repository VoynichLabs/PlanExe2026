---
title: Assumption Drift Monitor
date: 2026-02-11
status: proposal
author: PlanExe Team
---

# Assumption Drift Monitor

## Pitch
Continuously compare live execution data against original plan assumptions to detect drift early and trigger re-planning.

## Why
Most plan failures start as small deviations. If assumptions drift unnoticed, timelines and budgets collapse.

## Problem

- Assumptions are rarely tracked after planning.
- Deviations are detected too late.
- Re-planning is manual and reactive.

## Proposed Solution
Build a drift monitor that:

1. Catalogs critical assumptions from the plan.
2. Connects each assumption to live data sources.
3. Tracks deviation thresholds.
4. Triggers alerts and re-plan workflows.

## Architecture

```text
Plan Assumptions
  -> Assumption Registry
  -> Data Source Connectors
  -> Drift Detector
  -> Alert + Replan Trigger
  -> Governance Log
```

## Drift Categories

- Cost drift (unit costs, labor rates)
- Schedule drift (task durations)
- Demand drift (sales, adoption)
- Regulatory drift (policy changes)

## Drift Detection Logic

- Each assumption has a baseline value and tolerance band.
- Drift is detected when the observed value exceeds the band.
- Severity is ranked by impact on schedule, cost, or success probability.

## Alerting and Actions

- **Warning:** drift is near threshold, monitor closely.
- **Breach:** drift exceeds threshold, trigger re-plan.
- **Critical:** drift threatens viability, escalate to governance.

## Output Schema

```json
{
  "assumption_id": "a_33",
  "assumption": "Material cost = $120/ton",
  "current_value": 165,
  "drift_pct": 37.5,
  "status": "breach",
  "action": "replan_required"
}
```

## Integration Points

- Feeds into adaptive re-planning engine.
- Updates risk propagation and Monte Carlo inputs.
- Alerts execution governance layer.
- Updates execution readiness score.

## Success Metrics

- Time-to-drift detection.
- Reduction in unplanned overruns.
- % of plans with active assumption tracking.
- Percentage of drift events resolved within SLA.

## Risks

- Noisy data may cause false alarms.
- Data integration gaps.
- Over-alerting reduces trust.

## Future Enhancements

- Automatic re-baselining suggestions.
- Trend forecasting for early warning.
- Domain-specific drift thresholds.
- Causal attribution between drift sources and outcomes.
