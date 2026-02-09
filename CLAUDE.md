# CLAUDE.md
## Repo-Level Guidance

Read the package-level `AGENTS.md` files for service-specific rules (e.g., `worker_plan/AGENTS.md`, `frontend_single_user/AGENTS.md`).

The top-level `AGENTS.md` covers repo-wide safety and cross-service contracts.

The `knowledge.md` file provides a condensed reference for use by Codebuff (AI pair programming) and similar tools.


## Quick Reference

**Running tests:** `python test.py` (from repo root)

**Local development:** Each service has its own Python venv (worker_plan uses Python 3.13, frontend_single_user uses 3.11+). See `docs/install_developer.md` for setup.

**Docker development:** `docker compose up worker_plan frontend_single_user` (UI on localhost:7860, API on localhost:8000)

**Configuration:** Copy `.env.docker-example` to `.env` and set `OPENROUTER_API_KEY` (or configure your LLM provider per `docs/getting_started.md`)

## High-Level Architecture

PlanExe transforms a user idea into a 40-page strategic plan using LLMs. The architecture has three main deployment modes and several shared packages:

### Deployment Modes

1. **Single-user (local Docker):** `frontend_single_user` (Gradio UI) + `worker_plan` (FastAPI) + `.env` + outputs in `./run/`
2. **Multi-user (hosted):** `frontend_multi_user` (Flask) + Postgres + `worker_plan` + DB-polling workers (`worker_plan_database`)
3. **MCP server:** `mcp_cloud` (MCP stdio interface) wrapped with HTTP server for remote access

### Core Components

- **`worker_plan/`** - FastAPI service that exposes HTTP endpoints for plan generation. Spawns a subprocess pipeline that runs `worker_plan_internal.plan.run_plan_pipeline()`.

- **`worker_plan_internal/`** - Core planning logic (lives in `worker_plan/` directory). Orchestrates 15+ stages: prompts → LLM calls → Gantt charts, governance, risk registers, SWOT, etc. Uses Luigi for task orchestration. Outputs HTML reports and JSON/markdown artifacts.

- **`worker_plan_api/`** - Shared lightweight types (`filenames.py`, `generate_run_id.py`, LLM config helpers). Used by both worker and frontends. Must remain lightweight and must never import service apps.

- **`frontend_single_user/`** - Gradio UI (Python) for single-user local mode. Calls `worker_plan` API synchronously.

- **`frontend_multi_user/`** - Flask multi-user UI with admin views. Backed by Postgres for task persistence, user auth, event logging. Calls `worker_plan` API or polls Postgres for results.

- **`worker_plan_database/`** - Long-lived poller that reads `TaskItem` rows from Postgres, marks them processing, spawns pipeline, writes results back to DB. Run multiple instances (1, 2, 3) in parallel for concurrency.

- **`database_api/`** - Shared SQLAlchemy models (`TaskItem`, `Event`, `Worker`, `Nonce`). Imported by `frontend_multi_user` and `worker_plan_database`. Must remain backward compatible (nullable defaults for new columns).

- **`mcp_cloud/`** - MCP stdio server (follows MCP spec) wrapping PlanExe logic. Also includes HTTP wrapper for non-stdio clients. Bridges MCP tool calls to Postgres DB and worker_plan.

- **`mcp_local/`** - Local proxy scripts that forward tool calls to `mcp_cloud` and download artifacts. Used for local development and testing.

- **`open_dir_server/`** - Security-critical HTTP service that safely opens output directories on the host. Whitelists paths to prevent directory traversal.

### Data Flow

```
UI (Gradio or Flask)
  ↓ (HTTP POST /run)
worker_plan (FastAPI)
  ↓ (spawns subprocess)
worker_plan_internal.plan.run_plan_pipeline()
  ├─ Prompt catalog lookup
  ├─ LLM calls (15+ sequential stages via Luigi)
  ├─ Artifact generation (Gantt, risk register, HTML report, etc.)
  └─ Output written to ./run/<run_id>/
  ↓ (HTTP response)
UI displays progress/results or DB records event
```

## Key Technical Patterns

### Run Directory Structure

- Timestamped (single-user) or UUID (multi-user) directories under `./run/` or `PLANEXE_RUN_DIR`
- Each run contains: `log.txt`, `progress.json`, partial/final artifacts
- Configuration in `worker_plan/worker_plan_api/generate_run_id.py`
- Host path hinting via `PLANEXE_HOST_RUN_DIR` for Docker mounts

### Pipeline Stages (worker_plan_internal/)

1. **Prompt catalog** (`prompt/`) - Stores system prompts, prompt templates, and example outputs
2. **Expert agents** (`expert/`) - LLM calls to gather info, validate assumptions
3. **Chunking & context** (`chunk_dataframe_with_context/`) - Organize data for downstream stages
4. **Scheduling** (`schedule/`) - Generate Gantt charts
5. **Governance** - Define roles, stakeholder maps, decision trees
6. **Risk analysis** - Risk registers, mitigation strategies
7. **SWOT analysis** - Strengths, weaknesses, opportunities, threats
8. **Document assembly** (`document/`, `report/`) - HTML + Markdown output
9. **Assumptions review** (`assume/`) - Validate and condense assumptions
10. **Fiction planning** (`fiction/`) - Generate narrative scenarios

Each stage is a Luigi task with inputs/outputs. Stages are independent where possible; dependencies are explicit in task definitions.

### LLM Configuration

- Canonical env keys live in `.env.docker-example`, `.env.developer-example`, and `worker_plan/worker_plan_api/planexe_dotenv.py`
- **Do not add real API keys to these files**
- `llm_config.json` in repo root defines model profiles (cloud providers, local Ollama, LM Studio)
- `worker_plan_api/llm_info.py` reads and validates config at startup

### Shared Contracts (Breaking Changes Require Migration)

- **HTTP endpoints** in `worker_plan/app.py` must remain backward compatible
- **SQLAlchemy models** in `database_api/` must use nullable defaults for new columns
- **Prompt catalog UUIDs** in `worker_plan/worker_plan_api/prompt/data/*.jsonl` are used as defaults and should be stable
- **Run ID format** changes require coordination across frontends and workers

## Development Setup

### Local (venv-based)

Worker_plan requires Python 3.13 (native wheels for pydantic-core, orjson, tiktoken, greenlet, jiter not yet available for 3.14):

```bash
cd worker_plan
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
export PYTHONPATH=$PWD/..:$PYTHONPATH
python -m worker_plan.app
```

Frontend_single_user works with Python 3.11+. Each service is isolated in its own venv to avoid dependency conflicts.

### Docker (compose-based)

Services use Docker volumes to share `.env`, `llm_config.json`, and the `./run` output directory:

```bash
docker compose up worker_plan frontend_single_user
```

Watching code changes (live reload):
```bash
# Edit code and save; changes to worker_plan/ and frontend_single_user/ sync automatically via develop.watch
```

Rebuilding (after dependency or big code moves):
```bash
docker compose build --no-cache worker_plan frontend_single_user
```

## Running Tests

```bash
python test.py
```

The test runner re-executes itself with the `worker_plan` venv if needed, ensures `PYTHONPATH` includes `worker_plan`, then discovers all `test_*.py` files repo-wide using unittest.

**To run a single test file:**
```bash
cd worker_plan
.venv/bin/python -m unittest worker_plan_api.tests.test_generate_run_id
```

Tests are in `test_*.py` files scattered throughout the codebase (e.g., `worker_plan/worker_plan_api/tests/`, `database_api/tests/`).

## Environment Variables

Key variables for local development (read from `.env` in repo root):

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | *(none)* | API key for OpenRouter cloud LLM provider |
| `PLANEXE_CONFIG_PATH` | `.` | Path to find `.env` and `llm_config.json` |
| `PLANEXE_RUN_DIR` | `run` | Local directory for plan outputs |
| `PLANEXE_HOST_RUN_DIR` | *(unset)* | Host path hint for Docker mounts (display only) |
| `PLANEXE_WORKER_PLAN_URL` | `http://localhost:8000` | Frontend's URL for the worker API |
| `PLANEXE_WORKER_HOST` | `0.0.0.0` | Worker bind address (venv only) |
| `PLANEXE_WORKER_PORT` | `8000` | Worker listen port |
| `PLANEXE_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

For Postgres (multi-user mode):

| Variable | Default | Purpose |
| --- | --- | --- |
| `PLANEXE_POSTGRES_HOST` | `database_postgres` | Database host |
| `PLANEXE_POSTGRES_PORT` | `5432` | Database port (container-internal) |
| `PLANEXE_POSTGRES_USER` | `planexe` | Database user |
| `PLANEXE_POSTGRES_PASSWORD` | `planexe` | Database password |
| `PLANEXE_POSTGRES_DB` | `planexe` | Database name |

## Architecture Constraints & Hard Rules

1. **Service isolation:** `worker_plan_api`, `database_api`, and shared packages must never import from service apps (`frontend_*`, `worker_plan_database`, `worker_plan.app`). Move shared logic into packages instead.

2. **Backward compatibility:** Keep `worker_plan` HTTP endpoints and response shapes stable. New DB columns must have nullable defaults.

3. **Python versions:** Worker_plan strictly requires Python 3.13; frontends and database services accept 3.11+. Wheels don't build on 3.14 yet.

4. **Port conflicts:** Default Postgres port 5432 may conflict with local Postgres. Use `PLANEXE_POSTGRES_PORT` to remap (only affects host mapping; containers always use 5432 internally).

5. **Security:** Do not add real API keys to `.env.*` or `llm_config.json`. The `open_dir_server` has strict path validation—never relax it without explicit review.

6. **Cross-service imports:** `worker_plan` service app must not be imported by `database_api` or frontends. If a service needs shared logic, create/extend a helper in `worker_plan_api/` instead.

## Dependency Management

- **worker_plan, frontend_multi_user:** Add deps in `pyproject.toml`
- **frontend_single_user, worker_plan_database:** Add deps in `requirements.txt`
- Do not `pip install` ad-hoc without recording in the package manifest

## Coding Standards

- **Type hints:** All public function signatures must have type hints
- **Async/sync:** FastAPI code can be async; Flask routes must be sync
- **Error handling:** No bare `except:`; always log stack traces
- **Logging:** Use `logging` module, not `print()` in service code
- **Style:** No repo-wide formatter configured; follow the existing file's style (consistency within-file is more important than uniformity across-repo)

## Documentation Sync

When making changes, keep these docs in sync:

- Changing Docker services, env defaults, or port mappings → update `docker-compose.yml`, `docker-compose.md`, `docs/docker.md` together
- Changing single-user quickstart or LLM setup → update `docs/getting_started.md`
- Changing local dev startup steps or test commands → update `docs/install_developer.md`
- README uses absolute `https://docs.planexe.org/...` URLs for GitHub readers

