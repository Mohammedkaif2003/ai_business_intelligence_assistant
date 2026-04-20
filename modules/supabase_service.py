import base64
import json
import time
from typing import Any

import requests
import streamlit as st
import logging

from modules.app_secrets import get_secret
from modules.app_perf import record_timing


def _sanitize_json(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception as exc:
        logging.getLogger(__name__).debug("sanitize_json_failed", exc_info=True)
        return None


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    parts = str(token or "").strip().split(".")
    if len(parts) < 2:
        return None

    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)
    try:
        decoded = base64.urlsafe_b64decode((payload_segment + padding).encode("utf-8"))
        payload = json.loads(decoded.decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        logging.getLogger(__name__).debug("decode_jwt_failed", exc_info=True)
        return None


def _supabase_url() -> str:
    return str(get_secret("SUPABASE_URL", "") or "").strip().rstrip("/")


def _supabase_anon_key() -> str:
    return str(get_secret("SUPABASE_ANON_KEY", "") or "").strip()


def is_supabase_enabled() -> bool:
    return bool(_supabase_url() and _supabase_anon_key())


def sign_in_with_password(email: str, password: str) -> tuple[bool, str, dict[str, str] | None]:
    if not is_supabase_enabled():
        return False, "Supabase is not configured.", None

    normalized_email = str(email or "").strip()
    normalized_password = str(password or "")
    if not normalized_email or not normalized_password:
        return False, "Enter both email and password.", None

    try:
        response = requests.post(
            f"{_supabase_url()}/auth/v1/token?grant_type=password",
            headers={
                "apikey": _supabase_anon_key(),
                "Content-Type": "application/json",
            },
            json={"email": normalized_email, "password": normalized_password},
            timeout=15,
        )
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            message = str(payload.get("msg") or payload.get("error_description") or payload.get("error") or "Invalid credentials")
            return False, f"Sign in failed: {message}", None

        user = payload.get("user") or {}
        user_id = str(user.get("id") or "").strip()
        user_email = str(user.get("email") or normalized_email).strip()
        access_token = str(payload.get("access_token") or "").strip()

        if not user_id:
            return False, "Login failed. Please verify your credentials.", None

        return True, "Signed in successfully.", {
            "id": user_id,
            "email": user_email,
            "access_token": access_token,
        }
    except Exception as exc:
        return False, f"Sign in failed: {str(exc)}", None


def sign_up_with_password(email: str, password: str) -> tuple[bool, str]:
    if not is_supabase_enabled():
        return False, "Supabase is not configured."

    normalized_email = str(email or "").strip()
    normalized_password = str(password or "")
    if not normalized_email or not normalized_password:
        return False, "Enter email and password to create an account."
    if len(normalized_password) < 6:
        return False, "Password must be at least 6 characters."

    try:
        response = requests.post(
            f"{_supabase_url()}/auth/v1/signup",
            headers={
                "apikey": _supabase_anon_key(),
                "Content-Type": "application/json",
            },
            json={"email": normalized_email, "password": normalized_password},
            timeout=15,
        )
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            message = str(payload.get("msg") or payload.get("error_description") or payload.get("error") or "Sign up failed")
            if "anonymous sign-ins are disabled" in message.lower():
                return False, "Sign up failed: Email/password sign-up is disabled or missing credentials. Enable Email provider in Supabase Auth and enter a valid email/password."
            return False, f"Sign up failed: {message}"

        return True, "Account created. If email confirmation is enabled, verify your email first."
    except Exception as exc:
        return False, f"Sign up failed: {str(exc)}"


def sign_out(access_token: str | None = None) -> None:
    if not is_supabase_enabled():
        return

    try:
        token = str(access_token or "").strip()
        if not token:
            return
        requests.post(
            f"{_supabase_url()}/auth/v1/logout",
            headers={
                "apikey": _supabase_anon_key(),
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("sign_out_failed", exc_info=True)
        return


def send_password_reset_email(email: str, redirect_to: str | None = None) -> tuple[bool, str]:
    if not is_supabase_enabled():
        return False, "Supabase is not configured."

    normalized_email = str(email or "").strip()
    if not normalized_email:
        return False, "Enter your email to receive a reset link."

    try:
        payload: dict[str, str] = {"email": normalized_email}
        if redirect_to and str(redirect_to).strip():
            payload["redirect_to"] = str(redirect_to).strip()

        response = requests.post(
            f"{_supabase_url()}/auth/v1/recover",
            headers={
                "apikey": _supabase_anon_key(),
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        body = response.json() if response.content else {}
        if response.status_code >= 400:
            message = str(body.get("msg") or body.get("error_description") or body.get("error") or "Password reset failed")
            return False, f"Password reset failed: {message}"

        return True, "If this email exists, a password reset link has been sent."
    except Exception as exc:
        return False, f"Password reset failed: {str(exc)}"


def update_password(access_token: str, new_password: str) -> tuple[bool, str]:
    if not is_supabase_enabled():
        return False, "Supabase is not configured."

    token = str(access_token or "").strip()
    password = str(new_password or "")
    if not token:
        return False, "Reset session is missing. Open the latest reset link again."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    try:
        response = requests.put(
            f"{_supabase_url()}/auth/v1/user",
            headers={
                "apikey": _supabase_anon_key(),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"password": password},
            timeout=15,
        )
        body = response.json() if response.content else {}
        if response.status_code >= 400:
            message = str(body.get("msg") or body.get("error_description") or body.get("error") or "Password update failed")
            return False, f"Password update failed: {message}"

        return True, "Password updated successfully. Please sign in with your new password."
    except Exception as exc:
        return False, f"Password update failed: {str(exc)}"


def verify_recovery_token(token_hash: str) -> tuple[bool, str, str | None]:
    if not is_supabase_enabled():
        return False, "Supabase is not configured.", None

    normalized_token_hash = str(token_hash or "").strip()
    if not normalized_token_hash:
        return False, "Recovery token is missing.", None

    try:
        response = requests.post(
            f"{_supabase_url()}/auth/v1/verify",
            headers={
                "apikey": _supabase_anon_key(),
                "Content-Type": "application/json",
            },
            json={"type": "recovery", "token_hash": normalized_token_hash},
            timeout=15,
        )
        body = response.json() if response.content else {}
        if response.status_code >= 400:
            message = str(body.get("msg") or body.get("error_description") or body.get("error") or "Recovery verification failed")
            return False, f"Recovery verification failed: {message}", None

        access_token = str(body.get("access_token") or "").strip()
        if not access_token:
            return False, "Recovery verification failed: missing session token.", None

        return True, "Recovery link verified.", access_token
    except Exception as exc:
        return False, f"Recovery verification failed: {str(exc)}", None


def validate_access_token(access_token: str | None) -> tuple[bool, dict[str, str] | None]:
    if not is_supabase_enabled():
        return False, None

    token = str(access_token or "").strip()
    if not token:
        return False, None

    payload = _decode_jwt_payload(token)
    if isinstance(payload, dict):
        exp = payload.get("exp")
        if isinstance(exp, (int, float)) and exp < time.time():
            return False, None

    try:
        response = requests.get(
            f"{_supabase_url()}/auth/v1/user",
            headers={
                "apikey": _supabase_anon_key(),
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=15,
        )
        if response.status_code >= 400:
            return False, None

        payload = response.json() if response.content else {}
        user_id = str(payload.get("id") or "").strip()
        user_email = str(payload.get("email") or "").strip()
        if not user_id:
            return False, None

        return True, {
            "id": user_id,
            "email": user_email,
            "access_token": token,
        }
    except Exception as exc:
        logging.getLogger(__name__).exception("validate_access_token_failed", exc_info=True)
        return False, None


def save_cloud_chat_history(user_id: str, access_token: str | None, dataset_key: str | None, entry: dict[str, Any]) -> tuple[bool, str | None]:
    user_id = str(user_id or "").strip()
    token = str(access_token or "").strip()
    if not is_supabase_enabled() or not user_id or not token or not isinstance(entry, dict):
        return False, None

    payload = {
        "user_id": user_id,
        "dataset_key": str(dataset_key or "").strip() or None,
        "query": str(entry.get("query", "") or "").strip() or None,
        "ai_response": str(entry.get("ai_response", "") or "").strip() or None,
        "insight": str(entry.get("insight", "") or "").strip() or None,
        "summary": _sanitize_json(entry.get("summary", [])) or [],
        "intent": str(entry.get("intent", "") or "").strip() or None,
        "confidence": entry.get("confidence"),
        "source_columns": _sanitize_json(entry.get("source_columns", [])) or [],
        "metadata": _sanitize_json(
            {
                "query_rejected": bool(entry.get("query_rejected", False)),
                "has_charts": bool(entry.get("charts")),
                "result_type": type(entry.get("result")).__name__,
                "dataset_label": str(entry.get("dataset_label", "") or "").strip() or None,
            }
        )
        or {},
    }

    try:
        response = requests.post(
            f"{_supabase_url()}/rest/v1/chat_history",
            headers={
                "apikey": _supabase_anon_key(),
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=payload,
            timeout=15,
        )
        if response.status_code >= 300:
            return False, None
        payload = response.json() if response.content else []
        if isinstance(payload, list) and payload:
            inserted_row = payload[0] if isinstance(payload[0], dict) else {}
            # Clear cached cloud history so UI shows new row without stale cache
            try:
                from modules.cache_utils import safe_clear_cache

                ds_key = str(inserted_row.get("dataset_key", "") or "").strip() or None
                safe_clear_cache(ds_key)
            except Exception as exc:
                import logging

                logging.getLogger(__name__).debug("supabase_fetch_failed", exc_info=True)
            return True, str(inserted_row.get("id", "") or "") or None
        return True, None
    except Exception as exc:
        logging.getLogger(__name__).exception("save_cloud_chat_history_failed", exc_info=True)
        return False, None


@st.cache_data(show_spinner=False)
def fetch_cloud_chat_history(
    user_id: str,
    access_token: str | None,
    dataset_key: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    user_id = str(user_id or "").strip()
    token = str(access_token or "").strip()
    if not is_supabase_enabled() or not user_id or not token:
        return []

    params = [
        "select=id,user_id,dataset_key,query,ai_response,insight,summary,intent,confidence,source_columns,metadata,created_at",
        f"user_id=eq.{user_id}",
        f"order=created_at.asc",
        f"limit={int(limit) if int(limit) > 0 else 50}",
    ]
    dataset_value = str(dataset_key or "").strip()
    if dataset_value:
        params.insert(2, f"dataset_key=eq.{dataset_value}")

    try:
        started = time.perf_counter()
        response = requests.get(
            f"{_supabase_url()}/rest/v1/chat_history?{'&'.join(params)}",
            headers={
                "apikey": _supabase_anon_key(),
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=15,
        )
        duration_ms = (time.perf_counter() - started) * 1000
        try:
            record_timing("supabase_fetch_chat_history_ms", duration_ms)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("supabase_upsert_failed", exc_info=True)

        if response.status_code >= 400:
            return []
        payload = response.json() if response.content else []
        return payload if isinstance(payload, list) else []
    except Exception as exc:
        logging.getLogger(__name__).exception("fetch_cloud_chat_history_failed", exc_info=True)
        return []


def delete_cloud_chat_history(user_id: str, access_token: str | None, row_id: str) -> bool:
    user_id = str(user_id or "").strip()
    token = str(access_token or "").strip()
    row_id = str(row_id or "").strip()
    if not is_supabase_enabled() or not user_id or not token or not row_id:
        return False

    try:
        response = requests.delete(
            f"{_supabase_url()}/rest/v1/chat_history?id=eq.{row_id}&user_id=eq.{user_id}",
            headers={
                "apikey": _supabase_anon_key(),
                "Authorization": f"Bearer {token}",
            },
            timeout=15,
        )
        ok = response.status_code < 300
        if ok:
            try:
                from modules.cache_utils import safe_clear_cache

                # We don't have the dataset key here; skip global clear to avoid side effects
                safe_clear_cache(None)
            except Exception as exc:
                import logging

                logging.getLogger(__name__).debug("failed_clearing_cache_after_delete", exc_info=True)
        return ok
    except Exception as exc:
        logging.getLogger(__name__).exception("delete_cloud_chat_history_failed", exc_info=True)
        return False
