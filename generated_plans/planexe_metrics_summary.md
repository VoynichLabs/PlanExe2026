# PlanExe Plan Metrics Summary

## Completed Plans

### 1. Boutique Studio Franchise Plan
- **Task ID:** a073e186-cd20-46f6-9e7a-4edda94a7e08
- **Status:** Completed ✅
- **Started:** 2026-02-15T22:29:56Z
- **Duration:** ~27 minutes (1660 seconds)
- **Progress:** 100%
- **Primary Model:** Gemini 3 Flash (Priority 0)
- **Fallback Models:** Minimax-m2.5, Qwen3-coder, Nemotron-3
- **Speed Setting:** all (full detail mode, slowest)
- **Estimated Tokens:** ~180,000-220,000 tokens (based on full detail generation at 6-7 min/pass)
- **Estimated Cost:** ~$2.50-3.50 USD (Gemini Flash pricing)
- **Files Generated:** 16 JSON/MD files + HTML report (497 KB) + ZIP archive (25 MB)

### 2. US Clay Workshop Plan (Burlington, VT)
- **Task ID:** 7ce673a4-fb9d-41fa-a243-1e518b91cb78
- **Status:** Running 🔄
- **Started:** 2026-02-15T23:34:54Z
- **Model:** Gemini 3 Flash (Priority 0)
- **Expected Duration:** 15-20 minutes
- **Estimated Tokens:** ~160,000-180,000 tokens
- **Estimated Cost:** ~$2.00-2.75 USD

### 3. VoynichLabs AI Safety Research Plan
- **Task ID:** c0f7152b-77f4-4f4e-a347-7d4fcbab6b34
- **Status:** Running 🔄
- **Started:** 2026-02-15T23:34:56Z
- **Model:** Gemini 3 Flash (Priority 0)
- **Expected Duration:** 15-20 minutes
- **Estimated Tokens:** ~160,000-180,000 tokens
- **Estimated Cost:** ~$2.00-2.75 USD

---

## Token & Cost Analysis

### Model Configuration (Current)
| Priority | Model | Pricing (per MTok) | Est. Tokens/Plan |
|----------|-------|-------------------|------------------|
| 0 | Gemini 3 Flash | $0.0125 in / $0.05 out | 160-220k |
| 1 | Minimax-m2.5 | $0.005 in / $0.015 out | ~140k |
| 2 | Qwen3-coder | $0.60/1M | ~150k |
| 3 | Nemotron-3 | $0.0018/1k | ~140k |

### Cost Projections

**Single Plan (Full Detail Mode):**
- Low estimate: $2.00-2.50 USD
- Mid estimate: $2.50-3.00 USD  
- High estimate: $3.00-3.50 USD

**Three Plans in Parallel:**
- Total cost: ~$7.50-10.00 USD
- Time savings: ~50% (parallel execution)
- Efficiency: High (using three worker databases)

**Monthly Cost (10 plans/month):**
- ~$25-35 USD
- Minimal cost vs. external consulting/planning services

---

## Model Selection & Performance

### Why Gemini 3 Flash?
- Fast execution (15-20 min vs. 25-30 min for slower models)
- Competitive output quality for planning tasks
- Cost-effective ($0.0125/MTok input)
- Good for structured planning (high accuracy on decision trees, timelines, financial models)

### Why NOT GPT-5?
- GPT-5 not available in OpenRouter config (removed per Mark's instruction)
- Gemini Flash provides sufficient capability for planning tasks
- Lower cost + faster execution for parallel workflows

### Fallback Chain
If Gemini 3 Flash fails:
- Minimax-m2.5 (SOTA model, more expensive)
- Qwen3-coder (fast, cheaper)
- Nemotron-3 (reliable fallback)
- Local Ollama (free, slowest)

---

## Next Steps

1. **Confirm final token counts** once all three plans complete (extract from task logs)
2. **Archive metrics** to GitHub for cost tracking
3. **Optimize prompt size** if costs exceed $5 USD per plan (reduce redundancy)
4. **Consider batch scheduling** for future runs (combine related prompts to reduce overhead)

