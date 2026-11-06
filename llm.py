"""Shared Groq chat model and small helpers for calling it."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config import GROQ_API_KEY, GROQ_MODEL, LLM_MAX_RETRIES, LLM_MAX_TOKENS

llm = ChatGroq(
    model=GROQ_MODEL,
    api_key=GROQ_API_KEY,
    max_tokens=LLM_MAX_TOKENS,
    max_retries=LLM_MAX_RETRIES,
)


def llm_text(system_prompt: str, user_prompt: str) -> str:
    """Call the LLM with a system and user prompt and return the text."""
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return str(response.content)


def json_from_llm(text: str) -> dict[str, Any]:
    """Extract the first complete JSON object returned by the model."""
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("The model did not return a JSON object.")

    return json.loads(text[start : end + 1])
