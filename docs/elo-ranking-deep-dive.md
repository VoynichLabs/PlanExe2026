# ELO Ranking System: Deep Dive

**Author:** Larry (via OpenClaw)  
**Date:** 2026-02-08  
**Status:** Living document

---

## Overview

PlanExe uses an **ELO-based ranking system** to compare and rank generated plans without relying on fixed weights or static scoring formulas. This document explains how it works, why it matters, and how to evolve it.

---

## How It Works

### 1. Dynamic KPI Extraction

When a plan is submitted via `/api/rank`, the system:

1. **Stores the full plan JSON** in `plan_corpus.json_data` (JSONB column)
2. **Generates an embedding** of the plan's prompt using OpenAI embeddings
3. **Extracts baseline KPIs** (novelty, prompt quality, technical completeness, feasibility, impact) using Gemini-2.0-flash-001 via OpenRouter

### 2. Pairwise LLM Comparison

For each new plan:
- Select **10 neighbors** via embedding similarity (or random if no embeddings exist)
- For each neighbor, run a **pairwise comparison**:
  - LLM chooses **5–7 relevant KPIs** for both plans
  - Adds **one final "remaining considerations" KPI** (LLM names it)
  - Scores each KPI on a **Likert 1–5 integer scale**
  - Provides **≤30-word reasoning** for each KPI score

**Example KPI output:**
```json
[
  {
    "name": "Goal clarity & specificity",
    "plan_a": 4,
    "plan_b": 3,
    "reasoning": "Plan A defines concrete 24-month timeline and EASA compliance gates; Plan B has broad goals without operational detail."
  },
  {
    "name": "Schedule credibility",
    "plan_a": 5,
    "plan_b": 3,
    "reasoning": "Plan A includes PDR/CDR gates with milestone dates; Plan B timeline has internal inconsistencies flagged earlier."
  }
]
```

### 3. Computing Win Probability

Total scores:
- `total_a = sum(plan_a scores)`
- `total_b = sum(plan_b scores)`
- `diff = total_a - total_b`

Probability mapping:
| Diff      | prob_a | Interpretation      |
|-----------|--------|---------------------|
| ≥ +3      | 0.9    | Strong preference A |
| +2        | 0.7    | Moderate favor A    |
| +1        | 0.6    | Slight favor A      |
| 0         | 0.5    | Neutral             |
| -1        | 0.4    | Slight favor B      |
| -2        | 0.3    | Moderate favor B    |
| ≤ -3      | 0.1    | Strong preference B |

### 4. ELO Update

Standard ELO formula with K=32:
```python
expected_a = 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))
new_elo_a = elo_a + K * (prob_a - expected_a)
new_elo_b = elo_b + K * ((1 - prob_a) - (1 - expected_a))
```

After comparing against 10 neighbors, the plan's final ELO is stored in `plan_metrics.elo`.

---

## Value Proposition

### For Users

**1. Contextual ranking, not arbitrary scores**  
- "Your plan is in the **top 10%**" gives social context, not just a number.
- Bottom 10% signals prompt improvement opportunity.

**2. Comparative insight**  
- See how your plan stacks up against real peer plans.
- Understand *why* via KPI breakdown.

**3. Prompt improvement guidance**  
When paired with KPI feedback:
- **Low feasibility** → "Add operational constraints, staffing assumptions, timeline gates."
- **Low measurability** → "Add 3–5 numeric KPIs tied to acceptance criteria."
- **Low goal clarity** → "Write a single-sentence goal with time + scope bounds."

### For Investors / Stakeholders

**1. Filters noise**  
- Top 5–10% bubble up without reading hundreds of plans.
- Privacy-preserving: users only see their own plans + percentile.

**2. Identifies high-signal plans**  
- Plans with strong feasibility + clarity + measurable KPIs rise naturally.
- Weak prompts (vague ideas, no execution detail) sink.

---

## Current Limitations

### 1. False Confidence
**Problem:** Top 10% doesn't mean *objectively good*, just *better than peers*.  
**Risk:** If all plans in the corpus are weak, rankings still show a "winner."

**Mitigation ideas:**
- Absolute quality thresholds (e.g., flag plans with avg KPI < 3.0 as "needs improvement" even if top-ranked)
- Calibration dataset: seed corpus with known high-quality reference plans

### 2. Gaming Risk
**Problem:** Users might overfit prompts to model preferences rather than real-world utility.

**Mitigation ideas:**
- Rotate KPI sets periodically
- Use reasoning transparency (show *why* scores were assigned)
- Red-team evaluation: test whether gaming attempts produce worse real-world outcomes

### 3. Cold-Start Bias
**Problem:** Early plans set the baseline. Small or skewed corpus (e.g., all tech plans) biases rankings.

**Mitigation ideas:**
- Normalize ELO by plan category (tech / social / government / research)
- Bootstrap corpus with diverse high-quality examples from PlanExe-web

### 4. No Explicit Domain Expertise
**Problem:** LLM comparisons don't account for domain-specific nuance (e.g., regulatory complexity in energy vs software).

**Mitigation ideas:**
- Domain-aware KPI sets (energy plans weight regulatory compliance higher)
- Expert validation: flag top 5% plans for optional human review

---

## Ideas to Take It Up One More Level

### 1. KPI Reasoning Storage + Display

**Current state:** KPI comparisons generate reasoning, but it's discarded.

**Enhancement:**
- Store comparison results in `plan_metrics.kpi_details` (JSONB)
- UI: "Why is my plan ranked here?" → show top 3 KPI gaps vs higher-ranked neighbors

**Value:** Turns rank into **actionable feedback**.

---

### 2. Percentile Bands + Tier Labels

**Current state:** Raw ELO score (e.g., 1650).

**Enhancement:**
Map ELO to tier labels:
| ELO Range | Tier          | Percentile | UI Badge      |
|-----------|---------------|------------|---------------|
| 1800+     | Exceptional   | Top 5%     | 🏆 Gold       |
| 1700–1799 | Strong        | Top 10–25% | 🥈 Silver     |
| 1600–1699 | Solid         | 25–50%     | 🥉 Bronze     |
| 1500–1599 | Developing    | 50–75%     | 📊 Standard   |
| <1500     | Needs Work    | Bottom 25% | 🔧 Improve    |

**Value:** Human-readable ranking + motivational framing.

---

### 3. Prompt Improvement Suggestions (Per Tier)

**Enhancement:** Auto-generate tier-specific advice based on KPI gaps.

**Example (Bottom 25%):**
```
🔧 Your plan needs improvement (Bottom 25%, ELO 1420)

Weakest areas:
- Goal clarity (avg 2.1/5) → Add a single-sentence goal with time + scope bounds
- Measurability (avg 1.8/5) → Define 3–5 numeric KPIs with acceptance thresholds
- Risk management (avg 2.3/5) → Add risk register + mitigation triggers

Suggested prompt template:
"Build [specific deliverable] in [timeframe] with [3 KPIs]. 
Address risks: [top 3 risks]. Budget: [amount]. Success = [measurable outcome]."
```

**Value:** Converts demotivating rank into **learning opportunity**.

---

### 4. Domain-Specific Ranking Pools

**Current state:** All plans compete in one ELO pool.

**Enhancement:**
- Tag plans by domain (tech / energy / healthcare / social impact)
- Run separate ELO pools per domain
- Show **within-domain rank** + **global rank**

**Value:** Fairer comparison (energy plans compete with energy plans, not all software MVPs).

---

### 5. Temporal Decay for Old Plans

**Problem:** Plans generated 6 months ago may rank high but use outdated assumptions.

**Enhancement:**
- Apply ELO decay factor: `elo_effective = elo * (1 - 0.05 * months_since_creation)`
- Encourages re-ranking with fresh corpus

**Value:** Rankings stay current.

---

### 6. Investor View with Filters

**Current state:** `/api/leaderboard` shows top N globally.

**Enhancement:**
Add filters:
- Domain (tech / energy / social)
- Impact horizon (days / months / years / decades)
- Budget range
- Geographic region

**Value:** Investors find relevant plans faster.

---

### 7. A/B Test: Reasoning LLM for Top 10%

**Current approach:** All comparisons use Gemini-2.0-flash-001 (non-reasoning).

**Enhancement:**
- Use reasoning LLM (e.g., o1-mini) for **shortlist comparisons** (top 10% vs top 10%)
- Gemini-flash for initial filtering

**Value:** Better discrimination at the top of the leaderboard (where it matters most).

---

### 8. User Opt-In: "Compare My Plan to Top 5%"

**Enhancement:**
- User clicks "Compare to best" → system runs pairwise comparison vs top 5 plans
- Returns detailed KPI breakdown + reasoning
- Costs 1 credit

**Value:** Premium feature for serious users wanting expert-level feedback.

---

### 9. Public Benchmark Plans (Anonymous)

**Enhancement:**
- Maintain 10–20 **reference plans** (high-quality, hand-curated)
- New plans always compare against 2–3 reference plans
- Provides absolute quality anchor

**Value:** Mitigates cold-start and gaming risks.

---

### 10. Red-Team Gaming Detection

**Enhancement:**
- Monitor for prompt patterns that spike ELO without improving real-world utility
- Example: Plans that stuff keywords like "KPI" and "SMART goals" without substance
- Flag suspicious plans for human review

**Value:** Maintains ranking integrity.

---

## Implementation Roadmap

### Phase 1 (Now) ✅
- [x] Dynamic KPI extraction
- [x] Pairwise LLM comparison
- [x] ELO update
- [x] User plan list with ELO
- [x] Likert 1–5 integer scoring
- [x] 30-word reasoning cap
- [x] LLM-named "remaining considerations" KPI

### Phase 2 (Next)
- [ ] Store KPI reasoning in `kpi_details` JSONB
- [ ] Percentile tiers + UI badges
- [ ] Prompt improvement suggestions per tier
- [ ] Domain-specific ranking pools

### Phase 3 (Future)
- [ ] Investor filters (domain, budget, impact horizon)
- [ ] Reasoning LLM for top 10% comparisons
- [ ] Red-team gaming detection
- [ ] Public benchmark plans

---

## Technical Details

### Database Schema

**plan_corpus:**
```sql
id UUID PRIMARY KEY
title TEXT
url TEXT
json_data JSONB  -- full plan JSON for comparisons
owner_id UUID
embedding VECTOR(768)  -- OpenAI embedding
created_at TIMESTAMPTZ
```

**plan_metrics:**
```sql
plan_id UUID PRIMARY KEY REFERENCES plan_corpus(id)
novelty_score FLOAT
prompt_quality FLOAT
technical_completeness FLOAT
feasibility FLOAT
impact_estimate FLOAT
elo FLOAT DEFAULT 1500
bucket_id INT  -- for bucketing future experiments
review_comment TEXT  -- optional human feedback
updated_at TIMESTAMPTZ
```

**rate_limit:**
```sql
api_key TEXT PRIMARY KEY
last_ts TIMESTAMPTZ
count INT DEFAULT 0
```

### API Endpoints

**POST /api/rank**
- Input: `{plan_id, plan_json, budget_cents, title, url}`
- Returns: `{status, plan_id, elo, kpis}`
- Rate limit: 5 req/min per API key

**GET /api/leaderboard?limit=N**
- Returns top N plans (user-scoped)

**GET /api/export?limit=N**
- Returns top N plans with full metadata

**GET /rankings**
- User-facing UI: shows user's plans ranked by ELO

---

## Lessons Learned

### 1. Dynamic KPIs > Static Weights
Fixed KPI formulas invite gaming. Dynamic LLM-chosen KPIs adapt to plan type.

### 2. Integer Likert > Floats
Easier to audit ("why did feasibility get a 2?") and prevents false precision.

### 3. Reasoning Transparency Matters
30-word reasoning makes scores defensible and debuggable.

### 4. Context > Absolute Score
"Top 10%" means more to users than "ELO 1720."

### 5. Actionable Feedback > Judgment
Pairing rank with **specific prompt improvements** turns rankings into a learning tool.

---

## Conclusion

ELO ranking gives PlanExe users **contextual, comparative feedback** on plan quality while maintaining privacy. The next level involves:
1. **Storing + surfacing KPI reasoning** (turn rank into advice)
2. **Tier-based prompt improvement suggestions** (actionable feedback)
3. **Domain-specific pools** (fairer comparisons)
4. **Investor filters** (faster discovery)
5. **Reasoning LLM for top-tier plans** (better discrimination at the top)

The goal: make rankings a **tool for improvement**, not just a leaderboard.

---

**Next steps:**
- Implement Phase 2 enhancements (kpi_details storage, percentile tiers, prompt suggestions)
- Validate with real user cohort
- Iterate based on feedback

**Questions? Feedback?**  
Open an issue or PR at https://github.com/VoynichLabs/PlanExe2026
