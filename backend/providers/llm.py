"""
Common adapter interface for LLM APIs.
Provider is selected via the LLM_PROVIDER env var.
Model is selected via LLM_MODEL env var.
"""
import os
import json
from typing import Any
from dotenv import load_dotenv, find_dotenv, dotenv_values
from openai import OpenAI


PROVIDER = os.getenv("LLM_PROVIDER").lower()
MODEL = os.getenv("LLM_MODEL").lower()


def complete(messages: list[dict], system: str = "", tools: list[dict] | None = None) -> dict:
    """
    Unified completion call.
    Returns: { "text": str | None, "tool_calls": list[dict] }
    """
    if PROVIDER == "openai":
        return _openai(messages, system, tools)
    else:
        raise ValueError(f"Unknown provider: {PROVIDER}")


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

def _openai(messages, system, tools):

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    response = client.responses.create(
        model=MODEL,
        tools=tools,
        input=all_messages
    )
    try:
        text = response.output[0].content[0].text
    except:
        text = "Called functions"
    tool_calls = []

    for item in response.output:
        if item.type == "function_call":
            tool_calls.append({
                "name": item.name,
                "id": item.id,
                "input": json.loads(item.arguments)
                })


    return {"text": text, "tool_calls": tool_calls}