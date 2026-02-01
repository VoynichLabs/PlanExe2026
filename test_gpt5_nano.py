"""
Test GPT-5 Nano configuration with proper reasoning parameters.

Usage:
    python test_gpt5_nano.py

Requirements:
    - OPENROUTER_API_KEY environment variable must be set
"""
import os
from llama_index.llms.openrouter import OpenRouter
from llama_index.core.llms import ChatMessage, MessageRole

def test_gpt5_nano():
    """Test GPT-5 Nano with reasoning effort and provider routing."""
    print("=" * 60)
    print("Testing GPT-5 Nano Configuration")
    print("=" * 60)

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        print("❌ ERROR: OPENROUTER_API_KEY environment variable not set")
        return False

    print("\n📋 Configuration:")
    print("  - Model: openai/gpt-5-nano")
    print("  - Reasoning effort: medium")
    print("  - Verbosity: medium")
    print("  - Provider: OpenAI only (no fallbacks)")
    print("  - Max completion tokens: 8192")
    print("  - Timeout: 120s")

    try:
        llm = OpenRouter(
            api_key=openrouter_api_key,
            model="openai/gpt-5-nano",
            timeout=120.0,
            max_tokens=8192,  # Will be sent as max_completion_tokens for reasoning models
            additional_kwargs={
                "reasoning": {
                    "effort": "medium"
                },
                "text": {
                    "verbosity": "medium"
                },
                "provider": {
                    "order": ["openai"],
                    "allow_fallbacks": False
                },
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/PlanExeOrg/PlanExe",
                    "X-Title": "PlanExe - GPT-5 Nano Test"
                }
            }
        )

        messages = [
            ChatMessage(
                role=MessageRole.USER,
                content="Solve this: What is 15 * 23? Show your reasoning briefly."
            )
        ]

        print("\n🚀 Sending test request...")
        response = llm.chat(messages)
        response_text = response.message.content

        print("\n✅ SUCCESS! Response received:")
        print("-" * 60)
        print(response_text)
        print("-" * 60)

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gpt5_nano()
    exit(0 if success else 1)
