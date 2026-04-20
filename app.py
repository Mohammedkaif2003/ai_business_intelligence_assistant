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

# Centralized Streamlit session state initialization (do not overwrite existing values)
try:
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "ai_analyst"
    if "dataset_loaded" not in st.session_state:
        st.session_state["dataset_loaded"] = False
    if "current_chat_id" not in st.session_state:
        st.session_state["current_chat_id"] = None
    if "chats" not in st.session_state:
        st.session_state["chats"] = []
    # Restore persisted last active tab (if available) to return users to
    # their previous context across reloads/logins. Stored in prompt cache.
    try:
        from modules.prompt_cache import get_global_state_value

        last_tab = get_global_state_value("last_active_tab")
        if last_tab:
            st.session_state["active_tab"] = last_tab
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("app_init_failed", exc_info=True)
    # Initialize page state for single-tab navigation
    if "page" not in st.session_state:
        st.session_state["page"] = "home"
except Exception as exc:
    # During some import-time executions (tests or headless runs) st.session_state
    # may not be fully available; ignore initialization failures safely.
    import logging
    logging.getLogger(__name__).debug("app_session_state_init_failed", exc_info=True)

# New separate files
from config import APP_ICON, APP_TITLE, APP_VERSION, DATA_DIR, FRIENDLY_DATASET_NAMES
from styles import inject_styles
from ui_components import (
    render_sidebar_dataset_badge,
)

# Existing modules (do not rename)
from modules.dataset_analyzer import analyze_dataset
from modules.data_loader import normalize_columns, load_dataset as _load_dataset_from_module
import plotly.express as px
import plotly.graph_objects as go


def load_local_dataset(*args):
    """Compatibility wrapper: accept (name, path) or (path,) and load CSV from filesystem."""
    if not args:
        raise ValueError("Missing path for local dataset")
    path = args[-1]
    return _load_dataset_from_module(path)
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
    except Exception as exc:
        logger.exception("failed_saving_remembered_auth", exc_info=True)
        return


def _clear_remembered_auth() -> None:
    path = _remember_me_file_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as exc:
        logger.exception("failed_clearing_remembered_auth", exc_info=True)
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
    # If a remembered user was restored, navigate to the app view
    try:
        st.session_state["page"] = "app"
    except Exception:
        pass
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
    except Exception as exc:
        logger.exception("failed_get_query_param", exc_info=True)
        return ""


def _clear_auth_query_params() -> None:
    for key in ("auth_action", "type", "access_token", "refresh_token", "token_hash", "token", "code", "error", "error_description"):
        try:
            if key in st.query_params:
                del st.query_params[key]
        except Exception as exc:
            logger.exception("failed_clearing_query_param", extra={"key": key}, exc_info=True)
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
    except Exception as exc:
        logger.exception("failed_extract_recovery_token", exc_info=True)
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
    except Exception as exc:
        logger.exception("failed_building_password_reset_url", exc_info=True)
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

def _render_login_shell() -> tuple[str, str, str, bool, bool, bool, bool, bool]:
    """Render the login/signup form shell and return form values and actions."""
    st.markdown(
        """<style>
            .auth-tagline {
                margin-top: -8px;
                margin-bottom: 12px;
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
                margin-bottom: 12px;
                font-family: 'Manrope', sans-serif;
                opacity: 0.92;
                font-weight: 600;
            }

            [data-testid="stForm"] {
                width: clamp(340px, 36vw, 520px) !important;
                min-width: 340px !important;
                max-width: 520px !important;
                margin: 0 auto !important;
                position: relative !important;
                transform: none !important;
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 16px !important;
                background: linear-gradient(145deg, rgba(10, 26, 44, 0.62), rgba(6, 20, 36, 0.48)) !important;
                backdrop-filter: blur(12px) !important;
                -webkit-backdrop-filter: blur(12px) !important;
                box-shadow: 
                    0 14px 40px rgba(2, 10, 22, 0.48),
                    0 0 36px rgba(0, 150, 255, 0.12),
                    inset 0 1px 1px rgba(255, 255, 255, 0.06),
                    inset 0 -1px 1px rgba(0, 0, 0, 0.18) !important;
                padding: clamp(16px, 2.6vh, 24px) clamp(16px, 2.5vw, 20px) !important;
                transition: transform 240ms cubic-bezier(0.22, 1, 0.36, 1), max-width 240ms ease !important;
                overflow: visible !important;
                z-index: 2;
                animation: authFadeIn 0.55s ease both;
                max-height: 92dvh;
                scrollbar-width: none;
                display: flex;
                flex-direction: column;
                gap: 12px;
                align-items: stretch;
                box-sizing: border-box;
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
                transform: translateY(-6px) scale(1.02) !important;
                border-color: rgba(255, 255, 255, 0.12) !important;
                box-shadow: 
                    0 18px 48px rgba(2, 10, 22, 0.5),
                    0 0 44px rgba(0, 150, 255, 0.18),
                    inset 0 1px 1px rgba(255, 255, 255, 0.06),
                    inset 0 -1px 1px rgba(0, 0, 0, 0.18) !important;
            }

            [data-testid="stForm"] .stTextInput {
                margin-bottom: 8px;
                position: relative;
                padding-top: 12px;
            }

            [data-testid="stForm"] .stTextInput:last-of-type {
                margin-bottom: 12px;
            }

            [data-testid="stForm"] .stTextInput label {
                position: absolute;
                top: 18px;
                left: 12px;
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

            /* Show and style the password reveal toggle only for password inputs
               so it merges with our theme and isn't hidden by BaseWeb/Streamlit. */
            [data-testid="stForm"] div[data-baseweb="input"] input[type="password"] ~ [role="button"],
            [data-testid="stForm"] div[data-baseweb="input"] input[type="password"] ~ [type="button"] {
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                background: transparent !important;
                border: none !important;
                color: #ffffff !important;
                width: 36px !important;
                height: 36px !important;
                margin-right: 6px !important;
                padding: 4px !important;
                cursor: pointer !important;
            }

            /* Ensure the icon inherits color and sizes nicely */
            [data-testid="stForm"] div[data-baseweb="input"] input[type="password"] ~ [role="button"] svg,
            [data-testid="stForm"] div[data-baseweb="input"] input[type="password"] ~ [type="button"] svg {
                fill: currentColor !important;
                width: 20px !important;
                height: 20px !important;
            }

            [data-testid="stForm"] .stTextInput input {
                padding-right: 0.75rem !important;
            }

            /* Make inputs and buttons stretch full width inside card */
            [data-testid="stForm"] .stTextInput,
            [data-testid="stForm"] div[data-baseweb="input"],
            [data-testid="stForm"] div[data-baseweb="input"] > div,
            [data-testid="stForm"] .stTextInput > div > div,
            [data-testid="stForm"] input,
            [data-testid="stForm"] [data-testid="stFormSubmitButton"],
            [data-testid="stForm"] .stButton button,
            [data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
                width: 100% !important;
                box-sizing: border-box;
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
                gap: 8px;
                margin-top: 0;
                margin-bottom: 12px;
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
                width: clamp(300px, 30vw, 420px);
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
            /* Center login card and disable all motion inside .login-page wrapper */
            .login-page {
                position: fixed !important;
                inset: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 0 !important;
                margin: 0 !important;
                box-sizing: border-box !important;
                z-index: 9999 !important;
                pointer-events: none !important;
                overflow: hidden !important;
                touch-action: none !important;
            }

            /* Prevent page scrolling while login is shown */
            html, body, [data-testid="stAppViewContainer"], .main .block-container {
                height: 100vh !important;
                overflow: hidden !important;
            }

            /* Make form interactive while wrapper itself ignores pointer events */
            .login-page > *,
            .login-page [data-testid="stForm"] {
                pointer-events: auto !important;
            }

            /* Center the form itself using fixed positioning to avoid DOM nesting issues */
            [data-testid="stForm"] {
                position: fixed !important;
                left: 50% !important;
                top: 50% !important;
                transform: translate(-50%, -50%) !important;
                width: clamp(340px, 36vw, 520px) !important;
                min-width: 340px !important;
                max-width: 520px !important;
                margin: 0 !important;
                transition: none !important;
                animation: none !important;
                z-index: 10000 !important;
            }

            [data-testid="stForm"]::before,
            [data-testid="stForm"]::after {
                animation: none !important;
                transition: none !important;
            }

            [data-testid="stForm"]:hover,
            [data-testid="stForm"]:active,
            [data-testid="stForm"]:focus {
                transform: translate(-50%, -50%) !important;
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

    st.markdown('<div class="login-page">', unsafe_allow_html=True)
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

    st.markdown('</div>', unsafe_allow_html=True)
    return email, password, confirm_password, do_login, do_signup_submit, do_open_signup, do_back_to_login, do_forgot


def _render_home_page() -> None:
    """Render a minimal landing/home page that links to the login flow."""
    # Scoped CSS: lock viewport and remove scroll while home page is shown
    st.markdown(
        """
        <style>
            /* Lock viewport and prevent scrolling while home is visible */
            html, body, [data-testid="stAppViewContainer"], .main .block-container {
                height: 100vh !important;
                max-height: 100vh !important;
                overflow: hidden !important;
                overscroll-behavior: none !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            .home-page {
                position: fixed !important;
                inset: 0 !important;
                display:flex !important;
                align-items:center !important;
                justify-content:center !important;
                overflow:hidden !important;
                padding: 0 20px !important;
                box-sizing: border-box !important;
                z-index: 10000 !important;
                background: linear-gradient(165deg, #0b1220 0%, #070b14 55%, #03050a 100%);
            }

            .home-content {
                width:100%;
                max-width: 1100px;
                box-sizing: border-box;
            }

            /* Prevent horizontal overflow on small screens */
            .home-content > * { max-width: 100%; box-sizing: border-box; }
            @media (max-width:560px) {
                .home-page { padding: 12px !important; }
            }

            /* Eye-catching CTA styles (purely visual) */
            .home-cta {
                display: inline-block;
                padding: 12px 22px;
                border-radius: 12px;
                font-weight: 800;
                font-size: 16px;
                line-height: 1;
                cursor: pointer;
                transition: transform 140ms ease, box-shadow 140ms ease, opacity 140ms ease;
                border: none;
                text-decoration: none;
                -webkit-appearance: none;
            }

            .home-cta--primary {
                background: linear-gradient(90deg, #7c3aed 0%, #4f46e5 100%);
                color: #ffffff;
                box-shadow: 0 8px 24px rgba(79,70,229,0.18), 0 2px 6px rgba(2,6,23,0.6) inset;
            }

            .home-cta--secondary {
                background: rgba(255,255,255,0.02);
                color: #d1d5db;
                border: 1px solid rgba(255,255,255,0.06);
                box-shadow: 0 6px 18px rgba(2,6,23,0.5);
            }

            .home-cta:hover, .home-cta:focus {
                transform: translateY(-4px);
                box-shadow: 0 18px 40px rgba(79,70,229,0.20), 0 6px 24px rgba(2,6,23,0.6);
                opacity: 0.98;
                outline: none;
            }

            .home-cta:active {
                transform: translateY(-1px) scale(0.995);
                box-shadow: 0 8px 20px rgba(2,6,23,0.6);
            }

            .home-cta:focus-visible {
                box-shadow: 0 18px 40px rgba(79,70,229,0.20), 0 6px 24px rgba(2,6,23,0.6);
                outline: 3px solid rgba(124,58,237,0.18);
                outline-offset: 3px;
            }

            /* Feature cards: glass effect and professional typography */
            .feature-grid {
                display:grid;
                grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
                gap:16px;
                max-width:920px;
                width:100%;
            }

            .feature-card {
                padding:18px 20px;
                border-radius:14px;
                background: linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.01) 100%);
                border: 1px solid rgba(255,255,255,0.04);
                backdrop-filter: blur(8px) saturate(120%);
                -webkit-backdrop-filter: blur(8px) saturate(120%);
                box-shadow: 0 12px 30px rgba(2,6,23,0.6);
                color: #e6eefc;
                text-align:left;
                transition: transform 180ms ease, box-shadow 180ms ease;
            }

            .feature-card:hover, .feature-card:focus-within {
                transform: translateY(-6px);
                box-shadow: 0 28px 60px rgba(2,6,23,0.7);
            }

            .feature-card__title {
                font-family: 'Sora', 'Inter', Arial, sans-serif;
                font-weight: 700;
                font-size: 18px;
                color: #ffffff;
                display:block;
                margin-bottom:8px;
                letter-spacing: -0.01em;
            }

            .feature-card__desc {
                font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
                font-size: 15px;
                color: rgba(203,213,225,0.88);
                line-height:1.45;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="home-page">
            <div class="home-content">
                <!-- Top-right Login button removed because 'Get Started' already links to login -->
                <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;padding:40px;text-align:center;">
                    <h1 style="margin:0;font-size:42px;color:#fff;font-family:'Sora',sans-serif;">Apex Analytics</h1>
                    <p style="margin-top:8px;color:rgba(203,213,225,0.9);font-size:18px;max-width:880px;">Analyze datasets, generate insights, and chat with your data using AI</p>
                    <div style="height:18px"></div>
                    <div style="display:flex;gap:24px;align-items:center;justify-content:center;margin-top:18px;margin-bottom:8px;">
                        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
                            <form method="get" action="/" style="display:inline;margin:0;padding:0;">
                                <input type="hidden" name="route" value="login" />
                                <button type="submit" class="home-cta home-cta--primary">Get Started</button>
                            </form>
                            <div style="color:rgba(203,213,225,0.8);font-size:14px;">Create an account or sign in</div>
                        </div>
                        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
                            <form method="get" action="/" style="display:inline;margin:0;padding:0;">
                                <input type="hidden" name="route" value="demo" />
                                <button type="submit" class="home-cta home-cta--secondary">View Demo</button>
                            </form>
                            <div style="color:rgba(203,213,225,0.8);font-size:14px;">Explore the demo — no signup required.</div>
                        </div>
                    </div>
                    <div class="feature-grid">
                        <div class="feature-card" role="group" aria-label="Chat feature">
                            <span class="feature-card__title">Chat</span>
                            <div class="feature-card__desc">Ask natural-language questions about your data.</div>
                        </div>
                        <div class="feature-card" role="group" aria-label="Dashboard feature">
                            <span class="feature-card__title">Dashboard</span>
                            <div class="feature-card__desc">Quick summaries and KPIs for datasets.</div>
                        </div>
                        <div class="feature-card" role="group" aria-label="Forecasting feature">
                            <span class="feature-card__title">Forecasting</span>
                            <div class="feature-card__desc">Time-series forecasts and scenario projections.</div>
                        </div>
                        <div class="feature-card" role="group" aria-label="Reports feature">
                            <span class="feature-card__title">Reports</span>
                            <div class="feature-card__desc">Exportable insights and charts.</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
                # Navigate to app view after successful sign up + sign in
                st.session_state["page"] = "app"
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
            # Navigate to app view after successful login
            st.session_state["page"] = "app"
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
    # Ensure we return to the home page after logout
    try:
        st.session_state["page"] = "home"
    except Exception:
        pass
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
            except Exception as exc:
                logger.exception("cloud_delete_error", exc_info=True)

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

    # Render main navigation (updates `st.session_state.active_tab`)
    _ = render_main_navigation(logger)

    # Render tab content controlled by `st.session_state.active_tab` (do not overwrite UI)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    df = st.session_state["df"]
    schema_started = time.perf_counter()
    schema = st.session_state.get("schema", analyze_dataset(df))
    record_timing("schema_build_ms", (time.perf_counter() - schema_started) * 1000)

    # Helper renderers that delegate to existing component functions.
    def render_ai_analyst():
        render_sidebar_dataset_badge(st.session_state.get("dataset_name"), df.shape[0], df.shape[1])
        render_dashboard_header(df)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:20px; margin-bottom:10px;'></div>", unsafe_allow_html=True)
        render_chat_page(df, schema, api_key, logger)

    def render_dashboard():
        render_sidebar_dataset_badge(st.session_state.get("dataset_name"), df.shape[0], df.shape[1])
        render_dashboard_header(df)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:20px; margin-bottom:10px;'></div>", unsafe_allow_html=True)
        render_data_overview_page(df)

    # Determine which content to render by normalizing `active_tab`.
    active_tab = str(st.session_state.get("active_tab", "")).strip()
    # Accept both internal ids and human-friendly labels.
    if active_tab.lower() in {"ai_analyst", "ai analyst", "chat"}:
        render_ai_analyst()
    elif active_tab.lower() in {"dashboard", "data overview", "overview"}:
        render_dashboard()
    else:
        # Fallback: map known pages from render_main_navigation's active_page
        from components import app_pages
        active_page = st.session_state.get("active_page", "overview")
        app_pages.render_loaded_dataset_workspace(active_page, df, schema, api_key, st.session_state["dataset_name"])
    record_timing("app_total_render_ms", (time.perf_counter() - app_started) * 1000)

    perf_timings = st.session_state.get("perf_timings", {})
    if perf_timings:
        with st.sidebar.expander("Runtime Performance", expanded=False):
            top_items = sorted(perf_timings.items(), key=lambda item: item[1], reverse=True)[:8]
            for metric_name, metric_value in top_items:
                st.caption(f"{metric_name}: {metric_value:.2f} ms")


def show_demo() -> None:
    """Show a read-only demo using bundled sales_data.csv. Safe for unauthenticated users."""
    try:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">'
            "<span style=\"background:rgba(255,255,255,0.03);padding:6px 10px;border-radius:999px;font-weight:700;\">Demo mode — sample data</span></div>",
            unsafe_allow_html=True,
        )

        demo_file = os.path.join(os.path.dirname(__file__), DATA_DIR, "sales_data.csv")
        if not os.path.exists(demo_file):
            st.error("Demo dataset not available.")
            return

        demo_df = pd.read_csv(demo_file)
        demo_df = normalize_columns(demo_df)

        # Flexible column detection (handles case, spacing, and punctuation differences)
        import re

        def _norm(s: str) -> str:
            return re.sub(r"[^0-9a-z]", "_", str(s or "").lower()).strip("_")

        norm_map = {_norm(c): c for c in demo_df.columns}

        def _find(*candidates: str):
            for c in candidates:
                key = _norm(c)
                if key in norm_map:
                    return norm_map[key]
            return None

        rev_col = _find("revenue", "sales", "sales_amount", "total_sales")
        qty_col = _find("quantity", "units", "units_sold", "units sold")
        prod_col = _find("product", "item", "product_name")
        region_col = _find("region", "location", "area")
        year_col = _find("year")
        month_col = _find("month")
        date_col = _find("date")
        year_month_col = _find("year_month", "year month", "year-month", "yearmonth", "year month")

        # Build a series for monthly grouping (avoid relying on a literal column name)
        if year_month_col:
            ym_series = demo_df[year_month_col].astype(str)
        elif year_col and month_col:
            try:
                ym_series = demo_df[year_col].astype(str) + "-" + demo_df[month_col].astype(int).astype(str).str.zfill(2)
            except Exception:
                ym_series = demo_df.index.astype(str)
        elif date_col:
            try:
                demo_df[date_col] = pd.to_datetime(demo_df[date_col], errors="coerce")
                ym_series = demo_df[date_col].dt.to_period("M").astype(str)
            except Exception:
                ym_series = demo_df.index.astype(str)
        else:
            ym_series = demo_df.index.astype(str)

        def _safe_sum(col_name: str) -> float:
            if not col_name or col_name not in demo_df.columns:
                return 0.0
            try:
                return float(pd.to_numeric(demo_df[col_name], errors="coerce").sum())
            except Exception:
                return 0.0

        def _safe_mean(col_name: str) -> float:
            if not col_name or col_name not in demo_df.columns:
                return 0.0
            try:
                return float(pd.to_numeric(demo_df[col_name], errors="coerce").mean())
            except Exception:
                return 0.0

        def _render_dark_table(df: pd.DataFrame, cols: list | None = None, headers: list | None = None) -> None:
            """Render a dark-styled Plotly table for the given DataFrame (demo-only)."""
            try:
                df2 = df.copy()
                cols = cols or list(df2.columns)
                headers = headers or cols
                cell_values = [df2[c].astype(str).tolist() for c in cols]
                fill_row = ["rgba(7,18,30,0.86)" for _ in range(len(df2))]
                fig = go.Figure(
                    data=[
                        go.Table(
                            header=dict(values=headers, fill_color="#071827", align="left", font=dict(color="#f8fbff", size=12)),
                            cells=dict(values=cell_values, fill_color=[fill_row for _ in cols], align="left", font=dict(color="#eef5ff", size=11)),
                        )
                    ]
                )
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=8, r=8, t=8, b=8))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                return

        total_revenue = _safe_sum(rev_col) if not demo_df.empty else 0.0
        total_units = int(_safe_sum(qty_col)) if not demo_df.empty else 0
        avg_margin = _safe_mean(_find("profit_margin", "profit margin", "profitmargin", "profit_margin")) if not demo_df.empty else 0.0

        col1, col2, col3 = st.columns([1, 1, 1])
        col1.metric("Revenue", f"${total_revenue:,.0f}")
        col2.metric("Units sold", f"{total_units:,}")
        col3.metric("Avg profit margin", f"{avg_margin:.1f}%")

        st.markdown("---")

        st.subheader("Try sample queries")
        sample_queries = [
            "Revenue by month (last 12 months)",
            "Top 5 products by revenue",
            "Which region grew fastest YoY?",
            "Find anomalies (last 6 months)",
        ]

        chips_cols = st.columns(len(sample_queries))
        for i, q in enumerate(sample_queries):
            if chips_cols[i].button(q, key=f"demo_q_{i}"):
                st.session_state["demo_query"] = q

        demo_query = st.session_state.get("demo_query", "")
        if demo_query:
            st.markdown(f"**Result — {demo_query}**")
            if "Revenue by month" in demo_query:
                if rev_col:
                    try:
                        monthly = demo_df.groupby(ym_series, sort=False)[rev_col].sum()
                        try:
                            monthly = monthly.reindex(sorted(monthly.index))
                        except Exception:
                            pass
                        monthly_df = monthly.reset_index()
                        monthly_df.columns = ["period", "value"]
                        try:
                            fig = px.line(
                                monthly_df,
                                x="period",
                                y="value",
                                markers=True,
                                template="plotly_dark",
                                labels={"period": "Month", "value": f"{rev_col}"},
                            )
                            fig.update_traces(line=dict(color="#38bdf8", width=3), marker=dict(size=6, color="#38bdf8"))
                            fig.update_layout(
                                plot_bgcolor="rgba(0,0,0,0)",
                                paper_bgcolor="rgba(0,0,0,0)",
                                font_color="#eef5ff",
                                margin=dict(l=40, r=12, t=20, b=40),
                            )
                            fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False)
                            fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickprefix="$")
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception:
                            st.line_chart(monthly)
                        
                        # Render dark-themed table for monthly revenue
                        try:
                            table_df = monthly_df.copy()
                            table_df.columns = ["Month", rev_col]
                            table_df[rev_col] = pd.to_numeric(table_df[rev_col], errors="coerce").fillna(0).apply(lambda v: f"${v:,.0f}")
                            _render_dark_table(table_df, cols=["Month", rev_col], headers=["Month", "Revenue"])
                        except Exception:
                            pass
                    except Exception:
                        st.info("Failed to compute monthly revenue for demo data.")
                else:
                    st.info("No revenue column available in demo data.")
            elif "Top 5 products" in demo_query:
                if prod_col and rev_col:
                    try:
                        top = demo_df.groupby(prod_col)[rev_col].sum().nlargest(5)
                        top_df = top.reset_index()
                        top_df.columns = [prod_col, rev_col]
                        try:
                            fig = px.bar(
                                top_df,
                                x=prod_col,
                                y=rev_col,
                                template="plotly_dark",
                                color_discrete_sequence=["#f59e0b"],
                            )
                            fig.update_traces(texttemplate="$%{y:,.0f}", textposition="outside")
                            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#eef5ff", margin=dict(l=40, r=12, t=20, b=40))
                            fig.update_yaxes(tickprefix="$", gridcolor="rgba(255,255,255,0.04)")
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception:
                            st.bar_chart(top)
                        # Render dark-themed table for top products
                        try:
                            table_df = top_df.copy()
                            table_df[rev_col] = pd.to_numeric(table_df[rev_col], errors="coerce").fillna(0).apply(lambda v: f"${v:,.0f}")
                            _render_dark_table(table_df, cols=[prod_col, rev_col], headers=[prod_col, "Revenue"])
                        except Exception:
                            pass
                    except Exception:
                        st.info("Failed to compute top products for demo data.")
                else:
                    st.info("No product or revenue column available in demo data.")
            elif "region grew fastest" in demo_query:
                if year_col and region_col and rev_col:
                    try:
                        df_year = demo_df.copy()
                        df_year[year_col] = pd.to_numeric(df_year[year_col], errors="coerce")
                        current_year = int(df_year[year_col].max())
                        prev_year = current_year - 1
                        cur = df_year[df_year[year_col] == current_year].groupby(region_col)[rev_col].sum()
                        prev = df_year[df_year[year_col] == prev_year].groupby(region_col)[rev_col].sum()
                        growth = ((cur - prev) / prev.replace(0, 1) * 100).fillna(0).sort_values(ascending=False)
                        growth_df = growth.rename("yoy_pct").reset_index()
                        growth_df.columns = [region_col, "yoy_pct"]
                        try:
                            fig = px.bar(
                                growth_df,
                                x=region_col,
                                y="yoy_pct",
                                template="plotly_dark",
                                color_discrete_sequence=["#22c55e"],
                            )
                            fig.update_traces(texttemplate="%{y:.2f}%", textposition="auto")
                            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#eef5ff", margin=dict(l=40, r=12, t=20, b=40))
                            fig.update_yaxes(gridcolor="rgba(255,255,255,0.04)")
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception:
                            st.table(growth.rename("YoY %").map(lambda v: f"{v:.2f}%").to_frame())
                        # Render dark-themed table for YoY growth
                        try:
                            table_df = growth_df.copy()
                            table_df["yoy_pct"] = table_df["yoy_pct"].apply(lambda v: f"{v:.2f}%")
                            _render_dark_table(table_df, cols=[region_col, "yoy_pct"], headers=[region_col, "YoY %"])
                        except Exception:
                            pass
                    except Exception:
                        st.info("Not enough historical data for YoY comparison in demo dataset.")
                else:
                    st.info("Not enough historical data for YoY comparison in demo dataset.")
            elif "anomalies" in demo_query:
                if rev_col:
                    try:
                        monthly = demo_df.groupby(ym_series)[rev_col].sum()
                        m, s = monthly.mean(), monthly.std()
                        anomalies = monthly[monthly < (m - 2 * s)]
                        if anomalies.empty:
                            st.info("No significant anomalies found in the demo data.")
                        else:
                            an_df = anomalies.rename(rev_col).reset_index()
                            an_df.columns = ["period", rev_col]
                            try:
                                fig = go.Figure(data=[
                                    go.Table(
                                        header=dict(values=["Period", f"{rev_col}"], fill_color="#071827", font=dict(color="#f8fbff", family="Manrope,Segoe UI", size=12)),
                                        cells=dict(values=[an_df["period"], an_df[rev_col]], fill_color=[["rgba(7,18,30,0.86)" for _ in range(len(an_df))],["rgba(7,18,30,0.86)" for _ in range(len(an_df))]], font=dict(color="#eef5ff", family="Manrope,Segoe UI", size=12))
                                    )
                                ])
                                fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=8, r=8, t=8, b=8))
                                st.plotly_chart(fig, use_container_width=True)
                            except Exception:
                                st.table(anomalies)
                    except Exception:
                        st.info("Failed to compute anomalies for demo data.")
                else:
                    st.info("No monthly data available for anomaly detection.")

        st.markdown("### Sample data")
        try:
            sample_df = demo_df.head(200).copy()
            from pandas.api.types import is_numeric_dtype

            def _format_demo_columns(df):
                for c in df.columns:
                    try:
                        if is_numeric_dtype(df[c]):
                            lower = str(c).lower()
                            if any(k in lower for k in ("revenue", "profit", "amount", "sales", "total")):
                                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).apply(lambda v: f"${v:,.2f}")
                            elif any(k in lower for k in ("margin", "pct", "percent")):
                                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).apply(lambda v: f"{v:.1f}%")
                            else:
                                df[c] = df[c]
                    except Exception:
                        df[c] = df[c].astype(str)
                return df

            sample_df = _format_demo_columns(sample_df)
            _render_dark_table(sample_df, cols=list(sample_df.columns), headers=list(sample_df.columns))
        except Exception:
            try:
                st.dataframe(demo_df.head(200))
            except Exception:
                st.write(demo_df.head(50))

        cols = st.columns([1, 1, 1])
        if cols[0].button("Reset demo"):
            st.session_state.pop("demo_query", None)
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        if cols[1].button("Back to Home"):
            st.session_state["page"] = "home"
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()

    except Exception as exc:
        logger.exception("demo_unexpected_error", exc_info=True)
        st.error("Demo currently unavailable.")


if "user" not in st.session_state and st.session_state.get("_remember_me_checked") is None:
    st.session_state["_remember_me_checked"] = True
    _restore_user_from_remember_me()

# Session-state-based single-tab routing.
# Seed page from query param once if an external link used `?route=`.
route_param = _get_query_param("route").lower() if _get_query_param("route") else ""
if route_param and route_param != st.session_state.get("page", ""):
    st.session_state["page"] = route_param
    try:
        if "route" in st.query_params:
            del st.query_params["route"]
    except Exception:
        pass
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

page = st.session_state.get("page", "home")

if "user" not in st.session_state:
    # Unauthenticated flow
    if page == "app":
        # Protected page — redirect to login via session state
        st.session_state["page"] = "login"
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
    elif page == "demo":
        # Demo view accessible without login
        try:
            show_demo()
        except Exception:
            st.error("Demo currently unavailable.")
    elif page in {"login", "auth"}:
        show_login()
    else:
        # Default (root) -> landing/home
        _render_home_page()
else:
    # Authenticated flow — ensure logged-in users see the app view
    if page in {"", "home"}:
        st.session_state["page"] = "app"
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
    elif page in {"login", "auth"}:
        st.session_state["page"] = "app"
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
    else:
        show_app()
