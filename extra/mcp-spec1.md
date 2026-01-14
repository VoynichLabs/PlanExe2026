PlanExe MCP Interface Specification (v1.0)

1. Purpose

This document specifies a Model Context Protocol (MCP) interface for PlanExe that enables AI agents and client UIs to:
	1.	Create and run long-running plan generation workflows.
	2.	Receive real-time progress updates (phases, task status, log output).
	3.	List, read, and edit artifacts produced in an output directory.
	4.	Stop and resume execution with Luigi-aware incremental recomputation.

The interface is designed to support:
	•	interactive “build systems” behavior (like make / bazel),
	•	resumable DAG execution (Luigi),
	•	deterministic artifact management.

⸻

2. Goals

2.1 Functional goals
	•	Session-based orchestration: each run is associated with a session ID.
	•	Long-running execution: starts asynchronously; clients poll or subscribe to events.
	•	Artifact-first workflow: outputs are exposed as file-like artifacts.
	•	Stop / Resume with minimal recompute:
	•	on resume, only invalidated downstream tasks regenerate.
	•	Fine-grained progress reporting:
	•	overall progress
	•	phase
	•	current Luigi task (or logical task)
	•	Editable artifacts:
	•	user edits a generated file
	•	pipeline continues from that point, producing dependent outputs

2.2 Non-functional goals
	•	Idempotency: repeated tool calls should not corrupt state.
	•	Observability: logs, state transitions, and artifacts must be inspectable.
	•	Concurrency safety: prevent conflicting writes and illegal resume patterns.
	•	Extensibility: future versions can add task graph browsing, caching backends, exports.

⸻

3. Non-goals
	•	Defining PlanExe’s internal plan schema, content format, or prompt strategy.
	•	Providing remote code execution inside artifacts.
	•	Implementing a full Luigi UI clone in MCP v1 (optional later).
	•	Guaranteeing ETA estimates (allowed but must be optional / best-effort).

⸻

4. System Model

4.1 Core entities

Session
A long-lived container for a PlanExe project run.

Key properties
	•	session_id: stable unique identifier
	•	output_dir: artifact root namespace for session
	•	config: immutable run configuration (models, runtime limits, Luigi params)
	•	created_at, updated_at

Run
A single execution attempt inside a session (e.g., after a resume).

Key properties
	•	run_id: monotonic per session (run_0001, run_0002…)
	•	state: running | stopped | completed | failed
	•	phase: high-level stage (e.g., generating_plan, validating, exporting)
	•	progress: computed progress metrics
	•	started_at, ended_at

Artifact
A file-like output managed by PlanExe.

Key properties
	•	artifact_uri: stable URI
	•	path: path relative to session output root
	•	size, updated_at
	•	content_type: text/markdown, text/html, application/json, etc.
	•	kind: semantic label (plan, audit_report, log, state, intermediate)
	•	sha256: content hash for optimistic locking and invalidation

Event
A typed message emitted during execution for UI/agent consumption.

Key properties
	•	cursor: ordering token
	•	ts: timestamp
	•	type: event type
	•	data: event payload

⸻

5. State Machine

5.1 Session states

Sessions may exist independent of active runs.
	•	created: session initialized, no run started
	•	active: at least one run exists, may be running or stopped
	•	archived: optional; immutable, no new runs allowed

5.2 Run states
	•	running
	•	stopping (optional transitional state)
	•	stopped (user stopped, resumable)
	•	completed
	•	failed (resumable depending on failure type)

5.3 Allowed transitions
	•	created → running via session.start
	•	running → stopped via session.stop
	•	stopped → running via session.resume
	•	running → completed via normal success
	•	running → failed via error

Invalid
	•	completed → running (new run must be triggered via resume/new target)
	•	running → running (no concurrent runs in v1)

⸻

6. MCP Tools (v1 Required)

All tool names below are normative.

6.1 planexe.session.create

Creates a new session and output namespace.

Request

{
  "idea": "string",
  "config": {
    "planner_model": "string",
    "validator_model": "string",
    "max_runtime_sec": 7200,
    "luigi": {
      "workers": 4,
      "scheduler": "local"
    }
  },
  "metadata": {
    "user_id": "string",
    "tags": ["string"]
  }
}

Response

{
  "session_id": "pxe_2026_01_14__abcd1234",
  "output_dir_uri": "planexe://sessions/pxe_.../out",
  "created_at": "2026-01-14T12:34:56Z"
}

Behavior
	•	Must be idempotent only if client supplies an optional client_request_id (optional extension).
	•	Session config is immutable after creation in v1.

⸻

6.2 planexe.session.start

Starts execution for a target DAG output.

Request

{
  "session_id": "pxe_...",
  "target": "build_plan_and_validate",
  "inputs": {
    "seed_artifacts": ["planexe://.../out/prompt.md"]
  }
}

Response

{
  "run_id": "run_0001",
  "state": "running"
}

Constraints
	•	If a run is already running, must return error RUN_ALREADY_ACTIVE.

⸻

6.3 planexe.session.status

Returns run status and progress. Used for progress bars and UI states.

Request

{
  "session_id": "pxe_..."
}

Response

{
  "session_id": "pxe_...",
  "run_id": "run_0001",
  "state": "running",
  "phase": "generating_plan",
  "progress": {
    "overall": 0.62,
    "current_task": {
      "name": "WriteDetailedPlan",
      "pct": 0.33
    }
  },
  "timing": {
    "started_at": "2026-01-14T12:35:10Z",
    "elapsed_sec": 512
  },
  "latest_artifacts": [
    {
      "path": "plan.md",
      "artifact_uri": "planexe://sessions/pxe_.../out/plan.md",
      "kind": "plan",
      "updated_at": "2026-01-14T12:43:11Z"
    }
  ],
  "warnings": ["string"]
}

Notes
	•	progress.overall must be within [0,1].
	•	phase must be stable and enumerable.

⸻

6.4 planexe.session.stop

Stops the active run.

Request

{
  "session_id": "pxe_...",
  "run_id": "run_0001",
  "mode": "graceful"
}

Response

{
  "state": "stopped"
}

Required semantics
	•	Must stop workers cleanly where possible.
	•	Must persist enough Luigi state to resume incrementally.

⸻

6.5 planexe.session.resume

Resumes execution, reusing cached Luigi outputs and recomputing only invalidated tasks.

Request

{
  "session_id": "pxe_...",
  "target": "build_plan_and_validate",
  "resume_policy": "luigi_up_to_date",
  "invalidate": {
    "artifacts": [
      "planexe://sessions/pxe_.../out/plan.md"
    ],
    "tasks": []
  }
}

Response

{
  "run_id": "run_0002",
  "state": "running"
}

Required semantics
	•	Resume must not delete artifacts unless explicitly configured.
	•	If invalidate includes artifacts:
	•	mark downstream tasks dependent on these artifacts as stale.
	•	If a run is currently running, must return RUN_ALREADY_ACTIVE.

⸻

6.6 planexe.artifact.list

Lists artifacts under output namespace (supports UI “what files exist?”).

Request

{
  "session_id": "pxe_...",
  "path": "",
  "include_metadata": true
}

Response

{
  "entries": [
    {
      "type": "file",
      "path": "plan.md",
      "artifact_uri": "planexe://sessions/pxe_.../out/plan.md",
      "size": 48192,
      "updated_at": "2026-01-14T12:43:11Z",
      "content_type": "text/markdown",
      "kind": "plan",
      "sha256": "..."
    }
  ]
}

Constraints
	•	path must be relative and sandboxed to session root.
	•	Must never expose arbitrary server filesystem paths.

⸻

6.7 planexe.artifact.read

Reads an artifact (used for display and for agent post-processing).

Request

{
  "artifact_uri": "planexe://sessions/pxe_.../out/plan.md",
  "range": {
    "start": 0,
    "length": 200000
  }
}

Response

{
  "artifact_uri": "planexe://sessions/pxe_.../out/plan.md",
  "content_type": "text/markdown",
  "sha256": "...",
  "content": "..."
}


⸻

6.8 planexe.artifact.write

Writes an artifact (enables “Stop → Edit → Resume”).

Request

{
  "artifact_uri": "planexe://sessions/pxe_.../out/plan.md",
  "content": "string",
  "edit_reason": "user_patch",
  "lock": {
    "expected_sha256": "previous_sha256"
  }
}

Response

{
  "updated": true,
  "sha256": "new_sha256",
  "updated_at": "2026-01-14T12:52:00Z"
}

Required semantics
	•	Must support optimistic locking:
	•	if expected_sha256 mismatch → CONFLICT
	•	Writing must emit an event: artifact_updated

⸻

7. Event Streaming (v1 Strongly Recommended)

7.1 planexe.session.events

Provides incremental events for a session since a cursor.
This can be implemented as:
	•	long-poll,
	•	SSE,
	•	WebSocket,
	•	or “poll since cursor”.

Request

{
  "session_id": "pxe_...",
  "since": "cursor_123"
}

Response

{
  "cursor": "cursor_147",
  "events": [
    {
      "ts": "2026-01-14T12:41:00Z",
      "type": "phase_changed",
      "data": { "phase": "validating" }
    },
    {
      "ts": "2026-01-14T12:41:05Z",
      "type": "artifact_created",
      "data": {
        "path": "validation_report.html",
        "artifact_uri": "planexe://sessions/pxe_.../out/validation_report.html",
        "kind": "audit_report"
      }
    },
    {
      "ts": "2026-01-14T12:41:10Z",
      "type": "log",
      "data": {
        "level": "info",
        "msg": "Running PlanExe Self Audit…"
      }
    }
  ]
}

7.2 Event types (v1)
	•	run_started
	•	run_stopped
	•	run_completed
	•	run_failed
	•	phase_changed
	•	progress_updated
	•	task_started (optional if Luigi detail exposed)
	•	task_completed (optional)
	•	artifact_created
	•	artifact_updated
	•	artifact_deleted (optional)
	•	log

⸻

8. Targets and Phases

8.1 Standard targets

The following targets MUST be supported:
	•	build_plan
	•	validate_plan
	•	build_plan_and_validate

Targets map to Luigi “final tasks”.

8.2 Standard phases

Phases MUST be enumerable and stable (for UI progress bars).

Recommended phases:
	•	initializing
	•	generating_plan
	•	validating
	•	exporting
	•	finalizing

⸻

9. Incrementality & Invalidation Semantics

9.1 Baseline behavior

Luigi determines up-to-date tasks by output presence. In MCP:
	•	artifact writes by users must be treated as potential invalidations.

9.2 Artifact hashing

The server MUST compute and store sha256 for each artifact.

9.3 Required invalidation behavior

When artifact.write modifies an artifact:
	•	server MUST emit artifact_updated
	•	server SHOULD mark dependent tasks stale on next resume
	•	dependence mapping may be:
	•	explicit (preferred) via metadata files, or
	•	implicit (coarse) invalidation of all tasks downstream of a phase boundary

Minimum acceptable v1 approach:
	•	if user edits any “key artifact” (e.g. plan.md), server invalidates the validation phase.

⸻

10. Concurrency & Locking

10.1 Single active run per session

In v1, sessions MUST enforce:
	•	at most one run in running state.

10.2 Artifact writes during execution

Two allowed policies:
	•	Strict (recommended): reject writes while run is running (RUNNING_READONLY)
	•	Loose: allow writes but mark run inconsistent; enforce resume required

Recommended v1:
	•	Reject artifact writes while run is running
	•	UI flow stays: Stop → Edit → Resume

10.3 Optimistic locking

artifact.write must support expected_sha256 to prevent lost updates.

⸻

11. Error Model

Errors MUST return:
	•	code: stable machine-readable
	•	message: human-readable
	•	details: optional

Example:

{
  "error": {
    "code": "RUN_ALREADY_ACTIVE",
    "message": "A run is currently active for this session.",
    "details": { "run_id": "run_0001" }
  }
}

11.1 Required error codes
	•	SESSION_NOT_FOUND
	•	RUN_NOT_FOUND
	•	RUN_ALREADY_ACTIVE
	•	RUN_NOT_ACTIVE
	•	INVALID_TARGET
	•	INVALID_ARTIFACT_URI
	•	CONFLICT
	•	PERMISSION_DENIED
	•	RUNNING_READONLY
	•	INTERNAL_ERROR

⸻

12. Security & Isolation

12.1 Sandbox constraints
	•	All artifacts must live under session-scoped storage.
	•	Artifact URIs must not permit path traversal.

12.2 Access control

At minimum:
	•	session must be scoped to a user identity (metadata.user_id)
	•	callers without permission must receive PERMISSION_DENIED

12.3 Sensitive data handling
	•	logs may include model prompts/responses → treat logs as sensitive artifacts
	•	allow a config option to redact prompt content in event streaming

⸻

13. Performance Requirements

13.1 Responsiveness
	•	session.status must return within < 250ms under normal load.
	•	artifact.list must return within < 500ms for up to 5,000 artifacts.

13.2 Event throughput
	•	session.events should support 1–5 events/sec typical
	•	must tolerate log bursts without breaking clients (batching allowed)

13.3 Large artifacts
	•	artifact.read SHOULD support range reads
	•	server SHOULD impose max read size per call (e.g., 2–10MB)

⸻

14. Observability Requirements

The server MUST persist:
	•	run lifecycle events
	•	stop reasons
	•	failure tracebacks as artifacts (e.g., run_error.json)
	•	luigi execution logs (run.log)

⸻

15. Reference UI Integration Contract

To match your UI behavior:

Progress bars

Use:
	•	session.status.progress.overall
	•	session.status.phase
	•	or progress_updated events

Output directory viewer

Use:
	•	artifact.list every 1–2s (or subscribe to artifact events)

Stop/Edit/Resume
	1.	session.stop
	2.	artifact.read
	3.	artifact.write
	4.	session.resume

⸻

16. Compatibility & Versioning

16.1 Versioning strategy
	•	MCP server exposes: planexe.version = "1.0"
	•	breaking changes require major bump

16.2 Forward compatibility

Clients must ignore unknown fields and unknown event types.

⸻

17. Testing Strategy

17.1 Contract tests (required)
	•	Start/stop/resume loops
	•	Artifact read/write + sha256 locking
	•	Invalid transition errors
	•	Event cursor monotonicity

17.2 Determinism tests (recommended)
	•	Given same inputs + same edits, ensure same downstream artifacts unless models are stochastic
	•	If models are stochastic, test pipeline correctness, not identical bytes

17.3 Load tests (recommended)
	•	multiple sessions concurrently, one run each
	•	event streaming stability under heavy log output

⸻

Appendix A — Example End-to-End Flow

Create session

planexe.session.create({ "idea": "...", "config": {...} })

Start run

planexe.session.start({ "session_id": "pxe_...", "target": "build_plan_and_validate" })

Poll status

planexe.session.status({ "session_id": "pxe_..." })

Stop

planexe.session.stop({ "session_id": "pxe_...", "run_id": "run_0001", "mode": "graceful" })

Edit

planexe.artifact.read({ "artifact_uri": "planexe://.../plan.md" })
planexe.artifact.write({ "artifact_uri": "planexe://.../plan.md", "content": "...", "lock": {"expected_sha256":"..."} })

Resume

planexe.session.resume({ "session_id": "pxe_...", "target": "build_plan_and_validate" })


⸻

Appendix B — Recommended Artifact Kinds

kind	examples
plan	plan.md, plan.json
audit_report	validation_report.html
log	run.log
state	luigi_state.json
intermediate	prompt expansions, extracted assumptions


⸻

Appendix C — Optional v1.1 Extensions

If you want richer Luigi integration later:
	•	planexe.task.graph (nodes + edges + states)
	•	planexe.task.invalidate (rerun subtree)
	•	planexe.export.bundle (zip all artifacts)
	•	planexe.validate.only (audit without regeneration)
	•	planexe.session.archive (freeze session)
