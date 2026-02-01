# GPT-5 Nano Fix: OpenRouter → OpenAI Class Switch

**Date:** January 31, 2026
**Issue:** GPT-5 Nano was failing due to incorrect context window reporting
**Status:** ✅ Resolved and verified working (tenatively)

## Problem Statement

GPT-5 Nano was failing with context window validation errors despite being a powerful reasoning model with a 400,000 token context window. The LLM was reporting a context window of only 3,900 tokens, causing llama-index's validation to reject requests that should have been valid.

## Root Cause

The issue was in how llama-index's **OpenRouter class** handles context window information:

1. We had configured `context_window: 400000` in `llm_config.json`
2. However, the OpenRouter class queries the OpenRouter API at initialization time to get model metadata
3. OpenRouter's API returns a reported context window of 3,900 tokens for GPT-5 Nano
4. This API-returned value **overwrites** the configured `context_window` value
5. llama-index then validates max_tokens against this incorrect 3,900 limit and rejects valid requests

The OpenRouter API's 3,900 value appears to be a default or incorrect cached value—GPT-5 Nano's actual context window is 400,000 tokens.

## Solution: Switch to OpenAI Class

**Configuration Change in `llm_config.json`:**

```json
{
  "openrouter-paid-openai-gpt-5-nano": {
    "comment": "GPT-5 Nano - Fast reasoning model. Using OpenAI class directly to avoid context window issues.",
    "priority": 1,
    "class": "OpenAI",
    "arguments": {
      "model": "gpt-5-nano",
      "api_key": "${OPENAI_API_KEY}",
      "temperature": 1.0,
      "timeout": 120.0,
      "context_window": 400000,
      "is_function_calling_model": false,
      "is_chat_model": true,
      "max_tokens": 128000,
      "max_retries": 5
    }
  }
}
```

### Key Changes:

| Parameter | Old Value | New Value | Reason |
|-----------|-----------|-----------|--------|
| `class` | `OpenRouter` | `OpenAI` | Direct OpenAI API bypasses OpenRouter's incorrect metadata |
| `model` | `openai/gpt-5-nano` | `gpt-5-nano` | OpenAI class expects OpenAI model naming |
| `api_key` | `${OPENROUTER_API_KEY}` | `${OPENAI_API_KEY}` | Use OpenAI API directly |
| `context_window` | 400000 | 400000 | Explicit declaration, now properly respected |
| `max_tokens` | 8192 | 128000 | GPT-5 Nano supports up to 128,000 completion tokens |
| `temperature` | 0.1 | 1.0 | Reasoning models require temperature=1.0 per OpenAI specs |
| `timeout` | 60.0 | 120.0 | Reasoning models need more time |

## Why This Works

1. **OpenAI class doesn't query external APIs** for model metadata—it uses the configuration values directly
2. **Respects our configured `context_window: 400000`** instead of overwriting it with API data
3. **Uses OpenAI's Chat Completions API directly**, which GPT-5 Nano fully supports
4. **Proper token limits**: The 128,000 max_tokens reflects GPT-5 Nano's actual completion token limit
5. **Correct temperature for reasoning**: GPT-5 Nano is a reasoning model and requires `temperature: 1.0`

## Verification

✅ Successfully instantiates as `llama_index.llms.openai.OpenAI`
✅ Context window properly set to 400,000
✅ Max tokens accepts up to 128,000
✅ Completes inference requests successfully
✅ Plans now generate properly (tested with multiple task types)

## Notes

- The old Chat Completions API implementation is working correctly—no need to switch to newer APIs
- GPT-5 Nano was always capable of this; it was just a library configuration issue
- The `${OPENAI_API_KEY}` environment variable must be set in `.env` (already exists in your environment)
