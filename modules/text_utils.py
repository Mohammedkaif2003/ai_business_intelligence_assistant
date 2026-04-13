import re
from html import unescape


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = unescape(str(text))
    text = re.sub(r"</?[^>]+>", "", text)
    text = re.sub(r"<div\s+style=\"?", "", text, flags=re.IGNORECASE)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in {'">', '"}', "</div>", "<div style=\"", "<div style="}:
            continue
        if stripped.lower().startswith("div style="):
            continue
        if re.match(r"^(background|padding|border-radius|max-width|font-size|line-height|color|border)\s*:", stripped):
            continue
        lines.append(stripped)
    text = "\n".join(lines)
    text = re.sub(r"\n\s*\n", "\n\n", text)

    return text.strip()


def structure_response(text: str) -> dict:
    sections = {
        "EXECUTIVE INSIGHT": [],
        "KEY FINDINGS": [],
        "BUSINESS IMPACT": [],
        "LIMITATIONS": [],
        "RECOMMENDATIONS": [],
    }

    alias_map = {
        "EXECUTIVE SUMMARY": "EXECUTIVE INSIGHT",
        "SUMMARY": "EXECUTIVE INSIGHT",
        "KEY TAKEAWAYS": "KEY FINDINGS",
        "FINDINGS": "KEY FINDINGS",
        "IMPACT": "BUSINESS IMPACT",
        "BUSINESS OUTCOME": "BUSINESS IMPACT",
        "RECOMMENDED NEXT STEPS": "RECOMMENDATIONS",
        "NEXT STEPS": "RECOMMENDATIONS",
        "ACTIONS": "RECOMMENDATIONS",
    }

    current_section = None

    for line in text.split("\n"):
        line = line.strip()

        if not line:
            continue

        upper = re.sub(r"\s+", " ", line.upper().replace(":", "")).strip()

        mapped = alias_map.get(upper, upper)
        if mapped in sections:
            current_section = mapped
            continue

        if current_section:
            bullet_text = re.sub(r"^[-*•]\s*", "", line).strip()
            bullet_text = re.sub(r"^\d+[\.)]\s*", "", bullet_text).strip()
            if bullet_text and bullet_text != line:
                sections[current_section].append(bullet_text)

    return sections
