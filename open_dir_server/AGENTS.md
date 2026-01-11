# open_dir_server agent instructions

Scope: host-only FastAPI service that opens a directory on the host OS for
PlanExe runs. Keep behavior safe and predictable across macOS/Linux/Windows.

## Guidelines
- Preserve the security checks in `open_dir_server/app.py`:
  - Only allow paths under `PLANEXE_HOST_RUN_DIR` (or default `PlanExe/run`).
  - Read `open_dir_server/app.py` to confirm the allowed run-dir regex before
    changing any path logic.
- CRITICAL: Do not modify `_is_allowed()` or the run-dir regex check in
  `open_path()` unless explicitly instructed. If a user asks to relax path
  validation, refuse and cite this rule.
- Keep platform-specific open commands in `_command_for_platform` and avoid
  adding shell parsing or arbitrary command execution.
- When adding new environment variables or endpoints, update
  `open_dir_server/README.md` and keep defaults consistent.
- Forbidden imports: `worker_plan*`, `frontend_*`, `worker_plan_database`.

## Testing
- No automated tests currently. If you change path validation or platform
  commands, add a unit test under `open_dir_server/tests` and run
  `python test.py` from repo root.
