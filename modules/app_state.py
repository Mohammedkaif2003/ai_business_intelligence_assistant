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

from modules.prompt_cache import get_cached_dataset_state, save_cached_dataset_state, get_all_cached_dataset_states
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
                rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=None, limit=500)
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

    rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=None, limit=limit)
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

    def _add_if_new(entry: dict) -> None:
        identity_keys = _entry_identity_keys(entry)
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
        if query:
            st.session_state["messages"].append({"role": "user", "content": query})
        if answer:
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
    except Exception:
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
                except Exception:
                    # non-fatal; continue
                    pass
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
            cloud_deleted = delete_cloud_chat_history(user_id, access_token, hid)
            logger.info("cloud_delete_attempted", extra={"history_id": hid, "cloud_deleted": bool(cloud_deleted)})
        except Exception:
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
    except Exception:
        logger.exception("clear_delete_state_failed", extra={"history_id": hid})

    return bool(cloud_deleted or local_deleted)


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
    st.session_state["messages"].append({"role": "user", "content": query})
    if isinstance(result, pd.DataFrame):
        preview = result.head(5).to_string(index=False)
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    elif isinstance(result, pd.Series):
        preview = result.head(5).to_string()
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    else:
        st.session_state["messages"].append({"role": "assistant", "content": str(result)})


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
    except Exception:
        get_logger("app_state").exception("store_analysis_cloud_save_failed")

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
                    except Exception:
                        # non-fatal
                        pass
    except Exception:
        # Don't let cleanup errors break the main flow
        pass


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
        except Exception:
            get_logger("app_state").exception("persist_analysis_cycle_cloud_save_failed")

    persist_dataset_state()
