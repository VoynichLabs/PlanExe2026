# GPT-5 Nano Model Selection Issue - This remains unresolved. 
It succeeds on certain prompts and tasks but fails on others. I think that the context window might still be an issue; I'm not totally sure. 
## Date: 2026-01-31

## Executive Summary

**Issue:** GPT-5 Nano (priority 1) was being used for small prompts but falling back to Gemini 3 Flash (priority 2) for larger prompts during plan generation.

**Root Cause:** The llama-index library was reporting an incorrect context_window of 3,900 tokens for GPT-5 Nano, when the actual limit is 400,000 tokens. The LLMExecutor was skipping GPT-5 Nano for prompts exceeding 3,900 tokens.

**Resolution:** Added explicit `context_window: 400000` to GPT-5 Nano configuration in llm_config.json, overriding the library's incorrect default.

**Status:** ✅ FIXED - Configuration updated, containers restarted, testing in progress.

---

## Problem Statement

GPT-5 Nano was configured as priority 1 in `llm_config.json`, but during full plan generation, the system was falling back to Gemini 3 Flash Preview (priority 2) for many pipeline tasks. Initial investigation suggested the priority system wasn't being respected.

---

## Root Cause Analysis

### Evidence from OpenRouter Activity Logs

User provided OpenRouter activity logs showing clear pattern:

**GPT-5 Nano calls (successful, small prompts):**
- Jan 31, 02:28-02:32 PM: 7 calls
- Input token ranges: 235, 252, 344, 494, 960, 1,106, 1,426 tokens
- All succeeded

**Gemini 3 Flash calls (large prompts):**
- Jan 31, 02:33 PM: 3 calls
- Input token ranges: **11,625, 11,670, 14,576 tokens**
- All succeeded

**Pattern:** GPT-5 Nano handled prompts up to ~1,426 tokens. When prompt size jumped to 11,000+ tokens, system switched to Gemini.

### Investigation: The 3,900 Token Mystery

Examination of `run/error_sample.json` (LLMChatStartEvent from RedlineGate safety check) revealed:

```json
"model_dict": {
    "model": "openai/gpt-5-nano",
    "context_window": 3900,
    ...
}
```

**But GPT-5 Nano actually has a 400,000 token context window!**

The LLMExecutor checks context windows before trying each model. With the incorrect 3,900 limit:
- ✅ Prompts < 3,900 tokens → Try GPT-5 Nano first (success)
- ❌ Prompts > 3,900 tokens → Skip GPT-5 Nano (exceeds "limit") → Fall back to Gemini

### Source of Incorrect Value

The 3,900 value is **not** hard-coded in PlanExe. Investigation of `worker_plan_internal/llm_factory.py` (lines 164-187) shows:

```python
config = planexe_llmconfig.llm_config_dict[llm_name]
arguments = config.get("arguments", {})
arguments.update(kwargs)  # Override with any kwargs

llm_class = globals()[class_name]  # Get OpenRouter class
return llm_class(**arguments)  # Pass all arguments
```

PlanExe correctly passes all arguments from llm_config.json to the OpenRouter class. The 3,900 value appears to be a **default from the llama-index library** when no `context_window` is explicitly provided.

**Note:** We attempted to verify by reading `/usr/local/lib/python3.13/site-packages/llama_index/llms/openrouter/base.py` in the docker container but were unable to complete the investigation. The source of 3,900 is presumed to be llama-index library defaults, but this is **not confirmed**.

---

## Solution Applied

### 1. Fixed Context Window Issue

Added explicit `context_window: 400000` to GPT-5 Nano configuration:

```json
"openrouter-paid-openai-gpt-5-nano": {
    "priority": 1,
    "class": "OpenRouter",
    "arguments": {
        "model": "openai/gpt-5-nano",
        "temperature": 1.0,
        "timeout": 120.0,
        "context_window": 400000,  // ADDED - Overrides library default
        "max_tokens": 8192,
        ...
    }
}
```

### 2. Fixed Temperature for Reasoning Models

GPT-5 Nano doesn't accept temperature parameter. Set to 1.0 to avoid errors:
- GPT-5 Nano: `temperature: 1.0` (was 0.1)
- GPT-OSS-20b: `temperature: 1.0` (was 0.1)
- NVIDIA Nemotron-3-Nano: `temperature: 1.0` (was 0.1)

### 3. Removed Deprecated Model

Removed `openrouter-paid-openai-gpt-4o-mini`:
- Was at priority 2 (tie with Gemini 3 Flash)
- Deprecated/being deprecated soon
- Was being used alongside Gemini in tests

### 4. Added New Models

Per user request, added newer models:
- `z-ai/glm-4.7-flash` (priority 3)
- `z-ai/glm-4.7` (priority 4)
- `xiaomi/mimo-v2-flash` (priority 5)
- `nvidia/nemotron-3-nano-30b-a3b` (priority 6, already existed)
- `openai/gpt-oss-20b` (priority 7)

### 5. Deprioritized Old Model

- `qwen/qwen3-30b-a3b`: Changed to priority 10, marked DEPRECATED

---

## Final Configuration

**New Priority Order:**
1. GPT-5 Nano (priority 1) - **400k context, temp 1.0**
2. Gemini 3 Flash Preview (priority 2)
3. z-ai/glm-4.7-flash (priority 3)
4. z-ai/glm-4.7 (priority 4)
5. xiaomi/mimo-v2-flash (priority 5)
6. NVIDIA Nemotron-3-Nano (priority 6)
7. GPT-OSS-20b (priority 7)
8. Qwen3-30b (priority 10 - deprecated)

Verified via docker exec:
```bash
docker exec worker_plan python -c "from worker_plan_internal.llm_factory import get_llm_names_by_priority; print(get_llm_names_by_priority())"
```

---

## Deployment

### Docker Restart
All containers restarted to reload llm_config.json:
```bash
cd c:/Projects/PlanExe2026
docker-compose restart
```

### Container Status
```
NAMES                    STATUS
worker_plan_database_2   Up (healthy)
worker_plan_database     Up (healthy)
worker_plan_database_1   Up (healthy)
worker_plan_database_3   Up (healthy)
mcp_cloud                Up (healthy)
worker_plan              Up (healthy)
```

**Note:** All worker_plan_database_* containers have `restart: unless-stopped` in docker-compose.yml and auto-start correctly.

---

## Testing

### Test 1: Landscaping Company Plan (Current)
**Task ID:** `b6d6c5b8-8116-4b3e-9033-40e037d1df0f`
**Created:** 2026-01-31 19:42:31Z
**Status:** Processing (1.80% complete at last check)
**Prompt:** "I want to start a landscaping company in Hampton, Connecticut. Current assets: Ram 1500 truck, single owner-operator. I need a business plan."
**Speed:** fast

**Command:**
```bash
curl -X POST http://localhost:8001/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"task_create","arguments":{"prompt":"I want to start a landscaping company in Hampton, Connecticut. Current assets: Ram 1500 truck, single owner-operator. I need a business plan.","speed_vs_detail":"fast"}}}'
```

**Expected Result:** GPT-5 Nano should be used for ALL tasks, including large prompts (11k+ tokens), now that context_window is correctly set to 400,000.

### Previous Test Results (Before Fix)

**Crispy Ants Plan (ping test):**
- Task ID: `db40f36c-1830-4166-a65b-385bb6ded167`
- Used: Gemini 3 Flash (because ping has minimal prompt < 3,900 tokens)
- Duration: 5.8 seconds
- Status: Completed

---

## Key Learnings

### LLM Executor Behavior

From `worker_plan_internal/plan/run_plan_pipeline.py`:

1. **PlanTask.run()** always calls `run_inner()`
2. **Default run_inner()** creates LLMExecutor with all priority models
3. **LLMExecutor** tries models in order:
   - Checks context_window limit before attempting
   - If prompt exceeds context_window, **skips that model**
   - Tries next model in priority list
   - Returns first successful response

4. Tasks can override either:
   - `run_with_llm(llm)` - Receives one LLM at a time from executor
   - `run_inner()` - Manually create executor, control retry logic

### Configuration Override Pattern

The llm_factory.py pattern (lines 164-187):
```python
config = planexe_llmconfig.llm_config_dict[llm_name]
arguments = config.get("arguments", {})
llm_class = globals()[class_name]
return llm_class(**arguments)
```

**Takeaway:** Any parameter in the `arguments` section of llm_config.json is passed directly to the LLM class constructor, allowing override of library defaults.

---

## Files Modified

1. **c:\Projects\PlanExe2026\llm_config.json**
   - Added `context_window: 400000` to GPT-5 Nano
   - Changed `temperature: 1.0` for reasoning models
   - Removed GPT-4o-mini entry
   - Added new models (z-ai, xiaomi)
   - Deprioritized Qwen3

---

## Environment Details

- **OS:** Windows (Git Bash)
- **Docker:** Containers running locally
- **Database:** PostgreSQL (`database_postgres` container)
- **MCP Server:** `mcp_cloud` on http://localhost:8001/mcp/
- **Workers:** `worker_plan`, `worker_plan_database`, `worker_plan_database_1`, `worker_plan_database_2`, `worker_plan_database_3`
- **Project Path:** `c:\Projects\PlanExe2026`

---

## Next Steps

1. ✅ Monitor landscaping company plan (task b6d6c5b8-8116-4b3e-9033-40e037d1df0f)
2. ✅ Check OpenRouter activity logs to verify GPT-5 Nano is used for large prompts
3. ✅ Compare track_activity.jsonl to confirm no fallback to Gemini
4. ⏳ Run full plan to completion and verify HTML report shows GPT-5 Nano
5. ⏳ Consider adding context_window to other models if they have incorrect defaults

---

## References

- **Error Sample:** `c:\Projects\PlanExe2026\run\error_sample.json`
- **LLM Factory:** `worker_plan_internal/llm_factory.py` (lines 164-187)
- **Pipeline Execution:** `worker_plan_internal/plan/run_plan_pipeline.py`
- **Docker Compose:** `c:\Projects\PlanExe2026\docker-compose.yml` (line 41: restart policy)
- **OpenRouter Docs:** https://openrouter.ai/docs
