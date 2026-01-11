# frontend_multi_user agent instructions

Scope: Flask-based multi-user UI with Postgres backing, admin UI, and queue
logic. Talks to `worker_plan` for execution and uses shared `database_api`
models. Keep interfaces stable across services.

## Guidelines
- Preserve the `worker_plan` API contract used by the UI (run start/status,
  file listing/zip download, stop, and `/llm-info`).
- Keep Postgres wiring and env defaults stable:
  `PLANEXE_FRONTEND_MULTIUSER_DB_*` with fallbacks to `PLANEXE_POSTGRES_*`,
  and `SQLALCHEMY_DATABASE_URI` override.
- Maintain required admin auth (`PLANEXE_FRONTEND_MULTIUSER_ADMIN_USERNAME`
  / `PLANEXE_FRONTEND_MULTIUSER_ADMIN_PASSWORD`) and Flask login flow.
- Continue using `database_api.planexe_db_singleton.db`; do not create new
  SQLAlchemy engines or sessions here.
- Keep `.env` loading via `PlanExeDotEnv` and `update_os_environ()` early so
  local/debug behavior is consistent.
- If schema usage changes (e.g., new TaskItem columns), update the
  `_ensure_taskitem_artifact_columns()` helper and keep changes backward
  compatible.
- Do not store run state in module-level globals; fetch state from Postgres or
  `worker_plan` per request.
- Forbidden imports: `worker_plan_internal`, `worker_plan.app`,
  `frontend_single_user`, `open_dir_server`.

## Testing
- Local (repo root): `PYTHONPATH=$PWD/worker_plan python frontend_multi_user/src/app.py`
- Smoke checks:
```bash
PORT=${PLANEXE_FRONTEND_MULTIUSER_PORT:-5000}
curl http://localhost:${PORT}/healthcheck
curl -I http://localhost:${PORT}/login
```
