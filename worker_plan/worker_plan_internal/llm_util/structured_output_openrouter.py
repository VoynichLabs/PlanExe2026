"""
StructuredOutputOpenRouter: OpenRouter LLM subclass with reliable structured output.

Problem:
    The base OpenRouter class inherits OpenAI.structured_predict(), which falls through
    to `super().structured_predict()` with `tool_choice='required'` when the model is
    not in OpenAI's recognized list (e.g. `openai/gpt-5.4-nano` via OpenRouter prefix).
    This causes a 400 Bad Request: "Tool choice 'required' must be specified with 'tools'".

    Additionally, OpenAI's strict json_schema response_format rejects Pydantic models
    that use Dict fields (e.g. Dict[str, str]) because they generate schemas with
    `additionalProperties: {...}` which is forbidden under strict mode. This causes:
    "Invalid schema for response_format: 'required' is required to be supplied and to
    be an array including every key in properties."

    Separately, some OpenRouter model variants return a raw JSON string instead of a
    parsed Pydantic model instance, causing AttributeError in StructuredLLM.chat().

Fix:
    Override structured_predict() (and astructured_predict()) to use
    response_format={"type": "json_object"} — a looser format supported by all
    OpenRouter/OpenAI-compatible models — combined with explicit schema instructions
    injected into the system prompt, and parse the result via model_validate_json().

Usage in llm_config/<profile>.json:
    {
        "class": "StructuredOutputOpenRouter",
        "arguments": {
            "model": "openai/gpt-5.4-nano",
            ...
        }
    }
"""

import json
import logging
from typing import Any, Dict, Optional, Type

from llama_index.llms.openrouter import OpenRouter
from llama_index.core.types import Model
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole

logger = logging.getLogger(__name__)

_JSON_SCHEMA_INSTRUCTIONS = """

---
IMPORTANT: Respond with a single valid JSON object that conforms to the following JSON schema. Do not include any text outside the JSON object.

Schema:
{schema}
"""


class StructuredOutputOpenRouter(OpenRouter):
    """
    OpenRouter LLM subclass that bypasses the broken tool_choice/strict-schema path
    and uses json_object response_format + system prompt schema injection instead.

    This works reliably with all OpenRouter models, including those that don't support
    OpenAI's strict structured outputs (which rejects Dict fields, $defs, etc.).

    Drop-in replacement for OpenRouter in llm_config JSON files.
    """

    @classmethod
    def class_name(cls) -> str:
        return "StructuredOutputOpenRouter"

    def _should_use_structure_outputs(self) -> bool:
        # Return False so the base OpenAI class doesn't try to use strict json_schema.
        # We handle structured output ourselves in structured_predict.
        return False

    def structured_predict(
        self,
        output_cls: Type[Model],
        prompt: PromptTemplate,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        **prompt_args: Any,
    ) -> Model:
        """
        Structured predict using json_object response_format + schema in system prompt.

        Bypasses both the tool_choice='required' path and the strict json_schema path.
        Uses json_object mode (supported by all OpenAI-compatible endpoints) and injects
        the JSON schema into the system prompt for guidance.
        """
        llm_kwargs = dict(llm_kwargs or {})
        # Remove tool_choice if accidentally present (avoids 400 errors)
        llm_kwargs.pop("tool_choice", None)
        # Use json_object mode — supported universally, no schema strictness issues
        llm_kwargs["response_format"] = {"type": "json_object"}

        messages = list(self._extend_messages(prompt.format_messages(**prompt_args)))
        messages = self._inject_schema_into_messages(messages, output_cls)

        response = self.chat(messages, **llm_kwargs)
        return self._parse_structured_output(output_cls, response.message.content)

    async def astructured_predict(
        self,
        output_cls: Type[Model],
        prompt: PromptTemplate,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        **prompt_args: Any,
    ) -> Model:
        """Async version of structured_predict."""
        llm_kwargs = dict(llm_kwargs or {})
        llm_kwargs.pop("tool_choice", None)
        llm_kwargs["response_format"] = {"type": "json_object"}

        messages = list(self._extend_messages(prompt.format_messages(**prompt_args)))
        messages = self._inject_schema_into_messages(messages, output_cls)

        response = await self.achat(messages, **llm_kwargs)
        return self._parse_structured_output(output_cls, response.message.content)

    @staticmethod
    def _inject_schema_into_messages(
        messages: list, output_cls: Type[Model]
    ) -> list:
        """
        Append JSON schema instructions to the last system message (or create one).

        This guides the model to produce output that matches the Pydantic schema,
        even without strict response_format enforcement.
        """
        schema_str = json.dumps(output_cls.model_json_schema(), indent=2)
        schema_instruction = _JSON_SCHEMA_INSTRUCTIONS.format(schema=schema_str)

        # Find the last system message and append, or inject before user messages
        for i in reversed(range(len(messages))):
            if messages[i].role == MessageRole.SYSTEM:
                existing = messages[i].content or ""
                messages[i] = ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=existing + schema_instruction,
                )
                return messages

        # No system message found — prepend one
        messages.insert(
            0,
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=schema_instruction.strip(),
            ),
        )
        return messages

    @staticmethod
    def _parse_structured_output(output_cls: Type[Model], content: Any) -> Model:
        """
        Parse the LLM response content into the expected Pydantic model.

        Handles both str (raw JSON) and already-parsed model instances.
        """
        if isinstance(content, output_cls):
            return content
        if isinstance(content, str):
            try:
                return output_cls.model_validate_json(content)
            except Exception as e:
                logger.warning(
                    "StructuredOutputOpenRouter: model_validate_json failed (%s), "
                    "trying JSON parse + model_validate...",
                    e,
                )
                try:
                    data = json.loads(content)
                    return output_cls.model_validate(data)
                except Exception as e2:
                    logger.error(
                        "StructuredOutputOpenRouter: both parse attempts failed: %s | %s",
                        e, e2,
                    )
                    raise
        # If content is a dict or something else, try model_validate
        if hasattr(output_cls, "model_validate"):
            return output_cls.model_validate(content)
        raise ValueError(
            f"StructuredOutputOpenRouter: cannot parse response content of type "
            f"{type(content).__name__} into {output_cls.__name__}"
        )
