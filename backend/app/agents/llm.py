"""LLM access layer.

Uses a real OpenAI chat model (via langchain-openai) for all agent
reasoning. Requires OPENAI_API_KEY to be set in the environment / .env file.
"""
import json
import re

from app.config import settings


def get_llm():
    """Build the chat model used by every agent node.

    Raises a clear error at call time (not import time) if no API key is
    configured, so the app can still start up and surface a useful message
    instead of failing on import.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your environment or .env "
            "file to run SentinelX's agents (see .env.example)."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
    )


def call_llm_json(prompt: str) -> dict:
    """Invoke the configured LLM and parse a JSON object from its response."""
    llm = get_llm()
    result = llm.invoke(prompt)
    content = getattr(result, "content", str(result))
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise
