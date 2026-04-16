"""Unified page renderers extracted from app.py for modularity."""
import streamlit as st
from utils.logging import get_logger
from components.dashboard import render_data_overview_page, render_dashboard_header
from components.chat import render_chat_page
from components.forecast import render_forecasting_page
from components.reports import render_reports_page
from ui_components import render_sidebar_dataset_badge
from config import APP_TITLE, APP_VERSION

logger = get_logger("app_pages")

def render_loaded_dataset_workspace(active_page: str, df, schema, api_key, dataset_name: str):
    """Render main workspace after dataset loads - extracted from app.py."""
    render_sidebar_dataset_badge(dataset_name, df.shape[0], df.shape[1])

    # MAIN AREA
    render_dashboard_header(df)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:20px; margin-bottom:10px;'></div>", unsafe_allow_html=True)

    if active_page == "overview":
        render_data_overview_page(df)
    elif active_page == "chat":
        render_chat_page(df, schema, api_key, logger)
    elif active_page == "forecast":
        render_forecasting_page(df)
    elif active_page == "reports":
        render_reports_page()

    st.markdown(f"""
    <div style='text-align:center; color:#94A3B8; font-size:12px; margin-top:2rem; padding:1.2rem 0.6rem; opacity:0.85;'>
      {APP_TITLE} v{APP_VERSION} · Powered by Groq AI
    </div>
    """, unsafe_allow_html=True)

def render_no_dataset_workspace(active_page: str):
    """Empty state renderers - extracted from app.py."""
    st.markdown("""
    <div class="empty-state-hero">
        <div class="empty-state-hero__title">Analyze your data instantly</div>
        <div class="empty-state-hero__subtitle">Upload a CSV or select a dataset to start exploring insights.</div>
        <div class="empty-state-hero__support">Chat history is tied to each dataset and appears after you load one.</div>
    </div>
    """, unsafe_allow_html=True)

    if active_page == "chat":
        st.markdown("""
        <div class="chat-shell">
            <div class="chat-hero">
                <div>
                    <div class="chat-hero__eyebrow">Analyst Workspace</div>
                    <div class="chat-hero__title">AI Analyst Workspace</div>
                    <div class="chat-hero__subtitle">Select a dataset to start asking questions, generating charts, and saving chat history for this data source.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.info("Choose a dataset from the sidebar to enable AI analysis for this workspace.")
    elif active_page == "forecast":
        st.info("Forecasting becomes available after you load a dataset with date and numeric columns.")
    elif active_page == "reports":
        st.info("Reports become available after you run at least one analysis on a loaded dataset.")

