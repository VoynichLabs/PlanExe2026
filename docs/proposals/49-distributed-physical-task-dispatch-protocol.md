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

## Pitch
Define a secure protocol for dispatching physical tasks from the PlanExe Cloud to edge agents and verifying real-world execution.

## Why
Cloud planning is only valuable if it can reliably trigger real actions on devices. A standardized dispatch protocol closes the cloud-to-edge gap.

## Problem

- Gantt tasks are not executable by edge devices.
- No consistent task payload or authentication layer.
- Proof of physical execution is weak or absent.

## Proposed Solution
Implement a pub/sub dispatch protocol that:

1. Publishes `TaskManifest` payloads to secure device channels.
2. Authenticates edge agents with client certs.
3. Verifies task completion with proof-of-physical-work.

## Architecture

```text
PlanExe Cloud
  -> Dispatcher
  -> MQTT/WebSocket Bus
  -> Edge Agent
  -> Proof Upload
  -> Verification
```

## Task Manifest Schema

```json
{
  "task_id": "task_888",
  "command": "capture_image",
  "parameters": {
    "resolution": "1080p",
    "angle": "45_degrees",
    "target": "zone_a"
  },
  "deadline": "2026-02-12T09:00:00Z",
  "auth_token": "jwt_ey..."
}
```

## Proof of Physical Work (PoPW)

- Photo verification with timestamp
- Sensor logs (e.g., humidity spike)
- GPS signature for location-dependent tasks

## Integration Points

- Works with OpenClaw execution skill.
- Feeds into MoltBook gig dispatch.
- Used by assumption drift monitor for real-world signals.

## Success Metrics

- Dispatch latency (cloud -> edge ack).
- % tasks completed with valid PoPW.
- Reduction in false execution claims.

## Risks

- Device spoofing or token leakage.
- Network instability in remote sites.
- High verification cost for complex tasks.

## Future Enhancements

- Hardware attestation support.
- Offline task caching and delayed sync.
- Automated anomaly detection on PoPW.
