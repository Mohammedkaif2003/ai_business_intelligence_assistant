import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import time
import json
from io import BytesIO
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
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
from modules.app_state import delete_chat_history_everywhere
from modules.app_state import restore_persisted_analysis_state
from modules.app_state import restore_cloud_analysis_state
from modules.app_state import clear_analysis_state_memory
from modules.app_state import start_new_chat
from modules.app_state import get_sidebar_history_entries
from modules.supabase_service import (
    is_supabase_enabled,
    delete_cloud_chat_history,
    sign_in_with_password,
    sign_out,
    sign_up_with_password,
    send_password_reset_email,
    update_password,
    verify_recovery_token,
    validate_access_token,
)
from components.chat import render_chat_page
from components.dashboard import render_data_overview_page, render_dashboard_header
from components.forecast import render_forecasting_page
from components.history import render_chat_history_sidebar
from components.navigation import render_main_navigation
from components.reports import render_reports_page
from modules.upload_cache import compute_file_fingerprint, should_reuse_uploaded_dataframe
from modules.app_perf import record_timing

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide"
)
inject_styles(st)
logger = get_logger("app")


def _remember_me_file_path() -> str:
    return os.path.join(DATA_DIR, "cache", "remembered_auth.json")


def _is_local_remember_me_enabled() -> bool:
    mode = str(os.getenv("REMEMBER_ME_MODE", "local") or "local").strip().lower()
    return mode in {"1", "true", "yes", "on", "local", "dev", "development"}


def _load_remembered_auth() -> dict[str, str] | None:
    if not _is_local_remember_me_enabled():
        return None

    path = _remember_me_file_path()
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, dict):
            return None
        return {
            "id": str(payload.get("id", "") or "").strip(),
            "email": str(payload.get("email", "") or "").strip(),
            "access_token": str(payload.get("access_token", "") or "").strip(),
        }
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Failed to load remembered auth from {path}: {e}")
        return None


def _save_remembered_auth(user: dict[str, str]) -> None:
    if not _is_local_remember_me_enabled():
        return

    path = _remember_me_file_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        safe_payload = {
            "id": str(user.get("id", "") or "").strip(),
            "email": str(user.get("email", "") or "").strip(),
            "access_token": str(user.get("access_token", "") or "").strip(),
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(safe_payload, fh)
    except Exception:
        return


def _clear_remembered_auth() -> None:
    path = _remember_me_file_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        return


def _restore_user_from_remember_me() -> bool:
    if st.session_state.get("user"):
        return True

    if not _is_local_remember_me_enabled():
        _clear_remembered_auth()
        return False

    remembered = _load_remembered_auth()
    if not remembered:
        return False

    access_token = str(remembered.get("access_token", "") or "").strip()
    if not access_token:
        return False

    ok, user_data = validate_access_token(access_token)
    if not ok or not user_data:
        _clear_remembered_auth()
        return False

    if not user_data.get("email") and remembered.get("email"):
        user_data["email"] = remembered.get("email", "")

    st.session_state["user"] = user_data
    _seed_auth_compat_keys()
    ensure_analysis_state()
    return True


def _load_selected_dataset_context() -> tuple[str | None, pd.DataFrame | None, str | None]:
    selected_key = None
    df_to_load = None
    dataset_fingerprint = None

    st.sidebar.subheader("📂 Select Data Source")
    data_source = st.sidebar.radio(
        "Choose how to load data:",
        ["Upload CSV", "Use Pre-loaded Dataset"]
    )

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
            dataset_fingerprint = st.session_state.get("uploaded_fingerprint")
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
                    dataset_fingerprint = st.session_state.get("active_dataset_cache_key")
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

    return selected_key, df_to_load, dataset_fingerprint


def _seed_auth_compat_keys() -> None:
    user = st.session_state.get("user")
    if isinstance(user, dict):
        st.session_state["supabase_user_id"] = str(user.get("id", "") or "")
        st.session_state["supabase_user_email"] = str(user.get("email", "") or "")
        st.session_state["supabase_access_token"] = str(user.get("access_token", "") or "")


def _get_query_param(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value or "").strip()
    except Exception:
        return ""


def _clear_auth_query_params() -> None:
    for key in ("auth_action", "type", "access_token", "refresh_token", "token_hash", "token", "code", "error", "error_description"):
        try:
            if key in st.query_params:
                del st.query_params[key]
        except Exception:
            continue


def _with_query_params(url: str, extra_params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(extra_params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _extract_recovery_access_token(url_text: str) -> str:
    raw = str(url_text or "").strip()
    if not raw:
        return ""

    try:
        parsed = urlsplit(raw)
        query_map = dict(parse_qsl(parsed.query, keep_blank_values=True))
        fragment_map = dict(parse_qsl(parsed.fragment, keep_blank_values=True))
        token = str(
            query_map.get("access_token", "")
            or fragment_map.get("access_token", "")
            or ""
        ).strip()
        return token
    except Exception:
        return ""


def _password_reset_redirect_url() -> str | None:
    configured = str(
        get_secret("PASSWORD_RESET_REDIRECT_URL", "")
        or get_secret("APP_URL", "")
        or ""
    ).strip()
    if not configured:
        return None

    try:
        return _with_query_params(configured, {"auth_action": "recovery"})
    except Exception:
        return configured


def _promote_recovery_hash_to_query() -> None:
    # Supabase returns recovery tokens in URL hash; Streamlit cannot read hash directly.
    # This script promotes them into query params once so Python can process the reset flow.
    components.html(
        """
        <script>
        (() => {
          try {
                        const topWindow = window.parent && window.parent.location ? window.parent : window;
                        const rawHash = topWindow.location.hash ? topWindow.location.hash.substring(1) : "";
            if (!rawHash) return;
            const hashParams = new URLSearchParams(rawHash);
            const type = (hashParams.get("type") || "").toLowerCase();
            const accessToken = hashParams.get("access_token") || "";
            const tokenHash = hashParams.get("token_hash") || hashParams.get("token") || "";
            if (type !== "recovery" || (!accessToken && !tokenHash)) return;

                        const url = new URL(topWindow.location.href);
            if (url.searchParams.get("access_token") || url.searchParams.get("token_hash") || url.searchParams.get("token")) return;

            url.searchParams.set("auth_action", "recovery");
            url.searchParams.set("type", type);
                        if (accessToken) {
                            url.searchParams.set("access_token", accessToken);
                        }
                        if (tokenHash) {
                            url.searchParams.set("token_hash", tokenHash);
                        }

            const refreshToken = hashParams.get("refresh_token") || "";
            if (refreshToken) {
              url.searchParams.set("refresh_token", refreshToken);
            }

            url.hash = "";
                        topWindow.location.replace(url.toString());
          } catch (e) {
            // no-op
          }
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def load_csv_with_friendly_error(loader_fn, source_label: str, *args):
    try:
        return loader_fn(*args), None
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError):
        return None, f"Invalid CSV format. Please check delimiters, encoding, or missing headers while loading {source_label}."


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


def _render_login_shell() -> tuple[str, str, str, bool, bool, bool, bool, bool]:
    st.markdown(
        """
        <style>
            html, body, [data-testid="stApp"] {
                height: 100vh !important;
                overflow: hidden !important;
            }

            [data-testid="stSidebar"], [data-testid="collapsedControl"] {
                display: none;
            }

            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(900px 500px at 20% 5%, rgba(56, 189, 248, 0.15), rgba(2, 6, 23, 0) 60%),
                    radial-gradient(900px 550px at 90% 90%, rgba(99, 102, 241, 0.14), rgba(2, 6, 23, 0) 65%),
                    linear-gradient(165deg, #0b1220 0%, #070b14 55%, #03050a 100%);
                height: 100vh !important;
                overflow: hidden !important;
                overscroll-behavior: none !important;
            }

            [data-testid="stAppViewContainer"] .main {
                height: 100vh !important;
                overflow: hidden !important;
                overscroll-behavior: none !important;
            }

            .main .block-container {
                max-width: 100%;
                height: 100vh;
                min-height: 100vh;
                padding-top: 0 !important;
                padding-bottom: 0 !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                position: relative;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                overscroll-behavior: none;
            }

            .main .block-container::before {
                content: '';
                position: absolute;
                width: min(72vw, 760px);
                height: min(72vw, 760px);
                left: 50%;
                top: 42%;
                transform: translate(-50%, -50%);
                background: radial-gradient(circle, rgba(56, 189, 248, 0.18) 0%, rgba(59, 130, 246, 0.12) 24%, rgba(15, 23, 42, 0) 70%);
                filter: blur(10px);
                pointer-events: none;
                z-index: 0;
                animation: haloPulse 10s ease-in-out infinite;
            }

            .auth-logo {
                font-size: 28px;
                margin-bottom: 16px;
                animation: logoFloat 3s ease-in-out infinite;
            }

            .auth-brand {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 4px 10px;
                border-radius: 999px;
                margin-bottom: 8px;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #dbeafe;
                background: linear-gradient(135deg, rgba(79, 70, 229, 0.24), rgba(59, 130, 246, 0.2));
                border: 1px solid rgba(148, 163, 184, 0.24);
            }

            .auth-tagline {
                margin-top: -14px;
                margin-bottom: 18px;
                color: rgba(203, 213, 225, 0.8);
                font-size: 0.86rem;
                letter-spacing: 0.03em;
            }

            @keyframes logoFloat {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-4px); }
            }

            .auth-title {
                font-size: clamp(30px, 5vh, 42px);
                font-weight: 800;
                color: #ffffff;
                margin-bottom: 10px;
                letter-spacing: -0.02em;
                font-family: 'Sora', sans-serif;
                text-shadow: 0 4px 16px rgba(0, 0, 0, 0.32);
            }

            .auth-subtitle {
                color: #c6d5ea;
                font-size: 15px;
                line-height: 1.55;
                margin-bottom: 30px;
                font-family: 'Manrope', sans-serif;
                opacity: 0.92;
                font-weight: 600;
            }

            [data-testid="stForm"] {
                width: min(420px, 94vw) !important;
                margin: 0 !important;
                position: fixed !important;
                top: 50% !important;
                left: 50% !important;
                transform: translate(-50%, -50%) !important;
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 20px !important;
                background: 
                    linear-gradient(145deg, rgba(10, 26, 44, 0.62), rgba(6, 20, 36, 0.48)) !important;
                backdrop-filter: blur(24px) !important;
                -webkit-backdrop-filter: blur(24px) !important;
                box-shadow: 
                    0 14px 40px rgba(2, 10, 22, 0.48),
                    0 0 36px rgba(0, 150, 255, 0.14),
                    inset 0 1px 1px rgba(255, 255, 255, 0.08),
                    inset 0 -1px 1px rgba(0, 0, 0, 0.24) !important;
                padding: clamp(20px, 3.2vh, 36px) clamp(18px, 2.5vw, 28px) clamp(18px, 2.5vh, 28px) clamp(18px, 2.5vw, 28px) !important;
                transition: all 300ms cubic-bezier(0.34, 1.56, 0.64, 1) !important;
                position: fixed !important;
                overflow: hidden !important;
                z-index: 2;
                animation: authFadeIn 0.55s ease both;
                max-height: 92dvh;
                scrollbar-width: none;
            }

            [data-testid="stForm"]::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                pointer-events: none;
                background: transparent;
            }

            [data-testid="stForm"]::after {
                content: '';
                position: absolute;
                inset: -2px;
                border-radius: 22px;
                background: linear-gradient(120deg, rgba(56, 189, 248, 0.2), rgba(99, 102, 241, 0.18), rgba(139, 92, 246, 0.18));
                filter: blur(14px);
                opacity: 0.42;
                z-index: -1;
                pointer-events: none;
                animation: cardAura 8s linear infinite;
            }

            [data-testid="stForm"]:hover {
                transform: translate(-50%, -50%) !important;
                border-color: rgba(255, 255, 255, 0.12) !important;
                box-shadow: 
                    0 14px 40px rgba(2, 10, 22, 0.48),
                    0 0 44px rgba(0, 150, 255, 0.2),
                    inset 0 1px 1px rgba(255, 255, 255, 0.08),
                    inset 0 -1px 1px rgba(0, 0, 0, 0.2) !important;
            }

            [data-testid="stForm"] .stTextInput {
                margin-bottom: 16px;
                position: relative;
                padding-top: 16px;
            }

            [data-testid="stForm"] .stTextInput:last-of-type {
                margin-bottom: 28px;
            }

            [data-testid="stForm"] .stTextInput label {
                position: absolute;
                top: 25px;
                left: 14px;
                margin: 0 !important;
                z-index: 4;
                pointer-events: none;
                transition: all 0.24s ease;
            }

            [data-testid="stForm"] .stTextInput label p {
                margin: 0 !important;
            }

            [data-testid="stForm"] .stTextInput:focus-within label,
            [data-testid="stForm"] .stTextInput:has(input:not(:placeholder-shown)) label {
                top: 2px;
                left: 8px;
            }

            [data-testid="stForm"] .stTextInput:focus-within label p,
            [data-testid="stForm"] .stTextInput:has(input:not(:placeholder-shown)) label p {
                font-size: 0.72rem !important;
                letter-spacing: 0.08em !important;
                color: rgba(147, 197, 253, 0.96) !important;
                text-transform: uppercase;
            }

            [data-testid="stForm"] div[data-baseweb="input"] {
                position: relative;
                z-index: 1;
            }

            [data-testid="stForm"] div[data-baseweb="input"] > div,
            [data-testid="stForm"] div[data-baseweb="base-input"],
            [data-testid="stForm"] .stTextInput > div > div {
                background: rgba(255, 255, 255, 0.04) !important;
                border: 1px solid transparent !important;
                border-radius: 12px !important;
                transition: all 260ms ease !important;
                overflow: hidden !important;
                box-shadow: 
                    inset 0 1px 1px rgba(255, 255, 255, 0.05),
                    inset 0 -1px 2px rgba(0, 0, 0, 0.2) !important;
                outline: none !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] > div:focus,
            [data-testid="stForm"] div[data-baseweb="input"] > div:focus-visible,
            [data-testid="stForm"] div[data-baseweb="base-input"]:focus,
            [data-testid="stForm"] div[data-baseweb="base-input"]:focus-visible {
                outline: none !important;
                border-color: transparent !important;
                box-shadow: 
                    0 0 0 1px rgba(59, 130, 246, 0.5),
                    0 0 22px rgba(59, 130, 246, 0.22),
                    inset 0 1px 1px rgba(255, 255, 255, 0.05),
                    inset 0 -1px 2px rgba(0, 0, 0, 0.2) !important;
                background: rgba(255, 255, 255, 0.04) !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] > div::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 100%;
                border-radius: 14px;
                background: linear-gradient(180deg, rgba(255, 255, 255, 0.05), transparent);
                pointer-events: none;
                z-index: 1;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input,
            [data-testid="stForm"] .stTextInput input {
                background: transparent !important;
                color: #f3f8ff !important;
                -webkit-text-fill-color: #f3f8ff !important;
                caret-color: #60a5fa !important;
                font-size: 1rem !important;
                font-weight: 600 !important;
                font-family: 'Manrope', sans-serif !important;
                letter-spacing: 0.01em;
                position: relative;
                z-index: 2;
                box-shadow: none !important;
                border: none !important;
                outline: none !important;
                -webkit-appearance: none !important;
                appearance: none !important;
                transition: color 0.24s ease, text-shadow 0.24s ease;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input:focus,
            [data-testid="stForm"] .stTextInput input:focus {
                box-shadow: none !important;
                border: none !important;
                outline: none !important;
                background: transparent !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input::placeholder,
            [data-testid="stForm"] .stTextInput input::placeholder {
                color: rgba(203, 213, 225, 0.22) !important;
                -webkit-text-fill-color: rgba(203, 213, 225, 0.22) !important;
                opacity: 1 !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input::-webkit-outer-spin-button,
            [data-testid="stForm"] div[data-baseweb="input"] input::-webkit-inner-spin-button {
                -webkit-appearance: none;
                margin: 0;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill,
            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill:hover,
            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill:focus,
            [data-testid="stForm"] div[data-baseweb="input"] input:-webkit-autofill:active {
                -webkit-text-fill-color: #f7fbff !important;
                -webkit-box-shadow: inset 0 0 0 1000px rgba(255, 255, 255, 0.04) !important;
                box-shadow: 
                    inset 0 0 0 1000px rgba(255, 255, 255, 0.04) !important;
                transition: background-color 9999s ease-in-out 0s !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] input:-moz-autofill,
            [data-testid="stForm"] div[data-baseweb="input"] input:-moz-autofill:hover,
            [data-testid="stForm"] div[data-baseweb="input"] input:-moz-autofill:focus,
            [data-testid="stForm"] div[data-baseweb="input"] input:-moz-autofill:active {
                -webkit-text-fill-color: #f7fbff !important;
                color: #f7fbff !important;
                background: rgba(255, 255, 255, 0.04) !important;
                box-shadow: 
                    0 0 24px rgba(0, 150, 255, 0.28) inset !important,
                    inset 0 1px 1px rgba(255, 255, 255, 0.05),
                    inset 0 -1px 2px rgba(0, 0, 0, 0.2) !important;
                transition: background-color 9999s ease-in-out 0s !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"]:focus-within > div,
            [data-testid="stForm"] div[data-baseweb="base-input"]:focus-within,
            [data-testid="stForm"] .stTextInput:focus-within > div > div {
                border-color: transparent !important;
                box-shadow: 
                    0 0 0 1px rgba(59, 130, 246, 0.5),
                    0 0 22px rgba(59, 130, 246, 0.22),
                    inset 0 1px 2px rgba(0, 0, 0, 0.1) !important;
                background: rgba(255, 255, 255, 0.04) !important;
            }

            [data-testid="stForm"] div[aria-invalid="true"],
            [data-testid="stForm"] input[aria-invalid="true"] {
                border-color: transparent !important;
                box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.5) !important;
            }

            [data-testid="stForm"] input,
            [data-testid="stForm"] input:focus,
            [data-testid="stForm"] input:focus-visible,
            [data-testid="stForm"] input:active {
                border: none !important;
                outline: none !important;
                box-shadow: none !important;
                background: transparent !important;
            }

            [data-testid="stForm"] label p {
                color: #e8f2ff !important;
                font-weight: 700 !important;
                font-size: 0.93rem !important;
                font-family: 'Manrope', sans-serif !important;
                margin-bottom: 10px !important;
                letter-spacing: 0.02em;
            }

            [data-testid="stForm"] [data-testid="stTextInputStatus"] {
                display: none !important;
            }

            [data-testid="stForm"] [data-baseweb="input"] ~ div {
                display: none !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] [role="button"] {
                display: none !important;
            }

            [data-testid="stForm"] div[data-baseweb="input"] [type="button"] {
                display: none !important;
            }

            [data-testid="stForm"] .stTextInput input {
                padding-right: 0.75rem !important;
            }

            /* Hide native browser password reveal controls (Edge/Chromium). */
            [data-testid="stForm"] input[type="password"]::-ms-reveal,
            [data-testid="stForm"] input[type="password"]::-ms-clear {
                display: none !important;
                width: 0 !important;
                height: 0 !important;
            }

            [data-testid="stForm"] input[type="password"]::-webkit-credentials-auto-fill-button,
            [data-testid="stForm"] input[type="password"]::-webkit-contacts-auto-fill-button {
                display: none !important;
                visibility: hidden !important;
            }

            input[type="text"]:focus,
            input[type="password"]:focus {
                outline: none !important;
                box-shadow: none !important;
                border: none !important;
            }

            /* Deep override for Streamlit/BaseWeb nested input wrappers */
            div[data-baseweb="input"] {
                background: rgba(255,255,255,0.04) !important;
                border-radius: 12px !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
                padding: 2px !important;
            }

            div[data-baseweb="input"] > div {
                background: transparent !important;
            }

            div[data-baseweb="input"] input {
                background: transparent !important;
                color: white !important;
                border: none !important;
            }

            div[data-baseweb="input"]:focus-within {
                border: 1px solid rgba(59,130,246,0.6) !important;
                box-shadow: 0 0 0 1px rgba(59,130,246,0.4) !important;
            }

            input:focus {
                outline: none !important;
                box-shadow: none !important;
            }

            input::placeholder {
                color: rgba(255,255,255,0.4) !important;
            }

            input:-webkit-autofill {
                -webkit-box-shadow: 0 0 0 1000px transparent inset !important;
                -webkit-text-fill-color: white !important;
            }

            [data-testid="stFormSubmitButton"] {
                margin-top: 4px;
            }

            [data-testid="stFormSubmitButton"] button {
                border-radius: 13px !important;
                border: none !important;
                font-weight: 700 !important;
                font-family: 'Manrope', sans-serif !important;
                font-size: 0.95rem !important;
                height: 48px !important;
                transition: all 240ms cubic-bezier(0.34, 1.56, 0.64, 1) !important;
                position: relative;
                overflow: hidden;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }

            [data-testid="stFormSubmitButton"] button[kind="primary"] {
                background: linear-gradient(135deg, #5f5bff 0%, #7c3aed 52%, #4b7dff 100%) !important;
                color: #ffffff !important;
                box-shadow: 0 10px 24px rgba(79, 70, 229, 0.4) !important;
                position: relative;
            }

            [data-testid="stFormSubmitButton"] button[kind="primary"]::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 500ms ease;
            }

            [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
                transform: translateY(-3px);
                box-shadow: 0 14px 32px rgba(79, 70, 229, 0.54) !important;
                filter: brightness(1.1);
            }

            [data-testid="stFormSubmitButton"] button[kind="primary"]:hover::before {
                left: 100%;
            }

            [data-testid="stFormSubmitButton"] button[kind="primary"]:active {
                transform: translateY(-2px) scale(0.98);
            }

            [data-testid="stFormSubmitButton"] button[kind="secondary"] {
                background: rgba(255, 255, 255, 0.02) !important;
                border: 1px solid rgba(190, 210, 235, 0.16) !important;
                color: #b7c8de !important;
            }

            [data-testid="stFormSubmitButton"] button[kind="secondary"]:hover {
                transform: translateY(-3px);
                border-color: rgba(255, 255, 255, 0.15) !important;
                background: rgba(255, 255, 255, 0.06) !important;
                color: #d8e3f7 !important;
                box-shadow: 0 8px 20px rgba(0, 150, 255, 0.12) !important;
            }

            [data-testid="stFormSubmitButton"] button[kind="secondary"]:active {
                transform: translateY(-1px) scale(0.98);
            }

            .auth-meta-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-top: -8px;
                margin-bottom: 14px;
            }

            .auth-meta-row [data-testid="stCheckbox"] {
                margin-top: 0 !important;
            }

            .auth-meta-row [data-testid="stCheckbox"] label p {
                margin-bottom: 0 !important;
                font-size: 0.84rem !important;
                font-weight: 600 !important;
                color: rgba(203, 213, 225, 0.92) !important;
                letter-spacing: 0.01em !important;
                text-transform: none !important;
            }

            .auth-meta-row [data-testid="stCheckbox"] input {
                accent-color: #5f5bff;
            }

            .auth-meta-row [data-testid="stFormSubmitButton"] {
                margin-top: 0 !important;
            }

            .auth-meta-row [data-testid="stFormSubmitButton"] button {
                height: auto !important;
                min-height: 0 !important;
                padding: 2px 0 !important;
                border: none !important;
                box-shadow: none !important;
                background: transparent !important;
                color: #93c5fd !important;
                font-size: 0.84rem !important;
                text-transform: none !important;
                letter-spacing: 0 !important;
                justify-content: flex-end !important;
            }

            .auth-meta-row [data-testid="stFormSubmitButton"] button:hover {
                transform: none !important;
                filter: none !important;
                color: #bfdbfe !important;
                text-decoration: underline !important;
            }

            .forgot-link {
                text-align: right;
                padding-top: 3px;
            }

            .forgot-link a {
                color: #93c5fd;
                text-decoration: none;
                font-size: 0.84rem;
                font-weight: 600;
                transition: color 0.2s ease, opacity 0.2s ease;
            }

            .forgot-link a:hover {
                color: #bfdbfe;
                opacity: 0.95;
                text-decoration: underline;
            }

            .auth-reset-panel {
                width: min(420px, 94vw);
                margin: 12px auto 0 auto;
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 14px;
                background: linear-gradient(140deg, rgba(15, 23, 42, 0.65), rgba(9, 30, 48, 0.54));
                padding: 12px 14px 10px 14px;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.3);
            }

            .auth-reset-title {
                color: #e7f0ff;
                font-size: 0.9rem;
                font-weight: 700;
                margin-bottom: 6px;
                letter-spacing: 0.03em;
                text-transform: uppercase;
            }

            .auth-reset-help {
                color: rgba(203, 213, 225, 0.88);
                font-size: 0.84rem;
                margin-bottom: 8px;
            }

            @media (max-width: 560px) {
                [data-testid="stForm"] {
                    margin-top: 0 !important;
                    width: min(94vw, 420px) !important;
                    padding: 28px 20px 20px 20px !important;
                }

                .auth-title {
                    font-size: 32px !important;
                }

                .auth-logo {
                    font-size: 24px !important;
                }
            }

            @keyframes authFadeIn {
                from { opacity: 0; transform: translateY(12px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @keyframes cardAura {
                0% { transform: rotate(0deg); opacity: 0.36; }
                50% { transform: rotate(180deg); opacity: 0.5; }
                100% { transform: rotate(360deg); opacity: 0.36; }
            }

            @keyframes haloPulse {
                0%, 100% { opacity: 0.48; transform: translate(-50%, -50%) scale(1); }
                50% { opacity: 0.62; transform: translate(-50%, -50%) scale(1.05); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    auth_mode = str(st.session_state.get("auth_mode", "login") or "login").strip().lower()
    is_signup_mode = auth_mode == "signup"

    with st.form("auth_form", border=False):
        st.markdown('<div class="auth-brand">Apex Analytics</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-logo">📊</div>', unsafe_allow_html=True)
        if is_signup_mode:
            st.markdown('<div class="auth-title">Create Account</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="auth-subtitle">Start your analytics workspace in minutes</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="auth-tagline">Build faster. Analyze smarter.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="auth-title">Welcome Back</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="auth-subtitle">Sign in to your analytics workspace</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="auth-tagline">Forecast smarter. Decide faster.</div>', unsafe_allow_html=True)

        email = st.text_input("Email", placeholder=" ", key="auth_email_input")
        password = st.text_input(
            "Create Password" if is_signup_mode else "Password",
            type="password",
            placeholder=" ",
            key="auth_password_input",
        )
        confirm_password = ""
        if is_signup_mode:
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder=" ",
            )

        do_forgot = False
        do_login = False
        do_signup_submit = False
        do_open_signup = False
        do_back_to_login = False

        if not is_signup_mode:
            st.markdown('<div class="auth-meta-row">', unsafe_allow_html=True)
            meta_cols = st.columns([0.58, 0.42])
            with meta_cols[0]:
                remember_me_enabled = _is_local_remember_me_enabled()
                st.checkbox("Remember me", key="auth_remember_me", disabled=not remember_me_enabled)
            with meta_cols[1]:
                do_forgot = st.form_submit_button("Forgot password?", type="secondary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if not remember_me_enabled:
                st.caption("Remember me is disabled in this mode.")

            action_cols = st.columns(2, gap="small")
            with action_cols[0]:
                do_login = st.form_submit_button("Login", type="primary", use_container_width=True)
            with action_cols[1]:
                do_open_signup = st.form_submit_button("Create Account", type="secondary", use_container_width=True)
        else:
            action_cols = st.columns(2, gap="small")
            with action_cols[0]:
                do_signup_submit = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            with action_cols[1]:
                do_back_to_login = st.form_submit_button("Back to Sign In", type="secondary", use_container_width=True)

    return email, password, confirm_password, do_login, do_signup_submit, do_open_signup, do_back_to_login, do_forgot


def show_login() -> None:
    if not is_supabase_enabled():
        st.error("Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY in .env or Streamlit secrets.")
        st.stop()

    if "auth_show_reset_panel" not in st.session_state:
        st.session_state["auth_show_reset_panel"] = False
    if "auth_show_update_password_panel" not in st.session_state:
        st.session_state["auth_show_update_password_panel"] = False
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"
    if st.session_state.get("auth_remember_me_initialized") is None:
        st.session_state["auth_remember_me"] = False
        st.session_state["auth_remember_me_initialized"] = True

    _promote_recovery_hash_to_query()

    access_token_from_url = _get_query_param("access_token")
    recovery_token_hash = _get_query_param("token_hash") or _get_query_param("token")
    recovery_type = _get_query_param("type").lower()
    auth_action = _get_query_param("auth_action").lower()
    reset_error = _get_query_param("error_description") or _get_query_param("error")
    is_recovery_intent = recovery_type == "recovery" or auth_action == "recovery"

    if reset_error:
        st.error(f"Password reset link error: {reset_error}")

    if is_recovery_intent:
        st.session_state["auth_show_update_password_panel"] = True
        st.session_state["auth_show_reset_panel"] = False
        st.session_state["auth_mode"] = "login"

    if access_token_from_url and is_recovery_intent:
        st.session_state["auth_recovery_token"] = access_token_from_url
        st.session_state["auth_show_update_password_panel"] = True
        st.session_state["auth_show_reset_panel"] = False
        st.session_state["auth_mode"] = "login"

    if (not access_token_from_url) and recovery_token_hash and is_recovery_intent:
        recovery_exchange_key = f"recovery:{recovery_token_hash}"
        if str(st.session_state.get("auth_recovery_exchange_key", "") or "") != recovery_exchange_key:
            st.session_state["auth_recovery_exchange_key"] = recovery_exchange_key
            ok, message, exchanged_access_token = verify_recovery_token(recovery_token_hash)
            if ok and exchanged_access_token:
                st.session_state["auth_recovery_token"] = exchanged_access_token
            else:
                st.error(message)

    email = ""
    password = ""
    confirm_password = ""
    do_login = False
    do_signup_submit = False

    showing_recovery_panel = bool(
        st.session_state.get("auth_show_reset_panel", False)
        or st.session_state.get("auth_show_update_password_panel", False)
    )

    if not showing_recovery_panel:
        email, password, confirm_password, do_login, do_signup_submit, do_open_signup, do_back_to_login, do_forgot = _render_login_shell()

        if do_open_signup:
            st.session_state["auth_mode"] = "signup"
            st.session_state["auth_show_reset_panel"] = False
            st.rerun()

        if do_back_to_login:
            st.session_state["auth_mode"] = "login"
            st.rerun()

        if do_forgot:
            st.session_state["auth_show_reset_panel"] = True
            st.session_state["auth_show_update_password_panel"] = False
            if email and not st.session_state.get("auth_reset_email"):
                st.session_state["auth_reset_email"] = email
            st.rerun()

    if st.session_state.get("auth_show_update_password_panel", False):
        with st.form("update_password_form", border=False):
            st.markdown('<div class="auth-reset-panel">', unsafe_allow_html=True)
            st.markdown('<div class="auth-reset-title">Set New Password</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="auth-reset-help">Enter a new password to complete account recovery.</div>',
                unsafe_allow_html=True,
            )
            new_password = st.text_input("New Password", type="password", key="auth_new_password", placeholder="Minimum 6 characters")
            confirm_new_password = st.text_input("Confirm New Password", type="password", key="auth_confirm_new_password", placeholder="Re-enter password")
            update_cols = st.columns(2, gap="small")
            with update_cols[0]:
                do_update_password = st.form_submit_button("Update Password", key="update_password_btn", use_container_width=True, type="primary")
            with update_cols[1]:
                do_cancel_update = st.form_submit_button("Back to Sign In", key="cancel_update_password_btn", use_container_width=True, type="secondary")
            st.markdown('</div>', unsafe_allow_html=True)

        if do_update_password:
            if not str(st.session_state.get("auth_recovery_token", "") or "").strip():
                st.error("Reset session is missing. Open the latest password reset link again.")
                return
            if len(str(new_password or "")) < 6:
                st.error("Password must be at least 6 characters.")
            elif str(new_password or "") != str(confirm_new_password or ""):
                st.error("Passwords do not match.")
            else:
                with st.spinner("Updating password..."):
                    ok, message = update_password(str(st.session_state.get("auth_recovery_token", "") or ""), new_password)
                if ok:
                    st.success(message)
                    st.session_state["auth_show_update_password_panel"] = False
                    st.session_state["auth_mode"] = "login"
                    st.session_state.pop("auth_recovery_token", None)
                    _clear_auth_query_params()
                    st.rerun()
                else:
                    st.error(message)

        if do_cancel_update:
            st.session_state["auth_show_update_password_panel"] = False
            st.session_state["auth_mode"] = "login"
            st.session_state.pop("auth_recovery_token", None)
            _clear_auth_query_params()
            st.rerun()

    if st.session_state.get("auth_show_reset_panel", False):
        with st.form("password_reset_form", border=False):
            st.markdown('<div class="auth-reset-panel">', unsafe_allow_html=True)
            st.markdown('<div class="auth-reset-title">Password Reset</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-reset-help">Enter your account email and we will send a reset link.</div>', unsafe_allow_html=True)
            reset_redirect_url = _password_reset_redirect_url()
            if not reset_redirect_url:
                st.caption("Optional: set APP_URL or PASSWORD_RESET_REDIRECT_URL in .env so reset links open recovery mode directly.")
            reset_email = st.text_input("Reset Email", key="auth_reset_email", placeholder="you@example.com")
            panel_cols = st.columns(2, gap="small")
            with panel_cols[0]:
                do_send_reset = st.form_submit_button("Send Reset Link", key="send_reset_btn", use_container_width=True, type="primary")
            with panel_cols[1]:
                do_cancel_reset = st.form_submit_button("Cancel", key="cancel_reset_btn", use_container_width=True, type="secondary")
            st.markdown('</div>', unsafe_allow_html=True)

        if do_send_reset:
            with st.spinner("Sending password reset link..."):
                ok, message = send_password_reset_email(reset_email, redirect_to=reset_redirect_url)
            if ok:
                st.success(message)
                st.session_state["auth_show_reset_panel"] = False
            else:
                st.error(message)

        if do_cancel_reset:
            st.session_state["auth_show_reset_panel"] = False

    if do_signup_submit:
        if not str(email or "").strip() or not str(password or ""):
            st.error("Enter email and password to sign up.")
            return
        if len(str(password or "")) < 6:
            st.error("Password must be at least 6 characters.")
            return
        if str(password or "") != str(confirm_password or ""):
            st.error("Passwords do not match.")
            return
        with st.spinner("Creating your account..."):
            ok, message = sign_up_with_password(email, password)
        if ok:
            with st.spinner("Signing you in..."):
                login_ok, login_message, user_data = sign_in_with_password(email, password)
            if login_ok and user_data:
                st.session_state["user"] = {
                    "id": user_data.get("id", ""),
                    "email": user_data.get("email", email),
                    "access_token": user_data.get("access_token", ""),
                }
                if _is_local_remember_me_enabled() and st.session_state.get("auth_remember_me", False):
                    _save_remembered_auth(st.session_state["user"])
                else:
                    _clear_remembered_auth()
                st.session_state["auth_mode"] = "login"
                _seed_auth_compat_keys()
                ensure_analysis_state()
                st.rerun()
            else:
                st.success(message)
                st.info(f"Account created. Auto sign-in is pending: {login_message}")
        else:
            st.error(message)

    if do_login:
        if not str(email or "").strip() or not str(password or ""):
            st.error("Enter both email and password.")
            return
        with st.spinner("Signing you in..."):
            ok, message, user_data = sign_in_with_password(email, password)
        if ok and user_data:
            st.session_state["user"] = {
                "id": user_data.get("id", ""),
                "email": user_data.get("email", email),
                "access_token": user_data.get("access_token", ""),
            }
            if _is_local_remember_me_enabled() and st.session_state.get("auth_remember_me", False):
                _save_remembered_auth(st.session_state["user"])
            else:
                _clear_remembered_auth()
            _seed_auth_compat_keys()
            ensure_analysis_state()
            st.rerun()
        else:
            st.error(message)


def _logout() -> None:
    user = st.session_state.get("user") or {}
    token = str(user.get("access_token", "") or st.session_state.get("supabase_access_token", "") or "").strip()
    remembered_email = str(user.get("email", "") or st.session_state.get("auth_email_input", "") or "").strip()

    if token:
        sign_out(token)
    _clear_remembered_auth()
    st.session_state.clear()
    if remembered_email:
        st.session_state["auth_email_input"] = remembered_email
    st.session_state["auth_remember_me"] = False
    st.session_state["auth_remember_me_initialized"] = True
    st.rerun()


def _render_no_dataset_workspace(active_page: str) -> None:
    st.markdown(
        """
        <div class="empty-state-hero">
            <div class="empty-state-hero__title">Analyze your data instantly</div>
            <div class="empty-state-hero__subtitle">Upload a CSV or select a dataset to start exploring insights.</div>
            <div class="empty-state-hero__support">Chat history is tied to each dataset and appears after you load one.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if active_page == "chat":
        st.markdown(
            """
            <div class="chat-shell">
                <div class="chat-hero">
                    <div>
                        <div class="chat-hero__eyebrow">Analyst Workspace</div>
                        <div class="chat-hero__title">AI Analyst Workspace</div>
                        <div class="chat-hero__subtitle">Select a dataset to start asking questions, generating charts, and saving chat history for this data source.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("Choose a dataset from the sidebar to enable AI analysis for this workspace.")
    elif active_page == "forecast":
        st.info("Forecasting becomes available after you load a dataset with date and numeric columns.")
    elif active_page == "reports":
        st.info("Reports become available after you run at least one analysis on a loaded dataset.")


def _handle_history_deletion() -> None:
    delete_history_id = str(st.session_state.get("delete_chat_history_id", "") or "").strip()
    if not delete_history_id:
        return

    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
    # Attempt cloud deletion when user is authenticated; pass the delete id directly
    # since sidebar entries may be cloud-only rows that are not present in session_state chat_history.
    local_deleted = False
    try:
        cloud_deleted = False
        if user_id and access_token:
            try:
                # Try delete on cloud; delete_cloud_chat_history returns bool
                cloud_deleted = delete_cloud_chat_history(user_id, access_token, delete_history_id)
                if not cloud_deleted:
                    logger.warning(
                        "cloud_chat_history_delete_failed",
                        extra={"history_id": delete_history_id},
                    )
            except Exception:
                logger.exception("cloud_delete_error")

        # Remove locally everywhere (session + cached dataset states).
        local_deleted = delete_chat_history_everywhere(delete_history_id)
    finally:
        if cloud_deleted or local_deleted:
            deleted_ids = list(st.session_state.get("deleted_history_ids", []))
            st.session_state["deleted_history_ids"] = [item for item in deleted_ids if str(item or "").strip() != delete_history_id]
        st.session_state["delete_chat_history_id"] = ""
        st.session_state["selected_chat_history_id"] = ""
        st.rerun()


def show_app() -> None:
    app_started = time.perf_counter()
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

    dataset_context_started = time.perf_counter()
    selected_key, df_to_load, dataset_fingerprint = _load_selected_dataset_context()
    record_timing("dataset_context_selection_ms", (time.perf_counter() - dataset_context_started) * 1000)

    if selected_key and df_to_load is not None:
        current_key = str(st.session_state.get("active_dataset_key", "") or "")
        next_cache_key = str(dataset_fingerprint or selected_key)
        current_cache_key = str(st.session_state.get("active_dataset_cache_key", "") or current_key)
        should_check_activation = (
            current_key != selected_key
            or current_cache_key != next_cache_key
            or st.session_state.get("df") is None
        )

        if should_check_activation:
            activation_started = time.perf_counter()
            was_activated = activate_dataset(selected_key, df_to_load, dataset_fingerprint=dataset_fingerprint)
            record_timing("dataset_activation_ms", (time.perf_counter() - activation_started) * 1000)
            logger.info(
                "dataset_activation_checked",
                extra={
                    "dataset": selected_key,
                    "activated": was_activated,
                    "activation_ms": round((time.perf_counter() - activation_started) * 1000, 2),
                },
            )
        else:
            was_activated = False

        if was_activated:
            clear_analysis_state_memory()
            st.sidebar.markdown(
                f"<div class='sidebar-success-inline'>✅ {selected_key} loaded successfully</div>",
                unsafe_allow_html=True,
            )
            restore_persisted_analysis_state()
            restore_cloud_analysis_state()
            if not st.session_state.get("chat_history"):
                start_new_chat(target_page="overview")
            elif not (st.session_state.get("pending_query") or st.session_state.get("auto_query")):
                st.session_state["active_page"] = "overview"
                st.session_state["navigation_target_page"] = "overview"

    no_dataset_loaded = "df" not in st.session_state or st.session_state["df"] is None

    if False:
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

    # Single unified history view: always load merged 'All Datasets' history and render it.
    sidebar_scope_entries = get_sidebar_history_entries(scope="all", limit=200)
    render_chat_history_sidebar(
        sidebar_scope_entries,
        dataset_loaded=not no_dataset_loaded,
        active_dataset_label=st.session_state.get("dataset_name"),
        all_dataset_entries=None,
    )
    _handle_history_deletion()

    if st.session_state.get("pending_query") or st.session_state.get("auto_query"):
        st.session_state["active_page"] = "chat"

    if no_dataset_loaded:
        _render_no_dataset_workspace(st.session_state.get("active_page", "overview"))
        return

    active_page = render_main_navigation(logger)
    
    # Render tab content unconditionally (removed last_page guard blocking tabs)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    df = st.session_state["df"]
    schema_started = time.perf_counter()
    schema = st.session_state.get("schema", analyze_dataset(df))
    record_timing("schema_build_ms", (time.perf_counter() - schema_started) * 1000)

    from components import app_pages
    app_pages.render_loaded_dataset_workspace(active_page, df, schema, api_key, st.session_state["dataset_name"])
    record_timing("app_total_render_ms", (time.perf_counter() - app_started) * 1000)

    perf_timings = st.session_state.get("perf_timings", {})
    if perf_timings:
        with st.sidebar.expander("Runtime Performance", expanded=False):
            top_items = sorted(perf_timings.items(), key=lambda item: item[1], reverse=True)[:8]
            for metric_name, metric_value in top_items:
                st.caption(f"{metric_name}: {metric_value:.2f} ms")


if "user" not in st.session_state and st.session_state.get("_remember_me_checked") is None:
    st.session_state["_remember_me_checked"] = True
    _restore_user_from_remember_me()

if "user" not in st.session_state:
    show_login()
else:
    show_app()
