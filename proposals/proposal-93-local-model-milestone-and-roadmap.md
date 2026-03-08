# Proposal 93 — Local Model Milestone & Roadmap

**Date:** 2026-03-08  
**Authors:** EgonBot, Bubba  
**Status:** Draft

---

## Milestone Achieved: First Complete Local Model Run

On 2026-03-07, PlanExe completed a full pipeline run on a local model for the first time in the project's history.

**Run details:**
- Model: Qwen 3.5-9B (GGUF, llama.cpp via LM Studio)
- Hardware: Mac Mini (Bubba's local machine)
- Tasks: 63 scheduled, 56 executed, 7 cached, **0 failed**
- Runtime: ~70 minutes
- Prompt: HVT (paintball-style drone evasion combat simulation game)

Every previous local model attempt had failed at one or more pipeline gates. This run cleared all of them, including PremortemTask — the most complex structured-output gate in the pipeline.

---

## Why This Is Significant

### 1. Cost independence
PlanExe can now produce full planning output without any cloud API spend. A complete run on a 9B local model costs $0 in API fees and runs on consumer hardware. This is a viable alternative to cloud runs for development, testing, and cost-sensitive use cases.

### 2. Privacy
Sensitive plan prompts never leave the user's machine. For users in regulated industries or with confidentiality requirements, local execution is not just a cost option — it's the only acceptable option.

### 3. Reproducibility
With the LM Studio preset (`presets/lmstudio-planexe.json`) and the `llm_config/local.json` adapter config now in the repository, any developer can reproduce tonight's run by loading the preset and pointing PlanExe at their local LM Studio instance.

### 4. Structural pipeline health
To get here, we diagnosed and fixed a class of failure that had been silently undermining every local run:
- Wrong LM Studio adapter (`LMStudio` → `OpenAILike`) — structured output was never being enforced
- Pydantic `str(Enum)` fields generating `$defs`/`$ref` schemas that MLX Outlines cannot resolve
- Silent timeout failures (field name mismatch: `request_timeout` vs `timeout`)
- Thinking mode bleeding into `reasoning_content` instead of `content`

These fixes make the pipeline more robust for **all** backends, not just local models.

---

## What We Fixed (PRs Merged)

| PR | Description |
|----|-------------|
| #180 | Null guard: `chat_response.raw` None check |
| #182 | Levers prompt cleanup (strip embedded JSON examples) |
| #187 | `identify_purpose.py`: null guard + `Literal["personal","business","other"]` |
| #188 | Enum → Literal migration: 8 files, pipeline-wide |
| #189 | CI parity test: AST-based, verifies Literal↔Enum value sets stay in sync |

---

## Open PRs (Awaiting Review)

| PR | Description | Priority |
|----|-------------|----------|
| #177 | `plan_resume` MCP tool | Medium |
| #181 | `premortem.py`: per-archetype decomposition for small models | High |
| #183 | `DeduplicateLeversTask`: per-lever decomposition | High |
| #192 | LM Studio preset (correct format + improved system prompt) | Medium |
| #194 | `llm_config/local.json`: switch to `OpenAILike` adapter | **Critical** |

PR #194 is the core enabler — without it, local runs still use the wrong adapter.

---

## Roadmap: What Comes Next

### Immediate (next session)
1. **Merge #194** — make the OpenAILike adapter the official local config
2. **Merge #181 + #183** — premortem and dedup levers are the two remaining schema-complexity hotspots
3. **Push proof-run outputs** to VoynichLabs/PlanExe2026 and update the HVT comparison report with Qwen 9B GGUF as a fourth data point

### Short-term
4. **GLM 4.7 Flash** — still blocked on thinking mode at API level; investigate LM Studio v1.x `/api/v1/chat` endpoint which may expose per-request thinking control
5. **Proposal 89** (context complexity reduction) and **Proposal 90** (pipeline complexity audit) — sub-agents still running; review and decide which recommendations to implement
6. **`require_raw()` utility** — centralize null guard across 30+ task files (sub-agent `c8f16938` branch)
7. **`/api/v1/chat` migration research** — sub-agent `ce147333` investigating native endpoint advantages

### Medium-term
8. **Second local model** — run Qwen 3.5-35B A3B (Big Qwen) through the same pipeline; compare output quality vs 9B at higher parameter count
9. **LM Studio Hub preset publication** — `presets/lmstudio-planexe.json` to `lmstudio.ai/82deutschmark/planexe-agents`
10. **CI integration** — add `test_enum_literal_parity.py` to the GitHub Actions workflow so it runs on every PR

### Strategic
11. **ALL_DETAILS mode on local hardware** — tonight's proof run used FAST_BUT_SKIP_DETAILS. The full-quality run requires more capable local models or further schema simplification.
12. **Model routing** — let PlanExe auto-select cloud vs local based on task complexity, available hardware, and cost budget.

---

## Key Technical Decisions Recorded

- **`Literal[...]` for schema fields, `str(Enum)` for comparisons** — approved pattern (neoneye); produces flat JSON schema, no `$defs`/`$ref`
- **One fix per PR, clean branch per PR** — learned the hard way; dirty branches create review friction
- **Sub-agent doctrine** — anything >5s must be delegated; main session stays responsive (Mark's standing order, added to SOUL.md)
- **Evidence before claims** — never assert capability or limitation without checking docs or intercepting actual request/response (Mark's troubleshooting doctrine)
