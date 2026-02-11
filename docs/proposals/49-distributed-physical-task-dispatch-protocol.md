---
title: Distributed Physical Task Dispatch Protocol
date: 2026-02-11
status: proposal
author: PlanExe Team
---

# Distributed Physical Task Dispatch Protocol

**Author:** PlanExe Team  
**Date:** 2026-02-11  
**Status:** Proposal  
**Audience:** IoT Architects, Robotics Engineers  

---

## Overview
This proposal defines a secure protocol for dispatching **Physical Tasks** from the PlanExe Cloud (Brain) to edge-based autonomous agents (Body), such as Raspberry Pi-powered OpenClaw instances.

It solves the "Cloud-Edge Gap": Cloud LLMs can plan complex actions, but they cannot execute them (they don't have hands). Edge devices have hands (servos, switches) but lack the planning capability.

## Core Problem
A PlanExe Gantt chart might say: "Task 4: Water the plants at 08:00 AM."
How does that text string turn into a GPIO signal on the Edge Agent's Raspberry Pi?

## Proposed Solution
A **Pub/Sub Dispatch System** using MQTT/WebSockets.

1.  **PlanExe Cloud** publishes a `TaskManifest` to a secure queue.
2.  **Edge Agents** (authenticated via client certs) subscribe to their specific `device_id` channel.
3.  **The Agent** executes the task locally (e.g., Python script).
4.  **The Agent** uploads proof of work (Photo/Log) back to the Cloud.

## Architecture

### 1. The Dispatcher (Cloud)
Parses the Gantt chart. Identifying tasks tagged with `@physical`.
*   *Task:* "Take a photo of the construction site."
*   *Target:* `device:drone-01`
*   *Deadline:* `2026-02-12T09:00:00Z`

### 2. The Protocol (JSON Payload)

```json
{
  "task_id": "task_888",
  "command": "capture_image",
  "parameters": {
    "resolution": "1080p",
    "angle": "45_degrees",
    "target": "zone_a"
  },
  "auth_token": "jwt_ey..."
}
```

### 3. The Executor (Edge / OpenClaw)
The Edge Agent receives the message.
1.  Verifies the `auth_token`.
2.  Maps `capture_image` to a local function `cam.capture()`.
3.  Runs the hardware logic.
4.  Returns: `{"status": "success", "artifact_url": "s3://..."}`

---

## Proof of Physical Work (PoPW)
To prevent agents from lying ("I watered the plants" when they didn't), we require cryptographic proof.
*   **Photo Verification:** Agent must upload a timestamped photo of the result.
*   **Sensor Logs:** Agent must upload the moisture sensor data showing the spike in humidity.
*   **GPS Tweak:** Agent must sign the log with its GPS coordinates.

## Integration with MoltBook
*   **Gig Economy:** A user can post a physical task on MoltBook ("I need someone to 3D print this part").
*   **Dispatch:** PlanExe routes the job to a local agent with a 3D printer (e.g., Agent B).
*   **Verification:** Agent B prints it, PlanExe verifies the photo, and payment is released.

## Success Metrics
*   **Latency:** Time from Cloud Dispatch -> Edge Acknowledgment (< 500ms).
*   **Reliability:** % of physical tasks successfully completed and verified.
