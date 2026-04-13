import json
from typing import Any

import requests

from modules.app_secrets import get_secret


def _sanitize_json(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
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

    try:
        response = requests.post(
            f"{_supabase_url()}/auth/v1/token?grant_type=password",
            headers={
                "apikey": _supabase_anon_key(),
                "Content-Type": "application/json",
            },
            json={"email": email, "password": password},
            timeout=15,
        )
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            message = str(payload.get("msg") or payload.get("error_description") or payload.get("error") or "Invalid credentials")
            return False, f"Sign in failed: {message}", None

        user = payload.get("user") or {}
        user_id = str(user.get("id") or "").strip()
        user_email = str(user.get("email") or email).strip()
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

    try:
        response = requests.post(
            f"{_supabase_url()}/auth/v1/signup",
            headers={
                "apikey": _supabase_anon_key(),
                "Content-Type": "application/json",
            },
            json={"email": email, "password": password},
            timeout=15,
        )
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            message = str(payload.get("msg") or payload.get("error_description") or payload.get("error") or "Sign up failed")
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
    except Exception:
        return


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
            return True, str(inserted_row.get("id", "") or "") or None
        return True, None
    except Exception:
        return False, None


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
        response = requests.get(
            f"{_supabase_url()}/rest/v1/chat_history?{'&'.join(params)}",
            headers={
                "apikey": _supabase_anon_key(),
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=15,
        )
        if response.status_code >= 400:
            return []
        payload = response.json() if response.content else []
        return payload if isinstance(payload, list) else []
    except Exception:
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
        return response.status_code < 300
    except Exception:
        return False
