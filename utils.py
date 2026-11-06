"""Small text helpers shared across agents and the API layer."""

from typing import Any


def as_text(value: Any) -> str:
    """Flatten MCP tool output (str, or list of content blocks) into plain text."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(as_text(item))
        return "\n".join(parts)
    if isinstance(value, dict):
        return str(value.get("text", value))
    return "" if value is None else str(value)


def clip(text: Any, limit: int) -> str:
    """Truncate text so prompts stay inside the model's token budget."""
    text = str(text or "")
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"
