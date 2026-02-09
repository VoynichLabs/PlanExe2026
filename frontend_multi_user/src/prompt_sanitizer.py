"""
Prompt sanitization utilities for LLM input safety.

Prevents prompt injection, truncates oversized inputs, and ensures
safe interpolation into LLM prompts.
"""

import json
import re
from typing import Any, Dict


def sanitize_for_llm_prompt(text: str, max_length: int = 2000) -> str:
    """
    Sanitize user input for safe interpolation into LLM prompts.
    
    Args:
        text: Raw user input text
        max_length: Maximum allowed length (default 2000)
    
    Returns:
        Sanitized text safe for LLM prompts
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove common prompt injection patterns (case-insensitive)
    injection_patterns = [
        r"ignore\s+(previous|all|above|prior)\s+instructions?",
        r"disregard\s+(previous|all|above|prior)\s+instructions?",
        r"forget\s+(previous|all|above|prior)\s+instructions?",
        r"new\s+instructions?:",
        r"system\s+prompt:",
        r"you\s+are\s+now",
        r"act\s+as\s+if",
        r"pretend\s+(you\s+are|to\s+be)",
    ]
    
    for pattern in injection_patterns:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    
    # Escape curly braces that could break f-string/template formatting
    text = text.replace("{", "{{").replace("}", "}}")
    
    # Escape backticks that could break markdown code blocks
    text = text.replace("`", "\\`")
    
    # Normalize newlines - convert multiple newlines to single space
    # to prevent prompt structure breaking
    text = re.sub(r'\n\s*\n+', ' ', text)
    text = text.replace('\n', ' ')
    
    # Remove any non-printable characters except basic whitespace
    text = ''.join(char for char in text if char.isprintable() or char in [' ', '\t'])
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def truncate_plan_summary(plan_json: dict) -> dict:
    """
    Return a size-limited version of plan_json suitable for LLM prompts.
    
    Keeps only essential fields, truncates long strings, and ensures
    the serialized JSON doesn't exceed 2000 characters.
    
    Args:
        plan_json: Full plan dictionary
    
    Returns:
        Truncated plan dictionary (max 2000 chars when serialized)
    """
    if not isinstance(plan_json, dict):
        return {}
    
    # Essential fields to keep
    essential_fields = [
        'prompt', 'title', 'wbs', 'estimated_cost_cents',
        'duration_months', 'duration_days', 'plan_id'
    ]
    
    # Start with essential fields only
    truncated = {}
    for field in essential_fields:
        if field in plan_json:
            truncated[field] = plan_json[field]
    
    # Truncate string fields
    for key, value in truncated.items():
        if isinstance(value, str) and len(value) > 500:
            truncated[key] = value[:497] + "..."
    
    # Simplify WBS if present (keep structure but limit depth/content)
    if 'wbs' in truncated and isinstance(truncated['wbs'], dict):
        wbs_simplified = {}
        for wbs_key, wbs_value in list(truncated['wbs'].items())[:20]:  # Max 20 WBS items
            if isinstance(wbs_value, dict):
                # Keep only essential WBS fields
                wbs_simplified[wbs_key] = {
                    'title': str(wbs_value.get('title', ''))[:100],
                    'depends_on': wbs_value.get('depends_on', [])[:5],  # Max 5 dependencies
                }
            else:
                wbs_simplified[wbs_key] = wbs_value
        truncated['wbs'] = wbs_simplified
    
    # Serialize and check size
    serialized = json.dumps(truncated, ensure_ascii=False)
    
    # If still too large, progressively reduce
    if len(serialized) > 2000:
        # Further truncate strings
        for key, value in truncated.items():
            if isinstance(value, str) and len(value) > 200:
                truncated[key] = value[:197] + "..."
        
        # Further simplify WBS
        if 'wbs' in truncated and isinstance(truncated['wbs'], dict):
            wbs_minimal = {}
            for wbs_key in list(truncated['wbs'].keys())[:10]:  # Max 10 items
                wbs_minimal[wbs_key] = {'title': str(truncated['wbs'][wbs_key].get('title', ''))[:50]}
            truncated['wbs'] = wbs_minimal
        
        serialized = json.dumps(truncated, ensure_ascii=False)
    
    # Final safety check - if STILL too large, just keep bare minimum
    if len(serialized) > 2000:
        truncated = {
            'title': str(plan_json.get('title', ''))[:100],
            'prompt': str(plan_json.get('prompt', ''))[:500],
        }
    
    return truncated
