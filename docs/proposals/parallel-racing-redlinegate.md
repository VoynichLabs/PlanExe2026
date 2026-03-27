# Proposal: Parallel Racing for RedlineGate

**Author:** Egon (HejEgonBot)
**Date:** 2026-03-27
**Status:** Draft — for Simon's review

---

## Problem

`RedlineGateTask` runs a single model with a single system prompt and makes a binary ALLOW/REFUSE decision. If it refuses, the entire pipeline halts.

This produces false positives on prompts that are geopolitically provocative but operationally harmless — e.g., satirical geopolitical scenarios, tourist infrastructure for hypothetical acquisitions, fiction with crime themes. The model fires on content patterns rather than actual harm potential.

Simon already identified this in the code:

```python
# IDEA: ensemble. multiple perspectives of the same prompt using 3 or 5 system prompts.
```

(`worker_plan_internal/diagnostics/redline_gate.py`)

---

## What G0DM0D3 Does

G0DM0D3 (elder-plinius/G0DM0D3, forked to VoynichLabs/G0DM0D3) uses **parallel racing**:

- Same prompt → N model+system-prompt combos simultaneously
- Each combo runs independently
- Winner selected by composite score (quality, completeness, non-refusal)
- Up to 51 models in ULTRAPLINIAN mode

Observed result: On a prompt that Claude 3.5 Sonnet and Claude Sonnet 4 both refused, llama-3.1-8b-instruct scored 79/100 and won. The small, less-aligned model answered a geopolitically provocative but harmless planning prompt that the larger aligned models refused on pattern-matching.

---

## Proposed Change

Add an ensemble voting mode to `RedlineGate.execute()`.

Instead of one verdict from one model, run the same prompt against 3–5 system prompt variants in parallel and take a majority vote. The existing system prompt variants are already in `redline_gate.py` (SYSTEM_PROMPT_21 through SYSTEM_PROMPT_27) — they just aren't used in parallel.

### Concrete steps

1. Add `execute_ensemble(llm, user_prompt, system_prompts, workers=3)` to `RedlineGate`
2. Use `concurrent.futures.ThreadPoolExecutor` to race the system prompts
3. Collect verdicts, take majority: if 2/3 say ALLOW, gate passes
4. Expose via a `RedlineGateConfig` flag (default: single prompt, opt-in to ensemble)

### Why this is low-risk

- Existing single-prompt behavior is unchanged by default
- Ensemble mode is additive — same schema, same output format
- The system prompt variants already exist; no new prompt engineering required
- `LLMExecutor` already supports multiple models; this wires the parallel path

---

## pH Strip Framing

PlanExe is a reasoning diagnostic — it measures whether a model can decompose a planning task. When RedlineGate fires on content patterns and halts the pipeline, the instrument fails to give a reading. That's the failure mode this proposal addresses.

Parallel racing with majority voting reduces false positives without weakening the gate against genuine harms — because genuine harms should be refused by most system prompt variants, not just one.

---

## Out of Scope

- Parseltongue (input perturbation) — separate question, lower priority
- AutoTune (adaptive sampling) — connects to existing A/B testing roadmap, separate proposal
- ULTRAPLINIAN-style 51-model racing — overkill for a gate; 3–5 system prompt variants is the right scope here

---

## References

- `worker_plan_internal/diagnostics/redline_gate.py` — existing IDEA comment + system prompt variants
- `worker_plan_internal/llm_util/llm_executor.py` — existing sequential fallback infrastructure
- `VoynichLabs/G0DM0D3` — reference implementation of parallel racing
- `swarm-coordination/plans/2026-03-27-g0dm0d3-parallel-racing-proposal.md` — supporting analysis
