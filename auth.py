"""Simple session-based login gate for Apex Analytics."""
from __future__ import annotations

import hashlib
import html
import json
import os

import streamlit as st

_AUTH_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(_AUTH_DIR, "users.json")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _ensure_users_file() -> None:
    if os.path.exists(USERS_FILE):
        return
    defaults = {
        "admin": {
            "password_hash": _hash("admin123"),
            "display_name": "Administrator",
            "role": "admin",
        },
        "analyst": {
            "password_hash": _hash("analyst123"),
            "display_name": "Business Analyst",
            "role": "analyst",
        },
    }
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(defaults, f, indent=2)


def _load_users() -> dict:
    _ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_authenticated() -> bool:
    return bool(st.session_state.get("auth_user"))


def current_user() -> dict:
    return {
        "username": st.session_state.get("auth_user", ""),
        "display_name": st.session_state.get("auth_display_name", ""),
        "role": st.session_state.get("auth_role", ""),
    }


def logout() -> None:
    for key in ("auth_user", "auth_display_name", "auth_role"):
        st.session_state.pop(key, None)


def _verify(username: str, password: str) -> dict | None:
    users = _load_users()
    record = users.get(username.strip().lower())
    if not record:
        return None
    if record.get("password_hash") != _hash(password):
        return None
    return record


def render_login_view(app_title: str, app_icon: str) -> None:
    """Render the full-screen login page."""
    # Hide sidebar + default chrome on the login screen
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
            header[data-testid="stHeader"] { background: transparent; }
            .block-container { padding-top: 3.5rem !important; max-width: 520px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="login-hero">
            <div class="login-hero__badge">{html.escape(app_icon)}</div>
            <div class="login-hero__title">{html.escape(app_title)}</div>
            <div class="login-hero__subtitle">AI-Powered Business Intelligence</div>
            <div class="login-hero__divider"></div>
            <div class="login-hero__tag">Sign in to continue</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="e.g. admin", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Your password", key="login_password")
        submitted = st.form_submit_button("Sign In", type="primary", width='stretch')

    if submitted:
        if not username or not password:
            st.error("Please enter both username and password.")
            return
        record = _verify(username, password)
        if record is None:
            st.error("Invalid credentials. Please try again.")
            return
        st.session_state["auth_user"] = username.strip().lower()
        st.session_state["auth_display_name"] = record.get("display_name", username)
        st.session_state["auth_role"] = record.get("role", "user")
        st.rerun()

    with st.expander("Demo credentials", expanded=False):
        st.markdown(
            """
            **Administrator** &nbsp;·&nbsp; `admin` / `admin123`<br>
            **Business Analyst** &nbsp;·&nbsp; `analyst` / `analyst123`
            """,
            unsafe_allow_html=True
        )


def require_login(app_title: str, app_icon: str) -> None:
    """Block the rest of the app until the user signs in."""
    if is_authenticated():
        return
    render_login_view(app_title, app_icon)
    st.stop()


def render_sidebar_user_badge() -> None:
    """Small user card + logout button shown in the sidebar."""
    if not is_authenticated():
        return
    user = current_user()
    st.sidebar.markdown(
        f"""
        <div class="sidebar-user-card">
            <div class="sidebar-user-card__avatar">
                {html.escape((user['display_name'] or 'U')[:1].upper())}
            </div>
            <div>
                <div class="sidebar-user-card__name">{html.escape(user['display_name'])}</div>
                <div class="sidebar-user-card__role">{html.escape(str(user.get('role', '')).title())}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sign out", key="sidebar_logout_btn", width='stretch'):
        logout()
        st.rerun()
