"""
Tool implementations. Each function receives the current session state
and returns { "html": str, "message": str, "next_action": None }.
next_action is reserved for future chaining.
"""
import json
from providers.llm import complete
from ingestion.parser import get_section_by_selector, replace_section


def edit_section(html: str, style_spec: dict, sections: list[dict], selector: str, instruction: str) -> dict:
    section_html = get_section_by_selector(html, selector)
    if not section_html:
        return {"html": html, "message": f"Could not find section: {selector}", "next_action": None}

    system = _style_system_prompt(style_spec)
    prompt = (
        f"Edit the following HTML section according to this instruction: {instruction}\n\n"
        f"Return ONLY the updated HTML for this section, nothing else.\n\n"
        f"Current section HTML:\n{section_html}"
    )

    result = complete([{"role": "user", "content": prompt}], system=system)
    new_section_html = _extract_html(result.get("text", ""), section_html)
    new_html = replace_section(html, selector, new_section_html)

    return {"html": new_html, "message": f"Edited {selector}", "next_action": None}


def edit_global_style(html: str, style_spec: dict, sections: list[dict], instruction: str) -> dict:
    system = _style_system_prompt(style_spec)
    prompt = (
        f"Apply this global style change to the full HTML page: {instruction}\n\n"
        f"Return the complete updated HTML page, nothing else.\n\n"
        f"Current HTML:\n{html}"
    )

    result = complete([{"role": "user", "content": prompt}], system=system)
    new_html = _extract_html(result.get("text", ""), html)

    return {"html": new_html, "message": f"Applied global style change", "next_action": None}


def regenerate_section(html: str, style_spec: dict, sections: list[dict], selector: str, instruction: str) -> dict:
    section_html = get_section_by_selector(html, selector)
    if not section_html:
        return {"html": html, "message": f"Could not find section: {selector}", "next_action": None}

    system = _style_system_prompt(style_spec)
    prompt = (
        f"Regenerate this HTML section from scratch. Goal: {instruction}\n\n"
        f"Preserve the same tag structure and CSS classes where possible. "
        f"Match the style spec exactly. Return ONLY the new section HTML.\n\n"
        f"Original section for reference:\n{section_html}"
    )

    result = complete([{"role": "user", "content": prompt}], system=system)
    new_section_html = _extract_html(result.get("text", ""), section_html)
    new_html = replace_section(html, selector, new_section_html)

    return {"html": new_html, "message": f"Regenerated {selector}", "next_action": None}


def revert(html: str, style_spec: dict, sections: list[dict], version_id: int, version_store: list) -> dict:
    """Pure state operation - no LLM needed."""
    target = next((v for v in version_store if v["id"] == version_id), None)
    if not target:
        return {"html": html, "message": f"Version {version_id} not found", "next_action": None}

    return {
        "html": target["html"],
        "message": f"Reverted to version {version_id}: {target['description']}",
        "next_action": None,
        "reverted_to": version_id,
    }


def get_page_summary(html: str, style_spec: dict, sections: list[dict]) -> dict:
    """Returns a structural summary - used by the agent for context on ambiguous requests."""
    summary_parts = [f"Page has {len(sections)} top-level sections:"]
    for s in sections:
        summary_parts.append(
            f"  - {s['selector']} ({s['tag']}, ~{s['token_estimate']} tokens): {s['text_preview'][:80]}"
        )
    summary_parts.append(f"\nStyle spec colors: {', '.join(style_spec.get('colors', [])[:6])}")
    summary_parts.append(f"Fonts: {', '.join(style_spec.get('fonts', []))}")

    return {"html": html, "message": "\n".join(summary_parts), "next_action": None}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _style_system_prompt(style_spec: dict) -> str:
    return (
        "You are an HTML editor. You make precise, targeted edits to HTML.\n"
        "Always preserve the existing CSS classes, IDs, and style conventions.\n"
        f"Style spec for this page:\n"
        f"- Colors: {', '.join(style_spec.get('colors', []))}\n"
        f"- Fonts: {', '.join(style_spec.get('fonts', []))}\n"
        f"- Custom properties: {json.dumps(style_spec.get('custom_properties', {}))}\n"
        "Return only valid HTML. No markdown fences, no explanations."
    )


def _extract_html(text: str, fallback: str) -> str:
    """Strip any accidental markdown code fences."""
    if not text:
        return fallback
    text = text.strip()
    # Remove ```html ... ``` or ``` ... ```
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text if text else fallback