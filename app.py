import streamlit as st

# ── set_page_config MUST be the very first Streamlit call ──
# Import only the constants needed for it before any other module
# (other imports like app_tabs pull in @st.cache_data decorators at module level,
#  which would count as a Streamlit command and crash this call)
from config import APP_ICON, APP_TITLE, APP_VERSION, DATA_DIR, FRIENDLY_DATASET_NAMES

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Remaining imports (safe to do after set_page_config) ──────────────────
import os
import time
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv
from modules.app_secrets import get_secret
from styles import inject_styles
from ui_components import (
    render_sidebar_dataset_badge,
)

# Existing modules (do not rename)
from modules.dataset_analyzer import analyze_dataset
from modules.data_loader import normalize_columns
from modules.dataset_activation import activate_dataset
from modules.app_logging import get_logger
from modules.app_state import ensure_analysis_state
from modules.app_state import get_recent_activity
from modules.app_tabs import (
    render_ai_analyst_tab,
    render_dashboard_header,
    render_data_overview_tab,
    render_forecasting_tab,
    render_reports_tab,
)
from modules.upload_cache import compute_file_fingerprint, should_reuse_uploaded_dataframe

# Load environment variables
load_dotenv()
api_key = get_secret("GROQ_API_KEY")

if not api_key:
    st.error("Groq API key not found. Please check your .env file.")
    st.stop()
inject_styles(st)

# ── Auth gate ────────────────────────────────────────────────────────────
from auth import is_authenticated, render_login_view, render_sidebar_user_badge

if not is_authenticated():
    render_login_view(APP_TITLE, APP_ICON)
    st.stop()

st.markdown(
    """
    <style>
        [data-testid="stHeader"] {
            height: 3.5rem !important;
            min-height: 3.5rem !important;
            padding: 0 !important;
            overflow: visible !important;
            background: transparent !important;
        }
        [data-testid="stSidebar"] {
            display: block !important;
            visibility: visible !important;
        }
        [data-testid="collapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 999999 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

logger = get_logger("app")
ensure_analysis_state()

render_sidebar_user_badge()


# App branding at the very top
from ui_components import render_sidebar_branding
render_sidebar_branding(APP_TITLE, APP_ICON)

# ---------- SIDEBAR & DATASET LOADING ----------
st.sidebar.subheader("📂 Select Data Source")
data_source = st.sidebar.radio(
    "Choose how to load data:",
    ["Upload CSV", "Use Pre-loaded Dataset"]
)


@st.cache_data
def load_dataset(file_bytes: bytes):
    df = pd.read_csv(BytesIO(file_bytes))
    df = normalize_columns(df)
    return df

def load_local_dataset(path):
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
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
        <div class="empty-state-hero" style="text-align: center; padding: 40px 20px;">
            <div style="display: flex; justify-content: center; margin-bottom: 24px;">
                <svg width="180" height="140" viewBox="0 0 240 180" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="20" y="80" width="36" height="80" rx="6" fill="url(#paint0_linear)" fill-opacity="0.8"/>
                    <rect x="76" y="50" width="36" height="110" rx="6" fill="url(#paint1_linear)" fill-opacity="0.9"/>
                    <rect x="132" y="20" width="36" height="140" rx="6" fill="url(#paint2_linear)"/>
                    <rect x="188" y="90" width="36" height="70" rx="6" fill="url(#paint3_linear)" fill-opacity="0.7"/>
                    <path d="M38 70 L94 40 L150 10 L206 80" stroke="#818CF8" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="38" cy="70" r="6" fill="#0F172A" stroke="#818CF8" stroke-width="3"/>
                    <circle cx="94" cy="40" r="6" fill="#0F172A" stroke="#818CF8" stroke-width="3"/>
                    <circle cx="150" cy="10" r="6" fill="#0F172A" stroke="#818CF8" stroke-width="3"/>
                    <circle cx="206" cy="80" r="6" fill="#0F172A" stroke="#818CF8" stroke-width="3"/>
                    <defs>
                        <linearGradient id="paint0_linear" x1="38" y1="80" x2="38" y2="160" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#4F46E5"/>
                            <stop offset="1" stop-color="#312E81" stop-opacity="0"/>
                        </linearGradient>
                        <linearGradient id="paint1_linear" x1="94" y1="50" x2="94" y2="160" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#4F46E5"/>
                            <stop offset="1" stop-color="#312E81" stop-opacity="0"/>
                        </linearGradient>
                        <linearGradient id="paint2_linear" x1="150" y1="20" x2="150" y2="160" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#6366F1"/>
                            <stop offset="1" stop-color="#3730A3" stop-opacity="0"/>
                        </linearGradient>
                        <linearGradient id="paint3_linear" x1="206" y1="90" x2="206" y2="160" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#4F46E5"/>
                            <stop offset="1" stop-color="#312E81" stop-opacity="0"/>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <div class="empty-state-hero__title" style="font-size: 26px; font-weight: 800; color: #f8fbff; margin-bottom: 12px;">Analyze your data instantly</div>
            <div class="empty-state-hero__subtitle" style="font-size: 15px; color: #cbd5e1; margin-bottom: 16px;">Upload a CSV or select a dataset to start exploring insights.</div>
            <div class="empty-state-hero__support" style="font-size: 13px; color: #64748b; font-weight: 500;">Supports CSV files (e.g. sales, finance, analytics)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_csv_with_friendly_error(loader_fn, source_label: str, *args):
    try:
        return loader_fn(*args), None
    except Exception as e:
        logger.error("CSV load failed for %s: %s", source_label, e)
        return None, f"Could not load '{source_label}'. Check that the file is a valid CSV. ({e})"

selected_key = None
df_to_load = None

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

    elif "uploaded_df" in st.session_state:
        df_to_load = st.session_state["uploaded_df"]
        selected_key = st.session_state["uploaded_name"]
elif data_source == "Use Pre-loaded Dataset":
    _base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(_base, DATA_DIR)
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
                logger.info(
                    "dataset_preloaded_loaded",
                    extra={"dataset": selected_key, "load_ms": round((time.perf_counter() - load_started) * 1000, 2)},
                )
        else:
            st.sidebar.warning(f"No CSV files found in {DATA_DIR} folder.")
    else:
        st.sidebar.warning(f"{DATA_DIR} folder not found.")

if selected_key and df_to_load is not None:
    activation_started = time.perf_counter()
    was_activated = activate_dataset(selected_key, df_to_load)
    logger.info(
        "dataset_activation_checked",
        extra={
            "dataset": selected_key,
            "activated": was_activated,
            "activation_ms": round((time.perf_counter() - activation_started) * 1000, 2),
        },
    )
    if was_activated:
        st.toast(f"{selected_key} loaded successfully!", icon="✅")

if "df" not in st.session_state or st.session_state["df"] is None:
    render_empty_state_hero()
    st.stop()

df = st.session_state["df"]
schema = st.session_state.get("schema", analyze_dataset(df))

render_sidebar_dataset_badge(st.session_state["dataset_name"], df.shape[0], df.shape[1])

# ---------- MAIN AREA ----------
render_dashboard_header(df)
render_recent_activity_panel()

tab_labels = [
    "📊 Data Overview",
    "🤖 AI Analyst",
    "🔮 Forecasting",
    "📑 Reports",
]

# Session-state-backed tab navigation. Native st.tabs resets to the first tab
# on any rerun triggered by an internal button, which was kicking users back
# to Data Overview whenever they clicked a suggestion or generated a PDF.
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = tab_labels[0]

# If an auto_query was queued from another tab (e.g. "try asking"), snap to
# the AI Analyst so the question is visibly processed.
if st.session_state.get("auto_query"):
    st.session_state["active_tab"] = tab_labels[1]

# Styled tab bar: buttons-in-columns gives full visual control over the
# navigation. The `.apex-tab-nav-marker` span identifies the row so the
# CSS in styles.py can target only these buttons via an adjacent-sibling
# selector and not the rest of the app's buttons.
st.markdown('<span class="apex-tab-nav-marker"></span>', unsafe_allow_html=True)
_tab_cols = st.columns(len(tab_labels))
for _idx, _label in enumerate(tab_labels):
    with _tab_cols[_idx]:
        _is_active = st.session_state["active_tab"] == _label
        if st.button(
            _label,
            key=f"apex_tab_{_idx}",
            width='stretch',
            type="primary" if _is_active else "secondary",
        ):
            if not _is_active:
                st.session_state["active_tab"] = _label
                st.rerun()
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

active_tab = st.session_state["active_tab"]
if active_tab == tab_labels[0]:
    render_data_overview_tab(df)
elif active_tab == tab_labels[1]:
    render_ai_analyst_tab(df, schema, api_key, logger)
elif active_tab == tab_labels[2]:
    render_forecasting_tab(df)
elif active_tab == tab_labels[3]:
    render_reports_tab()

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
