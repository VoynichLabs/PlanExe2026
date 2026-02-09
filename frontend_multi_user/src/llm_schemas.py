"""JSON schemas for validating LLM responses in the PlanExe ranking pipeline."""

from typing import Any
from jsonschema import validate, ValidationError


KPI_EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["novelty_score", "prompt_quality", "technical_completeness", "feasibility", "impact_estimate"],
    "properties": {
        "novelty_score": {"type": ["integer", "number"], "minimum": 1, "maximum": 10},
        "prompt_quality": {"type": ["integer", "number"], "minimum": 1, "maximum": 10},
        "technical_completeness": {"type": ["integer", "number"], "minimum": 1, "maximum": 10},
        "feasibility": {"type": ["integer", "number"], "minimum": 1, "maximum": 10},
        "impact_estimate": {"type": ["integer", "number"], "minimum": 1, "maximum": 10}
    },
    "additionalProperties": False
}


COMPARISON_KPI_SCHEMA = {
    "type": "array",
    "minItems": 5,
    "maxItems": 8,
    "items": {
        "type": "object",
        "required": ["name", "plan_a", "plan_b", "reasoning"],
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 100},
            "plan_a": {"type": ["integer", "number"], "minimum": 1, "maximum": 5},
            "plan_b": {"type": ["integer", "number"], "minimum": 1, "maximum": 5},
            "reasoning": {"type": "string", "maxLength": 200}
        }
    }
}


def validate_llm_response(data: Any, schema: dict) -> None:
    """Validate LLM response against JSON schema. Raise ValueError if invalid."""
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        raise ValueError(f"LLM response validation failed: {e.message}") from e
