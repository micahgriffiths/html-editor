"""
Lightweight self-check pass after each edit.
Validates structure, not content - keeps it cheap (small prompt).
"""
from bs4 import BeautifulSoup


def self_check(original_html: str, new_html: str, instruction: str) -> dict:
    """
    Structural validation - no LLM needed for basic checks.
    Returns { "passed": bool, "issues": list[str] }
    """
    issues = []

    # 1. Parse check - is it valid HTML?
    try:
        new_soup = BeautifulSoup(new_html, "lxml")
    except Exception as e:
        return {"passed": False, "issues": [f"HTML parse error: {e}"]}

    orig_soup = BeautifulSoup(original_html, "lxml")

    # 2. Check page didn't get gutted - tag count shouldn't drop by more than 50%
    orig_tags = len(orig_soup.find_all())
    new_tags = len(new_soup.find_all())
    if orig_tags > 10 and new_tags < orig_tags * 0.5:
        issues.append(f"Tag count dropped significantly: {orig_tags} → {new_tags}")

    # 3. Check <head> is still present
    if orig_soup.find("head") and not new_soup.find("head"):
        issues.append("Missing <head> element")

    # 4. Check <body> is still present
    if orig_soup.find("body") and not new_soup.find("body"):
        issues.append("Missing <body> element")

    # 5. Check that <style> blocks weren't accidentally dropped
    orig_styles = len(orig_soup.find_all("style"))
    new_styles = len(new_soup.find_all("style"))
    if orig_styles > 0 and new_styles == 0:
        issues.append("All <style> blocks were removed")

    return {"passed": len(issues) == 0, "issues": issues}