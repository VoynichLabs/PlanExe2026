---
title: Evidence Traceability Ledger
date: 2026-02-11
status: proposal
author: PlanExe Team
---

# Evidence Traceability Ledger

## Pitch
Track every claim in a plan to its source, verification status, and freshness, producing a claim-to-evidence ledger that is auditable and investor-ready.

## Why
Plans are only as credible as their evidence. Without a traceable map, claims degrade into assumptions and cannot be trusted over time.

## Problem

- Claims and sources are scattered or missing.
- Evidence goes stale without visibility.
- Reviewers cannot quickly audit credibility.

## Proposed Solution
Build a ledger that:

1. Extracts claims from the plan.
2. Links each claim to one or more evidence sources.
3. Scores evidence strength and freshness.
4. Emits a traceable report with gaps and alerts.

## Evidence Levels

- **Level 1:** anecdotal or unverified
- **Level 2:** third-party reports or benchmarks
- **Level 3:** audited financials, signed contracts, regulatory approvals

## Workflow

1. Parse plan into structured claims.
2. Attach sources (internal data, public reports, contracts).
3. Score evidence strength (Level 1-3) and freshness.
4. Surface missing evidence and stale sources.

## Output Schema

```json
{
  "claim_id": "c_101",
  "claim": "TAM is $4.2B",
  "evidence": [
    {"type": "third_party_report", "url": "...", "level": "Level 2", "as_of": "2025-11-01"}
  ],
  "freshness_days": 102,
  "status": "stale"
}
```

## Integration Points

- Feeds into verification workflow and FEI.
- Used by investor audit packs.
- Inputs to execution readiness scoring.

## Success Metrics

- % of claims with evidence attached.
- Reduction in unverifiable claims.
- Faster audit time per plan.

## Risks

- Evidence ingestion gaps.
- False confidence if evidence is low quality.
- Maintenance burden for freshness updates.

## Future Enhancements

- Auto-refresh from public data sources.
- Evidence credibility scoring by source reputation.
- Continuous monitoring for conflicting evidence.
