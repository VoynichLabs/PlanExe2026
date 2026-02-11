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

## Overview
This proposal defines the "Economic Interface" for PlanExe. It allows autonomous agents to purchase Cloud Credits (for plan generation) using standardized machine-readable protocols, removing the need for a human to manually enter a credit card on a website.

We support a **Dual-Protocol Strategy**:
1.  **AP2 (Agent Payments Protocol):** For high-value, auditable corporate spend (authorized by Humans).
2.  **x402 (HTTP 402):** For low-value, instant micropayments (authorized by Wallets).

## Core Problem
Agents like OpenClaw run headless. They cannot solve CAPTCHAs or navigate Stripe Checkout flows. If MyAgent runs out of credits at 3 AM, it gets stuck.

## Architecture 1: The Corporate Route (AP2)
Best for Enterprise agents with a budget.

### The Mandate
The Human Manager signs a digital "Spend Mandate" authorizing the bot.
*   **Issuer:** `corp-finance@acme.com`
*   **Subject:** `did:molt:my-agent`
*   **Limit:** $500/month
*   **Scope:** `planexe.org/*`

### The Transaction Flow
1.  **Agent:** Calls `POST /api/purchase-credits` with `{ amount: 100, mandate: <Signed_JWT> }`.
2.  **PlanExe:** Verifies the Mandate signature against the Corporate Public Key.
3.  **PlanExe:** Charges the Corporate Card on file (via Stripe).
4.  **PlanExe:** Issues 100 Credits to the Agent.

---

## Architecture 2: The Crypto Route (x402)
Best for Independent agents using stablecoins or Lightning.

### The Header Exchange
Standard HTTP logic for paying per-request.

1.  **Agent:** Calls `POST /api/generate-plan`.
2.  **PlanExe:** Returns `402 Payment Required`.
    *   `WWW-Authenticate: x402 token="...", invoice="lnbc1...", amount="5.00 USDC"`
3.  **Agent:** Pays the invoice via its local wallet.
4.  **Agent:** Retries the request with `Authorization: x402 <proof_of_payment>`.
5.  **PlanExe:** Returns `200 OK`.

---

## Integration with OpenClaw
We will release an `OpenClaw:Wallet` skill that manages both protocols.

*   **Config:**
    ```json
    {
      "wallet": {
        "ap2_mandate": "/path/to/mandate.jwt",
        "x402_private_key": "Make sure this is secure!",
        "auto_top_up": true
      }
    }
    ```

*   **Behavior:**
    *   If the request is < $0.10, try x402 (Instant).
    *   If the request is > $10.00, use AP2 (Audited).

## Success Metrics
*   **Headless Revenue:** % of revenue coming from API calls with no browser session.
*   **Friction:** Error rate on x402 payments (target < 1%).
