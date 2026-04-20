import pandas as pd
import streamlit as st
import time
from datetime import datetime, timedelta, timezone
from utils.logging import get_logger

DUPLICATE_WINDOW_SECONDS = 5
MAX_RECENT_CHECK = 3

def _is_recent_duplicate(query: str, history_id: str, history_list: list) -> bool:
    """Check if query or ID is recent duplicate to prevent tab-click spam."""
    # Use timezone-aware now in UTC so comparisons with ISO timestamps work reliably
    current_time = datetime.now(timezone.utc)
    if not history_list:
        return False
    recent = history_list[-MAX_RECENT_CHECK:]
    for entry in recent:
        if not isinstance(entry, dict):
            continue
        entry_time_str = str(entry.get('created_at') or "").strip()
        if entry_time_str:
            try:
                entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
                if (current_time - entry_time).total_seconds() < DUPLICATE_WINDOW_SECONDS:
                    if (str(entry.get('query', "")) == query or 
                        str(entry.get('history_id', "")) == history_id or
                        str(entry.get('cloud_history_id', "")) == history_id):
                        return True
            except ValueError:
                pass  # Invalid timestamp, skip
    return False

from modules.prompt_cache import (
    get_cached_dataset_state,
    save_cached_dataset_state,
    get_all_cached_dataset_states,
)
from modules.deleted_history import (
    add_global_deleted_history_id,
    get_global_deleted_history_ids,
)
from modules.supabase_service import fetch_cloud_chat_history, save_cloud_chat_history, delete_cloud_chat_history


def ensure_analysis_state():
    defaults = {
        "chat_history": [],
        "messages": [],
        "analysis_history": [],
        "result_history": [],
        "result_history_details": [],
        "recent_activity": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value


def clear_transient_ui_state() -> None:
    defaults = {
        "pending_query": "",
        "pending_query_id": "",
        "last_processed_query_id": "",
        "selected_chat_history_id": "",
        "chat_view_mode": "new",
        "delete_chat_history_id": "",
        "navigation_target_page": "",
        "chat_processing": False,
        "analysis_result": None,
        "last_result": None,
        "last_query": "",
        "analysis_query": "",
        "chart_data": None,
        "report_charts": [],
    }
    for key, value in defaults.items():
        st.session_state[key] = value


def clear_analysis_state_memory() -> None:
    for key in ("chat_history", "messages", "analysis_history", "result_history", "result_history_details", "recent_activity"):
        st.session_state[key] = []

    clear_transient_ui_state()


def start_new_chat(*, target_page: str = "chat") -> None:
    st.session_state["selected_chat_history_id"] = ""
    st.session_state["chat_view_mode"] = "new"
    st.session_state["pending_query"] = ""
    st.session_state["pending_query_id"] = ""
    st.session_state["last_processed_query_id"] = ""
    st.session_state["active_page"] = target_page
    st.session_state["navigation_target_page"] = target_page


def open_chat_history(history_id: str) -> None:
    history_id = str(history_id or "").strip()
    st.session_state["selected_chat_history_id"] = history_id
    st.session_state["chat_view_mode"] = ""
    st.session_state["active_page"] = "chat"
    st.session_state["navigation_target_page"] = "chat"

    # If the selected entry isn't present in the local session `chat_history`,
    # try to load it from cloud (if user is signed in) so the main chat view
    # can render the saved chat contents.
    try:
        exists = any(_history_entry_id(entry) == history_id for entry in st.session_state.get("chat_history", []))
        if not exists:
            user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
            access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
            if user_id and access_token:
                try:
                    with st.spinner("Loading saved chat..."):
                        rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=None, limit=500)
                except Exception as exc:
                    get_logger("app_state").debug("fetch_cloud_chat_history_failed", exc_info=True)
                    rows = []

                if isinstance(rows, list):
                    for row in rows:
                        row_id = str(row.get("id", "") or "").strip()
                        if row_id == history_id:
                            entry = _cloud_row_to_chat_entry(row)
                            # append to session chat_history and normalize ids
                            current = _ensure_chat_history_ids(list(st.session_state.get("chat_history", [])))
                            current.append(entry)
                            st.session_state["chat_history"] = _ensure_chat_history_ids(current)
                            break
    except (AttributeError, TypeError, ValueError) as e:
        get_logger("app_state").debug(f"Cloud history fetch failed (non-fatal): {e}")
        # Non-fatal: if cloud fetch fails, the UI will simply show no chat contents.
        pass


def _active_dataset_cache_key() -> str:
    return str(st.session_state.get("active_dataset_cache_key") or st.session_state.get("active_dataset_key") or st.session_state.get("dataset_name") or "").strip()


def _active_dataset_label() -> str:
    return str(st.session_state.get("dataset_name") or st.session_state.get("active_dataset_key") or "").strip()


def _history_entry_id(entry: dict) -> str:
    if not isinstance(entry, dict):
        return ""
    return str(entry.get("history_id") or entry.get("cloud_history_id") or "").strip()


def _ensure_chat_history_ids(entries: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        normalized_entry = dict(entry)
        history_id = _history_entry_id(normalized_entry)
        if not history_id:
            history_id = str(time.time_ns())
        normalized_entry["history_id"] = history_id
        normalized.append(normalized_entry)
    return normalized


def _matches_entry_id(entry: dict, hid: str) -> bool:
    """Return True if the provided entry matches the given history identifier.

    Matches against `history_id`, `cloud_history_id`, or a signature
    of the form `sig::dataset_key::created_at::query` used by sidebar
    merging logic.
    """
    if not isinstance(entry, dict):
        return False
    hid = str(hid or "").strip()
    if not hid:
        return False

    if str(entry.get("history_id", "") or "").strip() == hid:
        return True
    if str(entry.get("cloud_history_id", "") or "").strip() == hid:
        return True

    ds = str(entry.get("dataset_key", "") or "").strip()
    created = str(entry.get("created_at", "") or "").strip()
    query = str(entry.get("query", "") or "").strip()
    if ds and created and query and hid == f"sig::{ds}::{created}::{query}":
        return True

    return False


def _resolve_cloud_id_for(hid: str) -> str | None:
    """Return a cloud row id for a given history identifier if available.

    This inspects in-memory chat history and any cached dataset states
    to find an associated `cloud_history_id` so cloud deletions can be
    targeted correctly even when the UI passes a signature/local id.
    """
    hid = str(hid or "").strip()
    if not hid:
        return None

    # Check in-memory session history
    for entry in list(st.session_state.get("chat_history", []) or []):
        try:
            if _matches_entry_id(entry if isinstance(entry, dict) else {}, hid):
                cloud_id = str((entry or {}).get("cloud_history_id", "") or "").strip()
                if cloud_id:
                    return cloud_id
        except Exception as exc:
            get_logger("app_state").debug("resolve_cloud_id_in_memory_entry_error", exc_info=True)
            continue

    # Check persisted cached dataset states
    try:
        cached_states = get_all_cached_dataset_states()
        if isinstance(cached_states, dict):
            for ds_state in cached_states.values():
                if not isinstance(ds_state, dict):
                    continue
                entries = ds_state.get("chat_history", [])
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    try:
                        if _matches_entry_id(entry if isinstance(entry, dict) else {}, hid):
                            cloud_id = str((entry or {}).get("cloud_history_id", "") or "").strip()
                            if cloud_id:
                                return cloud_id
                    except Exception as exc:
                        get_logger("app_state").debug("resolve_cloud_id_cached_entry_error", exc_info=True)
                        continue
    except Exception as exc:
        get_logger("app_state").debug("resolve_cloud_id_error", exc_info=True)

    return None


def _find_cloud_row_id_for(hid: str, user_id: str, access_token: str) -> str | None:
    """Fetch cloud chat history for the user and return a matching cloud row id.

    This is a best-effort lookup that normalizes cloud rows to the
    local chat entry shape and uses `_matches_entry_id` to find the
    corresponding cloud row. Returns the cloud `id` string when found.
    """
    hid = str(hid or "").strip()
    if not hid or not user_id or not access_token:
        return None

    try:
        try:
            with st.spinner("Looking up cloud chat rows..."):
                rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=None, limit=500)
        except Exception as exc:
            get_logger("app_state").debug("find_cloud_row_fetch_failed", exc_info=True)
            rows = []
        # Fetch cloud rows and attempt to match; minimal logging only on error.
        for row in rows:
            try:
                entry = _cloud_row_to_chat_entry(row)
                if _matches_entry_id(entry, hid):
                    rid = str(row.get("id", "") or "").strip()
                    if rid:
                        pass
                        return rid
            except Exception as exc:
                get_logger("app_state").debug("resolve_cloud_id_cloud_row_error", exc_info=True)
                continue
    except Exception as exc:
        logger = get_logger("app_state")
        logger.exception("cloud_fetch_error", extra={"history_id": hid})

    return None


def _find_cloud_row_entry_for(hid: str, user_id: str, access_token: str) -> tuple[str | None, dict | None]:
    """Return a tuple of (cloud_row_id, normalized_entry) for a matching cloud row.

    Normalized entry uses `_cloud_row_to_chat_entry` so callers can inspect
    `query`, `created_at`, and `dataset_key` for cache cleanup.
    """
    hid = str(hid or "").strip()
    if not hid or not user_id or not access_token:
        return None, None

    try:
        try:
            with st.spinner("Looking up cloud chat rows..."):
                rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=None, limit=500)
        except Exception as exc:
            get_logger("app_state").debug("find_cloud_row_entry_fetch_failed", exc_info=True)
            rows = []
        for row in rows:
            try:
                entry = _cloud_row_to_chat_entry(row)
                if _matches_entry_id(entry, hid):
                    rid = str(row.get("id", "") or "").strip()
                    pass
                    return (rid or None, entry)
            except Exception as exc:
                get_logger("app_state").debug("find_cloud_row_entry_error", exc_info=True)
                continue
    except Exception as exc:
        logger = get_logger("app_state")
        logger.exception("cloud_fetch_error_for_entry", extra={"history_id": hid})

    return None, None


def _remove_cached_entries_by_query_or_signature(hid: str, user_id: str | None = None, access_token: str | None = None) -> bool:
    """Remove cached dataset entries that match the given history id by id, signature, or query text.

    Returns True if any cached dataset state was modified.
    """
    hid = str(hid or "").strip()
    if not hid:
        return False

    # Try to find a cloud entry to get its query text for looser matching
    cloud_query = None
    try:
        if user_id and access_token:
            _, cloud_entry = _find_cloud_row_entry_for(hid, user_id, access_token)
            if isinstance(cloud_entry, dict):
                cloud_query = str(cloud_entry.get("query", "") or "").strip()
    except Exception as exc:
        get_logger("app_state").debug("find_cloud_row_entry_cloud_query_failed", exc_info=True)
        cloud_query = None

    modified_any = False
    try:
        cached_states = get_all_cached_dataset_states()
        if not isinstance(cached_states, dict):
            return False

        for ds_key, ds_state in list(cached_states.items()):
            if not isinstance(ds_state, dict):
                continue
            entries = ds_state.get("chat_history", [])
            if not isinstance(entries, list) or not entries:
                continue

            kept = []
            removed_here = False
            for entry in entries:
                entry_dict = entry if isinstance(entry, dict) else {}
                # Remove if ids/signature match
                try:
                    if _matches_entry_id(entry_dict, hid):
                        removed_here = True
                        continue
                except Exception as exc:
                    get_logger("app_state").debug("matches_entry_id_check_failed", extra={"hid": hid}, exc_info=True)

                # Fallback: remove if query text matches cloud query (loose match)
                try:
                    if cloud_query:
                        if str(entry_dict.get("query", "") or "").strip() == cloud_query:
                            removed_here = True
                            continue
                except Exception as exc:
                    get_logger("app_state").debug("cloud_query_match_failed", extra={"hid": hid}, exc_info=True)

                kept.append(entry_dict)

            if removed_here:
                updated_state = dict(ds_state)
                updated_state["chat_history"] = _ensure_chat_history_ids(kept)
                try:
                    save_cached_dataset_state(ds_key, updated_state)
                    modified_any = True
                except Exception as exc:
                    # non-fatal; continue
                    get_logger("app_state").debug("save_cached_dataset_state_failed", extra={"dataset_key": ds_key}, exc_info=True)
    except Exception as exc:
        get_logger("app_state").debug("remove_cached_entries_failed", exc_info=True)
        return False

    return modified_any


def restore_persisted_analysis_state() -> None:
    dataset_cache_key = _active_dataset_cache_key()
    if not dataset_cache_key:
        return

    cached_state = get_cached_dataset_state(dataset_cache_key)
    if not isinstance(cached_state, dict):
        return

    for key in ("chat_history", "analysis_history", "result_history", "result_history_details", "recent_activity", "messages"):
        value = cached_state.get(key)
        if isinstance(value, list):
            st.session_state[key] = value.copy()

    if isinstance(st.session_state.get("chat_history"), list):
        st.session_state["chat_history"] = _ensure_chat_history_ids(st.session_state["chat_history"])


def _cloud_row_to_chat_entry(row: dict) -> dict:
    row_id = str(row.get("id", "") or "").strip()
    metadata_value = row.get("metadata", {}) if isinstance(row, dict) else {}
    if not isinstance(metadata_value, dict):
        metadata_value = {}

    dataset_label = str(
        metadata_value.get("dataset_label", "")
        or metadata_value.get("dataset_name", "")
        or row.get("dataset_key", "")
        or ""
    ).strip()

    summary_value = row.get("summary", []) if isinstance(row, dict) else []
    if not isinstance(summary_value, list):
        summary_value = []

    source_columns_value = row.get("source_columns", []) if isinstance(row, dict) else []
    if not isinstance(source_columns_value, list):
        source_columns_value = []

    return {
        "history_id": row_id or str(time.time_ns()),
        "cloud_history_id": row_id or "",
        "dataset_key": str(row.get("dataset_key", "") or ""),
        "dataset_label": dataset_label,
        "created_at": row.get("created_at"),
        "query": str(row.get("query", "") or ""),
        "result": str(row.get("ai_response", "") or row.get("insight", "") or ""),
        "code": "",
        "chart_data": None,
        "insight": str(row.get("insight", "") or ""),
        "summary": summary_value,
        "charts": [],
        "ai_response": str(row.get("ai_response", "") or ""),
        "suggestions": "",
        "query_rejected": False,
        "confidence": row.get("confidence"),
        "source_columns": source_columns_value,
        "intent": row.get("intent"),
        "rephrases": [],
    }


def get_sidebar_history_entries(scope: str = "dataset", limit: int = 200) -> list[dict]:
    current_history = _ensure_chat_history_ids(list(st.session_state.get("chat_history", [])))
    if str(scope or "dataset").strip().lower() != "all":
        return current_history

    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
    if not user_id or not access_token:
        return current_history

    try:
        # Some test helpers or minimal `st` dummies may not implement `spinner`.
        # Prefer using it when available, otherwise call directly.
        if hasattr(st, "spinner") and callable(getattr(st, "spinner")):
            try:
                with st.spinner("Loading cloud chat history..."):
                    rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=None, limit=limit)
            except Exception as exc:
                get_logger("app_state").debug("fetch_cloud_chat_history_spinner_failed", exc_info=True)
                rows = []
        else:
            try:
                rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=None, limit=limit)
            except Exception as exc:
                get_logger("app_state").debug("fetch_cloud_chat_history_direct_failed", exc_info=True)
                rows = []
    except Exception as exc:
        get_logger("app_state").debug("fetch_cloud_chat_history_outer_failed", exc_info=True)
        rows = []
    # If cloud is unavailable or returned no rows, still attempt to include locally cached histories from disk.
    cloud_entries = _ensure_chat_history_ids([_cloud_row_to_chat_entry(row) for row in rows]) if rows else []

    # Load any locally cached dataset states (persisted per-dataset).
    # NOTE: to avoid duplicating many unrelated cached histories when cloud rows are present,
    # only include local cached entries when cloud returned no rows. This preserves test
    # expectations and avoids noisy cross-project caches contaminating the 'All Datasets' view.
    local_cached_entries: list[dict] = []
    if not cloud_entries:
        cached_states = get_all_cached_dataset_states()
        if isinstance(cached_states, dict):
            for ds_key, ds_state in cached_states.items():
                if not isinstance(ds_state, dict):
                    continue
                entries = ds_state.get("chat_history", [])
                if isinstance(entries, list) and entries:
                    local_cached_entries.extend(entries)

        # Normalize ids for local cached entries as well
        local_cached_entries = _ensure_chat_history_ids(local_cached_entries)

    def _entry_identity_keys(entry: dict) -> set[str]:
        keys: set[str] = set()
        cloud_id = str(entry.get("cloud_history_id", "") or "").strip()
        history_id = str(entry.get("history_id", "") or "").strip()
        if cloud_id:
            keys.add(f"cloud::{cloud_id}")
        if history_id:
            keys.add(f"history::{history_id}")

        dataset_key = str(entry.get("dataset_key", "") or "").strip()
        created_at = str(entry.get("created_at", "") or "").strip()
        query = str(entry.get("query", "") or "").strip()
        if created_at and query:
            keys.add(f"sig::{dataset_key}::{created_at}::{query}")
        return keys

    merged_entries: list[dict] = []
    seen_keys: set[str] = set()

    # Exclude any globally-marked deleted ids persisted on disk.
    deleted_ids_global = {str(i).strip() for i in get_global_deleted_history_ids()}

    def _add_if_new(entry: dict) -> None:
        identity_keys = _entry_identity_keys(entry)
        # Skip entries that match a globally deleted id
        if identity_keys and any(k.split("::", 1)[1] in deleted_ids_global for k in identity_keys):
            return
        if identity_keys and any(key in seen_keys for key in identity_keys):
            return
        merged_entries.append(entry)
        seen_keys.update(identity_keys)

    # Prefer cloud entries first, then locally cached entries, then the current in-memory history.
    for entry in cloud_entries:
        _add_if_new(entry)
    for entry in local_cached_entries:
        _add_if_new(entry)
    for entry in current_history:
        _add_if_new(entry)

    return merged_entries


def restore_cloud_analysis_state() -> bool:
    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
    if not user_id or not access_token:
        return False

    dataset_key = _active_dataset_cache_key()
    rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=dataset_key, limit=100)
    if not rows:
        return False

    current_history = _ensure_chat_history_ids(list(st.session_state.get("chat_history", [])))
    existing_ids = {
        _history_entry_id(entry)
        for entry in current_history
        if _history_entry_id(entry)
    }
    cloud_entries = [_cloud_row_to_chat_entry(row) for row in rows if str(row.get("id", "") or "").strip() not in existing_ids]

    if cloud_entries:
        # Dedupe cloud entries before merge
        existing_ids = {str(_history_entry_id(e)) for e in current_history}
        deduped_cloud = [e for e in cloud_entries if str(_history_entry_id(e)) not in existing_ids]
        
        st.session_state["chat_history"] = _ensure_chat_history_ids(current_history + deduped_cloud)

    if not st.session_state.get("messages"):
        st.session_state["messages"] = []
    for entry in deduped_cloud:
        query = str(entry.get("query", "") or "").strip()
        answer = str(entry.get("ai_response", "") or entry.get("insight", "") or "").strip()
        # Deduplicate using recent messages window to avoid repeats
        recent_msgs = st.session_state.get("messages", [])[-20:]
        if query:
            if not any(m.get("role") == "user" and str(m.get("content", "")).strip() == query for m in recent_msgs):
                st.session_state["messages"].append({"role": "user", "content": query})
        if answer:
            if not any(m.get("role") == "assistant" and str(m.get("content", "")).strip() == answer for m in recent_msgs):
                st.session_state["messages"].append({"role": "assistant", "content": answer})

        if not st.session_state.get("analysis_history"):
            st.session_state["analysis_history"] = []
        for entry in cloud_entries:
            st.session_state["analysis_history"].append(
                {
                    "query": str(entry.get("query", "") or ""),
                    "result": str(entry.get("ai_response", "") or entry.get("insight", "") or ""),
                    "code": "",
                    "insight": str(entry.get("insight", "") or ""),
                    "ai_response": str(entry.get("ai_response", "") or ""),
                    "charts": [],
                    "summary": entry.get("summary", []) if isinstance(entry.get("summary", []), list) else [],
                    "intent": entry.get("intent"),
                    "confidence": entry.get("confidence"),
                    "source_columns": entry.get("source_columns", []) if isinstance(entry.get("source_columns", []), list) else [],
                }
            )

        if not st.session_state.get("result_history"):
            st.session_state["result_history"] = []
        st.session_state["result_history"].extend([str(entry.get("ai_response", "") or entry.get("insight", "") or "") for entry in cloud_entries])

        if not st.session_state.get("result_history_details"):
            st.session_state["result_history_details"] = []
        st.session_state["result_history_details"].extend(
            [{"query": str(entry.get("query", "") or ""), "history_id": _history_entry_id(entry)} for entry in cloud_entries]
        )

    return True


def delete_chat_history_entry(history_id: str) -> bool:
    hid = str(history_id or "").strip()
    if not hid:
        return False

    chat_history = list(st.session_state.get("chat_history", []))
    kept: list[dict] = []
    removed_any = False
    for entry in chat_history:
        if _matches_entry_id(entry if isinstance(entry, dict) else {}, hid):
            removed_any = True
            continue
        if isinstance(entry, dict):
            kept.append(entry)

    if not removed_any:
        return False

    # Normalize ids and update session state
    st.session_state["chat_history"] = _ensure_chat_history_ids(kept)

    # Rebuild dependent state from remaining history
    remaining_history = st.session_state.get("chat_history", [])
    st.session_state["analysis_history"] = [
        {
            "query": str(e.get("query", "") or ""),
            "result": e.get("result"),
            "code": e.get("code", ""),
            "insight": e.get("insight", ""),
            "ai_response": e.get("ai_response", ""),
            "charts": e.get("charts", []) if isinstance(e.get("charts", []), list) else [],
            "summary": e.get("summary", []) if isinstance(e.get("summary", []), list) else [],
            "intent": e.get("intent"),
            "confidence": e.get("confidence"),
            "source_columns": e.get("source_columns", []) if isinstance(e.get("source_columns", []), list) else [],
        }
        for e in remaining_history
    ]

    st.session_state["result_history"] = [e.get("result") for e in remaining_history]
    st.session_state["result_history_details"] = [
        {"query": e.get("query", ""), "history_id": _history_entry_id(e)} for e in remaining_history
    ]

    msgs: list[dict[str, str]] = []
    for e in remaining_history:
        q = str(e.get("query", "") or "").strip()
        a = str(e.get("ai_response", "") or e.get("insight", "") or "").strip()
        if q:
            msgs.append({"role": "user", "content": q})
        if a:
            msgs.append({"role": "assistant", "content": a})
    st.session_state["messages"] = msgs

    # If the selected entry was deleted, clear it or pick the last one
    selected = str(st.session_state.get("selected_chat_history_id", "") or "").strip()
    if selected and _matches_entry_id({"history_id": selected, "cloud_history_id": selected}, hid):
        st.session_state["selected_chat_history_id"] = remaining_history[-1]["history_id"] if remaining_history else ""

    persist_dataset_state()
    return True


def delete_chat_history_everywhere(history_id: str) -> bool:
    """
    Delete a history entry id from in-memory state and all cached dataset states.

    This makes sidebar deletion reliable when the UI is showing merged history
    from multiple sources/datasets.
    """
    hid = str(history_id or "").strip()
    if not hid:
        return False

    removed_any = False

    # Remove from in-memory session state
    try:
        removed_any = delete_chat_history_entry(hid) or removed_any
    except Exception as exc:
        get_logger("app_state").debug("delete_chat_history_entry_failed", extra={"history_id": hid}, exc_info=True)
        removed_any = removed_any

    # Remove from persisted cached dataset states
    cached_states = get_all_cached_dataset_states()
    if isinstance(cached_states, dict):
        for dataset_cache_key, dataset_state in cached_states.items():
            if not isinstance(dataset_state, dict):
                continue
            cached_history = dataset_state.get("chat_history", [])
            if not isinstance(cached_history, list) or not cached_history:
                continue

            kept: list[dict] = []
            removed_here = False
            for entry in cached_history:
                entry_dict = entry if isinstance(entry, dict) else {}
                if _matches_entry_id(entry_dict, hid):
                    removed_here = True
                    continue
                kept.append(entry_dict)

            if removed_here:
                updated_state = dict(dataset_state)
                updated_state["chat_history"] = _ensure_chat_history_ids(kept)
                try:
                    save_cached_dataset_state(dataset_cache_key, updated_state)
                except Exception as exc:
                    # non-fatal; continue but log for diagnostics
                    get_logger("app_state").debug("save_cached_dataset_state_failed", extra={"dataset_key": dataset_cache_key}, exc_info=True)
                removed_any = True

    return removed_any


def delete_history_immediate(history_id: str) -> bool:
    """Delete a history entry by id, attempting cloud deletion first when possible.

    This is an immediate helper intended to be called from UI handlers so the
    deletion happens in the same click without relying on a separate global
    deletion handler.
    """
    hid = str(history_id or "").strip()
    if not hid:
        return False

    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()

    logger = get_logger("app_state")
    cloud_deleted = False
    if user_id and access_token:
        try:
            logger.info("attempt_cloud_delete", extra={"history_id": hid, "user_id": user_id})
            # Try to resolve a true cloud row id for this history identifier.
            cloud_target = _resolve_cloud_id_for(hid)
            # Fall back to the provided id if no mapping found (keeps backward compatibility).
            cloud_target = str(cloud_target or hid).strip()
            if cloud_target:
                cloud_deleted = delete_cloud_chat_history(user_id, access_token, cloud_target)

            # If cloud delete failed, attempt a best-effort lookup of the
            # real cloud row id by fetching cloud rows and deleting that id.
            if not cloud_deleted:
                try:
                    lookup_id = _find_cloud_row_id_for(hid, user_id, access_token)
                    if lookup_id and lookup_id != cloud_target:
                        cloud_deleted = delete_cloud_chat_history(user_id, access_token, lookup_id)
                        logger.info("cloud_delete_lookup_attempt", extra={"history_id": hid, "lookup_id": lookup_id, "cloud_deleted": bool(cloud_deleted)})
                except Exception as exc:
                    logger.exception("cloud_lookup_delete_failed", extra={"history_id": hid})

            logger.info("cloud_delete_attempted", extra={"history_id": hid, "cloud_target": cloud_target, "cloud_deleted": bool(cloud_deleted)})

            # If we deleted in cloud, also persist this id to the global
            # deleted list (on disk) and attempt to remove any cached
            # dataset entries that may be present so the deletion persists.
            try:
                if cloud_deleted:
                    # Persist both the provided id and any resolved cloud id
                    try:
                        add_global_deleted_history_id(hid)
                    except Exception as exc:
                        get_logger("app_state").debug("add_global_deleted_history_id_failed", extra={"history_id": hid}, exc_info=True)
                    try:
                        # cloud_target may be a resolved cloud row id
                        if cloud_target and str(cloud_target).strip() and cloud_target != hid:
                            add_global_deleted_history_id(str(cloud_target).strip())
                    except Exception as exc:
                        get_logger("app_state").debug("add_global_deleted_cloud_id_failed", extra={"history_id": hid, "cloud_target": cloud_target}, exc_info=True)
                    cleaned = _remove_cached_entries_by_query_or_signature(hid, user_id, access_token)
                    logger.info("cached_state_cleanup", extra={"history_id": hid, "cleaned": bool(cleaned)})
            except Exception as exc:
                logger.exception("cached_cleanup_failed", extra={"history_id": hid})
        except Exception as exc:
            logger.exception("cloud_delete_error", extra={"history_id": hid})

    local_deleted = delete_chat_history_everywhere(hid)
    logger.info("local_delete_result", extra={"history_id": hid, "local_deleted": bool(local_deleted)})

    # Clear any transient deletion state and selection
    try:
        deleted_ids = list(st.session_state.get("deleted_history_ids", []))
        # If deleted via immediate action, add to deleted ids so UI hides it instantly
        if (cloud_deleted or local_deleted) and hid and hid not in deleted_ids:
            st.session_state["deleted_history_ids"] = deleted_ids + [hid]
        st.session_state["delete_chat_history_id"] = ""
        selected = str(st.session_state.get("selected_chat_history_id", "") or "").strip()
        if selected and _matches_entry_id({"history_id": selected, "cloud_history_id": selected}, hid):
            st.session_state["selected_chat_history_id"] = ""
    except Exception as exc:
        logger.exception("clear_delete_state_failed", extra={"history_id": hid})

    # Invalidate cache after any deletion so cached cloud fetches refresh
    try:
        if cloud_deleted or local_deleted:
            try:
                from modules.cache_utils import safe_clear_cache

                # Attempt to clear only dataset-specific cache when possible
                dataset_key = str(st.session_state.get("active_dataset_cache_key") or "").strip() or None
                safe_clear_cache(dataset_key)
            except Exception as exc:
                get_logger("app_state").debug("failed_clearing_cache", exc_info=True)
    except Exception as exc:
        # ignore cache clear failures
        get_logger("app_state").debug("cache_clear_outer_failed", exc_info=True)

    return bool(cloud_deleted or local_deleted)


def delete_history_cloud_only(hid: str, user_id: str, access_token: str) -> bool:
    """Attempt cloud-only deletion and cached-state cleanup without
    mutating `st.session_state`. Safe to call from background threads.
    """
    hid = str(hid or "").strip()
    user_id = str(user_id or "").strip()
    access_token = str(access_token or "").strip()
    if not hid or not user_id or not access_token:
        return False

    cloud_deleted = False
    try:
        # Try to find a matching cloud row id and delete it
        try:
            target = _find_cloud_row_id_for(hid, user_id, access_token) or hid
        except Exception as exc:
            get_logger("app_state").debug("find_cloud_row_id_lookup_failed", extra={"history_id": hid}, exc_info=True)
            target = hid

        if target:
            try:
                cloud_deleted = delete_cloud_chat_history(user_id, access_token, target)
            except Exception as exc:
                get_logger("app_state").debug("delete_cloud_chat_history_failed", extra={"target": target}, exc_info=True)
                cloud_deleted = False

        # If deleted, persist global deleted id and clean cached dataset states
        if cloud_deleted:
            try:
                add_global_deleted_history_id(hid)
            except Exception as exc:
                get_logger("app_state").debug("failed_ensuring_ids", extra={"ds_key": ds_key}, exc_info=True)
            try:
                if target and str(target).strip() and target != hid:
                    add_global_deleted_history_id(str(target).strip())
            except Exception as exc:
                get_logger("app_state").debug("failed_saving_global_deleted_ids", exc_info=True)
            try:
                _remove_cached_entries_by_query_or_signature(hid, user_id, access_token)
            except Exception as exc:
                get_logger("app_state").debug("failed_loading_cached_states", exc_info=True)
    except Exception as exc:
        get_logger("app_state").debug("delete_history_cloud_only_failed", exc_info=True)
        return False

    return bool(cloud_deleted)


def persist_dataset_state() -> None:
    dataset_cache_key = _active_dataset_cache_key()
    if not dataset_cache_key:
        return

    save_cached_dataset_state(
        dataset_cache_key,
        {
            "chat_history": st.session_state.get("chat_history", []),
            "analysis_history": st.session_state.get("analysis_history", []),
            "result_history": st.session_state.get("result_history", []),
            "result_history_details": st.session_state.get("result_history_details", []),
            "recent_activity": st.session_state.get("recent_activity", []),
            "messages": st.session_state.get("messages", []),
        },
    )


def reset_analysis_state():
    clear_analysis_state_memory()
    persist_dataset_state()


def add_recent_activity(kind: str, description: str, limit: int = 8):
    if "recent_activity" not in st.session_state:
        st.session_state["recent_activity"] = []

    st.session_state["recent_activity"].insert(0, {"kind": kind, "description": description})
    st.session_state["recent_activity"] = st.session_state["recent_activity"][:limit]


def get_recent_activity():
    return st.session_state.get("recent_activity", [])


def append_message_pair(query: str, result):
    # Avoid duplicating messages: if UI already appended the user message or assistant
    # placeholder, do not append identical entries again. This keeps `messages` in
    # sync across immediate UI updates and persisted saves.
    st.session_state.setdefault("messages", [])
    msgs = st.session_state["messages"]
    # Append user message only if the last user message doesn't match this query
    if not (msgs and msgs[-1].get("role") == "user" and str(msgs[-1].get("content", "")).strip() == str(query).strip()):
        msgs.append({"role": "user", "content": query})

    # Build assistant preview content
    assistant_preview = None
    if isinstance(result, pd.DataFrame):
        preview = result.head(5).to_string(index=False)
        assistant_preview = f"Here are the top results:\n\n{preview}"
    elif isinstance(result, pd.Series):
        preview = result.head(5).to_string()
        assistant_preview = f"Here are the top results:\n\n{preview}"
    else:
        assistant_preview = str(result)

    # Append assistant preview only if the most recent assistant message differs
    if assistant_preview is not None:
        if not (msgs and msgs[-1].get("role") == "assistant" and str(msgs[-1].get("content", "")).strip() == str(assistant_preview).strip()):
            msgs.append({"role": "assistant", "content": assistant_preview})
    st.session_state["messages"] = msgs


def store_analysis_outputs(query, result, chart_data, chart_figs, code, report_insight, ai_response, summary_list, suggestions, query_rejected, is_axes_result):
    history_id = str(time.time_ns())
    created_at = pd.Timestamp.now("UTC").isoformat()
    dataset_key = _active_dataset_cache_key()
    dataset_label = _active_dataset_label()
    st.session_state["analysis_result"] = result
    st.session_state["last_result"] = result
    st.session_state["last_query"] = query
    # Dedupe before append
    if _is_recent_duplicate(query, history_id, st.session_state.get("chat_history", [])):
        logger.warning("skipping_duplicate_store_analysis", extra={"query": query[:100], "history_id": history_id})
    else:
        st.session_state["result_history"].append(result)
        st.session_state["analysis_query"] = query

    if chart_data is not None:
        st.session_state["chart_data"] = chart_data
        st.session_state["report_charts"] = chart_figs

    if not query_rejected:
        st.session_state["analysis_history"].append({
            "query": query,
            "result": result if not is_axes_result else None,
            "code": code,
            "insight": report_insight,
            "ai_response": ai_response,
            "charts": chart_figs,
            "summary": summary_list,
        })

    st.session_state["chat_history"].append({
        "history_id": history_id,
        "dataset_key": dataset_key,
        "dataset_label": dataset_label,
        "created_at": created_at,
        "query": query,
        "result": result,
        "code": code if not query_rejected else "",
        "chart_data": chart_data if not query_rejected else None,
        "insight": report_insight if not query_rejected else "",
        "summary": summary_list if not query_rejected else [],
        "charts": chart_figs if not query_rejected else [],
        "ai_response": ai_response,
        "suggestions": suggestions if (not query_rejected and suggestions) else "",
        "query_rejected": query_rejected,
    })

    persist_dataset_state()

    # Log save attempt for cloud persistence
    try:
        logger = get_logger("app_state")
        user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
        access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
        if user_id:
            latest_entry = st.session_state["chat_history"][-1]
            ok, cloud_history_id = save_cloud_chat_history(user_id, access_token, _active_dataset_cache_key(), latest_entry)
            logger.info("store_analysis_cloud_save", extra={"user_id": user_id, "ok": bool(ok), "cloud_history_id": cloud_history_id})
            if ok and cloud_history_id:
                latest_entry["cloud_history_id"] = cloud_history_id
    except Exception as exc:
        get_logger("app_state").exception("store_analysis_cloud_save_failed", exc_info=True)

    # Also remove this entry from any persisted cached dataset states to
    # ensure deletion is permanent across reloads/logins.
    try:
        cached_states = get_all_cached_dataset_states()
        if isinstance(cached_states, dict):
            for ds_key, ds_state in cached_states.items():
                if not isinstance(ds_state, dict):
                    continue
                entries = ds_state.get("chat_history", [])
                if not isinstance(entries, list) or not entries:
                    continue
                kept = []
                removed = False
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    if _matches_entry_id(e, history_id):
                        removed = True
                        continue
                    kept.append(e)
                if removed:
                    new_state = dict(ds_state)
                    new_state["chat_history"] = _ensure_chat_history_ids(kept)
                    try:
                        save_cached_dataset_state(ds_key, new_state)
                    except Exception as exc:
                        # non-fatal; log for diagnostics
                        get_logger("app_state").debug("save_cached_dataset_state_failed_in_store", extra={"ds_key": ds_key}, exc_info=True)
    except Exception as exc:
        # Don't let cleanup errors break the main flow
        get_logger("app_state").debug("store_analysis_cleanup_failed", exc_info=True)


def persist_analysis_cycle(
    *,
    query: str,
    result,
    chart_data,
    chart_figs,
    code: str,
    insight: str,
    ai_response: str,
    summary_list: list,
    suggestions: str,
    query_rejected: bool,
    is_axes_result: bool,
    intent: str | None,
    rephrases: list,
    result_history_entry: dict,
    confidence: float | None = None,
    source_columns: list[str] | None = None,
):
    history_id = str(time.time_ns())
    created_at = pd.Timestamp.now("UTC").isoformat()
    dataset_key = _active_dataset_cache_key()
    dataset_label = _active_dataset_label()
    st.session_state["messages"].append({"role": "user", "content": query})
    if isinstance(result, pd.DataFrame):
        preview = result.head(5).to_string(index=False)
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    elif isinstance(result, pd.Series):
        preview = result.head(5).to_string()
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    else:
        st.session_state["messages"].append({"role": "assistant", "content": str(result)})

    st.session_state["analysis_result"] = result
    st.session_state["last_result"] = result
    st.session_state["last_query"] = query

    if "result_history" not in st.session_state:
        st.session_state["result_history"] = []
    if "result_history_details" not in st.session_state:
        st.session_state["result_history_details"] = []

    # Dedupe before append
    if not _is_recent_duplicate(query, history_id, st.session_state.get("chat_history", [])):
        st.session_state["result_history"].append(result)
        st.session_state["result_history_details"].append(result_history_entry)
        st.session_state["analysis_query"] = query
    else:
        logger.warning("skipping_duplicate_persist_cycle", extra={"query": query[:100], "history_id": history_id})

    if chart_data is not None:
        st.session_state["chart_data"] = chart_data
        st.session_state["report_charts"] = chart_figs

    report_insight = insight if insight else (ai_response if ai_response else "Analysis completed.")
    if "<Axes:" in str(report_insight) or "<AxesSubplot" in str(report_insight):
        report_insight = ai_response if ai_response else "Analysis completed - see AI response for details."

    if not query_rejected:
        st.session_state["analysis_history"].append(
            {
                "query": query,
                "result": result if not is_axes_result else None,
                "code": code,
                "insight": report_insight,
                "ai_response": ai_response,
                "charts": chart_figs,
                "summary": summary_list,
                "intent": intent,
                "confidence": confidence,
                "source_columns": source_columns or [],
            }
        )

    st.session_state["chat_history"].append(
        {
            "history_id": history_id,
            "dataset_key": dataset_key,
            "dataset_label": dataset_label,
            "created_at": created_at,
            "query": query,
            "result": result,
            "code": code if not query_rejected else "",
            "chart_data": chart_data if not query_rejected else None,
            "insight": insight if not query_rejected else "",
            "summary": summary_list if not query_rejected else [],
            "charts": chart_figs if not query_rejected else [],
            "ai_response": ai_response,
            "suggestions": suggestions if (not query_rejected and suggestions) else "",
            "query_rejected": query_rejected,
            "confidence": confidence,
            "source_columns": source_columns or [],
            "intent": intent,
            "rephrases": rephrases,
        }
    )

    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
    if user_id:
        latest_entry = st.session_state["chat_history"][-1]
        try:
            ok, cloud_history_id = save_cloud_chat_history(user_id, access_token, _active_dataset_cache_key(), latest_entry)
            logger = get_logger("app_state")
            logger.info("persist_analysis_cycle_cloud_save", extra={"user_id": user_id, "ok": bool(ok), "cloud_history_id": cloud_history_id})
            if ok and cloud_history_id:
                latest_entry["cloud_history_id"] = cloud_history_id
        except Exception as exc:
            get_logger("app_state").exception("persist_analysis_cycle_cloud_save_failed", exc_info=True)

    persist_dataset_state()
