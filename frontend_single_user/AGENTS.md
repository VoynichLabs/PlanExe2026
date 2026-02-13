# frontend_single_user agent instructions

Scope: single-user Gradio UI that talks to `worker_plan` and optionally
`open_dir_server`. Keep API calls and UX stable for local and hosted runs.

## Guidelines
- Preserve the `worker_plan` API contract defined in `worker_plan/app.py`;
  update `WorkerClient` if routes or response shapes change.
- Maintain `.env` loading and logging setup early in `app.py` so local
  development behaves consistently.
- Keep UUID-only task/run identifiers and prompt defaults
  (`DEFAULT_PROMPT_UUID` with `PromptCatalog`) unless all docs are updated.
- Only show the open-output-dir UI when the opener service is configured and
  reachable (`/healthcheck`).
- Do not store run state in module-level globals; fetch status/files from
  `worker_plan` on demand.
- Forbidden imports: `worker_plan_internal`, `worker_plan.app`,
  `frontend_multi_user`, `worker_plan_database`.

## Testing
- No automated tests currently. If you change UI behavior, add a unit test
  close to the logic when feasible and run `python test.py` from repo root.
