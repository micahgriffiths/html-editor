"""
Agent router: classifies user intent → selects tool(s) → executes → self-checks.
Single-turn by default. next_action hook is in place for future chaining.
"""
import json
from providers.llm import complete
from tools.definitions import TOOLS
from tools.implementations import (
    edit_section,
    edit_global_style,
    regenerate_section,
    revert,
    get_page_summary,
)
from agents.self_check import self_check

MAX_RETRIES = 2


def run(
    user_message: str,
    html: str,
    style_spec: dict,
    sections: list[dict],
    version_store: list[dict],
    chat_history: list[dict],
) -> dict:
    """
    Main agent entry point.
    Returns:
      {
        "html": str,               # updated HTML (or unchanged on revert/summary)
        "message": str,            # human-readable result description
        "tool_used": str,
        "self_check": dict,
        "version_saved": bool,
      }
    """
    system = _build_system_prompt(sections, style_spec)

    messages = chat_history + [{"role": "user", "content": user_message}]

    # Step 1: Let the model pick a tool
    response = complete(messages, system=system, tools=TOOLS)

    tool_calls = response.get("tool_calls", [])

    # If no tool was called, return the text response directly
    if not tool_calls:
        return {
            "html": html,
            "message": response.get("text", "I didn't know how to handle that."),
            "tool_used": "none",
            "self_check": {"passed": True, "issues": []},
            "version_saved": False,
        }

    # Step 2: Execute the first tool call (single-turn mode)
    # next_action hook: if a tool returns next_action, we could loop here
    tool_call = tool_calls[0]
    result = _dispatch(tool_call, html, style_spec, sections, version_store)

    new_html = result["html"]
    tool_used = tool_call["name"]

    # Step 3: Self-check (skip for revert and summary - they don't modify HTML)
    check_result = {"passed": True, "issues": []}
    if tool_used not in ("revert", "get_page_summary"):
        check_result = self_check(html, new_html, user_message)

        # Retry once if self-check fails
        if not check_result["passed"] and MAX_RETRIES > 0:
            retry_instruction = (
                f"{user_message}\n\n"
                f"Previous attempt had issues: {', '.join(check_result['issues'])}. "
                f"Please fix these while applying the edit."
            )
            retry_messages = messages + [{"role": "user", "content": retry_instruction}]
            retry_response = complete(retry_messages, system=system, tools=TOOLS)
            retry_calls = retry_response.get("tool_calls", [])
            if retry_calls:
                retry_result = _dispatch(retry_calls[0], html, style_spec, sections, version_store)
                retry_check = self_check(html, retry_result["html"], user_message)
                if retry_check["passed"]:
                    new_html = retry_result["html"]
                    check_result = retry_check
                    result["message"] = retry_result["message"] + " (auto-corrected)"

    version_saved = tool_used not in ("revert", "get_page_summary")

    return {
        "html": new_html,
        "message": result["message"],
        "tool_used": tool_used,
        "self_check": check_result,
        "version_saved": version_saved,
    }


def _dispatch(tool_call: dict, html: str, style_spec: dict, sections: list, version_store: list) -> dict:
    name = tool_call["name"]
    args = tool_call["input"]

    if name == "edit_section":
        return edit_section(html, style_spec, sections, **args)
    elif name == "edit_global_style":
        return edit_global_style(html, style_spec, sections, **args)
    elif name == "regenerate_section":
        return regenerate_section(html, style_spec, sections, **args)
    elif name == "revert":
        return revert(html, style_spec, sections, version_store=version_store, **args)
    elif name == "get_page_summary":
        return get_page_summary(html, style_spec, sections)
    else:
        return {"html": html, "message": f"Unknown tool: {name}", "next_action": None}


def _build_system_prompt(sections: list[dict], style_spec: dict) -> str:
    section_list = "\n".join(
        f"  - {s['selector']} ({s['tag']}): {s['text_preview'][:80]}"
        for s in sections
    )
    return (
        "You are an intelligent HTML page editor. "
        "The user will give you natural language instructions to edit an HTML page.\n\n"
        "Use the available tools to fulfill the request. "
        "Pick the most targeted tool available - prefer edit_section over edit_global_style "
        "unless the change truly affects the whole page.\n\n"
        f"Page sections available:\n{section_list}\n\n"
        f"Page fonts: {', '.join(style_spec.get('fonts', []))}\n"
        f"Page colors: {', '.join(style_spec.get('colors', [])[:8])}\n\n"
        "When in doubt about which section to target, use get_page_summary first."
    )
