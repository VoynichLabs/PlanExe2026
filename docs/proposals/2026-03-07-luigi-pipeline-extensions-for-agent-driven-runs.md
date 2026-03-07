# Luigi Pipeline Extensions for Agent-Driven Runs

Date: 2026-03-07  
Author: EgonBot  
Reviewers: neoneye, Bubba

---

## 1) Why this proposal exists

Luigi's resume capability is already one of PlanExe's most practical strengths. When a run dies mid-pipeline, restarting the script causes Luigi to skip all completed tasks and continue from the failure point. This saves hours of compute and allows iterative progress without discarding prior work.

However, the current resume model has a significant gap: it works at the task level, but it does not expose any programmatic hooks for agents or operators to interact with a run-in-progress. If a task fails, the only option is:
1. Fix the code or config.
2. Restart the pipeline.

There is no way to patch task output in place, force a single task to re-run without invalidating its dependents, inject revised data, or be notified externally when a specific task completes or fails.

For agent-driven operations (where an AI agent is attempting to keep the pipeline alive overnight), these gaps make the loop slower and more fragile than it needs to be.

This proposal defines concrete, minimal extensions to the pipeline that would allow agents to participate more effectively.

---

## 2) Target scenarios

The following scenarios motivated this proposal, all observed in real overnight runs:

**Scenario A — Agent edits a schema default and needs to resume without losing prior tasks.**  
Currently: must restart full pipeline. Completed tasks re-validate and Luigi skips them, but there is no way to target-invalidate just the failing task.

**Scenario B — A task produces known-bad output (e.g., empty `combined_summary`) due to truncation. The agent wants to patch the output file and retry only that task + dependents.**  
Currently: no supported path.

**Scenario C — An external webhook should fire when `CreateWBSLevel3Task` succeeds, so a downstream review agent can begin working.**  
Currently: no notification mechanism.

**Scenario D — An operator wants to restart `PreProjectAssessmentTask` alone, without clearing the whole run, because LM Studio timed out.**  
Currently: must delete the output file manually and restart, then hope Luigi re-runs only that task.

---

## 3) Proposed extensions (concrete)

### 3.1 Per-task invalidation CLI

Add a CLI subcommand (or flag) to `run_plan_pipeline.py` that allows targeted invalidation of one or more tasks.

```
python run_plan_pipeline.py --invalidate-task PreProjectAssessmentTask
```

Behavior:
- Deletes the Luigi output marker/file for the named task.
- Optionally: deletes output markers for all downstream dependent tasks.
- Does not touch any other task outputs.

Implementation sketch:
- Each `PlanTask` output is a `luigi.LocalTarget` with a known path.
- Invalidation means deleting that target file.
- Dependency graph walk is already implicit in Luigi's requires() chain.
- A new utility function `invalidate_task(task_class, cascade=True)` would recurse the dependency graph.

Acceptance criteria:
- Operator can re-run a single failing task without discarding completed upstream work.
- Luigi resume picks up correctly after invalidation.

---

### 3.2 Output file editing with task re-queue

Allow a task's output JSON to be edited in place (by agent or operator), then explicitly marked for re-validation/re-use.

Approach:
- Each task that writes JSON output should document the exact output path and schema.
- Add a `--validate-output PreProjectAssessmentTask` CLI flag that re-validates the current output file against the task's schema without running the LLM, and marks it as valid or invalid.

Use case:
- Agent detects truncation failure → patches the output file → validates → downstream tasks resume from patched data.

Acceptance criteria:
- Output file path is documented per task.
- Validation check produces clear pass/fail.

---

### 3.3 Webhook/callback hooks at task lifecycle points

Add an optional webhook delivery mechanism that fires at defined points in the task lifecycle.

Proposed hook points:
- `task_completed(task_name, output_path, duration_seconds)`
- `task_failed(task_name, error_class, error_summary, attempt_count)`
- `pipeline_completed(run_dir, total_tasks, total_duration)`
- `pipeline_failed(run_dir, failing_task, error_summary)`

Configuration: add optional `webhooks` block to pipeline config or `.env`:
```json
"webhooks": {
  "on_task_failed": "https://my-agent.example.com/planexe-notify",
  "on_pipeline_completed": "https://my-agent.example.com/planexe-notify"
}
```

Payload schema (per event):
```json
{
  "event": "task_failed",
  "task_name": "PreProjectAssessmentTask",
  "run_dir": "/path/to/run/output",
  "error_class": "ReadTimeout",
  "error_summary": "...",
  "timestamp_utc": "2026-03-07T02:55:00Z"
}
```

Behavior:
- Best-effort (never block pipeline execution on webhook failure).
- Optional, disabled by default.
- Log delivery status in `log.txt`.

Acceptance criteria:
- Webhook fires within 5 seconds of task event.
- Missing/unreachable webhook does not crash or slow pipeline.

---

### 3.4 Structured run manifest (always written)

After each pipeline execution (success or partial), write a `run_manifest.json` to the run output directory:

```json
{
  "run_dir": "...",
  "started_at_utc": "2026-03-07T02:30:00Z",
  "completed_at_utc": null,
  "status": "partial",
  "tasks_completed": [...],
  "tasks_failed": [
    {
      "task": "PreProjectAssessmentTask",
      "error_class": "ReadTimeout",
      "error_summary": "...",
      "attempt_count": 3
    }
  ],
  "tasks_pending": [...],
  "pipeline_version": "..."
}
```

This manifest is useful for:
- agent status polling without log scraping,
- human morning review,
- webhook payloads,
- future dashboard integration.

Acceptance criteria:
- Written atomically on pipeline completion or termination.
- Parseable without custom code.

---

### 3.5 Downstream cascade invalidation utility

Extend the per-task invalidation (3.1) with an explicit `--invalidate-from TaskName` mode that:
- Deletes the output of the named task AND all tasks that depend on it (recursively via `requires()`).
- Prints the list of invalidated tasks before deleting, with confirmation prompt.

This gives agents and operators a safe way to re-run a partial subtree without guessing which outputs to delete.

---

## 4) Scope and non-goals

### In scope
- Minimal, safe extensions to existing Luigi pipeline integration.
- CLI options for targeted invalidation.
- Optional webhook delivery.
- Run manifest output.

### Not in scope
- UI changes.
- Changing core Luigi internals.
- Real-time streaming APIs (a separate concern).
- Multi-run orchestration.

---

## 5) Implementation order

1. Run manifest writer (simplest, no behavior change, adds immediate value for debugging and agent status polling).
2. Per-task invalidation CLI (`--invalidate-task`).
3. Webhook/callback hooks for task fail + pipeline complete events.
4. Output file validation CLI (`--validate-output`).
5. Downstream cascade invalidation (`--invalidate-from`).

Each item is independently mergeable.

---

## 6) Acceptance tests (before marking done)

- Run pipeline → fail at `PreProjectAssessmentTask` → use `--invalidate-task PreProjectAssessmentTask` → restart → Luigi skips everything above and re-runs only that task.
- Configure a webhook on `on_task_failed` → cause failure → confirm webhook received within 5 seconds.
- Run manifest contains correct task lists after partial run.
- `--validate-output` correctly reports pass/fail on known-good and known-bad output files.
