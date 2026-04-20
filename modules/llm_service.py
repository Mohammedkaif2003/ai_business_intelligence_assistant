import json
from typing import Any

from modules.ai_service_new import call_json_completion

from modules.app_secrets import get_secret

GROQ_MODEL_NAME = "llama-3.3-70b-versatile"


def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text


def call_groq_json(prompt: str, logger=None) -> dict[str, Any]:
    """
    Single Groq call entrypoint with retry/backoff for rate limits.

    Returns a dict with keys:
      - ok: bool
      - content: str (when ok)
      - error: str (when not ok)
      - rate_limited: bool
    """
    # Delegate to ai_service which caches/creates the client.
    try:
        result = call_json_completion(prompt, model=GROQ_MODEL_NAME, temperature=0.2, max_tokens=360)
        return result
    except Exception as exc:
        rate_limited = _is_rate_limit_error(exc)
        if logger:
            logger.warning(
                "ai_json_call_failed",
                extra={"provider": "fallback", "rate_limited": rate_limited, "error": str(exc)[:300]},
            )
        return {"ok": False, "content": "", "error": str(exc), "rate_limited": rate_limited}



def safe_json_loads(raw_text: str) -> dict[str, Any]:
    """Parse JSON safely and tolerate accidental fenced output."""
    import re

    text = (raw_text or "").strip()
    if not text:
        return {}

    # Remove surrounding triple backticks or markdown fences
    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]

    # If the text is pure JSON, parse directly
    try:
        return json.loads(text)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("llm_service_init_failed", exc_info=True)

    # Attempt to extract the first JSON object or array from noisy text
    # Find the first { or [ and then find the matching closing bracket.
    match = re.search(r"[\{\[]", text)
    if not match:
        # No JSON found — as a last resort, try to parse laxly by finding a substring
        # that looks like JSON between the first and last braces.
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidate = text[first : last + 1]
            try:
                return json.loads(candidate)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug("safe_json_candidate_parse_failed", exc_info=True)
                return {}
        return {}

    start = match.start()
    opener = text[start]
    closer = "]" if opener == "[" else "}"

    depth = 0
    end_index = None
    for idx in range(start, len(text)):
        ch = text[idx]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                end_index = idx
                break

    if end_index is None:
        # Fallback: try first/last braces
        first = text.find(opener)
        last = text.rfind(closer)
        if first != -1 and last != -1 and last > first:
            candidate = text[first : last + 1]
            try:
                return json.loads(candidate)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug("safe_json_candidate_parse_failed", exc_info=True)
                return {}
        return {}

    candidate = text[start : end_index + 1]
    try:
        return json.loads(candidate)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("safe_json_candidate_full_parse_failed", exc_info=True)
        return {}
