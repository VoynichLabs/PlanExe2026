# worker_plan agent instructions

Scope: FastAPI worker service and shared `worker_plan_internal`/`worker_plan_api`
packages used by frontends and database workers. Keep interfaces stable across
consumers.

## Guidelines
- Preserve the public API contract in `worker_plan/app.py`:
  - Keep request/response shapes and endpoint paths backward compatible.
  - Avoid renaming response fields like `run_id`, `run_dir`, `display_run_dir`.
- Maintain the run directory conventions (`PlanExe_...`) and environment-driven
  paths (`PLANEXE_RUN_DIR`, `PLANEXE_HOST_RUN_DIR`, `PLANEXE_CONFIG_PATH`).
- When changing pipeline behavior, keep the subprocess invocation in
  `start_pipeline_subprocess` consistent with `worker_plan_internal`.
- Keep `PlanExeDotEnv.load().update_os_environ()` early so `.env` overrides work.
- CRITICAL: `worker_plan_api` must stay lightweight. Allowed imports are
  stdlib, `typing`, `dataclasses`, `enum`, and `pydantic`. Do not import
  `llama_index`, `fastapi`, `httpx`, `numpy`, `pandas`, or `torch` there.
- Keep planning logic in `worker_plan_internal` (pipeline stages:
  prompt parsing -> LLM planning -> file/report output).
- If new environment variables or endpoints are added, update
  `worker_plan/README.md` and any Railway docs.

## Testing
- Local (repo root): `PYTHONPATH=$PWD/worker_plan python -m worker_plan.app`
- CLI smoke checks (replace `<MODEL_ID>` with a value from `/llm-info`):
```bash
PORT=${PLANEXE_WORKER_PORT:-8000}
curl http://localhost:${PORT}/healthcheck
curl http://localhost:${PORT}/llm-info
curl -X POST http://localhost:${PORT}/runs \\
  -H 'Content-Type: application/json' \\
  -d '{"submit_or_retry":"submit","plan_prompt":"Hello","llm_model":"<MODEL_ID>","speed_vs_detail":"all_details_but_slow"}'
```
