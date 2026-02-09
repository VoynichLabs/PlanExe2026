# Plan Ranking Pipeline (Elo + KPI)

## Overview
PlanExe ranks generated plans using a two‑phase LLM evaluation to avoid gaming static weights:

1. **Extract raw KPI vector** (novelty, prompt quality, technical completeness, feasibility, impact)
2. **Pairwise LLM comparison** of KPI vectors → Likert preference
3. **Elo update** for new plan and sampled neighbors

## Defaults
- LLM: **Gemini‑2.0‑flash‑001 via OpenRouter** (`OPENROUTER_API_KEY`)
- Embeddings: **OpenAI embeddings** (`OPENAI_API_KEY`)
- Vector store: **pgvector** (Postgres extension)
- Rate limit: **5 req/min per API key**
- Corpus source: PlanExe‑web `_data/examples.yml`

## Endpoints
- `POST /api/rank` → rank plan, update Elo
- `GET /api/leaderboard?limit=N` → user‑scoped leaderboard
- `GET /api/export?limit=N` → top‑N export

## Data Tables
- `plan_corpus`: plan metadata + embeddings + json_data (for dynamic KPI comparisons)
- `plan_metrics`: KPI values + Elo
- `rate_limit`: per‑API‑key rate limiting

## Setup
1. Run migrations:
   - `mcp_cloud/migrations/2026_02_09_create_plan_metrics.sql`
   - `mcp_cloud/migrations/2026_02_10_add_plan_json.sql`
2. Seed corpus: `scripts/seed_corpus.py` (set `PLANEXE_WEB_EXAMPLES_PATH`)
3. Set env:
   - `OPENROUTER_API_KEY`
   - `OPENAI_API_KEY`
   - `PLANEXE_API_KEY_SECRET`

## Notes
- Ranking uses **real data only** (no mocks)
- Embeddings stored in pgvector for novelty sampling
- Leaderboard UI at `/rankings`
