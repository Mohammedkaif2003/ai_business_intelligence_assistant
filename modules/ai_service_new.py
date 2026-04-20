from __future__ import annotations

"""Groq client helper used across modules (replacement shim).

This module mirrors the expected `modules.ai_service` API but is
implemented cleanly to avoid the corrupted file issues.
"""
import time
import random
from typing import Any
import importlib
import warnings

from modules.app_secrets import get_secret
from modules.app_logging import get_logger

try:
    from groq import Groq
except Exception as exc:
    Groq = None  # type: ignore
# Prefer the newer `google.genai` package. Do not import the deprecated
# `google.generativeai` at module import time to avoid its FutureWarning.
genai = None
try:
    genai = importlib.import_module("google.genai")
except Exception as exc:
    genai = None
try:
    from openai import OpenAI as OpenAIClient
    _openai = None
except Exception as exc:
    OpenAIClient = None
    try:
        import openai as _openai
    except Exception as exc:
        _openai = None

_cached_client: Any | None = None
_cached_gemini: Any | None = None
_cached_openai: Any | None = None
_logger = get_logger("ai_service_new")


def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text


def get_groq_client() -> Groq | None:
    global _cached_client
    if _cached_client is not None:
        return _cached_client

    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        if Groq is None:
            _logger.warning("groq_sdk_missing")
            return None
        _cached_client = Groq(api_key=api_key)
        _logger.info("groq_client_initialized")
        return _cached_client
    except Exception as exc:
        _logger.exception("groq_client_init_failed")
        return None


def get_gemini_client() -> Any | None:
    """Return a configured Gemini (Google Generative) module or None."""
    global _cached_gemini
    if _cached_gemini is not None:
        return _cached_gemini

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        return None

    # If the preferred `google.genai` module wasn't available at import time,
    # attempt a lazy import of the older `google.generativeai` package while
    # suppressing its deprecation FutureWarning. This keeps tests and runtime
    # free of the noisy warning unless the deprecated package is actually used.
    global genai
    if genai is None:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning)
                genai = importlib.import_module("google.generativeai")
        except Exception as exc:
            genai = None
            _logger.debug("lazy_import_google_generativeai_failed", exc_info=True)

    if genai is None:
        _logger.warning("gemini_sdk_missing")
        return None

    try:
        # Prefer module-level configure (older/newer variants)
        if hasattr(genai, "configure") and callable(getattr(genai, "configure")):
            genai.configure(api_key=api_key)
            _cached_gemini = genai
        elif hasattr(genai, "Client") and callable(getattr(genai, "Client")):
            # google.genai provides a Client class in newer SDK
            _cached_gemini = genai.Client(api_key=api_key)
        else:
            # Unknown API surface; return the module and rely on runtime checks
            _cached_gemini = genai

        _logger.info("gemini_client_initialized")
        return _cached_gemini
    except Exception as exc:
        _logger.exception("gemini_client_init_failed")
        return None


def get_openai_client() -> Any | None:
    """Return configured OpenAI module or None."""
    global _cached_openai
    if _cached_openai is not None:
        return _cached_openai

    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        return None

    # Accept either the new `OpenAI` class import or the legacy `openai` module.
    if OpenAIClient is None and _openai is None:
        _logger.warning("openai_sdk_missing")
        return None

    try:
        # Prefer the newer OpenAI client class when available
        if 'OpenAIClient' in globals() and OpenAIClient is not None:
            _cached_openai = OpenAIClient(api_key=api_key)
        else:
            _openai.api_key = api_key
            _cached_openai = _openai
        _logger.info("openai_client_initialized")
        return _cached_openai
    except Exception as exc:
        _logger.exception("openai_client_init_failed")
        return None


def call_chat_completion(messages: list[dict[str, str]], model: str, **kwargs) -> dict[str, Any]:
    client = get_groq_client()
    if not client:
        # Try Gemini then OpenAI as fallbacks
        gemini = get_gemini_client()
        if gemini is None:
            openai_client = get_openai_client()
            if openai_client is None:
                return {"ok": False, "response": None, "error": "Missing GROQ_API_KEY, GEMINI_API_KEY, and OPENAI_API_KEY"}
        else:
            # let gemini be used below if available
            client = None

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
                # Attempt Gemini as a fallback when Groq fails or is rate-limited
                gemini = get_gemini_client()
                if gemini is not None:
                                    try:
                                        # Try multiple possible Gemini SDK call patterns for compatibility
                                        resp = None
                                        # module-level interface: genai.chat.create(...)
                                        if hasattr(gemini, "chat") and callable(getattr(gemini.chat, "create", None)):
                                            resp = gemini.chat.create(messages=[m for m in messages], model=model)
                                        # client instance interface: client.chat.create(...)
                                        elif hasattr(gemini, "chat") and callable(getattr(gemini.chat, "create", None)):
                                            resp = gemini.chat.create(messages=[m for m in messages], model=model)
                                        # older generativeai: genai.chat.completions.create(...)
                                        elif hasattr(gemini, "chat") and hasattr(gemini.chat, "completions") and callable(getattr(gemini.chat.completions, "create", None)):
                                            resp = gemini.chat.completions.create(model=model, messages=messages)
                                        if resp is not None:
                                            return {"ok": True, "response": resp, "error": ""}
                                    except Exception as gexc:
                                        _logger.warning("gemini_call_failed", extra={"error": str(gexc)[:300]})

                # Attempt OpenAI as a tertiary fallback
                openai_client = get_openai_client()
                if openai_client is not None:
                    try:
                        # Map messages to OpenAI ChatCompletion format
                        o_messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
                        # Prefer new client instance API: client.chat.completions.create(...)
                        if hasattr(openai_client, "chat") and hasattr(openai_client.chat, "completions"):
                            resp = openai_client.chat.completions.create(model=model, messages=o_messages, **kwargs)
                        elif hasattr(openai_client, "ChatCompletion") and callable(getattr(openai_client, "ChatCompletion", None)):
                            resp = openai_client.ChatCompletion.create(model=model, messages=o_messages, **kwargs)
                        else:
                            resp = None

                        if resp is not None:
                            return {"ok": True, "response": resp, "error": ""}
                    except Exception as oexc:
                        _logger.warning("openai_call_failed", extra={"error": str(oexc)[:300]})

                return {"ok": False, "response": None, "error": text, "rate_limited": rate_limited}
            delay = base_delay * (2 ** (attempt - 1))
            delay = delay + random.uniform(0, delay * 0.1)
            time.sleep(delay)


def call_json_completion(prompt: str, model: str, **kwargs) -> dict[str, Any]:
    client = get_groq_client()
    # Primary: Groq; Secondary: Gemini; Tertiary: OpenAI
    if not client:
        _logger.info("groq_client_missing_trying_fallbacks")
        gemini = get_gemini_client()
        openai_client = get_openai_client()
        if gemini is None and openai_client is None:
            return {"ok": False, "content": "", "error": "Missing GROQ_API_KEY, GEMINI_API_KEY, and OPENAI_API_KEY", "rate_limited": False}

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
                # Try Gemini
                gemini = get_gemini_client()
                if gemini is not None:
                        try:
                            # Try multiple call styles for different genai SDKs
                            resp = None
                            messages_payload = [{"role": "system", "content": "Return only valid JSON. No markdown or extra text."}, {"role": "user", "content": prompt}]
                            if hasattr(gemini, "chat") and callable(getattr(gemini.chat, "create", None)):
                                resp = gemini.chat.create(messages=messages_payload, model=model)
                            if hasattr(gemini, "chat") and hasattr(gemini.chat, "completions") and callable(getattr(gemini.chat.completions, "create", None)):
                                resp = gemini.chat.completions.create(model=model, messages=messages_payload)

                            if resp is not None:
                                content = ""
                                try:
                                    content = getattr(resp, "last", None) or getattr(resp, "content", None) or str(resp)
                                except Exception as exc:
                                    _logger.debug("extracting_gemini_content_failed", exc_info=True)
                                    content = str(resp)
                                return {"ok": True, "content": content, "error": "", "rate_limited": False}
                        except Exception as gexc:
                            _logger.warning("gemini_json_call_failed", extra={"error": str(gexc)[:300]})

                # Try OpenAI
                openai_client = get_openai_client()
                if openai_client is not None:
                    try:
                        # Prefer new client instance API first
                        messages_payload = [{"role": "system", "content": "Return only valid JSON. No markdown or extra text."}, {"role": "user", "content": prompt}]
                        o_resp = None
                        if hasattr(openai_client, "chat") and hasattr(openai_client.chat, "completions"):
                            o_resp = openai_client.chat.completions.create(model=model, messages=messages_payload, **kwargs)
                        elif hasattr(openai_client, "ChatCompletion") and callable(getattr(openai_client, "ChatCompletion", None)):
                            o_resp = openai_client.ChatCompletion.create(model=model, messages=messages_payload, **kwargs)

                        content = ""
                        if o_resp is not None:
                            try:
                                content = o_resp.choices[0].message.get("content") if hasattr(o_resp.choices[0], 'message') else getattr(o_resp.choices[0], 'text', '')
                            except Exception as exc:
                                try:
                                    content = getattr(o_resp.choices[0], 'text', '')
                                except Exception as exc:
                                    _logger.debug("extracting_openai_content_failed", exc_info=True)
                                    content = str(o_resp)
                        return {"ok": True, "content": content or "", "error": "", "rate_limited": False}
                    except Exception as oexc:
                        _logger.warning("openai_json_call_failed", extra={"error": str(oexc)[:300]})

                return {"ok": False, "content": "", "error": text, "rate_limited": rate_limited}
            delay = base_delay * (2 ** (attempt - 1))
            delay = delay + random.uniform(0, delay * 0.1)
            time.sleep(delay)
