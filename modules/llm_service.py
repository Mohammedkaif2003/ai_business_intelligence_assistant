import json
from typing import Any

from groq import Groq

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
    try:
        api_key = get_secret("GROQ_API_KEY")
        if not api_key:
            return {
                "ok": False,
                "content": "",
                "error": "Missing GROQ_API_KEY",
                "rate_limited": False,
            }

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON. No markdown or extra text.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=360,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        safe_json_loads(content)
        return {"ok": True, "content": content, "error": "", "rate_limited": False}
    except Exception as exc:
        rate_limited = _is_rate_limit_error(exc)
        if logger:
            logger.warning(
                "ai_json_call_failed",
                extra={"provider": "fallback", "rate_limited": rate_limited, "error": str(exc)[:300]},
            )
        return {
            "ok": False,
            "content": "",
            "error": str(exc),
            "rate_limited": rate_limited,
        }



def safe_json_loads(raw_text: str) -> dict[str, Any]:
    """Parse JSON safely and tolerate accidental fenced output."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return json.loads(text)
