import streamlit as st
import pandas as pd
import os
import time
from io import BytesIO
from dotenv import load_dotenv
from modules.app_secrets import get_secret

# Load environment variables before importing app modules that may read secrets at import time.
load_dotenv(override=True)

# New separate files
from config import APP_ICON, APP_TITLE, APP_VERSION, DATA_DIR, FRIENDLY_DATASET_NAMES
from styles import inject_styles
from ui_components import (
    render_sidebar_dataset_badge,
)

# Existing modules (do not rename)
from modules.dataset_analyzer import analyze_dataset
from modules.data_loader import normalize_columns
from modules.dataset_activation import activate_dataset
from utils.logging import get_logger
from modules.app_state import ensure_analysis_state
from modules.app_state import delete_chat_history_entry
from modules.app_state import restore_persisted_analysis_state
from modules.app_state import restore_cloud_analysis_state
from modules.supabase_service import (
    is_supabase_enabled,
    delete_cloud_chat_history,
    sign_in_with_password,
    sign_out,
    sign_up_with_password,
)
from components.chat import render_chat_page
from components.dashboard import render_data_overview_page, render_dashboard_header
from components.forecast import render_forecasting_page
from components.history import render_chat_history_sidebar
from components.navigation import render_main_navigation
from components.reports import render_reports_page
from modules.upload_cache import compute_file_fingerprint, should_reuse_uploaded_dataframe

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide"
)
inject_styles(st)
logger = get_logger("app")


def _seed_auth_compat_keys() -> None:
    user = st.session_state.get("user")
    if isinstance(user, dict):
        st.session_state["supabase_user_id"] = str(user.get("id", "") or "")
        st.session_state["supabase_user_email"] = str(user.get("email", "") or "")
        st.session_state["supabase_access_token"] = str(user.get("access_token", "") or "")


@st.cache_data(show_spinner=False)
def load_dataset(file_bytes: bytes):
    df = pd.read_csv(BytesIO(file_bytes))
    df = normalize_columns(df)
    return df


@st.cache_data(show_spinner=False)
def load_local_dataset(path):
    df = pd.read_csv(path)
    df = normalize_columns(df)
    return df


def _render_login_shell() -> tuple[str, str, bool, bool]:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], [data-testid="collapsedControl"] {
                display: none;
            }

            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(900px 500px at 20% 5%, rgba(56, 189, 248, 0.15), rgba(2, 6, 23, 0) 60%),
                    radial-gradient(900px 550px at 90% 90%, rgba(99, 102, 241, 0.14), rgba(2, 6, 23, 0) 65%),
                    linear-gradient(165deg, #0b1220 0%, #070b14 55%, #03050a 100%);
            }

            .main .block-container {
                max-width: 100%;
                padding-top: 0.2vh;
                padding-bottom: 0.2vh;
            }

            .auth-logo {
                font-size: 18px;
                margin-bottom: 4px;
            }

            .auth-title {
                font-size: 27px;
                font-weight: 800;
                color: #f8fbff;
                margin-bottom: 1px;
                letter-spacing: 0.01em;
            }

            .auth-subtitle {
                color: #b6c4de;
                font-size: 12.5px;
                line-height: 1.4;
                margin-bottom: 8px;
            }

            [data-testid="stForm"] {
                width: min(420px, 94vw) !important;
                margin: 10vh auto 0 auto !important;
                border: 1px solid rgba(148, 163, 184, 0.2) !important;
                border-radius: 16px !important;
                background: linear-gradient(155deg, rgba(15, 23, 42, 0.74), rgba(30, 41, 59, 0.52)) !important;
                backdrop-filter: blur(12px) !important;
                box-shadow: 0 16px 34px rgba(2, 6, 23, 0.4) !important;
                padding: 16px 16px 12px 16px !important;
                transition: transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease !important;
            }

            [data-testid="stForm"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 24px 50px rgba(2, 6, 23, 0.5) !important;
                border-color: rgba(125, 211, 252, 0.36) !important;
            }

            [data-testid="stForm"] .stTextInput {
                margin-bottom: 0.2rem;
            }

            [data-testid="stForm"] div[data-baseweb="input"] > div {
                background: rgba(15, 23, 42, 0.68) !important;
                border: 1px solid rgba(148, 163, 184, 0.25) !important;
                border-radius: 12px !important;
                transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input {
                background: transparent !important;
                color: #e8f2ff !important;
                -webkit-text-fill-color: #e8f2ff !important;
                caret-color: #93c5fd !important;
                font-size: 0.98rem !important;
                font-weight: 500 !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input::placeholder {
                color: #9fb2cb !important;
                -webkit-text-fill-color: #9fb2cb !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill,
            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill:hover,
            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill:focus,
            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill:active {
                -webkit-text-fill-color: #e8f2ff !important;
                transition: background-color 9999s ease-in-out 0s !important;
                box-shadow: 0 0 0 1000px rgba(15, 23, 42, 0.01) inset !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input:-moz-autofill {
                color: #e8f2ff !important;
                box-shadow: 0 0 0 1000px rgba(15, 23, 42, 0.01) inset !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] > div:focus-within {
                border-color: rgba(96, 165, 250, 0.95) !important;
                box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.22) !important;
                transform: translateY(-1px);
            }

            [data-testid="stForm"] label p {
                color: #d8e3f7 !important;
                font-weight: 600 !important;
            }

            .password-row {
                margin-top: 0px;
            }

            .password-eye-col {
                margin-left: -38px;
                z-index: 5;
            }

            .password-eye-col [data-testid="stCheckbox"] {
                margin-top: 30px;
                background: rgba(15, 23, 42, 0.82);
                border: 1px solid rgba(148, 163, 184, 0.32);
                border-radius: 9px;
                padding: 2px 6px;
            }

            .password-eye-col [data-testid="stCheckbox"] label p {
                font-size: 11px !important;
                color: #dbeafe !important;
            }

            [data-testid="stFormSubmitButton"] button[kind="primary"] {
                border-radius: 12px !important;
                border: 1px solid rgba(59, 130, 246, 0.8) !important;
                background: linear-gradient(120deg, #2563eb, #4f46e5) !important;
                box-shadow: 0 10px 24px rgba(37, 99, 235, 0.34) !important;
                transition: transform 140ms ease, box-shadow 140ms ease, filter 140ms ease;
            }

            [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
                transform: translateY(-1px) scale(1.01);
                box-shadow: 0 12px 26px rgba(37, 99, 235, 0.42) !important;
                filter: brightness(1.04);
            }

            [data-testid="stFormSubmitButton"] button[kind="secondary"] {
                border-radius: 12px !important;
                border: 1px solid rgba(148, 163, 184, 0.5) !important;
                background: rgba(15, 23, 42, 0.4) !important;
                color: #d7e2f7 !important;
                transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
            }

            [data-testid="stFormSubmitButton"] button[kind="secondary"]:hover {
                transform: translateY(-1px);
                border-color: rgba(96, 165, 250, 0.8) !important;
                background: rgba(30, 41, 59, 0.6) !important;
            }

            @media (max-width: 560px) {
                [data-testid="stForm"] {
                    margin-top: 6vh !important;
                    width: min(94vw, 420px) !important;
                }
            }

            @keyframes authFadeIn {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.form("auth_form", border=False):
        st.markdown('<div class="auth-logo">🤖</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">Welcome Back</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-subtitle">Sign in or create your account to continue to your analytics workspace.</div>',
            unsafe_allow_html=True,
        )

        email = st.text_input("Email", placeholder="you@example.com")

        st.markdown('<div class="password-row">', unsafe_allow_html=True)
        pass_col, eye_col = st.columns([0.86, 0.14], gap="small")
        with pass_col:
            password = st.text_input(
                "Password",
                type="default" if st.session_state.get("auth_show_password", False) else "password",
                placeholder="••••••••",
            )
        with eye_col:
            st.markdown('<div class="password-eye-col">', unsafe_allow_html=True)
            st.checkbox("👁", key="auth_show_password", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        action_cols = st.columns(2)
        with action_cols[0]:
            do_login = st.form_submit_button("Login", type="primary", use_container_width=True)
        with action_cols[1]:
            do_signup = st.form_submit_button("Sign Up", type="secondary", use_container_width=True)
    return email, password, do_login, do_signup


def show_login() -> None:
    if not is_supabase_enabled():
        st.error("Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY in .env or Streamlit secrets.")
        st.stop()

    email, password, do_login, do_signup = _render_login_shell()

    if do_signup:
        with st.spinner("Creating your account..."):
            ok, message = sign_up_with_password(email, password)
        if ok:
            st.success(message)
        else:
            st.error(message)

    if do_login:
        with st.spinner("Signing you in..."):
            ok, message, user_data = sign_in_with_password(email, password)
        if ok and user_data:
            st.session_state["user"] = {
                "id": user_data.get("id", ""),
                "email": user_data.get("email", email),
                "access_token": user_data.get("access_token", ""),
            }
            _seed_auth_compat_keys()
            ensure_analysis_state()
            st.rerun()
        else:
            st.error(message)


def _logout() -> None:
    user = st.session_state.get("user") or {}
    token = str(user.get("access_token", "") or st.session_state.get("supabase_access_token", "") or "").strip()
    if token:
        sign_out(token)
    st.session_state.clear()
    st.rerun()


def load_csv_with_friendly_error(loader_fn, source_label: str, *args):
    try:
        return loader_fn(*args), None
    except Exception:
        return None, f"Invalid CSV format. Please check delimiters, encoding, or missing headers while loading {source_label}."


def _handle_history_deletion() -> None:
    delete_history_id = str(st.session_state.get("delete_chat_history_id", "") or "").strip()
    if not delete_history_id:
        return

    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
    selected_entry = next(
        (entry for entry in st.session_state.get("chat_history", []) if str(entry.get("history_id") or entry.get("cloud_history_id") or "").strip() == delete_history_id),
        None,
    )
    if selected_entry is not None and selected_entry.get("cloud_history_id") and user_id and access_token:
        delete_cloud_chat_history(user_id, access_token, str(selected_entry.get("cloud_history_id")))

    try:
        delete_chat_history_entry(delete_history_id)
    finally:
        st.session_state["delete_chat_history_id"] = ""
        st.session_state["selected_chat_history_id"] = ""
        st.rerun()


def show_app() -> None:
    _seed_auth_compat_keys()
    ensure_analysis_state()
    st.session_state["app_logger"] = logger

    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        st.error("Groq API key not found. Add it to .env for local use or to Streamlit secrets for deployment.")
        st.stop()

    user = st.session_state.get("user") or {}
    user_email = str(user.get("email", "") or "").strip()

    # ---------- SIDEBAR ----------
    st.sidebar.markdown(f"### 👤 {user_email or 'Authenticated User'}")
    if st.sidebar.button("Logout", key="logout_btn", width="stretch"):
        _logout()

    st.sidebar.subheader("📂 Select Data Source")
    data_source = st.sidebar.radio(
        "Choose how to load data:",
        ["Upload CSV", "Use Pre-loaded Dataset"]
    )

    selected_key = None
    df_to_load = None
    dataset_fingerprint = None

    if data_source == "Upload CSV":
        uploaded_file = st.sidebar.file_uploader("Upload CSV Dataset", type=["csv"])

        if uploaded_file:
            uploaded_name = uploaded_file.name
            uploaded_bytes = uploaded_file.getvalue()
            uploaded_fingerprint = compute_file_fingerprint(uploaded_bytes)
            cached_uploaded_fingerprint = st.session_state.get("uploaded_fingerprint")
            cached_uploaded_df = st.session_state.get("uploaded_df")

            if should_reuse_uploaded_dataframe(cached_uploaded_df, cached_uploaded_fingerprint, uploaded_fingerprint):
                selected_key = uploaded_name
                df_to_load = cached_uploaded_df
            else:
                selected_key = uploaded_name
                load_started = time.perf_counter()
                df_to_load, load_error = load_csv_with_friendly_error(load_dataset, uploaded_name, uploaded_bytes)
                if load_error:
                    st.sidebar.error(load_error)
                    st.stop()
                logger.info(
                    "dataset_upload_loaded",
                    extra={"dataset": selected_key, "load_ms": round((time.perf_counter() - load_started) * 1000, 2)},
                )
                st.session_state["uploaded_df"] = df_to_load

            st.session_state["uploaded_name"] = selected_key
            st.session_state["uploaded_fingerprint"] = uploaded_fingerprint
            dataset_fingerprint = uploaded_fingerprint

        elif "uploaded_df" in st.session_state:
            df_to_load = st.session_state["uploaded_df"]
            selected_key = st.session_state["uploaded_name"]
    else:
        data_dir = os.path.join(os.path.dirname(__file__), DATA_DIR)
        if os.path.exists(data_dir):
            csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
            if csv_files:
                display_names = [FRIENDLY_DATASET_NAMES.get(f, f) for f in csv_files]
                selected_display = st.sidebar.selectbox("Select a dataset:", display_names)
                selected_file = csv_files[display_names.index(selected_display)]
                selected_key = selected_file
                if st.session_state.get("active_dataset_key") == selected_key and st.session_state.get("df") is not None:
                    df_to_load = st.session_state["df"]
                else:
                    file_path_to_load = os.path.join(data_dir, selected_file)
                    load_started = time.perf_counter()
                    df_to_load, load_error = load_csv_with_friendly_error(load_local_dataset, selected_file, file_path_to_load)
                    if load_error:
                        st.sidebar.error(load_error)
                        st.stop()
                    with open(file_path_to_load, "rb") as dataset_file:
                        selected_fingerprint = compute_file_fingerprint(dataset_file.read())
                    logger.info(
                        "dataset_preloaded_loaded",
                        extra={"dataset": selected_key, "load_ms": round((time.perf_counter() - load_started) * 1000, 2)},
                    )
                    dataset_fingerprint = selected_fingerprint
            else:
                st.sidebar.warning(f"No CSV files found in {DATA_DIR} folder.")
        else:
            st.sidebar.warning(f"{DATA_DIR} folder not found.")

    if selected_key and df_to_load is not None:
        activation_started = time.perf_counter()
        was_activated = activate_dataset(selected_key, df_to_load, dataset_fingerprint=dataset_fingerprint)
        logger.info(
            "dataset_activation_checked",
            extra={
                "dataset": selected_key,
                "activated": was_activated,
                "activation_ms": round((time.perf_counter() - activation_started) * 1000, 2),
            },
        )
        if was_activated:
            st.sidebar.markdown(
                f"<div class='sidebar-success-inline'>✅ {selected_key} loaded successfully</div>",
                unsafe_allow_html=True,
            )
            restore_persisted_analysis_state()
            restore_cloud_analysis_state()

    if "df" not in st.session_state or st.session_state["df"] is None:
        st.markdown(
            """
            <div class="empty-state-hero">
                <div class="empty-state-hero__title">📊 Analyze your data instantly</div>
                <div class="empty-state-hero__subtitle">Upload a CSV or select a dataset to start exploring insights.</div>
                <div class="empty-state-hero__support">Supports CSV files (e.g. sales, finance, analytics)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    df = st.session_state["df"]
    schema = st.session_state.get("schema", analyze_dataset(df))

    render_sidebar_dataset_badge(st.session_state["dataset_name"], df.shape[0], df.shape[1])
    render_chat_history_sidebar(st.session_state.get("chat_history", []))
    _handle_history_deletion()

    # ---------- MAIN AREA ----------
    render_dashboard_header(df)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if st.session_state.get("pending_query") or st.session_state.get("auto_query"):
        st.session_state["active_page"] = "chat"

    active_page = render_main_navigation(logger)

    if active_page == "overview":
        render_data_overview_page(df)
    elif active_page == "chat":
        render_chat_page(df, schema, api_key, logger)
    elif active_page == "forecast":
        render_forecasting_page(df)
    elif active_page == "reports":
        render_reports_page()

    st.markdown(f"""
    <div style="
    text-align:center;
    color:#94A3B8;
    font-size:12px;
    margin-top:2rem;
    padding:1.2rem 0.6rem;
    opacity:0.85;
    ">
      {APP_TITLE} v{APP_VERSION} · Powered by Groq AI
    </div>
    """, unsafe_allow_html=True)


if "user" not in st.session_state:
    show_login()
else:
    show_app()
