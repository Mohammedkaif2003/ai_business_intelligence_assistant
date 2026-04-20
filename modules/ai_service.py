"""Compatibility shim for `modules.ai_service`.

This module provides a minimal, stable shim that re-exports the
public helpers from `modules.ai_service_new`. Keeping this file small
avoids duplication and prevents accidental imports of corrupted code.
"""

from modules.ai_service_new import (
    get_groq_client,
    call_chat_completion,
    call_json_completion,
)

__all__ = ["get_groq_client", "call_chat_completion", "call_json_completion"]
