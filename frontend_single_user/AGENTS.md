# frontend_single_user agent instructions

Scope: single-user Gradio UI that talks to `worker_plan` and optionally
`open_dir_server`. Keep API calls and UX stable for local and hosted runs.

## Guidelines
- Preserve the `worker_plan` API contract used by `WorkerClient`:
  `/runs`, `/runs/{id}`, `/runs/{id}/files`, `/runs/{id}/zip`, `/runs/{id}/stop`,
  `/llm-info`, `/purge-runs`.
- Maintain `.env` loading and logging setup early in `app.py` so local
  development behaves consistently.
- Keep the run-id conventions (`RUN_ID_PREFIX`) and prompt defaults
  (`DEFAULT_PROMPT_UUID` with `PromptCatalog`) unless all docs are updated.
- Only show the open-output-dir UI when the opener service is configured and
  reachable (`/healthcheck`).
- Do not store run state in module-level globals; fetch status/files from
  `worker_plan` on demand.
- Forbidden imports: `worker_plan_internal`, `worker_plan.app`,
  `frontend_multi_user`, `worker_plan_database`.

## Testing
- Local (repo root): `PYTHONPATH=$PWD/worker_plan python frontend_single_user/app.py`
- Smoke check:
```bash
PORT=${PORT:-${PLANEXE_GRADIO_SERVER_PORT:-7860}}
curl -I http://localhost:${PORT}/
```
