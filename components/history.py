import streamlit as st
from datetime import datetime, timedelta


def _parse_datetime(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        # Supabase often returns UTC timestamps with trailing Z.
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
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


def render_chat_history_sidebar(history_entries: list[dict]) -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Chat History")
    st.sidebar.caption("Saved one-time chats. Click a chat to open it.")

    if st.sidebar.button("＋ New chat", key="new_chat_btn", width="stretch"):
        st.session_state["selected_chat_history_id"] = ""
        st.session_state["chat_view_mode"] = "new"
        st.session_state["active_page"] = "chat"
        st.session_state["navigation_target_page"] = "chat"

    if not history_entries:
        st.sidebar.caption("No saved chats yet.")
        return

    search_text = st.sidebar.text_input("Search chats", key="chat_history_search", placeholder="Search by question...")

    selected_history_id = str(st.session_state.get("selected_chat_history_id", "") or "").strip()
    ordered_entries = [entry for entry in reversed(history_entries) if _matches_search(entry, search_text)]

    if not ordered_entries:
        st.sidebar.caption("No chats match your search.")
        return

    current_group = None

    for index, entry in enumerate(ordered_entries, start=1):
        history_id = str(entry.get("history_id") or entry.get("cloud_history_id") or "").strip()
        if not history_id:
            history_id = f"history_{index}"

        is_selected = history_id == selected_history_id
        title = _title_for_entry(entry, len(history_entries) - index + 1)

        group = _group_label(entry.get("created_at"))
        if group != current_group:
            current_group = group
            st.sidebar.markdown(f"**{group}**")

        cols = st.sidebar.columns([0.82, 0.18])
        with cols[0]:
            button_label = f"▶ {title}" if is_selected else title
            if st.button(button_label, key=f"history_select_{history_id}", width="stretch"):
                st.session_state["selected_chat_history_id"] = history_id
                st.session_state["chat_view_mode"] = ""
                st.session_state["active_page"] = "chat"
                st.session_state["navigation_target_page"] = "chat"
        with cols[1]:
            if st.button("🗑", key=f"history_delete_{history_id}", help="Delete this chat", width="stretch"):
                st.session_state["delete_chat_history_id"] = history_id
