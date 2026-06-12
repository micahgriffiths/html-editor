"""
regenerate_page: full-page reconceptualisation using a plan→map→reduce pipeline.

Steps:
  1. Summarise  — get_page_summary gives the planner grounding in existing structure
  2. Plan       — one LLM call produces a structured design brief: a shared <head>
                  block plus an ordered list of section generation instructions
  3. Map        — one LLM call per section, fired in parallel, each receiving the
                  shared brief and its own section instruction
  4. Reduce     — stitch <head> + ordered section HTMLs into a valid full page
"""

import json
import concurrent.futures
from providers.llm import complete
from tools.implementations import get_page_summary

# Max parallel section generation calls. Keep low enough to avoid rate limits.
_MAX_WORKERS = 4


def regenerate_page(
    html: str,
    style_spec: dict,
    sections: list[dict],
    instruction: str,
) -> dict:
    # ------------------------------------------------------------------
    # Step 1 — Summarise: cheap structured context for the planner
    # ------------------------------------------------------------------
    summary = get_page_summary(html, style_spec, sections)["message"]

    # ------------------------------------------------------------------
    # Step 2 — Plan: design brief + per-section instructions + <head>
    # ------------------------------------------------------------------
    plan = _plan(summary, style_spec, instruction)
    if plan is None:
        return {
            "html": html,
            "message": "Planning step failed — page unchanged.",
            "next_action": None,
        }

    head_html: str = plan["head"]
    section_plans: list[dict] = plan["sections"]  # [{id, tag, instruction}, ...]
    brief: str = plan["brief"]

    # ------------------------------------------------------------------
    # Step 3 — Map: generate each section in parallel
    # ------------------------------------------------------------------
    generated_sections = _map_sections(section_plans, brief, head_html)

    # ------------------------------------------------------------------
    # Step 4 — Reduce: assemble into a valid HTML document
    # ------------------------------------------------------------------
    body_html = "\n".join(generated_sections)
    new_html = f"""<!DOCTYPE html>
<html lang="en">
{head_html}
<body>
{body_html}
</body>
</html>"""

    section_names = ", ".join(s["id"] for s in section_plans)
    return {
        "html": new_html,
        "message": (
            f"Regenerated full page ({len(section_plans)} sections: {section_names}). "
            f"Brief: {brief[:120]}{'...' if len(brief) > 120 else ''}"
        ),
        "next_action": None,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _plan(summary: str, style_spec: dict, instruction: str) -> dict | None:
    """
    Ask the planner LLM to produce a structured JSON design brief.
    Returns a dict with keys: brief, head, sections.
    """
    system = (
        "You are a senior web designer and HTML architect. "
        "Given a description of an existing page and a reconceptualisation instruction, "
        "produce a structured JSON plan for a full page rewrite.\n\n"
        "Return ONLY a valid JSON object with this exact shape:\n"
        "{\n"
        '  "brief": "2-3 sentence summary of the new design direction",\n'
        '  "head": "<head> block HTML including all styles, fonts, CSS variables — '
        'complete and self-contained",\n'
        '  "sections": [\n'
        '    { "id": "hero", "tag": "section", "instruction": "..." },\n'
        '    { "id": "features", "tag": "section", "instruction": "..." }\n'
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- The head block must define all CSS variables, font imports, and base styles "
        "so that sections can reference them without repeating declarations.\n"
        "- Each section instruction must be self-contained: describe content, tone, "
        "layout, and any specific elements needed. Do not assume the section generator "
        "has access to other sections.\n"
        "- Include 3-7 sections. Match the structure to the instruction, not slavishly "
        "to the existing page.\n"
        "- No markdown fences, no explanation outside the JSON object."
    )

    prompt = (
        f"Existing page summary:\n{summary}\n\n"
        f"Current style spec:\n"
        f"  Colors: {', '.join(style_spec.get('colors', []))}\n"
        f"  Fonts: {', '.join(style_spec.get('fonts', []))}\n\n"
        f"Reconceptualisation instruction: {instruction}\n\n"
        "Produce the JSON plan."
    )

    response = complete([{"role": "user", "content": prompt}], system=system)
    text = response.get("text", "").strip()

    # Strip accidental markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        plan = json.loads(text)
        assert "head" in plan and "sections" in plan and "brief" in plan
        assert isinstance(plan["sections"], list) and len(plan["sections"]) > 0
        return plan
    except (json.JSONDecodeError, AssertionError):
        return None


def _generate_section(section_plan: dict, brief: str, head_html: str) -> str:
    """Generate HTML for a single section given the shared brief and head context."""
    system = (
        "You are an expert HTML developer. "
        "Generate a single HTML section based on the design brief and instruction provided. "
        "Return ONLY the HTML for this section — no DOCTYPE, no <html>, no <head>, no <body> wrapper. "
        "CSS variables and fonts are already declared in the <head>; reference them freely. "
        "No markdown fences, no explanation."
    )

    prompt = (
        f"Design brief: {brief}\n\n"
        f"Head block (for reference — do not repeat these declarations):\n{head_html}\n\n"
        f"Section to generate:\n"
        f"  id: {section_plan['id']}\n"
        f"  tag: {section_plan['tag']}\n"
        f"  instruction: {section_plan['instruction']}\n\n"
        f"Generate the <{section_plan['tag']}> HTML now."
    )

    response = complete([{"role": "user", "content": prompt}], system=system)
    text = response.get("text", "").strip()

    # Strip accidental markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    return text if text else f"<{section_plan['tag']} id=\"{section_plan['id']}\"></{section_plan['tag']}>"


def _map_sections(section_plans: list[dict], brief: str, head_html: str) -> list[str]:
    """
    Fire one _generate_section call per section plan in parallel.
    Results are returned in the original plan order regardless of completion order.
    """
    results: list[str] = [""] * len(section_plans)

    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_to_index = {
            executor.submit(_generate_section, plan, brief, head_html): i
            for i, plan in enumerate(section_plans)
        }
        for future in concurrent.futures.as_completed(future_to_index):
            i = future_to_index[future]
            try:
                results[i] = future.result()
            except Exception as e:
                # Degrade gracefully: emit an empty placeholder so the page
                # still assembles; the user can re-edit that section.
                plan = section_plans[i]
                results[i] = (
                    f"<{plan['tag']} id=\"{plan['id']}\" "
                    f"style=\"padding:2rem;color:red\">"
                    f"Section generation failed: {e}"
                    f"</{plan['tag']}>"
                )

    return results
