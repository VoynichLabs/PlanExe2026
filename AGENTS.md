# PlanExe agent instructions

Scope: repo-level guardrails for PlanExe services and shared packages.
Always check the package-level AGENTS listed below for file-specific rules.

## Local agent files
- `database_api/AGENTS.md`
- `worker_plan/AGENTS.md`
- `worker_plan_database/AGENTS.md`
- `frontend_single_user/AGENTS.md`
- `frontend_multi_user/AGENTS.md`
- `open_dir_server/AGENTS.md`

## Repo map (high-level)
- `worker_plan`
- `frontend_single_user`
- `frontend_multi_user`
- `worker_plan_database`
- `database_api`
- `open_dir_server`
- `database_postgres`
Keep this list in sync when top-level directories are added/removed.

## Shared contracts
- Keep `worker_plan` HTTP endpoints and response shapes backward compatible.
- Preserve shared SQLAlchemy models in `database_api` (nullable defaults for new columns).
- Run directory naming:
  - Single-user default: `PlanExe_YYYYMMDD_HHMMSS` (regex `^PlanExe_\\d+_\\d+$`).
  - Multi-user or forced UUID: `run_id` is a UUID (used to avoid collisions).
- Keep prompt catalog UUIDs stable when used as defaults; they live in
  `worker_plan/worker_plan_api/prompt/data/*.jsonl`.

## Hard rules (agent safety)
- Do not add real API keys or passwords to `.env`, `.env.*`, or `llm_config.json`.
- Do not change run-dir validation or path-allowlist logic in `open_dir_server/app.py`
  unless explicitly instructed.
- Shared packages (`database_api`, `worker_plan_api`) must not import service apps
  (`frontend_*`, `worker_plan_database`, `open_dir_server`, `worker_plan.app`).

## Common env keys
- `PLANEXE_CONFIG_PATH`, `PLANEXE_RUN_DIR`, `PLANEXE_HOST_RUN_DIR`
- `PLANEXE_WORKER_PLAN_URL`, `PLANEXE_WORKER_PLAN_TIMEOUT`
- `PLANEXE_POSTGRES_HOST|PORT|DB|USER|PASSWORD`, `SQLALCHEMY_DATABASE_URI`
- `PLANEXE_FRONTEND_MULTIUSER_DB_*`, `PLANEXE_FRONTEND_MULTIUSER_ADMIN_*`
- `PLANEXE_OPEN_DIR_SERVER_URL`, `PLANEXE_PASSWORD`, `OPENROUTER_API_KEY`

## Cross-service conventions
- `.env` and `llm_config.json` are expected in the repo root for Docker setups.
- Use `PLANEXE_*` env vars; prefer existing defaults when adding new ones.
- Do not assume ports; read `docker-compose.yml` or the service env defaults
  (`PLANEXE_*_PORT`) before running curl checks.

## Docker notes
- `PLANEXE_POSTGRES_PORT` changes the host port mapping only; containers still
  connect to Postgres on 5432.
- The `Open Output Dir` button requires the host `open_dir_server` and
  `PLANEXE_OPEN_DIR_SERVER_URL` (OS-specific URLs live in `extra/docker.md`).
- Keep `PLANEXE_HOST_RUN_DIR` consistent with run dir mounts so outputs land in
  the expected host folder.

## Documentation sync
- When changing Docker services, env defaults, or port mappings, update
  `docker-compose.yml`, `docker-compose.md`, and `extra/docker.md` together.
- When changing single-user quickstart or LLM env requirements (e.g.
  `OPENROUTER_API_KEY`), update `extra/getting_started.md`.
- When changing local dev startup steps or the test command, update
  `extra/install_developer.md`.

## Testing
- Repo tests: `python test.py` (117 tests).
- Service-specific checks live in each package `AGENTS.md`.

## Coding standards
- Type hints: add to all public function signatures.
- Async/sync: FastAPI code can be `async`; Flask routes must stay sync.
- Error handling: do not use bare `except:`; log stack traces.
- Logging: use `logging` (avoid `print()` in service code).
