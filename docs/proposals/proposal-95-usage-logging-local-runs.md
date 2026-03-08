# Proposal 95: Usage Logging for Local / Direct CLI Runs

**Status:** Draft  
**Author:** Egon (EgonBot)  
**Date:** 2026-03-08  
**Scope:** `worker_plan/worker_plan_internal/llm_util/`, `worker_plan/worker_plan_internal/plan/`

---

## Problem

PlanExe already has a complete token metrics system (`token_counter.py`, `token_metrics_store.py`,
`token_instrumentation.py`, `track_activity.py`). It captures input/output/thinking tokens, duration,
provider, model, and cost per LLM call and exposes them at `/token-metrics/{task_id}`.

However, the system only activates when `PLANEXE_TASK_ID` is set in the environment. When running
pipelines directly via CLI scripts (the common local development and batch-comparison workflow),
`PLANEXE_TASK_ID` is not set, so all metrics are silently dropped.

The consequence:

- Token throughput (tok/s) is invisible to operators and developers.
- Per-run cost estimates are not recorded.
- Model comparison reports must rely on wall-clock eyeball estimates instead of instrumented data.
- Every alternative to LM Studio (Ollama, llamafile, llama.cpp server, etc.) has the same gap —
  none of them expose a queryable tok/s API; the only reliable source is the `usage` object in
  the LLM response.

---

## Goals

1. Capture `usage` data (input/output/thinking tokens, duration, model) from every LLM response,
   regardless of whether a task ID is present.
2. Log this data to a per-run JSONL file in the output directory so it survives without a database.
3. Compute and print a summary (total tokens, total duration, avg tok/s) at the end of each run.
4. Keep the database path working unchanged for server-mode deployments.
5. No provider-specific code. Work from the standard `response.raw["usage"]` / `response.usage`
   fields that any OpenAI-compatible endpoint returns.

---

## Non-Goals

- Do not add LM Studio-specific instrumentation.
- Do not add new environment variables to configure this behavior; it should be always-on.
- Do not change the `/token-metrics/{task_id}` API contract.
- Do not instrument prompt text or response text — tokens and timing only.

---

## Proposed Implementation

### 1. JSONL fallback store (`llm_util/usage_log.py`)

```python
"""Provider-agnostic per-run usage logger.

Writes one JSON line per LLM call to <output_dir>/usage.jsonl.
Works without a database or PLANEXE_TASK_ID.
"""
import json
import time
import threading
from pathlib import Path
from typing import Optional

_lock = threading.Lock()
_log_path: Optional[Path] = None


def init_usage_log(output_dir: Path) -> None:
    """Call once at pipeline startup with the run's output directory."""
    global _log_path
    with _lock:
        _log_path = output_dir / "usage.jsonl"


def record_usage(
    *,
    model: str,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    thinking_tokens: Optional[int],
    duration_seconds: float,
    success: bool,
    task_name: Optional[str] = None,
) -> None:
    """Append one record to the JSONL log. No-op if init_usage_log() was not called."""
    with _lock:
        if _log_path is None:
            return
        row = {
            "ts": time.time(),
            "task": task_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "duration_seconds": round(duration_seconds, 3),
            "success": success,
        }
        with _log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")


def print_usage_summary(output_dir: Path) -> None:
    """Print a summary table from usage.jsonl at the end of a run."""
    log_path = output_dir / "usage.jsonl"
    if not log_path.exists():
        return
    rows = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    if not rows:
        return
    total_input = sum(r.get("input_tokens") or 0 for r in rows)
    total_output = sum(r.get("output_tokens") or 0 for r in rows)
    total_thinking = sum(r.get("thinking_tokens") or 0 for r in rows)
    total_duration = sum(r.get("duration_seconds") or 0 for r in rows)
    total_calls = len(rows)
    avg_toks = (total_output / total_duration) if total_duration > 0 else 0
    print("\n=== Usage Summary ===")
    print(f"  Calls         : {total_calls}")
    print(f"  Input tokens  : {total_input:,}")
    print(f"  Output tokens : {total_output:,}")
    print(f"  Thinking tokens: {total_thinking:,}")
    print(f"  Total duration: {total_duration:.1f}s")
    print(f"  Avg output tok/s: {avg_toks:.1f}")
    print("=====================\n")
```

### 2. Integration point in `token_instrumentation.py`

After existing database write in `record_llm_tokens()`, add:

```python
from .usage_log import record_usage as _record_usage_log

# inside record_llm_tokens() after the database write:
_record_usage_log(
    model=llm_model,
    input_tokens=token_count.input_tokens,
    output_tokens=token_count.output_tokens,
    thinking_tokens=token_count.thinking_tokens,
    duration_seconds=duration_seconds,
    success=success,
    task_name=task_name,
)
```

### 3. Pipeline startup (`run_plan_pipeline.py`)

```python
from worker_plan_internal.llm_util.usage_log import init_usage_log, print_usage_summary

# at pipeline start:
init_usage_log(Path(output_dir))

# at pipeline end (success or failure):
print_usage_summary(Path(output_dir))
```

---

## Output example

`planexe-outputs/2026-03-08/ALGO_qwen35b_v2/usage.jsonl`:

```json
{"ts": 1741449600.0, "task": "IdentifyPurposeTask", "model": "qwen/qwen3.5-35b-a3b", "input_tokens": 1240, "output_tokens": 312, "thinking_tokens": 0, "duration_seconds": 28.4, "success": true}
{"ts": 1741449630.0, "task": "AssumptionsTask", "model": "qwen/qwen3.5-35b-a3b", "input_tokens": 2100, "output_tokens": 890, "thinking_tokens": 0, "duration_seconds": 35.1, "success": true}
```

End-of-run console summary:

```
=== Usage Summary ===
  Calls         : 63
  Input tokens  : 98,240
  Output tokens : 31,450
  Thinking tokens: 0
  Total duration: 4,210.3s
  Avg output tok/s: 7.5
=====================
```

---

## Why JSONL (not only database)

- JSONL survives without a running database server.
- The file lands in the output directory alongside other artifacts — easy to inspect, diff, and commit.
- It can be post-processed by any script without importing PlanExe code.
- Database path remains fully functional for server-mode; the JSONL log is additive.

---

## Affected Files

| File | Change |
|------|--------|
| `worker_plan/worker_plan_internal/llm_util/usage_log.py` | **New** — JSONL fallback store |
| `worker_plan/worker_plan_internal/llm_util/token_instrumentation.py` | Add `_record_usage_log()` call |
| `worker_plan/worker_plan_internal/plan/run_plan_pipeline.py` | Call `init_usage_log()` and `print_usage_summary()` |

---

## Acceptance Criteria

- [ ] Running a pipeline produces `usage.jsonl` in the output directory with one row per LLM call.
- [ ] End-of-run console prints the summary table.
- [ ] Summary includes avg output tok/s derived from `output_tokens / duration_seconds`.
- [ ] Works without `PLANEXE_TASK_ID` being set.
- [ ] Works with any OpenAI-compatible backend (LM Studio, Ollama, llamafile, OpenRouter, etc.).
- [ ] Database token metrics path continues to work unchanged.
- [ ] No new environment variables required.
