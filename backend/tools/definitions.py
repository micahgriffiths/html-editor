"""
Tool schemas passed to the LLM for structured tool selection.
Each tool maps to an implementation in the tools/ directory.
"""

TOOLS = [
    {
        "type": "function",
        "name": "edit_section",
        "description": (
            "Apply a targeted natural-language edit to a specific section of the page "
            "(e.g. 'shorten the footer', 'make the hero heading larger'). "
            "Use when the instruction clearly targets one part of the page."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector of the section to edit (from the section map).",
                },
                "instruction": {
                    "type": "string",
                    "description": "The natural language edit instruction to apply to this section.",
                },
            },
            "required": ["selector", "instruction"],
        },
    },
    {
        "type": "function",
        "name": "edit_global_style",
        "description": (
            "Modify a global style property that affects the whole page "
            "(e.g. 'change background to light blue', 'switch to a serif font'). "
            "Updates the <style> block and style spec."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "The natural language style change to apply.",
                },
            },
            "required": ["instruction"],
        },
    },
    {
        "type": "function",
        "name": "regenerate_section",
        "description": (
            "Fully rewrite a section from scratch while preserving brand/style. "
            "Use when the section needs heavy restructuring, not just a tweak."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector of the section to regenerate.",
                },
                "instruction": {
                    "type": "string",
                    "description": "What the regenerated section should achieve.",
                },
            },
            "required": ["selector", "instruction"],
        },
    },
    {
        "type": "function",
        "name": "revert",
        "description": "Revert the page to a previously saved version.",
        "parameters": {
            "type": "object",
            "properties": {
                "version_id": {
                    "type": "integer",
                    "description": "The version number to revert to (0 = original).",
                },
            },
            "required": ["version_id"],
        },
    },
    {
        "type": "function",
        "name": "get_page_summary",
        "description": (
            "Get a high-level structural summary of the page. "
            "Use when the instruction is ambiguous or cross-cutting and you need "
            "to understand the page structure before deciding what to edit."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "regenerate_page",
        "description": (
            "Fully reconceptualises and rewrites the entire page from scratch using a "
            "plan-then-generate pipeline. Use this when the instruction implies a change "
            "in strategic direction, audience, tone, or overall purpose — for example, "
            "'refocus the page on enterprise customers' or 'make this feel more like a "
            "research lab than a startup'. "
            "Do NOT use for targeted visual or content tweaks (font changes, colour "
            "updates, copy edits, layout adjustments within a section) — prefer "
            "edit_section or edit_global_style for those."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": (
                        "The high-level reconceptualisation goal. Be specific about the "
                        "new direction, audience, or purpose. Example: 'Reframe this page "
                        "to emphasise the hard-science credibility of the team rather than "
                        "the commercial product.'"
                    ),
                }
            },
            "required": ["instruction"],
        },
    }
]