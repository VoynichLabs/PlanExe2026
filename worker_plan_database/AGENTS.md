# worker_plan_database agent instructions

Scope: database-backed worker that polls Postgres `TaskItem` rows, runs the
PlanExe pipeline, and updates task state/progress.

## Guidelines
- Keep database access wired through `database_api.planexe_db_singleton.db`;
  do not create new engine/session instances here.
- Preserve the startup sequence in `worker_plan_database/app.py`:
  `.env` loading, logging setup, Flask app config, then `db.init_app(app)`.
- Maintain the DB connection logic:
  - Prefer `SQLALCHEMY_DATABASE_URI` when set.
  - Otherwise build from `PLANEXE_POSTGRES_*` (see root `AGENTS.md` for keys).
- Keep worker identity and required env checks intact (`PLANEXE_WORKER_ID`,
  `PLANEXE_IFRAME_GENERATOR_CONFIRMATION_*`).
- When changing schema usage, add columns in a backward-compatible way and
  ensure `ensure_taskitem_artifact_columns()` or related helpers are updated.
- Forbidden imports: `worker_plan.app`, `frontend_*`, `open_dir_server`.

## Testing
- No automated tests currently. If you change worker behavior, add a unit test
  close to the logic when feasible and run `python test.py` from repo root.
