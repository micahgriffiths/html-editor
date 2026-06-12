"""
Agent router: classifies user intent → selects tool(s) → executes → self-checks.
Supports multiple tool calls per turn, threading HTML forward between each step.
"""

from providers.llm import complete
from tools.definitions import TOOLS
from tools.implementations import (
    edit_section,
    edit_global_style,
    regenerate_section,
    revert,
    get_page_summary,
)
from tools.regenerate_page import regenerate_page
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
        "tool_used": str,          # comma-separated list if multiple
        "self_check": dict,        # result of last check
        "version_saved": bool,
      }
    """
    system = _build_system_prompt(sections, style_spec, version_store)
    messages = chat_history + [{"role": "user", "content": user_message}]

    # Step 1: Let the model pick tool(s)
    response = complete(messages, system=system, tools=TOOLS)
    tool_calls = response.get("tool_calls", [])

    # No tool called — return text response directly
    if not tool_calls:
        return {
            "html": html,
            "message": response.get("text", "I didn't know how to handle that."),
            "tool_used": "none",
            "self_check": {"passed": True, "issues": []},
            "version_saved": False,
        }

    # Step 2: Execute all tool calls in order, threading HTML forward between them
    new_html = html
    messages_log = []
    check_result = {"passed": True, "issues": []}
    any_version_saved = False

    reverted_to = None  # tracks the version_id if a revert tool ran

    for tool_call in tool_calls:
        tool_used = tool_call["name"]
        result = _dispatch(tool_call, new_html, style_spec, sections, version_store)
        messages_log.append(f"[{tool_used}] {result['message']}")

        # Self-check each HTML-modifying step
        if tool_used not in ("revert", "get_page_summary"):
            step_check = self_check(new_html, result["html"], user_message)

            # Retry once if self-check fails
            if not step_check["passed"] and MAX_RETRIES > 0:
                retry_instruction = (
                    f"{user_message}\n\n"
                    f"Previous attempt had issues: {', '.join(step_check['issues'])}. "
                    f"Please fix these while applying the edit."
                )
                retry_response = complete(
                    messages + [{"role": "user", "content": retry_instruction}],
                    system=system,
                    tools=TOOLS,
                )
                retry_calls = retry_response.get("tool_calls", [])
                if retry_calls:
                    retry_result = _dispatch(retry_calls[0], new_html, style_spec, sections, version_store)
                    retry_check = self_check(new_html, retry_result["html"], user_message)
                    if retry_check["passed"]:
                        result = retry_result
                        step_check = retry_check
                        messages_log[-1] += " (auto-corrected)"

            check_result = step_check
            any_version_saved = True
        elif tool_used == "revert":
            # Capture the version_id the revert tool resolved to so the server
            # can truncate its version list and set a clean head.
            reverted_to = result.get("reverted_to")

        new_html = result["html"]

    return {
        "html": new_html,
        "message": "\n".join(messages_log),
        "tool_used": ", ".join(tc["name"] for tc in tool_calls),
        "self_check": check_result,
        "version_saved": any_version_saved,
        "reverted_to": reverted_to,
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
    elif name == "regenerate_page":
        return regenerate_page(html, style_spec, sections, **args)
    else:
        return {"html": html, "message": f"Unknown tool: {name}", "next_action": None}


def _build_system_prompt(sections: list[dict], style_spec: dict, version_store: list[dict]) -> str:
    section_list = "\n".join(
        f"  - {s['selector']} ({s['tag']}): {s['text_preview'][:80]}"
        for s in sections
    )
    version_list = "\n".join(
        f"  - V{v['id']}: {v['description']}"
        for v in version_store
    )
    return (
        "You are an intelligent HTML page editor. "
        "The user will give you natural language instructions to edit an HTML page.\n\n"
        "Use the available tools to fulfill the request. "
        "You may call multiple tools in a single turn if the instruction requires changes "
        "to more than one section — for example, 'shorten the footer and make the hero heading larger' "
        "should call edit_section twice.\n\n"
        "Pick the most targeted tool available - prefer edit_section over edit_global_style "
        "unless the change truly affects the whole page.\n\n"
        f"Page sections available:\n{section_list}\n\n"
        f"Page fonts: {', '.join(style_spec.get('fonts', []))}\n"
        f"Page colors: {', '.join(style_spec.get('colors', [])[:8])}\n\n"
        f"Version history (use exact IDs when calling the revert tool):\n{version_list}\n\n"
        "When in doubt about which section to target, use get_page_summary first.\n\n"
        "Tool selection guidance:\n"
        "  - edit_section / edit_global_style: targeted visual or content tweaks\n"
        "  - regenerate_section: rewrite one section from scratch\n"
        "  - regenerate_page: full reconceptualisation only - change of direction,\n"
        "    audience, or purpose. Do not use for tweaks, even sweeping ones."
    )