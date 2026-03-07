"""
Utility for guarding against None structured LLM responses.

When a local/small model fails structured output validation (e.g. echoes
the schema instead of producing values), llama_index's StructuredLLM.chat()
may return a ChatResponse where .raw is None rather than raising.

Accessing .raw.model_dump() or .raw.<field> on a None value raises
AttributeError with no context — making failures hard to diagnose.

Use require_raw() immediately after sllm.chat() to surface a clear
ValueError that names the model and the expected Pydantic type.
"""
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def require_raw(chat_response, model_class: Type[T]) -> T:
    """
    Assert that chat_response.raw is a valid instance of model_class.

    Raises:
        ValueError: If chat_response.raw is None or not an instance of model_class.
            The error message names the expected type to aid diagnosis.
    """
    raw = chat_response.raw
    if raw is None:
        raise ValueError(
            f"Structured LLM returned None for {model_class.__name__}. "
            "The model likely echoed the schema instead of producing values. "
            "Check model compatibility with structured output."
        )
    if not isinstance(raw, model_class):
        raise ValueError(
            f"Structured LLM returned unexpected type {type(raw).__name__!r} "
            f"instead of {model_class.__name__}. "
            "Check model compatibility with structured output."
        )
    return raw
