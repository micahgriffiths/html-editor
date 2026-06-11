"""
Parses HTML into a section map without LLM involvement.
Identifies top-level semantic chunks with selectors and size estimates.
"""
from bs4 import BeautifulSoup, Tag


# Tags we treat as top-level sections
SECTION_TAGS = {"header", "footer", "main", "nav", "section", "article", "aside"}

# Rough token estimate: 1 token ≈ 4 chars
CHARS_PER_TOKEN = 4


def parse_sections(html: str) -> list[dict]:
    """
    Returns a list of sections, each with:
      - selector: CSS selector to find this element
      - tag: element tag name
      - id / classes: for selector construction
      - char_count / token_estimate
      - text_preview: first 120 chars of text content
      - html: the raw HTML of this section
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body") or soup

    sections = []
    seen_selectors = set()

    for el in body.find_all(SECTION_TAGS, recursive=False):
        section = _describe_element(el, seen_selectors)
        sections.append(section)

    # Fallback: if no semantic tags found, treat direct children of body as sections
    if not sections:
        for el in body.children:
            if isinstance(el, Tag):
                section = _describe_element(el, seen_selectors)
                sections.append(section)

    return sections


def _describe_element(el: Tag, seen: set) -> dict:
    selector = _build_selector(el, seen)
    seen.add(selector)

    raw_html = str(el)
    text = el.get_text(separator=" ", strip=True)

    return {
        "selector": selector,
        "tag": el.name,
        "id": el.get("id", ""),
        "classes": el.get("class", []),
        "char_count": len(raw_html),
        "token_estimate": len(raw_html) // CHARS_PER_TOKEN,
        "text_preview": text[:120],
        "html": raw_html,
    }


def _build_selector(el: Tag, seen: set) -> str:
    """Build a reasonably unique CSS selector for this element."""
    if el.get("id"):
        return f"#{el['id']}"

    classes = el.get("class", [])
    if classes:
        base = f"{el.name}.{'.'.join(classes[:2])}"
    else:
        base = el.name

    # Deduplicate with an index suffix if needed
    candidate = base
    i = 2
    while candidate in seen:
        candidate = f"{base}:nth({i})"
        i += 1

    return candidate


def get_section_by_selector(html: str, selector: str) -> str | None:
    """Extract the raw HTML of a section by its selector."""
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one(selector)
    return str(el) if el else None


def replace_section(html: str, selector: str, new_section_html: str) -> str:
    """Replace a section in the full HTML with new content."""
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one(selector)
    if not el:
        return html  # selector not found, return unchanged

    new_el = BeautifulSoup(new_section_html, "lxml").find()
    if new_el:
        el.replace_with(new_el)

    return str(soup)