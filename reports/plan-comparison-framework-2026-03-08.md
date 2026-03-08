# Plan Comparison Framework — 2026-03-08

**Author:** Egon (EgonBot)  
**Date:** 2026-03-08  
**Source data:** `swarm-coordination/events/2026/mar/08-planexe-runs.md`  
**Purpose:** Define how to compare multi-model PlanExe runs across the ALGO/HVT/BAT scenarios.

---

## 1. Comparison Dimensions

### 1.1 Task Completion

| Dimension | Description |
|---|---|
| **Tasks total** | Total pipeline tasks attempted |
| **Tasks ok** | Tasks that completed without error |
| **Tasks failed** | Tasks with a non-zero error (JSON decode, timeout, thinking bleed, etc.) |
| **Completion rate** | `tasks_ok / tasks_total` — primary health metric |
| **Run status** | COMPLETE / PARTIAL / FAIL (categorical) |

### 1.2 Failure Modes

Failures observed across today's runs fall into distinct categories. Each run should be tagged with
the failure modes present:

| Failure Mode | Description | Example Run |
|---|---|---|
| `thinking_bleed` | Model emits `<think>` tokens into structured output field | ALGO_nemotron_v1, HVT_nemotron_v1 |
| `additional_kwargs_error` | `TypeError` from llama_index when `enable_thinking` passed directly | ALGO_qwen35b_v1 |
| `context_truncation` | Silent prompt truncation due to `context_window=3900` default | JEX runs (fixed) |
| `venv_lock` | Python environment lock / dependency conflict on startup | ALGO_qwen35b_v1 |
| `shallow_output` | Run completes but produces far fewer files than expected (~17 vs ~63) | ALGO_glm47flash_v1 |
| `config_issue` | Misconfiguration (wrong preset, missing field) that aborts early | ALGO_qwen9b_v2 |
| `unknown` | Failure with no clear root cause yet assigned | — |

### 1.3 Output Quality Markers

These are proxies for plan quality, not gold-standard evaluation, but useful for quick triage:

| Marker | How to measure |
|---|---|
| **File count** | Count of files in output dir (more ≈ more complete pipeline) |
| **Pipeline stage reached** | Highest-numbered task file present (e.g., `063-...` = all stages done) |
| **`999-pipeline_complete.txt` present** | Binary complete/not signal |
| **Structured JSON validity** | Can output files be parsed as valid JSON? (spot check) |
| **Depth of plan** | Line count / section count in final plan markdown (shallow runs produce thin plans) |

---

## 2. Data Currently Available vs Missing

### Available Now

- **Run directories** on Bubba's Mac Mini at  
  `/Users/macmini/Documents/GitHub/PlanExe2026/planexe-outputs/2026-03-08/`
- **File counts** per run (manually counted and recorded in `08-planexe-runs.md`)
- **Run status** (COMPLETE / PARTIAL / FAIL) — manually assessed
- **Failure mode notes** — written up in `08-planexe-runs.md` key findings section
- **Inference speed** — recorded for Qwen 3.5-35B and Qwen 3.5-9B (prefill + generation tok/s)

### Missing / Not Yet Captured

| Gap | Root Cause | When Fixed |
|---|---|---|
| Per-task pass/fail counts | No `run_summary.json` exists | After Proposal 96 is implemented |
| Per-call token counts | `PLANEXE_TASK_ID` not set in CLI runs → metrics dropped | After Proposal 95 is implemented |
| Wall-clock duration per run | Not recorded (only rough estimates from Bubba's notes) | After Proposal 96 (`run_summary.json`) |
| Model name per run | Inferred from dir name, not from a machine-readable artifact | After Proposal 96 |
| Cost per run | No usage log for local runs | After Proposal 95 (`usage.jsonl`) |
| Output quality scores | Not yet defined or computed | Future work |

---

## 3. What Proposal 95 (Usage Logging) Will Add

Proposal 95 writes `usage.jsonl` to the output directory — one line per LLM call — regardless of
whether `PLANEXE_TASK_ID` is set. Once implemented, each run directory will contain:

- **Total input/output/thinking tokens** for the full run
- **Per-call duration** (enables tok/s computation)
- **Model name** as reported by the LLM response
- **Cost estimate** (if pricing data is in config)

This closes the biggest data gap for local CLI runs and makes model comparison data-driven rather
than based on wall-clock impressions.

---

## 4. Suggested Comparison Table

One row per run, columns cover all comparison dimensions. Scenario and model are the primary keys.

```
| Scenario | Model          | Run Dir             | Status   | Files | Tasks OK | Tasks Fail | Failure Modes              | Tok/s | Duration |
|----------|----------------|---------------------|----------|-------|----------|------------|----------------------------|-------|----------|
| ALGO     | glm-4-7b-flash | ALGO_glm47flash_v1  | PARTIAL  | ~17   | ?        | ?          | shallow_output             | ?     | ?        |
| ALGO     | lfm2           | ALGO_lfm2_v1        | PARTIAL  | 32    | ?        | 4          | (4 task errors)            | ?     | ?        |
| ALGO     | nemotron       | ALGO_nemotron_v1    | FAIL     | ~4    | ?        | ?          | thinking_bleed             | ?     | ?        |
| ALGO     | qwen3.5-9b     | ALGO_qwen9b_v1      | FAIL     | ~2    | ?        | ?          | thinking_bleed, config     | ?     | ?        |
| ALGO     | qwen3.5-35b    | ALGO_qwen35b_v1     | FAIL     | ~1    | ?        | ?          | venv_lock, kwargs_error    | ?     | ?        |
| ALGO     | qwen3.5-35b    | ALGO_qwen35b_v2     | COMPLETE | 152   | ?        | 0          | —                          | 32.8  | ?        |
| HVT      | glm-4-7b-flash | HVT_glm47flash_v1   | PARTIAL  | 17    | ?        | ?          | shallow_output             | ?     | ?        |
| HVT      | lfm2           | HVT_lfm2_v1         | PARTIAL  | 62    | ?        | 4          | (4 task errors)            | ?     | ?        |
| HVT      | nemotron       | HVT_nemotron_v1     | FAIL     | ~2    | ?        | ?          | thinking_bleed             | ?     | ?        |
| HVT      | qwen3.5-9b     | HVT_qwen9b (Mar 7)  | COMPLETE | 63    | 63       | 0          | —                          | ?     | ~75 min  |
| BAT      | glm-4-7b-flash | BAT_glm47flash_v1   | PARTIAL  | —     | ?        | ?          | shallow_output             | ?     | ?        |
| BAT      | lfm2           | BAT_lfm2_v1         | PARTIAL  | 28    | ?        | 2          | (2 task errors)            | ?     | ?        |
| BAT      | nemotron       | BAT_nemotron_v1     | FAIL     | —     | ?        | ?          | thinking_bleed             | ?     | ?        |
| BAT      | qwen3.5-35b    | BAT_qwen35b_v2      | IN PROG  | —     | —        | —          | —                          | 32.8  | —        |
```

`?` = data not yet captured. These fields will be populated once:
- Proposal 95 (`usage.jsonl`) is implemented → fills Tok/s and token counts
- Proposal 96 (`run_summary.json`) is implemented → fills Tasks OK/Fail, Duration
- Bubba runs a post-run file-count scan on completed output dirs

---

## 5. Priority Gaps to Close

1. **Task-level pass/fail counts** — currently unknown for all PARTIAL runs. Even a simple script
   that counts `*-error.txt` vs `*-complete.txt` files in each run dir would fill this without
   waiting for Proposal 96.

2. **Shallow output diagnosis** — GLM-4-7B-Flash produces ~17 files vs ~63 for complete runs.
   Root cause unclear. Is it hitting a rate limit? Context overflow? Task dependency failure early
   in the pipeline that cascades? Needs a run with verbose logging enabled.

3. **HVT_qwen35b_v2 and BAT_qwen35b_v2 outcomes** — both in progress as of this writing. Results
   will complete the 35B column for HVT and BAT.

---

## 6. Next Steps

| Action | Owner | Unblocked By |
|---|---|---|
| Script to count pass/fail files per run dir | Egon / Bubba | Nothing — can do now |
| Implement Proposal 95 (usage.jsonl) | Egon | PR review |
| Implement Proposal 96 (run_summary.json) | Egon | PR review |
| Re-run ALGO/HVT/BAT with usage logging ON | Bubba | Proposal 95 merged |
| Populate comparison table from run_summary.json | Egon | Proposal 96 merged |
