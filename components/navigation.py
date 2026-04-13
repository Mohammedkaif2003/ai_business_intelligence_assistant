import streamlit as st

NAV_OPTIONS = [
    ("overview", "Data Overview"),
    ("chat", "AI Analyst"),
    ("forecast", "Forecasting"),
    ("reports", "Reports"),
]


def _label_for(option_id: str) -> str:
    labels = {k: v for k, v in NAV_OPTIONS}
    return labels.get(option_id, option_id)


def render_main_navigation(logger=None) -> str:
    default_page = "chat" if st.session_state.get("pending_query") or st.session_state.get("auto_query") else "overview"
    active_page = st.session_state.get("active_page_radio", st.session_state.get("active_page", default_page))

    valid_pages = [item[0] for item in NAV_OPTIONS]
    if active_page not in valid_pages:
        active_page = default_page

    st.session_state["active_page"] = active_page

    # Initialize radio state once. Do not overwrite it on every rerun,
    # otherwise user clicks are immediately reverted.
    if "active_page_radio" not in st.session_state or st.session_state["active_page_radio"] not in valid_pages:
        st.session_state["active_page_radio"] = active_page

    target_page = str(st.session_state.get("navigation_target_page", "") or "").strip()
    if target_page in valid_pages:
        st.session_state["active_page"] = target_page
        st.session_state["active_page_radio"] = target_page
        st.session_state["navigation_target_page"] = ""

    st.markdown('<div class="main-nav-wrap">', unsafe_allow_html=True)
    selected_page = st.radio(
        "Main Navigation",
        options=valid_pages,
        key="active_page_radio",
        horizontal=True,
        label_visibility="collapsed",
        format_func=_label_for,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    previous_page = st.session_state.get("last_active_page", active_page)
    if selected_page != previous_page and logger:
        logger.info("navigation_switched", extra={"from": previous_page, "to": selected_page})

    st.session_state["active_page"] = selected_page
    st.session_state["last_active_page"] = selected_page
    return selected_page
