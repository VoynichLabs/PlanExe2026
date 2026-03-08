# Proposal 96: Agent-Native PlanExe CLI

**Status:** Draft  
**Author:** Egon (EgonBot)  
**Date:** 2026-03-08  
**Scope:** CLI entrypoint, pipeline runner, output directory

---

## Problem

PlanExe is a powerful planning system, but invoking it from an AI agent or automation script
requires a human-in-the-loop at multiple points:

1. **Web UI required to start a plan.** There is no CLI command to submit a prompt and kick off
   a full pipeline run. An operator must open a browser and click through the UI.

2. **`PLANEXE_TASK_ID` must be set manually.** The token metrics system only activates when this
   env var is present. A human must set it before each run; otherwise metrics are silently dropped.

3. **LM Studio thinking suppression requires UI interaction.** The `planexe-agents` preset that
   suppresses `<think>` token bleed must be applied by clicking in the LM Studio UI. There is
   no way to inject a system prompt or model parameter from the command line. If the model is
   reloaded (e.g., between runs or after a crash), the preset is lost and the next run fails.

4. **No structured completion signal.** The only signal that a run finished is the presence of
   `999-pipeline_complete.txt` in the output directory. There is no exit code, no structured
   summary, and no machine-readable record of what succeeded or failed.

5. **No machine-readable failure report.** When tasks fail, the information is scattered across
   individual task files and console logs. An orchestrating agent cannot determine what failed
   without parsing human-readable text.

These gaps make it impractical to use PlanExe inside automated agent loops, CI pipelines, or
multi-run comparison workflows without manual babysitting at each step.

---

## Goals

1. Provide a single CLI command that runs a complete plan end-to-end.
2. Auto-generate and set `PLANEXE_TASK_ID` (UUID) per run — no manual setup.
3. Return exit code `0` on full success, non-zero on any failure.
4. Write `run_summary.json` to the output directory at completion.
5. Support a `--system-prompt` flag to inject instructions (e.g., `/no_think`) without modifying
   config files or touching the LM Studio UI.
6. Emit one structured JSON line to stdout per completed task, for agent log parsing.

---

## Non-Goals

- Full MCP server interface (separate proposal).
- Changing the existing web UI or its API contracts.
- Real-time streaming of partial task output.
- New authentication or multi-user CLI flows.
- Changing the output directory file layout (tasks, artifacts, etc. remain as-is).

---

## Proposed CLI Interface

```
planexe run \
  --prompt "Build a plan for X" \
  --output-dir ./output/my-run \
  --llm-config llm_config/local.json \
  [--system-prompt "/no_think"] \
  [--mode FAST_BUT_SKIP_DETAILS] \
  [--dry-run]
```

### Flags

| Flag | Type | Description |
|---|---|---|
| `--prompt` | string (required) | The planning prompt. |
| `--output-dir` | path (required) | Directory to write all output files. Created if absent. |
| `--llm-config` | path | JSON config for the LLM provider/model. Default: `llm_config/local.json`. |
| `--system-prompt` | string | Prepended to every LLM call as a system instruction. Useful for `/no_think`, persona, etc. |
| `--mode` | enum | Pipeline mode: `FULL`, `FAST_BUT_SKIP_DETAILS`. Default: `FULL`. |
| `--dry-run` | flag | Validate config and print the run plan; do not execute. |
| `--quiet` | flag | Suppress per-task JSON lines on stdout; only print final summary. |

### Behavior

1. On start, generate a UUID and set it as `PLANEXE_TASK_ID` for the process.
2. If `--system-prompt` is given, inject it as a system message prefix on every LLM call for
   this run (no config file modification required).
3. Run the pipeline. For each completed task, emit one JSON line to stdout:
   ```json
   {"event": "task_complete", "task_id": 42, "name": "identify_resources", "status": "ok", "duration_s": 3.2}
   ```
   For failures:
   ```json
   {"event": "task_complete", "task_id": 43, "name": "estimate_cost", "status": "fail", "error": "JSONDecodeError: ..."}
   ```
4. On completion (success or partial), write `run_summary.json` to `--output-dir`.
5. Exit `0` if all tasks completed successfully. Exit `1` if any tasks failed. Exit `2` on
   configuration or startup errors (before any tasks ran).

---

## `run_summary.json` Schema

```json
{
  "run_id": "a3f7c2d1-...",
  "prompt": "Build a plan for X",
  "model": "lmstudio-qwen3.5-35b",
  "llm_config": "llm_config/local.json",
  "mode": "FULL",
  "system_prompt": "/no_think",
  "started_at": "2026-03-08T14:50:00Z",
  "completed_at": "2026-03-08T16:05:00Z",
  "duration_s": 4500,
  "tasks_total": 63,
  "tasks_ok": 61,
  "tasks_failed": 2,
  "failures": [
    {
      "task_id": 43,
      "name": "estimate_cost",
      "error": "JSONDecodeError: Expecting value at line 1"
    },
    {
      "task_id": 57,
      "name": "risk_matrix",
      "error": "TimeoutError after 120s"
    }
  ],
  "exit_code": 1
}
```

All fields are required. `failures` is an empty array `[]` on a clean run. `system_prompt` is
`null` if not provided. `exit_code` mirrors the process exit code.

---

## Relationship to Proposal 95 (Usage Logging)

Proposal 95 adds `usage.jsonl` to the output directory, capturing per-call token counts, duration,
and cost. Proposal 96's `run_summary.json` is complementary: it captures run-level outcomes (task
pass/fail, total duration, model used), not per-call token detail.

Both files land in the same `--output-dir`. A downstream agent or report script can read both.

---

## Acceptance Criteria

- [ ] `planexe run --prompt "..." --output-dir ./out --llm-config llm_config/local.json` runs
      end-to-end without browser or manual setup.
- [ ] A UUID `PLANEXE_TASK_ID` is automatically generated and visible in logs and `run_summary.json`.
- [ ] `run_summary.json` is present in `--output-dir` after every run, success or failure.
- [ ] Exit code is `0` for a clean run, `1` for partial failures, `2` for startup/config errors.
- [ ] `--system-prompt "/no_think"` causes the string to appear in the system message of every LLM
      call, confirmed by intercepting one call in tests.
- [ ] Structured JSON lines appear on stdout as each task completes.
- [ ] `--dry-run` exits `0` without executing any LLM calls.
- [ ] Existing web UI flows are unaffected (no regressions in server-mode startup or API).

---

## Open Questions

1. Should `--system-prompt` be additive (prepend to any existing system prompt in the config) or
   replacement? Additive is safer; replacement is simpler.
2. Is `planexe` the right top-level binary name, or should this live under a subcommand of the
   existing `run_plan.py` entry point?
3. Should `run_summary.json` be written incrementally as tasks complete (resilient to crashes) or
   only at the end? Incremental is more robust for long runs.
