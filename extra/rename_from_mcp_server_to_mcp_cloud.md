# Rename Checklist: mcp_server → mcp_cloud

This checklist scopes a repo-wide rename from `mcp_server` to `mcp_cloud`, while keeping `mcp_local` as the local runner.

## 1) Decide on Compatibility Strategy

- [ ] Choose whether to keep `mcp_server` as a compatibility alias (recommended).
- [ ] Decide on a deprecation window and messaging (e.g., warn for 1–2 releases).

## 2) Directory and Module Renames

- [ ] Rename folder: `mcp_server/` → `mcp_cloud/`.
- [ ] Update import paths across the repo (`mcp_server.*` → `mcp_cloud.*`).
- [ ] Update package metadata or module paths if any tooling relies on the old path.
- [ ] If keeping compatibility, add a thin `mcp_server/` shim that re-exports from `mcp_cloud/`.

## 3) Environment and Configuration

- [ ] Review env vars in `.env.docker-example`, `.env.developer-example`, and
      `worker_plan/worker_plan_api/planexe_dotenv.py` for names referencing `MCP_SERVER`.
- [ ] Decide whether to keep `PLANEXE_MCP_*` as-is (likely) or add `*_CLOUD_*` variants.
- [ ] If new env keys are added, document them in the canonical env files and preserve old keys.

## 4) Documentation Updates

- [ ] Update repo-level `AGENTS.md` (`mcp_server` → `mcp_cloud` description).
- [ ] Update `mcp_server/README.md` to `mcp_cloud/README.md` and revise wording.
- [ ] Update `mcp_local/README.md` references.
- [ ] Update `extra/mcp.md` and `extra/planexe_mcp_interface.md` if they mention `mcp_server`.
- [ ] Update any Docker docs (`docker-compose.md`, `extra/docker.md`) if names appear.

## 5) Docker & Deployment

- [ ] Update `docker-compose.yml` service names (if `mcp_server` is a service).
- [ ] Update any deployment scripts or cloud configs referencing `mcp_server`.
- [ ] Confirm the HTTP base URL and health checks still point to the correct service.

## 6) Tests and Local Validation

- [ ] Run `python test.py` from repo root (or targeted tests if available).
- [ ] Start `mcp_cloud` (cloud or local) and confirm `mcp_local` can call it.
- [ ] Verify `mcp_local` can download artifacts via `task_download`.

## 7) Compatibility and Deprecation

- [ ] If keeping an alias, log a warning when `mcp_server` is used.
- [ ] Ensure old paths don’t break existing integrations during the transition.
- [ ] Update release notes / changelog if used.
