"""Backup of the corrupted `modules/ai_service.py` before cleanup.

This file preserves the original contents so maintainers can inspect
the corrupted/duplicated code if needed. It should NOT be imported.
"""

"""Compatibility shim for `modules.ai_service`.

This module intentionally re-exports key helpers from `modules.ai_service_new`.
Keep this file minimal to avoid duplication and maintenance drift.
"""

from modules.ai_service_new import (
    get_groq_client,
    call_chat_completion,
    call_json_completion,
)

__all__ = ["get_groq_client", "call_chat_completion", "call_json_completion"]


def call_json_completion(prompt: str, model: str, **kwargs) -> dict[str, Any]:
    """Convenience wrapper for JSON-oriented completions where response_format is json_object.

    Retries on transient failures with exponential backoff.
    """
    client = get_groq_client()
    if not client:
        return {"ok": False, "content": "", "error": "Missing GROQ_API_KEY", "rate_limited": False}

    # Retry with backoff
    attempts = int(kwargs.pop("attempts", 3))
    base_delay = float(kwargs.pop("base_delay", 0.5))
    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Return only valid JSON. No markdown or extra text."}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                **kwargs,
            )
            content = getattr(response.choices[0].message, "content", "") or ""
            return {"ok": True, "content": content, "error": "", "rate_limited": False}
        except Exception as exc:
            text = str(exc)
            rate_limited = "429" in text or "rate limit" in text.lower()
            _logger.warning("groq_json_call_failed", extra={"attempt": attempt, "error": text[:300], "rate_limited": rate_limited})
            if attempt == attempts or rate_limited:
                return {"ok": False, "content": "", "error": text, "rate_limited": rate_limited}
            delay = base_delay * (2 ** (attempt - 1))
            delay = delay + random.uniform(0, delay * 0.1)
            time.sleep(delay)
            return None
        _cached_client = Groq(api_key=api_key)
        _logger.info("groq_client_initialized")
        return _cached_client
    except Exception as exc:
        _logger.exception("groq_client_init_failed")
        return None


def call_chat_completion(messages: list[dict[str, str]], model: str, **kwargs) -> dict[str, Any]:
    """Call Groq chat completions with a cached client and retry/backoff logic.

    Returns a dict: {"ok": bool, "response": GroqResponse|None, "error": str}
    """
    client = get_groq_client()
    if not client:
        return {"ok": False, "response": None, "error": "Missing GROQ_API_KEY"}

    # Retry with exponential backoff on transient failures
    attempts = int(kwargs.pop("attempts", 3))
    base_delay = float(kwargs.pop("base_delay", 0.5))
    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(model=model, messages=messages, **kwargs)
            return {"ok": True, "response": response, "error": ""}
        except Exception as exc:
            text = str(exc)
            rate_limited = "429" in text or "rate limit" in text.lower()
            _logger.warning("groq_call_failed", extra={"attempt": attempt, "error": text[:300], "rate_limited": rate_limited})
            if attempt == attempts or rate_limited:
                return {"ok": False, "response": None, "error": text, "rate_limited": rate_limited}
            # backoff with jitter
            delay = base_delay * (2 ** (attempt - 1))
            delay = delay + random.uniform(0, delay * 0.1)
            time.sleep(delay)


def call_json_completion(prompt: str, model: str, **kwargs) -> dict[str, Any]:
    """Convenience wrapper for JSON-oriented completions where response_format is json_object.

    Retries on transient failures with exponential backoff.
    """
    client = get_groq_client()
    if not client:
        return {"ok": False, "content": "", "error": "Missing GROQ_API_KEY", "rate_limited": False}

    # Retry with backoff
    attempts = int(kwargs.pop("attempts", 3))
    base_delay = float(kwargs.pop("base_delay", 0.5))
    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Return only valid JSON. No markdown or extra text."}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                **kwargs,
            )
            content = getattr(response.choices[0].message, "content", "") or ""
            return {"ok": True, "content": content, "error": "", "rate_limited": False}
        except Exception as exc:
            text = str(exc)
            rate_limited = "429" in text or "rate limit" in text.lower()
            _logger.warning("groq_json_call_failed", extra={"attempt": attempt, "error": text[:300], "rate_limited": rate_limited})
            if attempt == attempts or rate_limited:
                return {"ok": False, "content": "", "error": text, "rate_limited": rate_limited}
            delay = base_delay * (2 ** (attempt - 1))
            delay = delay + random.uniform(0, delay * 0.1)
            time.sleep(delay)
