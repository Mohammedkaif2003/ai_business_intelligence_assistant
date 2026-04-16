from datetime import datetime, timedelta
import re

import streamlit as st
from config import FRIENDLY_DATASET_NAMES

from modules.app_state import open_chat_history, start_new_chat, delete_chat_history_entry, delete_history_immediate
from modules.app_secrets import get_secret
from utils.logging import get_logger


logger = get_logger("history")


def _parse_datetime(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception as exc:
        logger.warning("chat_history_timestamp_parse_failed", extra={"value": text[:120], "error": str(exc)[:200]})
        return None


def _group_label(created_at: str | None) -> str:
    parsed = _parse_datetime(created_at)
    if parsed is None:
        return "Older"

    today = datetime.now(parsed.tzinfo).date() if parsed.tzinfo else datetime.now().date()
    chat_day = parsed.date()
    if chat_day == today:
        return "Today"
    if chat_day == (today - timedelta(days=1)):
        return "Yesterday"
    return chat_day.strftime("%b %d, %Y")


def _title_for_entry(entry: dict, index: int) -> str:
    query = str(entry.get("query", "") or "").strip().replace("\n", " ")
    if not query:
        return f"Chat {index}"

    if len(query) > 54:
        return f"{query[:51].rstrip()}..."
    return query


def _matches_search(entry: dict, search_text: str) -> bool:
    term = str(search_text or "").strip().lower()
    if not term:
        return True

    query = str(entry.get("query", "") or "").lower()
    insight = str(entry.get("insight", "") or "").lower()
    response = str(entry.get("ai_response", "") or "").lower()
    return term in query or term in insight or term in response


def _entry_dataset_label(entry: dict, fallback: str) -> str:
    def _is_hash_like(value: str) -> bool:
        text = str(value or "").strip().lower()
        if not text:
            return False
        # Hex-like short ids (e.g. d65eb363) or longer hashes; treat UUIDs and hex strings as hash-like.
        if re.fullmatch(r"[a-f0-9]{6,64}", text):
            return True
        if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text):
            return True
        return False


    preferred = str(entry.get("dataset_label", "") or "").strip()
    dataset_text = str(entry.get("dataset_key", "") or "").strip()

    # Only use fallback if it's not the current loaded dataset name and not a hash.
    fallback_text = str(fallback or "").strip()
    if fallback_text == dataset_text or _is_hash_like(fallback_text):
        fallback_text = ""

    # 1) Prefer explicit human label stored with the entry.
    if preferred and not _is_hash_like(preferred):
        return FRIENDLY_DATASET_NAMES.get(preferred, preferred)

    # 2) Use per-entry dataset_key when it's human-readable.
    if dataset_text and not _is_hash_like(dataset_text):
        return FRIENDLY_DATASET_NAMES.get(dataset_text, dataset_text)

    # 3) If entry has only an internal hash key, show a friendly "Uploaded <date>" label.
    if _is_hash_like(dataset_text):
        created = _parse_datetime(entry.get("created_at"))
        if created:
            return f"Uploaded {created.strftime('%b %d, %Y')}"
        return "Uploaded dataset"
    if _is_hash_like(preferred):
        created = _parse_datetime(entry.get("created_at"))
        if created:
            return f"Uploaded {created.strftime('%b %d, %Y')}"
        return "Uploaded dataset"

    # 4) Only if entry has no dataset identity, fallback to active dataset label (but not if it's a hash or matches the entry's key).
    if fallback_text and not _is_hash_like(fallback_text):
        return FRIENDLY_DATASET_NAMES.get(fallback_text, fallback_text)
    if _is_hash_like(fallback_text):
        # Prefer a generic uploaded label rather than exposing a hash-like fallback.
        return "Uploaded dataset"

    return "Uploaded dataset"


def render_chat_history_sidebar(
    history_entries: list[dict],
    *,
    dataset_loaded: bool,
    active_dataset_label: str | None,
    all_dataset_entries: list[dict] | None = None,
) -> None:
    if "deleted_history_ids" not in st.session_state or not isinstance(st.session_state.get("deleted_history_ids"), list):
        st.session_state["deleted_history_ids"] = []

    st.sidebar.markdown("---")
    st.sidebar.subheader("Saved Chats")
    st.sidebar.caption("All saved chats across datasets")

    # Helper to call Streamlit rerun/experimental_rerun and then stop execution.
    def _rerun_and_stop():
        # Prefer modern API if available, fall back to experimental.
        try:
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        except AttributeError:
            pass  # Streamlit version lacks API
        try:
            if hasattr(st, "stop"):
                st.stop()
        except AttributeError:
            pass  # Expected for older Streamlit

    # Handle any pending delete action before rendering the list. This
    # ensures the UI uses the latest state and avoids double-click issues.
    try:
        delete_id = str(st.session_state.get("delete_chat_history_id", "") or "").strip()
        if delete_id:
            removed = False
            try:
                removed = delete_history_immediate(delete_id)
            except (ValueError, KeyError):
                logger.warning("Delete history immediate failed", extra={"delete_id": delete_id})
                removed = False

            if removed:
                st.session_state["deleted_history_ids"] = list(st.session_state.get("deleted_history_ids", [])) + [delete_id]

            # Clear pending id and force rerun/stop so UI reflects deletion immediately.
            st.session_state["delete_chat_history_id"] = ""
            _rerun_and_stop()
    except Exception as e:
        logger.warning(f"History sidebar render error: {e}", exc_info=True)
        # Non-fatal: continue rendering if delete handling fails.

    new_chat_label = "+ New chat"
    if st.sidebar.button(new_chat_label, key="new_chat_btn", width="stretch", disabled=not dataset_loaded):
        start_new_chat()

    history_scope = "This Dataset"
    if all_dataset_entries is not None:
        history_scope = st.sidebar.radio(
            "History Scope",
            options=["This Dataset", "All Datasets"],
            key="chat_history_scope",
            horizontal=True,
        )

    scope_entries = history_entries if history_scope == "This Dataset" else list(all_dataset_entries or [])
    if not scope_entries:
        empty_message = "No saved chats for this dataset yet." if history_scope == "This Dataset" else "No saved chats across datasets yet."
        st.sidebar.caption(empty_message)
        return

    search_text = st.sidebar.text_input("Search chats", key="chat_history_search", placeholder="Search by question...")

    selected_history_id = str(st.session_state.get("selected_chat_history_id", "") or "").strip()
    deleted_ids = {str(item or "").strip() for item in st.session_state.get("deleted_history_ids", []) if str(item or "").strip()}
    ordered_entries = []
    for entry in reversed(scope_entries):
        entry_id = str(entry.get("cloud_history_id") or entry.get("history_id") or "").strip()
        if entry_id and entry_id in deleted_ids:
            continue
        if _matches_search(entry, search_text):
            ordered_entries.append(entry)

    if not ordered_entries:
        st.sidebar.caption("No chats match your search.")
        return

    current_group = None

    for index, entry in enumerate(ordered_entries, start=1):
        # Compute a stable identity for the entry. Prefer `cloud_history_id`,
        # then `history_id`. If neither exists (e.g. cached entries without
        # an id), fall back to a deterministic signature that won't change
        # between reruns: `sig::dataset_key::created_at::query`.
        cloud_id = str(entry.get("cloud_history_id") or "").strip()
        local_id = str(entry.get("history_id") or "").strip()
        if cloud_id:
            history_id = cloud_id
        elif local_id:
            history_id = local_id
        else:
            ds = str(entry.get("dataset_key", "") or "").strip()
            created = str(entry.get("created_at", "") or "").strip()
            query_text = str(entry.get("query", "") or "").strip()
            history_id = f"sig::{ds}::{created}::{query_text}"

        is_selected = history_id == selected_history_id
        title = _title_for_entry(entry, len(scope_entries) - index + 1)

        group = _group_label(entry.get("created_at"))
        if group != current_group:
            current_group = group
            st.sidebar.markdown(f"**{group}**")

        entry_dataset_label = _entry_dataset_label(entry, str(active_dataset_label or "dataset"))
        is_cross_dataset = history_scope == "All Datasets" and entry_dataset_label != str(active_dataset_label or "")
        if history_scope == "All Datasets":
            st.sidebar.caption(f"Dataset: {entry_dataset_label}")

        cols = st.sidebar.columns([0.82, 0.18])
        with cols[0]:
            button_label = f"> {title}" if is_selected else title
            if st.button(
                button_label,
                key=f"history_select_{history_id}",
                width="stretch",
                disabled=is_cross_dataset,
                help="Switch to this dataset to open this chat." if is_cross_dataset else None,
            ):
                logger.info("sidebar_open_chat_clicked", extra={"history_id": history_id, "index": index, "is_cross_dataset": bool(is_cross_dataset)})
                # Set selected id and force rerun so UI updates immediately.
                st.session_state["selected_chat_history_id"] = history_id
                _rerun_and_stop()
        with cols[1]:
            if st.button(
                "Del",
                key=f"history_delete_{history_id}",
                help="Delete this chat" if not is_cross_dataset else "Switch to this dataset to delete this chat.",
                width="stretch",
                disabled=is_cross_dataset,
            ):
                logger.info("sidebar_delete_clicked", extra={"history_id": history_id, "index": index, "is_cross_dataset": bool(is_cross_dataset)})
                # Defer deletion handling to top-level: mark pending id and
                # force a rerun/stop so the deletion is processed before
                # the UI is re-rendered.
                st.session_state["delete_chat_history_id"] = history_id
                _rerun_and_stop()

    # Optional debug panel: enabled when DEBUG_HISTORY is set in .env or
    # when `st.session_state["DEBUG_HISTORY"] = True` (useful to diagnose clicks).
    debug_env = str(get_secret("DEBUG_HISTORY", "") or "").strip().lower()
    debug_enabled = bool(debug_env in ("1", "true", "yes")) or bool(st.session_state.get("DEBUG_HISTORY", False))
    if debug_enabled:
        with st.sidebar.expander("History Debug", expanded=False):
            st.write({
                "supabase_user_id": st.session_state.get("supabase_user_id"),
                "supabase_access_token_set": bool(st.session_state.get("supabase_access_token")),
                "selected_chat_history_id": st.session_state.get("selected_chat_history_id"),
                "delete_chat_history_id": st.session_state.get("delete_chat_history_id"),
                "deleted_history_ids": st.session_state.get("deleted_history_ids"),
                "chat_history_count": len(st.session_state.get("chat_history", [])),
            })
