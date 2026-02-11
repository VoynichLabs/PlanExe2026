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

## Overview
This proposal defines **PlanExe** as a standardized "Skill" that can be legally installed into an [OpenClaw](https://github.com/Starttoaster/OpenClaw) agent. 

Rather than just exposing raw API endpoints, this Skill provides a high-level cognitive interface that transforms an OpenClaw instance from a "Task Doer" (running shell commands) into a "Project Manager" (orchestrating complex workflows).

## Core Problem
Autonomous agents like OpenClaw differ in capability. "EdgeBot" runs on a Raspberry Pi (low compute, high sensor access). "CloudBot" runs on a server (high compute).
Currently, EdgeBot cannot plan because it lacks the LLM horsepower. CloudBot can plan but lacks the sensors. They are disconnected functionalities.

## Proposed Solution
Package PlanExe as a **Skill** ($PlanExeSkill) that abstracts the complexity of the cloud pipeline.

When installed, the agent gains the ability to:
1.  **Draft Plans:** Outsouring the heavy "thinking" to the PlanExe Cloud.
2.  **Verify Feasibility:** Asking PlanExe to run Monte Carlo sims on its ideas.
3.  **Breakdown Tasks:** Converting a vague goal ("Grow Tomatoes") into concrete cron jobs.

## Architecture

### 1. The Skill Manifest (`skill.json`)
Standard OpenClaw skill definition.

```json
{
  "name": "PlanExe Project Manager",
  "version": "1.0.0",
  "description": "Gives the agent the ability to plan, budget, and track complex projects via the PlanExe Cloud.",
  "permissions": ["network_access"],
  "tools": [
    "create_plan",
    "check_plan_status",
    "get_next_action_item"
  ]
}
```

### 2. The Bridge (MCP Client)
The skill acts as an MCP Client. It does *not* run the models locally. It proxies requests to `mcp.planexe.org` (or a local Docker container).

### 3. The "Director" Persona
The skill injects a new system prompt into the Agent:
> "You have access to PlanExe. When asked to do something complex, do not try to do it all at once. First, generate a Plan. Then, execute the Plan step-by-step."

---

## Skill Capabilities (Tools)

### `create_plan(goal: str, constraints: list)`
Triggers the full pipeline.
*   **Input:** "Build a hydroponic tower."
*   **Process:** Agent waits (async) for PlanExe to generate the PDF/JSON.
*   **Output:** A `plan_id` and a summary of the approach.

### `get_next_action_item(plan_id: str)`
The "Next Step" engine.
*   **Input:** Plan ID.
*   **Output:** A specific, atomic task for the agent to perform *right now*.
    *   *Example:* "Run `sudo apt-get install python3-gpiozero` on the Pi."

### `report_result(plan_id: str, task_id: str, output: str)`
Closing the loop.
*   **Input:** "Task installed successfully."
*   **Impact:** PlanExe updates the Gantt chart and checks for assumption drift.

---

## Agent-to-Agent Protocol
If "CloudBot" (Server) has the `PlanExe:Generator` skill and "EdgeBot" (Pi) has the `PlanExe:Executor` skill:

1.  **EdgeBot** detects a problem (Low water level).
2.  **EdgeBot** pings **CloudBot**: "I need a plan to fix the irrigation."
3.  **CloudBot** generates the plan (using Cloud LLMs) and sends the `plan_id` to EdgeBot.
4.  **EdgeBot** mounts the plan and executes the steps (ordering a new pump, turning on backup valve).

## Success Metrics
*   **Installation Rate:** % of OpenClaw instances with PlanExe installed.
*   **Plan Completion:** % of AI-generated plans that are successfully executed by the agent without human intervention.
