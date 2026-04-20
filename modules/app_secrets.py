import os
from pathlib import Path

import streamlit as st
import logging


def _read_project_env_value(name: str):
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return None

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() != name:
                continue
            cleaned = str(value).strip().strip('"').strip("'")
            return cleaned if cleaned else None
    except Exception as exc:
        logging.getLogger(__name__).debug("read_project_env_failed", exc_info=True)
        return None

    return None


def get_secret(name: str, default=None):
    # Local development should prefer the project .env file so a stale shell
    # variable does not override an updated key.
    value = _read_project_env_value(name)
    if value is not None:
        return value

    # Streamlit Cloud / deployment secrets are the next source.
    # They are used when no project .env entry exists.
    try:
        secret_value = st.secrets.get(name, default)
        if secret_value is not None:
            cleaned = str(secret_value).strip().strip('"').strip("'")
            if cleaned:
                return cleaned
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("load_secret_failed", exc_info=True)

    # Final fallback for explicit shell environment variables.
    value = os.getenv(name)
    if value is not None:
        cleaned = str(value).strip().strip('"').strip("'")
        if cleaned:
            return cleaned

    return default
