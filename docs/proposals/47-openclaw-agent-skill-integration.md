---
title: OpenClaw Agent Skill Integration
date: 2026-02-11
status: proposal
author: PlanExe Team
---

# OpenClaw Agent Skill Integration

**Author:** PlanExe Team  
**Date:** 2026-02-11  
**Status:** Proposal  
**Audience:** OpenClaw Developers, Agent Architects

---

## Pitch
Package PlanExe as a standardized OpenClaw skill that turns agents into project managers: generate plans in the cloud, execute locally on edge devices, and report progress back into PlanExe.

## Why
Edge agents have sensors and actuators but low compute. Cloud agents can plan but lack physical access. A unified skill bridges this split and enables coordinated execution.

## Problem

- Edge agents lack LLM capacity to generate robust plans.
- Cloud agents cannot directly execute physical tasks.
- There is no consistent interface for plan generation and task execution.

## Proposed Solution
Create a $PlanExeSkill for OpenClaw that:

1. Drafts plans via PlanExe Cloud.
2. Breaks plans into executable tasks.
3. Routes tasks to edge or human executors.
4. Reports results and updates the plan state.

## Architecture

```text
OpenClaw Agent
  -> PlanExe Skill
     -> MCP Client
        -> PlanExe Cloud
           -> Plan JSON
     -> Task Executor
  -> Result Reporter
```

### Skill Manifest (`skill.json`)

```json
{
  "name": "PlanExe Project Manager",
  "version": "1.0.0",
  "description": "Gives the agent the ability to plan, budget, and track complex projects via the PlanExe Cloud.",
  "permissions": ["network_access"],
  "tools": [
    "create_plan",
    "check_plan_status",
    "get_next_action_item",
    "report_result"
  ]
}
```

## Skill Capabilities (Tools)

### `create_plan(goal: str, constraints: list)`

- Input: goal + constraints
- Output: `plan_id` + plan summary

### `get_next_action_item(plan_id: str)`

- Input: plan ID
- Output: atomic next task

### `report_result(plan_id: str, task_id: str, output: str)`

- Input: task output
- Output: plan updated, progress logged

## Agent-to-Agent Protocol

- **EdgeBot** detects a local issue (low water).
- **EdgeBot** requests a plan from **CloudBot**.
- **CloudBot** generates the plan and sends `plan_id`.
- **EdgeBot** executes local steps and reports back.

## Integration Points

- Uses PlanExe MCP interface for plan creation.
- Feeds execution data to assumption drift and readiness scoring.
- Works with distributed physical task dispatch protocol.

## Success Metrics

- Installation rate: % of OpenClaw instances with PlanExe skill.
- Plan completion rate without human intervention.
- Mean time from goal to first actionable task.

## Risks

- Over-reliance on cloud connectivity.
- Misaligned task interfaces between cloud and edge.
- Skill misuse without governance or budget limits.

## Future Enhancements

- Offline plan caching for intermittent connectivity.
- Capability-aware task routing across multiple agents.
- Automatic escalation to humans for high-risk tasks.
