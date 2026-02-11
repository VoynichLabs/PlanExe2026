---
title: Agent-to-Agent Payment Gateway (AP2 + x402)
date: 2026-02-11
status: proposal
author: PlanExe Team
---

# Agent-to-Agent Payment Gateway (AP2 + x402)

**Author:** PlanExe Team  
**Date:** 2026-02-11  
**Status:** Proposal  
**Audience:** Financial Architects, OpenClaw Developers

---

## Pitch
Enable headless agents to pay for PlanExe services using standardized protocols for corporate spend and micropayments.

## Why
Agents operate without browsers or CAPTCHAs. Payments must be machine-native, auditable, and reliable at scale.

## Problem

- Headless agents cannot use standard checkout flows.
- Corporate payments require audit trails and limits.
- Micropayments must be instant and low-friction.

## Proposed Solution
Implement a dual-protocol payment gateway:

1. **AP2 (Agent Payments Protocol):** corporate spend with signed mandates.
2. **x402 (HTTP 402):** instant micropayments for per-request charging.

## Architecture 1: The Corporate Route (AP2)

### The Mandate
A human manager signs a digital spend mandate authorizing the bot.

- Issuer: `corp-finance@acme.com`
- Subject: `did:molt:my-agent`
- Limit: $500/month
- Scope: `planexe.org/*`

### Transaction Flow

1. Agent calls `POST /api/purchase-credits` with `{ amount: 100, mandate: <Signed_JWT> }`.
2. PlanExe verifies mandate signature.
3. PlanExe charges corporate card on file.
4. PlanExe issues credits to the agent.

## Architecture 2: The Crypto Route (x402)

### Header Exchange

1. Agent calls `POST /api/generate-plan`.
2. PlanExe returns `402 Payment Required` with invoice header.
3. Agent pays via wallet.
4. Agent retries with `Authorization: x402 <proof_of_payment>`.
5. PlanExe returns `200 OK`.

## Integration with OpenClaw

Release an `OpenClaw:Wallet` skill that handles both protocols.

```json
{
  "wallet": {
    "ap2_mandate": "/path/to/mandate.jwt",
    "x402_private_key": "secure-me",
    "auto_top_up": true
  }
}
```

## Success Metrics

- Headless revenue share (% of revenue from agent payments).
- Error rate on x402 (< 1%).
- Time-to-top-up for AP2 mandates.

## Risks

- Mandate key compromise.
- Payment replay attacks.
- Wallet integration failures on edge devices.

## Future Enhancements

- Multi-currency pricing and FX handling.
- Per-agent spending dashboards.
- Payment routing by risk tier.
