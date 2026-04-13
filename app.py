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
from modules.app_state import restore_persisted_analysis_state
from modules.app_state import get_recent_activity
from components.chat import render_chat_page
from components.dashboard import render_data_overview_page, render_dashboard_header
from components.forecast import render_forecasting_page
from components.navigation import render_main_navigation
from components.reports import render_reports_page
from modules.upload_cache import compute_file_fingerprint, should_reuse_uploaded_dataframe
api_key = get_secret("GROQ_API_KEY")

if not api_key:
    st.error("Groq API key not found. Add it to .env for local use or to Streamlit secrets for deployment.")
    st.stop()

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide"
)
inject_styles(st)
logger = get_logger("app")
st.session_state["app_logger"] = logger
ensure_analysis_state()


# ---------- SIDEBAR & DATASET LOADING ----------
st.sidebar.subheader("📂 Select Data Source")
data_source = st.sidebar.radio(
    "Choose how to load data:",
    ["Upload CSV", "Use Pre-loaded Dataset"]
)


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


def render_recent_activity_panel():
    recent_activity = get_recent_activity()
    if not recent_activity:
        return

    st.markdown("#### Recent Activity")
    for entry in recent_activity:
        kind = str(entry.get("kind", "activity")).replace("_", " ").title()
        description = str(entry.get("description", ""))
        st.write(f"- {kind}: {description}")


def render_onboarding_hint():
    st.caption("Upload a CSV or select a dataset to start exploring insights instantly.")


def render_empty_state_hero():
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


def load_csv_with_friendly_error(loader_fn, source_label: str, *args):
    try:
        return loader_fn(*args), None
    except Exception:
        return None, f"Invalid CSV format. Please check delimiters, encoding, or missing headers while loading {source_label}."

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
elif data_source == "Use Pre-loaded Dataset":
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

if "df" not in st.session_state or st.session_state["df"] is None:
    render_empty_state_hero()
    st.stop()

df = st.session_state["df"]
schema = st.session_state.get("schema", analyze_dataset(df))

render_sidebar_dataset_badge(st.session_state["dataset_name"], df.shape[0], df.shape[1])

# ---------- MAIN AREA ----------
render_dashboard_header(df)
render_recent_activity_panel()

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
padding:1.5rem;
border-top: 1px solid rgba(255,255,255,0.1);
opacity:0.8;
">
  {APP_TITLE} v{APP_VERSION} · Powered by Groq AI
</div>
""", unsafe_allow_html=True)
