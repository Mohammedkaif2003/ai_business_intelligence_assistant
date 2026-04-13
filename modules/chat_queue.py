import time

import streamlit as st


def queue_query(query_text: str) -> None:
    cleaned = str(query_text or "").strip()
    if not cleaned:
        return

    # Always route queued actions (follow-ups, rephrases, quick prompts) to the
    # active live chat flow so a single click triggers visible processing.
    st.session_state["selected_chat_history_id"] = ""
    st.session_state["chat_view_mode"] = ""
    st.session_state["pending_query"] = cleaned
    st.session_state["pending_query_id"] = str(time.time_ns())
    st.session_state["active_page"] = "chat"
    st.session_state["navigation_target_page"] = "chat"
