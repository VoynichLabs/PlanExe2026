# /plan Admin UI Telemetry Rollout (Phased, Small-PR Plan)

Date: 2026-02-17
Owner: Larry (VoynichLabs)
Target repo: PlanExeOrg/PlanExe (PRs from VoynichLabs/PlanExe2026)

## Goal
Make `home.planexe.org/plan` developer-technical-forward by surfacing operational telemetry and diagnostics directly in the UI, while keeping each change small and easy to review.

## Constraints (agreed)
- Small PRs only (no massive review bundles).
- Base every branch on latest `upstream/main`.
- No placeholder/fake telemetry values; only render fields that exist in persisted plan/run artifacts.
- Keep current user flow intact (this is visibility + diagnostics first).

## Data Discovery (Step 0, before PR1)
Identify where these fields currently live and document exact JSON paths:
- Provider + model actually used (including fallback/provider-switch evidence)
- Token usage: prompt/completion/total (and any cached token details)
- Cost: estimated/actual (if both exist), currency, granularity
- Timing: queue/start/end latency, generation duration
- Failure details: stage, error type, message, retry count, partial outputs

Deliverable:
- Add/update a short mapping note in docs (or PR description) with `field -> source path`.

---

## PR 1 — Usage + Cost panel (highest value)
Branch: `feature/plan-usage-cost-panel`

Scope:
- Add a technical "Usage & Cost" section on `/plan` detail view.
- Show token stats (prompt/completion/total), provider, model, and cost fields when available.
- Add "copy telemetry JSON" action for debugging.

Acceptance:
- Developer can inspect one plan and quickly answer: token count, provider/model, and cost.
- Missing fields degrade gracefully (show `N/A` or hidden row, no crashes).

Out of scope:
- Failure traces and retry waterfall (PR3).

---

## PR 2 — Prompt visibility/readability (technical)
Branch: `feature/plan-prompt-visibility`

Scope:
- Improve prompt readability for long prompts:
  - larger readable block
  - monospace toggle or preserved formatting
  - expand/collapse for very long text
  - copy prompt action

Acceptance:
- Dev can quickly audit full prompt content without raw file diving.

Out of scope:
- Styling overhauls.

---

## PR 3 — Failure Modes + Execution Trace
Branch: `feature/plan-failure-trace-panel`

Scope:
- Add diagnostics section:
  - stage failed
  - error class/message
  - retry count/backoff summary
  - duration/timing summary
  - fallback/provider-switch indicators
- If partial output exists, expose it safely (collapsed by default).

Acceptance:
- Dev can identify where/why a run failed without leaving `/plan`.

Out of scope:
- New backend retry logic.

---

## PR 4 — Safer delete flow + operator affordances
Branch: `feature/plan-safer-delete`

Scope:
- Improve destructive action UX:
  - clear danger styling
  - explicit confirmation text
  - prevent accidental click path
  - success/failure toast clarity

Acceptance:
- Reduced accidental deletion risk; clear operator confidence on result.

Out of scope:
- Undo stack (optional future).

---

## PR 5 — Dense technical polish (not consumer fluff)
Branch: `feature/plan-technical-polish`

Scope:
- Compact layout tuning for high-information density.
- Better labels/tooltips for technical fields.
- Align section ordering for incident triage flow:
  1) Status
  2) Usage/Cost
  3) Provider/Model
  4) Trace/Failures
  5) Prompt/Output

Acceptance:
- Faster scanability for power users / agent operators.

Out of scope:
- Full visual redesign.

---

## Implementation Notes
- Keep each PR to one concern.
- Include screenshots in each PR description (before/after).
- Include exact changed file list in PR update comments.
- Rebase each feature branch onto latest upstream before opening PR.

## Suggested Execution Order
1. PR1 Usage+Cost
2. PR2 Prompt visibility
3. PR3 Failure trace
4. PR4 Safer delete
5. PR5 Technical polish

## Ready-to-run Git Workflow (for any executor)
```bash
git fetch upstream --prune
git checkout main
git merge --ff-only upstream/main
git push origin main

# Example for PR1
git checkout -b feature/plan-usage-cost-panel upstream/main
# ...implement...
git add <files>
git commit -m "feat(plan): add usage and cost telemetry panel"
git push origin feature/plan-usage-cost-panel

# Open PR to upstream (not fork)
gh pr create \
  --repo PlanExeOrg/PlanExe \
  --base main \
  --head VoynichLabs:feature/plan-usage-cost-panel \
  --title "feat(plan): usage + cost telemetry panel" \
  --body "Small PR 1/5: expose token/provider/cost telemetry on /plan"
```
