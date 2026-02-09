"""
Input validation utilities for PlanExe ranking pipeline.

Provides sanitization and validation for user-submitted data to prevent
injection attacks, oversized payloads, and malformed data.
"""
import html
import json
import re
from typing import Any, Dict
from urllib.parse import urlparse


def validate_plan_json(plan_json: dict, max_size_bytes: int = 1048576) -> None:
    """
    Validate the plan JSON structure and size.
    
    Args:
        plan_json: Dictionary containing the plan data
        max_size_bytes: Maximum allowed size in bytes (default 1MB)
    
    Raises:
        ValueError: If validation fails
        TypeError: If plan_json is not a dict
    """
    if not isinstance(plan_json, dict):
        raise TypeError(f"plan_json must be a dict, got {type(plan_json).__name__}")
    
    # Check total JSON size in bytes
    try:
        json_str = json.dumps(plan_json, ensure_ascii=False)
        json_size = len(json_str.encode('utf-8'))
    except (TypeError, ValueError) as e:
        raise ValueError(f"plan_json is not JSON-serializable: {e}")
    
    if json_size > max_size_bytes:
        raise ValueError(
            f"plan_json exceeds maximum size: {json_size} bytes > {max_size_bytes} bytes"
        )
    
    # Validate required fields exist
    required_fields = ["prompt"]
    missing_fields = [field for field in required_fields if field not in plan_json]
    if missing_fields:
        raise ValueError(f"plan_json missing required fields: {', '.join(missing_fields)}")
    
    # Validate nested structure depth (prevent deeply nested objects)
    max_depth = 20
    
    def check_depth(obj: Any, current_depth: int = 0) -> int:
        """Recursively check nesting depth of JSON structure."""
        if current_depth > max_depth:
            raise ValueError(f"plan_json exceeds maximum nesting depth of {max_depth}")
        
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(check_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(check_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    try:
        actual_depth = check_depth(plan_json)
        if actual_depth > max_depth:
            raise ValueError(f"plan_json nesting depth {actual_depth} exceeds maximum {max_depth}")
    except RecursionError:
        raise ValueError(f"plan_json nesting depth exceeds maximum {max_depth}")


def validate_title(title: str) -> str:
    """
    Validate and sanitize a plan title.
    
    Args:
        title: The title string to validate
    
    Returns:
        Sanitized title string
    
    Raises:
        ValueError: If title is invalid
        TypeError: If title is not a string
    """
    if not isinstance(title, str):
        raise TypeError(f"title must be a string, got {type(title).__name__}")
    
    # Strip whitespace
    title = title.strip()
    
    # Check length
    max_length = 200
    if len(title) > max_length:
        raise ValueError(f"title exceeds maximum length of {max_length} characters")
    
    # Escape HTML entities to prevent XSS
    title = html.escape(title, quote=True)
    
    # Remove control characters (except newlines/tabs which html.escape handles)
    title = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', title)
    
    return title


def validate_url(url: str) -> str:
    """
    Validate and sanitize a URL.
    
    Args:
        url: The URL string to validate
    
    Returns:
        Sanitized URL string (or empty string if URL was empty)
    
    Raises:
        ValueError: If URL is invalid
        TypeError: If url is not a string
    """
    if not isinstance(url, str):
        raise TypeError(f"url must be a string, got {type(url).__name__}")
    
    # Strip whitespace
    url = url.strip()
    
    # Empty URL is allowed
    if not url:
        return ""
    
    # Check length
    max_length = 2000
    if len(url) > max_length:
        raise ValueError(f"url exceeds maximum length of {max_length} characters")
    
    # Validate URL format
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")
    
    # Must be HTTP or HTTPS
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(
            f"url must use http or https scheme, got: {parsed.scheme or '(none)'}"
        )
    
    # Must have a netloc (domain)
    if not parsed.netloc:
        raise ValueError("url must include a domain name")
    
    # Remove control characters and other dangerous characters
    url = re.sub(r'[\x00-\x1f\x7f]', '', url)
    
    # Basic check for common injection patterns
    dangerous_patterns = [
        'javascript:',
        'data:',
        'vbscript:',
        'file:',
        'about:',
    ]
    url_lower = url.lower()
    for pattern in dangerous_patterns:
        if pattern in url_lower:
            raise ValueError(f"url contains forbidden pattern: {pattern}")
    
    return url


def validate_prompt(prompt: str) -> str:
    """
    Validate and sanitize a prompt string.
    
    Args:
        prompt: The prompt string to validate
    
    Returns:
        Sanitized prompt string
    
    Raises:
        ValueError: If prompt is invalid
        TypeError: If prompt is not a string
    """
    if not isinstance(prompt, str):
        raise TypeError(f"prompt must be a string, got {type(prompt).__name__}")
    
    # Check length
    max_length = 5000
    if len(prompt) > max_length:
        raise ValueError(f"prompt exceeds maximum length of {max_length} characters")
    
    # Remove null bytes and other control characters that could cause issues
    # Keep newlines, tabs, and carriage returns as they're valid in prompts
    prompt = re.sub(r'[\x00\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', prompt)
    
    # Remove potentially dangerous Unicode characters
    # Right-to-left override, zero-width characters, etc.
    dangerous_unicode = [
        '\u202e',  # Right-to-left override
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\u200e',  # Left-to-right mark
        '\u200f',  # Right-to-left mark
        '\ufeff',  # Zero-width no-break space (BOM)
    ]
    for char in dangerous_unicode:
        prompt = prompt.replace(char, '')
    
    return prompt
