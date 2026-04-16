import streamlit as st
import contextlib
import time

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
    active_page = st.session_state.get("active_page", default_page)
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = _label_for(active_page)
    # Ensure visual_tabs index reflects the active page on first render
    if "visual_tabs" not in st.session_state:
        st.session_state["visual_tabs"] = next(
            (i for i, (pid, _) in enumerate(NAV_OPTIONS) if pid == active_page), 0
        )

    valid_pages = [item[0] for item in NAV_OPTIONS]
    if active_page not in valid_pages:
        active_page = default_page

    st.session_state["active_page"] = active_page

    target_page = str(st.session_state.get("navigation_target_page", "") or "").strip()
    if target_page in valid_pages:
        st.session_state["active_page"] = target_page
        active_page = target_page
        st.session_state["active_tab"] = _label_for(target_page)
        # update visual tab index so the UI reflects programmatic navigation
        st.session_state["visual_tabs"] = next(
            (i for i, (pid, _) in enumerate(NAV_OPTIONS) if pid == target_page), 0
        )
        st.session_state["navigation_target_page"] = ""

    # Use a container if available; fall back to a no-op context for test mocks
    container_ctx = st.container() if hasattr(st, "container") else contextlib.nullcontext()
    with container_ctx:
        st.markdown('<div class="top-tabs">', unsafe_allow_html=True)
        # If Streamlit supports columns/buttons, render custom pill buttons.
        if hasattr(st, "columns") and hasattr(st, "button"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                is_active = st.session_state.get("active_page") == "overview"
                if st.button("Data Overview", key="tab_overview"):
                    st.session_state["active_page"] = "overview"
                    st.session_state["active_tab"] = _label_for("overview")
                    st.session_state["visual_tabs"] = 0
                    st.rerun()
                if is_active:
                    st.markdown('<div style="position: absolute; bottom: -4px; left: 50%; transform: translateX(-50%); width: 24px; height: 3px; background: #3B82F6; border-radius: 2px;"></div>', unsafe_allow_html=True)
            with col2:
                is_active = st.session_state.get("active_page") == "chat"
                if st.button("AI Analyst", key="tab_chat"):
                    st.session_state["active_page"] = "chat"
                    st.session_state["active_tab"] = _label_for("chat")
                    st.session_state["visual_tabs"] = 1
                    st.rerun()
                if is_active:
                    st.markdown('<div style="position: absolute; bottom: -4px; left: 50%; transform: translateX(-50%); width: 24px; height: 3px; background: #3B82F6; border-radius: 2px;"></div>', unsafe_allow_html=True)
            with col3:
                is_active = st.session_state.get("active_page") == "forecast"
                if st.button("Forecasting", key="tab_forecast"):
                    st.session_state["active_page"] = "forecast"
                    st.session_state["active_tab"] = _label_for("forecast")
                    st.session_state["visual_tabs"] = 2
                    st.rerun()
                if is_active:
                    st.markdown('<div style="position: absolute; bottom: -4px; left: 50%; transform: translateX(-50%); width: 24px; height: 3px; background: #3B82F6; border-radius: 2px;"></div>', unsafe_allow_html=True)
            with col4:
                is_active = st.session_state.get("active_page") == "reports"
                if st.button("Reports", key="tab_reports"):
                    st.session_state["active_page"] = "reports"
                    st.session_state["active_tab"] = _label_for("reports")
                    st.session_state["visual_tabs"] = 3
                    st.rerun()
                if is_active:
                    st.markdown('<div style="position: absolute; bottom: -4px; left: 50%; transform: translateX(-50%); width: 24px; height: 3px; background: #3B82F6; border-radius: 2px;"></div>', unsafe_allow_html=True)
        else:
            # Fallback: use Streamlit's tabs widget when available in mock or runtime
            try:
                st.tabs([label for _, label in NAV_OPTIONS], key="visual_tabs")
            except Exception:
                # some minimal mocks may not implement tabs; ignore
                pass

        st.markdown('</div>', unsafe_allow_html=True)

    # Get current active index for logging
    # Sync visual selection (from `visual_tabs`) to `active_page` for fallback/tab-based flows
    tab_index = st.session_state.get(
        "visual_tabs",
        next((i for i, (_, label) in enumerate(NAV_OPTIONS) if label == st.session_state.get("active_tab", "")), 0),
    )

    selected_index = int(tab_index or 0)
    active_index = next((i for i, (pid, _) in enumerate(NAV_OPTIONS) if pid == st.session_state.get("active_page", "overview")), 0)
    if selected_index != active_index:
        new_page_id = NAV_OPTIONS[selected_index][0]
        st.session_state["active_page"] = new_page_id
        st.session_state["active_tab"] = NAV_OPTIONS[selected_index][1]
        st.session_state["last_active_page"] = new_page_id
        # reflect immediately for the caller
        active_page = new_page_id
        try:
            st.rerun()
        except Exception:
            # Some Streamlit test mocks may not implement rerun; ignore
            pass

    previous_page = st.session_state.get("last_active_page", active_page)
    if active_page != previous_page and logger:
        logger.info("navigation_switched", extra={"from": previous_page, "to": active_page})

    return active_page
