"""
Test script to verify the new and updated LLM configurations.

Usage:
    python test_new_llm_configs.py

Requirements:
    - OPENROUTER_API_KEY environment variable must be set
    - llama-index and llama-index-llms-openrouter must be installed
"""
import os
from llama_index.llms.openrouter import OpenRouter
from llama_index.core.llms import ChatMessage, MessageRole

# Models to test
models_to_test = [
    {
        "name": "Gemini 3 Flash Preview",
        "model": "google/gemini-3-flash-preview",
        "description": "Correct preview version (verified)"
    },
    {
        "name": "GPT-5-Mini",
        "model": "openai/gpt-5-mini",
        "description": "Updated from GPT-4o-mini"
    },
    {
        "name": "Arcee Trinity Large",
        "model": "arcee-ai/trinity-large-preview:free",
        "description": "New free model"
    },
    {
        "name": "Xiaomi Mimo v2 Flash",
        "model": "xiaomi/mimo-v2-flash",
        "description": "New fast model"
    },
    {
        "name": "Minimax M2.1",
        "model": "minimax/minimax-m2.1",
        "description": "New large context model"
    }
]

def test_model(model_info: dict) -> bool:
    """Test a single model configuration."""
    print(f"\nTesting {model_info['name']} ({model_info['description']})...")
    print(f"Model ID: {model_info['model']}")

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        print("❌ ERROR: OPENROUTER_API_KEY environment variable not set")
        return False

    try:
        llm = OpenRouter(
            api_key=openrouter_api_key,
            max_tokens=100,
            context_window=2048,
            model=model_info['model'],
            timeout=30.0
        )

        messages = [
            ChatMessage(
                role=MessageRole.USER,
                content="Reply with 'PONG' and confirm you can answer requests."
            )
        ]

        print("  Sending ping request...")
        response = llm.chat(messages)
        response_text = response.message.content

        print(f"  ✓ Response: {response_text[:100]}...")
        return True

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("Testing Updated and New LLM Configurations")
    print("=" * 60)

    results = []
    for model_info in models_to_test:
        success = test_model(model_info)
        results.append((model_info['name'], success))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{total} models passed")

if __name__ == "__main__":
    main()
