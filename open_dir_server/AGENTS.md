# open_dir_server agent instructions

Scope: host-only FastAPI service that opens a directory on the host OS for
PlanExe runs. Keep behavior safe and predictable across macOS/Linux/Windows.

## Guidelines
- Preserve the security checks in `open_dir_server/app.py`:
  - Only allow paths under `PLANEXE_HOST_RUN_DIR` (or default `PlanExe/run`).
  - Keep the run-dir regex `^PlanExe_\\d+_\\d+$` unless all callers are updated.
- CRITICAL: Do not modify `_is_allowed()` or the run-dir regex check in
  `open_path()` unless explicitly instructed.
- Keep platform-specific open commands in `_command_for_platform` and avoid
  adding shell parsing or arbitrary command execution.
- When adding new environment variables or endpoints, update
  `open_dir_server/README.md` and keep defaults consistent.
- Forbidden imports: `worker_plan*`, `frontend_*`, `worker_plan_database`.

## Testing
- Local (repo root):
```bash
python open_dir_server/app.py
HOST=${PLANEXE_OPEN_DIR_SERVER_HOST:-127.0.0.1}
PORT=${PLANEXE_OPEN_DIR_SERVER_PORT:-5100}
curl http://${HOST}:${PORT}/healthcheck
mkdir -p "$PWD/run/PlanExe_20000101_000000"
curl -X POST http://${HOST}:${PORT}/open \\
  -H 'Content-Type: application/json' \\
  -d "{\"path\":\"$PWD/run/PlanExe_20000101_000000\"}"
```
