# Project knowledge

This file gives Codebuff context about your project: goals, commands, conventions, and gotchas.

## Quickstart
- **Docker (users):** Copy `.env.docker-example` to `.env`, set `OPENROUTER_API_KEY`, `docker compose up worker_plan frontend_single_user` (UI: localhost:7860).
- **Dev:** Multiple terminals/venvs per service (worker_plan Python 3.13 preferred); see `docs/install_developer.md`.
- **Test:** `python test.py` (unittest on all `test_*.py`).

## Architecture
- **Key directories:** 
  - `worker_plan/`: Core FastAPI pipeline API + `worker_plan_internal/` (planning logic).
  - `frontend_single_user/`: Gradio UI (local).
  - `frontend_multi_user/`: Flask multi-user UI + Postgres.
  - `worker_plan_database/`: DB-polling workers.
  - `mcp_cloud/`: MCP interface.
  - `database_api/`: Shared SQLAlchemy models.
- **Data flow:** UI -> worker_plan API -> `run_plan_pipeline` in `worker_plan_internal/plan/` -> LLM calls -> outputs in `./run/<id>/`.

## Conventions
- **Formatting/linting:** None repo-wide; mimic existing style (no black/mypy enforced).
- **Patterns:** Type hints on public funcs; FastAPI async, Flask sync; `logging` not `print`; `PLANEXE_*` env vars.
- **Things to avoid:** Cross-service imports; changing shared models/endpoints without compat; bare `except:`; Docker port conflicts (Postgres 5432).

## Gotchas
- Venvs per service (deps conflict); Python 3.13 for worker_plan wheels.
- `.env`/ `llm_config.json` in root for Docker.
- Outputs: `./run/` bind-mounted.
- Tests need worker_plan venv/PYTHONPATH.
