# PlanExe + Chlorpromazine MCP Integration Design

**Version:** 1.0  
**Date:** February 8, 2026  
**Author:** OpenClaw Agent  
**Status:** Design Phase

---

## Executive Summary

This document outlines the strategy for integrating **PlanExe** (a strategic planning tool) into **Chlorpromazine MCP Server** to enable organic discovery by AI agents and establish a monetization pathway. The integration will add PlanExe as a new MCP tool in Chlorpromazine, allowing AI agents to automatically invoke comprehensive planning workflows when users express planning needs.

**Key Benefits:**
- **Organic Discovery**: AI agents discover PlanExe through Smithery.ai's MCP directory
- **Seamless Integration**: Single tool call triggers 15-20 minute planning workflow
- **Built-in Monetization**: Credit system with free tier -> paid conversion funnel
- **Low Friction**: No user authentication required for discovery; API key only for paid usage

---

## 1. Integration Strategy

### 1.1 High-Level Architecture

```
User -> AI Agent (Claude/GPT) -> Chlorpromazine MCP -> PlanExe HTTP API -> Strategic Plan
                                    |
                            Smithery.ai Directory
                                    |
                           Organic Discovery
```

### 1.2 Tool Name Options

Recommended tool names (ranked by discoverability):

1. **`strategic_plan`** * RECOMMENDED
   - Clear, professional, matches what users ask for
   - Natural language: "create a strategic plan for..."
   - SEO-friendly for Smithery.ai search

2. **`plan_escape`**
   - Clever callback to "PlanExe" branding
   - Less discoverable (users don't search for "escape")
   
3. **`make_a_plan`**
   - Conversational, approachable
   - Matches natural speech patterns
   - Risk: Too generic, may conflict with other tools

4. **`structured_thinking`**
   - Abstract, less clear about output
   - Doesn't convey "business plan" or "strategic plan"

### 1.3 When AI Agents Should Invoke It

**Context Triggers** (high-confidence scenarios):

1. **Explicit Planning Requests**
   - "Create a business plan for..."
   - "I need a strategic plan for..."
   - "Help me plan a project to..."
   - "Generate a feasibility study for..."

2. **Project Kickoffs**
   - User describes a new venture/project without a clear path
   - Questions like "How do I start a [business/project]?"
   - "What would it take to launch..."

3. **Complex Problem Decomposition**
   - Multi-month initiatives with unclear scope
   - Budget planning for large projects ($10k+)
   - Stakeholder coordination needs
   - Regulatory/compliance-heavy projects

4. **User Frustration Signals**
   - "I don't know where to start"
   - "This is too overwhelming"
   - "Can you break this down for me?"

**Anti-Triggers** (when NOT to invoke):
- Simple task lists or to-dos
- Quick tactical decisions
- Code architecture discussions (use other tools)
- Time-sensitive questions (PlanExe takes 15-20 min)

---

## 2. Technical Implementation

### 2.1 Tool Handler Structure

Following Chlorpromazine's pattern, create a new tool at:
`/mnt/d/1Projects/chlorpromazine-mcp/src/tools/strategic-plan/`

**File Structure:**
```
strategic-plan/
├── handler.ts       # Core logic, API calls to PlanExe
├── schema.ts        # Zod schemas for input/output validation
├── index.ts         # Tool definition and exports
└── README.md        # Documentation for contributors
```

[TRUNCATED FOR CLEAN PUSH]
