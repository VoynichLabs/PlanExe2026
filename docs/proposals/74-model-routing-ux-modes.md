# Proposal 74: Model Routing UX — Automatic, Optimize, and Review Modes

**Author:** Larry (Sonnet 4.6)  
**Date:** 2026-02-27 (updated same day)  
**Status:** Draft — for Simon's consideration  
**Depends on:** Proposal 73 (task complexity scoring + model routing)

---

## The Problem

Most users pick their best model and use it for everything. Cognitively easy. Also expensive and, for many tasks, overkill.

The alternative — manually routing each task to the right model tier — requires understanding context windows, pricing tiers, semantic complexity, session hygiene, the 200K token cliff, speed tradeoffs, and local vs cloud options. Most developers don't want to think about this any more than most drivers want to think about gear ratios.

This is exactly the problem the automatic transmission solved in 1940.

---

## The Transmission Analogy

**Opus-for-everything = 4WD Truck**  
Big, shiny, handles anything. Gets 5 miles to the gallon. When you're heading to the store on a sunny day, it's overkill — but it works, and you don't have to think.

**Power user = Street Racer with a Stick Shift**  
Maximum efficiency, maximum control. Feel every gear change. Know exactly which model to use for which task. Zip through a codebase like a street race through downtown. Requires skill and attention — but the payoff is real.

**PlanExe's job = The 1940 GM Hydra-Matic**  
Earl Thompson spent a decade encoding the expertise of gear-shifting into the machine. The driver just says "go." The car figures out the gears. PlanExe can do the same for model selection. Encode the expertise. The user benefits without needing to possess it.

---

## What Windsurf Got Right

Windsurf's architecture is instructive: **plan with Opus, execute with SWE-1.5**.

SWE-1.5 runs at approximately 1,000 tokens per second. Opus runs at 30–40 tokens/second. For a 500-token execution task:
- SWE-1.5: 0.5 seconds
- Opus: 12–15 seconds

Scale that to 100 parallel execution tasks: 50 seconds vs 20+ minutes. The bottleneck shifts from "waiting for AI" to "waiting for CI/CD." At that point, speed IS the value — faster feedback loops mean more iterations per hour, which means more output per developer-day, regardless of cost.

**The insight:** execution speed and cost are separate levers. The best routing decisions optimize both, not just one.

---

## The Four Routing Axes

Our original proposal (Proposal 73) treated routing as a cost optimization: pick the cheapest model that can handle the task. That's incomplete. The full decision has four axes:

### 1. Capability
Does the model get it right? Complex reasoning, cross-file architectural refactors, and security analysis of race conditions require Opus-level capability. Mechanical renames, docstring generation, and test stubs do not.

Key finding: the **Agentica framework** (Symbolica, MIT licensed, from Berkeley Sky Computing Lab) achieved 85.28% on ARC-AGI-2 with Opus 4.6 — vs 79.03% without the framework. More strikingly, Agentica + Opus 4.5 scored 49.58% vs 28.15% bare Opus 4.5. The framework architecture matters as much as model tier for complex reasoning tasks.

This means: a well-designed execution harness on a smaller model can outperform a bare Opus call. Routing isn't just "which model" — it's "which model + which framework pattern."

### 2. Cost
Cloud API pricing (per 1M tokens, via OpenRouter — flat, no context-length doubling):
- Local inference: **$0** (after hardware amortization)
- Minimax M2.5: **$0.30 input / $1.10 output**
- Haiku 4.5: **$1 / $5**
- Sonnet 4.6: **$3 / $15**
- Opus 4.6: **$5 / $25**

Note: The $5/$10 per-1M-token price jump at the 200K context boundary is **Anthropic direct API only**. OpenRouter pricing is flat regardless of session length.

### 3. Speed
Tokens per second varies significantly by model and provider:
- Fast execution models (SWE-1.5, Haiku on fast inference): **500–1,000+ TPS**
- Sonnet: **~50–100 TPS**
- Opus: **~30–40 TPS**
- Local inference (Mac Mini M4 Pro, 64GB): **~30–50 TPS** (zero API cost)

For tight iteration loops — code review, test generation, rename sweeps — speed matters more than marginal capability gains. Route to fast models for execution, reserve slow models for planning.

### 4. Local vs Cloud
A Mac Mini M4 Pro with 64GB unified memory can run a 70B parameter model at 4-bit quantization locally at 30–50 TPS. Zero marginal cost per token after hardware.

**Example local models that fit in 64GB:**
- Qwen 2.5 72B (4-bit) — strong code generation
- Llama 3.3 70B (4-bit) — general reasoning
- Comparable to Minimax M2.5 class for documentation, tests, simple renames

**Break-even math:** At $20/day in cloud API costs for execution tasks that could run locally, Mac Mini M4 Pro hardware (~$2,400) pays for itself in ~4 months. After that, those tasks cost nothing.

**Full routing tier list (lowest to highest cost):**
```
Local (free) → Minimax cloud ($0.30) → Haiku ($1) → Sonnet ($3) → Opus ($5)
```

---

## The 4096 max_tokens Trap

A common mistake in production code — including the example in Anthropic's own published articles — is setting `max_tokens=4096` for code analysis tasks.

**4,096 output tokens ≈ 250–300 lines of code** (at ~3.5 chars/token, ~50 chars/line).

For a file like `http_server.py` at 1,089 lines, a security review with structured JSON output (vulnerability list, severity ratings, confidence scores, patch suggestions) will truncate mid-response. The model doesn't warn you — it just stops. You get malformed JSON, missing findings, half-written patches.

**Production minimum for large file analysis:** 16,000–32,000 output tokens.

PlanExe's routing layer should set output token limits based on input file size, not a hardcoded constant. Suggested heuristic:
- Files < 200 lines: max_tokens 4,096
- Files 200–500 lines: max_tokens 8,192
- Files 500–1,000 lines: max_tokens 16,384
- Files > 1,000 lines: max_tokens 32,768 (or chunk by file boundary, not module boundary)

**Chunking rule:** When batching large codebases, chunk by file boundary — not module boundary. Module boundaries produce unpredictable context sizes. File boundaries are measurable and consistent.

---

## The Batch API Dimension

Anthropic's Batch API supports up to 100 concurrent requests at reduced rates. A 500-file codebase reviewed sequentially takes ~40 minutes. Batched: under 5 minutes.

For Simon's 108-file refactor, sequential routing gets the cost right but not the throughput. Parallel batched execution on the execution-tier models (Haiku/Minimax) with Opus used only for the planning pass is the optimal pattern:

1. **Opus pass** (one session): read architecture, generate routing plan + task list
2. **Batch execution** (100 concurrent): dispatch execution tasks to Haiku/Minimax
3. **Sonnet review** (targeted): validate outputs that scored low confidence

Wall-clock time collapses. Cost stays controlled.

---

## The Domain Scope — Beyond Code

The Novo Nordisk case: regulatory documentation creation from 10+ weeks → 10 minutes with Claude.

This isn't code. It's structured knowledge work — repetitive, rule-bound document generation. Our complexity rubric applies here too, and the routing implications are significant: documentation tasks score low on our rubric (low file size, low semantic complexity, low ambiguity, low context dependency) and belong in Minimax territory. Savings over all-Opus for documentation generation: 90%+, not the 53% we projected for code.

PlanExe's routing layer should not be code-only. Task type is a first-class routing input.

---

## Three UX Modes

### Mode 1: `auto`
Everything runs on the configured model. No routing logic. Maximum capability, maximum simplicity. For teams with budget flexibility who value predictability over optimization.

Config: `model_routing: auto`

---

### Mode 2: `optimize`
PlanExe scores each task (Proposal 73), selects model + local/cloud tier automatically, manages session boundaries, and executes without asking. The Hydra-Matic.

Config: `model_routing: optimize`

**Example summary shown after plan generation:**
```
Routing plan:
  Local inference:  2 tasks (docs, test stubs)           — $0.00
  Minimax cloud:    3 tasks (renames, simple edits)      — $0.18
  Haiku:            2 tasks (auth hardening, deploy fix) — $0.40
  Sonnet:           1 task  (perf optimization)          — $0.85
  Opus:             1 task  (module split, planning)     — $3.20

Estimated total: $4.63 (vs $18.00 at Opus-only) — 74% savings
Estimated wall-clock: 4.5 min (batch) vs 22 min (sequential Opus)
```

---

### Mode 3: `review`
Rubric scores tasks, generates routing recommendations with per-task cost and confidence estimates, pauses for human approval before execution. Power user mode.

Config: `model_routing: review`

**Example UI:**
```
Task A: Module split (http_server.py, 1,089 lines)
  Score: 19/20 → Opus (planning) recommended
  Speed: 30–40 TPS | Estimated output: 8,000 tokens (~4 min)
  Cost: $3.20 | Confidence: HIGH
  [Accept] [Override: Sonnet]

Task B: API rename (task_id → plan_id, 88 files)
  Score: 13/20 → Sonnet plan + Minimax execution
  Speed: Sonnet plan ~2 min | Minimax batch ~30 sec
  Cost: $0.85 | Confidence: MEDIUM
  [Accept] [Override: all-Opus]

Task F: Documentation updates (6 markdown files)
  Score: 5/20 → Local inference (if available) or Minimax
  Speed: Local ~15 sec | Minimax batch ~5 sec
  Cost: $0.00 local / $0.04 cloud | Confidence: HIGH
  [Accept] [Use local] [Use Minimax cloud]
```

---

## Structured Scoring Output (Anti-Hallucination)

The complexity scorer (Proposal 73) should return structured JSON with explicit confidence scores — not free text. Mirrors the security review pattern from the Anthropic Messages API:

```json
{
  "task_id": "A",
  "description": "Module split of http_server.py",
  "scores": {
    "file_size": 5,
    "semantic_complexity": 5,
    "ambiguity": 4,
    "context_dependency": 5
  },
  "total": 19,
  "recommended_model": "opus",
  "recommended_tier": "cloud",
  "confidence": 0.92,
  "reasoning": "1,089-line file, cross-module architectural refactor, whole-codebase context required",
  "estimated_input_tokens": 12000,
  "estimated_output_tokens": 8000,
  "estimated_cost_usd": 3.20,
  "flag_for_review": false
}
```

If `confidence < 0.6`, automatically escalate to `review` mode for that task regardless of global setting. **Do not hallucinate scores** — if file size cannot be determined, return `null` and explain.

---

## The Session Hygiene Rule

Opus writes the plan → session ends → new session opens → smaller model executes.

This isn't about the 200K cliff specifically (which is Anthropic direct only, not OpenRouter). It's about context drag: old file reads, abandoned exploration paths, prior conversation history accumulating in the session and degrading signal-to-noise. Keep planning sessions short and surgical. Keep execution sessions task-scoped.

---

## Questions for Simon

1. Does local inference (Mac Mini M4 Pro) belong in PlanExe's routing config as a first-class tier, or is it out of scope for v1?
2. For the Batch API pattern — should PlanExe manage concurrency itself, or delegate to Anthropic's batch endpoint?
3. Speed estimates in the `review` mode UI — too much noise, or genuinely useful for task prioritization?
4. Are there task types in PlanExe's current plan generation that should never route below Sonnet, regardless of score?
5. Should `confidence < threshold` auto-escalate globally, or should the threshold be per-task-type?

---

*Docs-only. No code. Companion to Proposal 73. Both PRs open for morning review.*
