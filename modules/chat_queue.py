import time

import streamlit as st


def queue_query(query_text: str) -> None:
    cleaned = str(query_text or "").strip()
    if not cleaned:
        return

    # Always route queued actions (follow-ups, rephrases, quick prompts) to the
    # active live chat flow so a single click triggers visible processing.
    st.session_state["selected_chat_history_id"] = ""
    # Ensure the chat view is set to a fresh canvas so the pending query is visible
    # and the analyst workspace renders the live chat processing UI.
    st.session_state["chat_view_mode"] = "new"
    # Store both `auto_query` (used by chat input flow) and `pending_query` (used by processing flow)
    # to make follow-up clicks robust across reruns and UI layouts.
    st.session_state["pending_query"] = cleaned
    st.session_state["pending_query_id"] = str(time.time_ns())
    st.session_state["auto_query"] = cleaned
    st.session_state["active_page"] = "chat"
    st.session_state["navigation_target_page"] = "chat"
    # Do not force a rerun here; updating `st.session_state` is sufficient for Streamlit
    # to pick up the pending query on the next natural rerun triggered by the UI.
