"""
Extracts a style spec from raw HTML without LLM involvement.
Pulls CSS custom properties, colors, fonts, and class patterns.
"""
import re
import tinycss2
from bs4 import BeautifulSoup


def extract_style_spec(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    raw_css = _collect_css(soup)
    tokens = tinycss2.parse_stylesheet(raw_css, skip_whitespace=True, skip_comments=True)

    return {
        "custom_properties": _extract_custom_properties(tokens),
        "colors": _extract_colors(raw_css),
        "fonts": _extract_fonts(raw_css, soup),
        "class_names": _extract_class_names(soup),
        "raw_css": raw_css,  # kept for full-page regeneration context
    }


def _collect_css(soup: BeautifulSoup) -> str:
    """Pull all inline <style> blocks into one string."""
    parts = []
    for tag in soup.find_all("style"):
        parts.append(tag.get_text())
    return "\n".join(parts)


def _extract_custom_properties(tokens) -> dict:
    """Extract CSS custom properties (--var: value)."""
    props = {}
    raw = " ".join(
        t.value if hasattr(t, "value") else ""
        for t in tokens
    )
    for match in re.finditer(r"(--[\w-]+)\s*:\s*([^;}{]+)", raw):
        props[match.group(1).strip()] = match.group(2).strip()
    return props


def _extract_colors(css: str) -> list[str]:
    """Pull unique color values: hex, rgb, rgba, hsl, named."""
    patterns = [
        r"#[0-9a-fA-F]{3,8}\b",
        r"rgba?\([^)]+\)",
        r"hsla?\([^)]+\)",
    ]
    colors = set()
    for pattern in patterns:
        for match in re.finditer(pattern, css):
            colors.add(match.group().strip())
    return sorted(colors)


def _extract_fonts(css: str, soup: BeautifulSoup) -> list[str]:
    """Pull font families from CSS and Google Fonts link tags."""
    fonts = set()

    # From CSS font-family declarations
    for match in re.finditer(r"font-family\s*:\s*([^;}{]+)", css):
        raw = match.group(1).strip().strip("'\"")
        for f in raw.split(","):
            f = f.strip().strip("'\"")
            if f and f.lower() not in ("inherit", "initial", "unset", "sans-serif", "serif", "monospace"):
                fonts.add(f)

    # From Google Fonts link hrefs
    for tag in soup.find_all("link", href=True):
        href = tag["href"]
        if "fonts.googleapis.com" in href:
            for match in re.finditer(r"family=([^&:]+)", href):
                fonts.add(match.group(1).replace("+", " "))

    return sorted(fonts)


def _extract_class_names(soup: BeautifulSoup) -> list[str]:
    """Collect unique class names used in the document."""
    classes = set()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            classes.add(cls)
    return sorted(classes)