import html
import hashlib
import re
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.chat_queue import queue_query
from modules.chat_handler import chat_handler
from modules.chat_handler import generate_ai_dataset_questions
from modules.auto_insights import generate_auto_insights
from modules.auto_visualizer import auto_visualize, validate_chart_data
from modules.forecasting import forecast_revenue
from modules.insight_engine import generate_business_insight
from modules.kpi_engine import generate_kpis
from modules.report_generator import generate_pdf
from modules.text_utils import clean_text, structure_response
from modules.app_state import add_recent_activity, persist_analysis_cycle
from modules.app_state import persist_dataset_state
from modules.prompt_cache import (
    get_cached_try_asking_questions,
    save_cached_try_asking_questions,
    get_cached_response,
    save_cached_response,
    cleanup_stale_cache,
    clear_cache_for_dataset,
)
from modules.cache_metrics import record_cache_hit, record_cache_miss, get_cache_stats
from modules.request_queue import queue_request, try_process_queue, get_queue_stats, is_api_unavailable
from modules.query_optimizer import find_similar_cached_response, _similarity_score
from modules.app_perf import record_timing
from modules.app_views import (
    init_analysis_state,
    render_chart_collection,
    render_chat_history_entry,
    render_dataframe_result,
    render_dict_result,
    render_follow_up_section,
)
from modules.app_logic import (
    augment_kpis_with_trends,
    build_ai_summary_fallback,
    build_failure_message,
    build_follow_up_suggestions,
    build_graphable_query_suggestions,
    build_overview_hero_chart,
    build_result_history_entry,
    build_summary_list,
    format_metric_value,
    generate_quick_insights,
    is_error_like_text,
    summarize_report_history,
)
from ui_components import (
    render_assistant_bubble,
    render_cache_statistics,
    render_chart_card,
    render_insight_card,
    render_kpi_cards,
    render_quality_badge,
    render_queue_status,
    render_result_status,
    render_section_header,
    render_settings_panel,
    render_structured_response,
    render_table_panel,
    render_user_bubble,
)


# Similar-query reuse can return wrong answers for near-but-different queries
# (for example, "budget" vs "actual"). Keep exact-query cache as default.
ENABLE_SIMILAR_QUERY_REUSE = False


@st.cache_data(show_spinner=False)
def _compute_overview_cards(df: pd.DataFrame) -> dict[str, str]:
    return generate_quick_insights(df)


@st.cache_data(show_spinner=False)
def _compute_overview_hero_chart(df: pd.DataFrame):
    return build_overview_hero_chart(df)


@st.cache_data(show_spinner=False)
def _compute_column_details(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Column": df.columns,
            "Type": df.dtypes.astype(str).values,
            "Non-Null Count": df.count().values,
            "Null Count": df.isnull().sum().values,
            "Unique Values": df.nunique().values,
            "Example Value": [str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else "N/A" for col in df.columns],
        }
    )


@st.cache_data(show_spinner=False)
def _compute_statistics(df: pd.DataFrame) -> pd.DataFrame:
    return df.describe(include="all").reset_index()


@st.cache_data(show_spinner=False)
def _compute_auto_insights(df: pd.DataFrame) -> list[str]:
    return generate_auto_insights(df)


def _normalize_summary_lines(summary_value) -> list[str]:
    if summary_value is None:
        return []

    if isinstance(summary_value, str):
        lines = [line.strip("-•\t ") for line in summary_value.replace("\r", "").splitlines() if line.strip()]
        return lines or ([summary_value.strip()] if summary_value.strip() else [])

    if isinstance(summary_value, (list, tuple, set)):
        values = [str(item or "").strip() for item in summary_value if str(item or "").strip()]
        if len(values) >= 4 and all(len(item) <= 2 for item in values):
            joined = "".join(values).strip()
            if joined:
                joined = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", joined)
                joined = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", joined)
                return [joined]
        return values

    text = str(summary_value).strip()
    return [text] if text else []


def _query_cache_key(query: str, dataset_key: str | None) -> str:
    normalized = " ".join(str(query or "").strip().lower().split())
    source = f"{dataset_key or 'dataset'}::{normalized}".encode("utf-8")
    return hashlib.sha1(source).hexdigest()


def _pick_preferred_column(columns: list[str], keywords: list[str]) -> str | None:
    if not columns:
        return None

    lowered = [(col, str(col).lower()) for col in columns]
    for keyword in keywords:
        for original, lower_name in lowered:
            if keyword in lower_name:
                return original
    return columns[0]


def _detect_datetime_columns(df: pd.DataFrame, schema: dict) -> list[str]:
    schema_dates = schema.get("datetime_columns", []) if schema else []
    if schema_dates:
        return schema_dates

    date_like_cols = []
    for col in df.columns:
        lower_col = str(col).lower()
        if any(token in lower_col for token in ("date", "time", "month", "year", "day")):
            date_like_cols.append(col)
    return date_like_cols


def _format_dataset_label(dataset_name: str | None) -> str:
    if not dataset_name:
        return "this dataset"

    dataset_label = re.sub(r"\.[^.]+$", "", str(dataset_name))
    dataset_label = re.sub(r"[_-]+", " ", dataset_label).strip()
    return dataset_label.title() if dataset_label else "this dataset"


def _generate_dynamic_query_suggestions(
    df: pd.DataFrame,
    schema: dict | None = None,
    dataset_name: str | None = None,
) -> list[str]:
    schema = schema or {}
    numeric_cols = schema.get("numeric_columns", []) or df.select_dtypes(include="number").columns.tolist()
    categorical_cols = schema.get("categorical_columns", []) or df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = _detect_datetime_columns(df, schema)
    dataset_label = _format_dataset_label(dataset_name)

    preferred_metric = _pick_preferred_column(
        numeric_cols,
        ["revenue", "sales", "profit", "price", "amount", "cost", "income"],
    )
    preferred_category = _pick_preferred_column(
        categorical_cols,
        ["region", "product", "category", "segment", "department", "team"],
    )
    secondary_metric = numeric_cols[1] if len(numeric_cols) > 1 else None

    by_type: dict[str, str] = {}

    if preferred_metric and preferred_category:
        by_type["ranking"] = f"In {dataset_label}, what are the top 5 {preferred_category} by {preferred_metric}?"

    if preferred_metric and datetime_cols:
        by_type["trend"] = f"In {dataset_label}, how has {preferred_metric} changed over time?"

    if preferred_metric and preferred_category:
        by_type["comparison"] = f"In {dataset_label}, compare {preferred_metric} across {preferred_category}."

    if preferred_metric and preferred_category:
        by_type["aggregation"] = f"In {dataset_label}, what is the average {preferred_metric} per {preferred_category}?"

    if preferred_metric and preferred_category:
        by_type["distribution"] = f"In {dataset_label}, how is {preferred_metric} distributed across {preferred_category}?"

    if len(by_type) < 3 and preferred_metric and secondary_metric:
        by_type["metric_pair"] = f"In {dataset_label}, what is the relationship between {preferred_metric} and {secondary_metric}?"

    if len(by_type) < 3 and preferred_metric:
        by_type["summary"] = f"In {dataset_label}, summarize key statistics for {preferred_metric}."

    if len(by_type) < 3 and preferred_category:
        by_type["category_overview"] = f"In {dataset_label}, show the distribution of records by {preferred_category}."

    if len(by_type) < 3:
        col_name = df.columns[0] if len(df.columns) else "the dataset"
        by_type["dataset_overview"] = f"In {dataset_label}, give an overview of {col_name} and key trends."

    ordered_types = [
        "ranking",
        "trend",
        "comparison",
        "aggregation",
        "distribution",
        "metric_pair",
        "summary",
        "category_overview",
        "dataset_overview",
    ]

    suggestions: list[str] = []
    for suggestion_type in ordered_types:
        if suggestion_type in by_type:
            suggestions.append(by_type[suggestion_type])

    return suggestions[:5]


def _get_ai_try_asking_suggestions(df: pd.DataFrame, schema: dict | None = None, force_regenerate: bool = False) -> list[str]:
    """
    Get 'Try Asking' question suggestions for the dataset.
    
    Uses rule-based generation scaled to dataset complexity (no API calls).
    
    Args:
        df: Dataset
        schema: Dataset schema
        force_regenerate: Force new generation (ignore cache)
    
    Returns:
        List of suggestion questions
    """
    schema = schema or {}
    dataset_key = str(st.session_state.get("active_dataset_cache_key") or st.session_state.get("active_dataset_key") or st.session_state.get("dataset_name") or "dataset")
    cache_key = f"ai_try_asking_questions::{dataset_key}"

    # Check session cache first (fastest)
    if not force_regenerate:
        cached = st.session_state.get(cache_key)
        if isinstance(cached, list) and cached:
            return cached

        # Check disk cache (persisted across restarts)
        persisted = get_cached_try_asking_questions(dataset_key)
        if persisted:
            st.session_state[cache_key] = persisted
            return st.session_state[cache_key]

    # Generate using rule-based logic (zero API costs)
    from modules.chat_handler import generate_try_asking_suggestions
    
    try:
        questions = generate_try_asking_suggestions(df, schema, st.session_state.get("dataset_name"))
    except Exception as exc:
        questions = []

    if not questions:
        return []

    saved_questions = save_cached_try_asking_questions(dataset_key, questions)
    st.session_state[cache_key] = saved_questions
    return st.session_state[cache_key]


def _render_try_asking_section(df: pd.DataFrame, schema: dict | None = None):
    suggestions = _get_ai_try_asking_suggestions(df, schema)
    if not suggestions:
        return

    # Keep this section simple to avoid extra visual artifacts.
    st.markdown("#### Try asking")
    st.markdown("<div class='try-box try-asking-section'>", unsafe_allow_html=True)
    for start in range(0, len(suggestions), 3):
        row_items = suggestions[start:start + 3]
        chip_cols = st.columns(len(row_items), gap="small")
        for offset, suggestion in enumerate(row_items):
            idx = start + offset
            with chip_cols[offset]:
                if st.button(suggestion, key=f"try_asking_{idx}", width="stretch"):
                    queue_query(suggestion)
    st.markdown("</div>", unsafe_allow_html=True)


def render_data_overview_tab(df: pd.DataFrame):
    perf_started = time.perf_counter()
    quick_insights = _compute_overview_cards(df)
    hero_fig = _compute_overview_hero_chart(df)
    st.markdown(
        f"""
        <div class="quick-insights-panel section-hero">
            <div class="section-hero__eyebrow">Quick Insights Panel</div>
            <div class="section-hero__title">AI signal summary for this dataset</div>
            <div class="section-hero__subtitle">The dashboard surfaces a standout driver, a weak point, and the strongest anomaly before you ask a question.</div>
            <div class="quick-insights-grid">
                <div class="quick-insight-item">
                    <div class="quick-insight-label">Highest Value Driver</div>
                    <div class="quick-insight-value">{html.escape(quick_insights["Highest Value Driver"])}</div>
                </div>
                <div class="quick-insight-item">
                    <div class="quick-insight-label">Lowest Performance Signal</div>
                    <div class="quick-insight-value">{html.escape(quick_insights["Lowest Performance Signal"])}</div>
                </div>
                <div class="quick-insight-item">
                    <div class="quick-insight-label">Key Anomaly</div>
                    <div class="quick-insight-value">{html.escape(quick_insights["Key Anomaly"])}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if hero_fig is not None:
        st.markdown('<div class="hero-chart-card" style="margin-bottom: 16px;">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Hero Chart</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">A spotlight view of the clearest trend or comparison available in the current dataset.</div>', unsafe_allow_html=True)
        render_chart_card(hero_fig, st)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    render_table_panel("Dataset Preview", df, "dataset_preview", max_rows=100)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    fast_mode = bool(st.session_state.get("ui_fast_mode", True))

    with st.expander("Column Details", expanded=not fast_mode):
        col_info = _compute_column_details(df)
        render_table_panel("Column Details", col_info, "column_details")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.expander("Statistics", expanded=False):
        stats_df = _compute_statistics(df)
        render_table_panel("Statistics", stats_df, "statistics")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.expander("Automatic Dataset Insights", expanded=not fast_mode):
        st.markdown('<div class="glass-card insight-block" style="margin-bottom: 24px;">', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Fast pattern detection pulled straight from the current data shape and distributions.</div>', unsafe_allow_html=True)
        auto_insights = _compute_auto_insights(df)
        for insight in auto_insights:
            st.write("•", insight)
        st.markdown("</div>", unsafe_allow_html=True)

    record_timing("overview_render_ms", (time.perf_counter() - perf_started) * 1000)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def render_ai_analyst_tab(df: pd.DataFrame, schema: dict, api_key: str, logger):
    # Cleanup stale cache periodically (prevent unbounded growth)
    # This runs once per tab render, fairly harmless since it's cached on disk
    try:
        cleanup_stale_cache(max_cache_entries_per_dataset=100, max_age_seconds=604800)  # 7 days
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("cleanup_stale_cache_failed", exc_info=True)
    
    # Render settings panel in sidebar
    ai_settings = render_settings_panel()
    
    # Render cache statistics in sidebar
    cache_stats = get_cache_stats()
    render_cache_statistics(cache_stats)
    
    st.markdown(
        """
    <div class="chat-shell">
        <div class="chat-hero">
            <div>
                <div class="chat-hero__eyebrow">Analyst Workspace</div>
                <div class="chat-hero__title">AI Analyst Workspace</div>
                <div class="chat-hero__subtitle">Ask anything about your data, review structured answers, and move from question to insight fast.</div>
            </div>
            <div class="chat-status">
                <span class="typing-dots"><span></span><span></span><span></span></span>
                <span style="margin-left:8px;">Live analysis ready</span>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if st.button("🧹 Clear Current View", key="clear_chat_btn"):
        # Non-destructive clear: keep saved chats in history, just reset the active view.
        st.session_state.pending_query = ""
        st.session_state.pending_query_id = ""
        st.session_state.last_processed_query_id = ""
        st.session_state["selected_chat_history_id"] = ""
        st.session_state["chat_view_mode"] = "new"

    st.markdown("</div>", unsafe_allow_html=True)
    init_analysis_state()

    selected_history_id = str(st.session_state.get("selected_chat_history_id", "") or "").strip()
    chat_view_mode = str(st.session_state.get("chat_view_mode", "") or "").strip()
    history_entries = list(st.session_state.chat_history)
    # Default to a clean new-chat canvas. Saved history appears only when a
    # specific entry is selected from the sidebar.
    visible_history_entries = []
    if chat_view_mode == "new":
        visible_history_entries = []
    if selected_history_id:
        visible_history_entries = [
            entry
            for entry in history_entries
            if str(entry.get("history_id") or entry.get("cloud_history_id") or "").strip() == selected_history_id
        ]
        if not visible_history_entries:
            st.session_state["selected_chat_history_id"] = ""
            visible_history_entries = []

    if selected_history_id and visible_history_entries:
        st.info("Viewing a saved chat. Start a new question or open the latest chat to continue.")
        if st.button("⬅️ Back to new chat", key="back_to_latest_chat_btn"):
            st.session_state["selected_chat_history_id"] = ""
            st.session_state["chat_view_mode"] = "new"
            st.rerun()
    elif chat_view_mode == "new":
        st.info("New chat ready. Ask your next question to start a fresh thread.")

    for entry in visible_history_entries:
        render_chat_history_entry(entry)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Render try-asking suggestions in an expander to save space and API calls
    # (suggestions are lazy-loaded only when user expands the section)
    with st.expander("💡 Try asking...", expanded=False):
        _render_try_asking_section(df, schema)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
    is_processing = bool(st.session_state.get("chat_processing", False))
    submitted_query = st.chat_input(
        "Ask anything about your data...",
        key="analyst_chat_input",
        disabled=is_processing,
    )

    if "auto_query" in st.session_state:
        # If an auto_query was scheduled (e.g., from a follow-up click), set the pending
        # query directly instead of calling `queue_query()` to avoid double-queuing and
        # race conditions that can cause the previous query to be prematurely persisted.
        submitted_query = st.session_state.get("auto_query")
        try:
            del st.session_state.auto_query
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("failed_delete_auto_query", exc_info=True)
        if submitted_query:
            st.session_state["selected_chat_history_id"] = ""
            st.session_state["chat_view_mode"] = "new"
            st.session_state["pending_query"] = submitted_query
            st.session_state["pending_query_id"] = str(time.time_ns())

    if submitted_query:
        # This branch handles user-entered chat input (not auto_query follow-ups).
        st.session_state["selected_chat_history_id"] = ""
        st.session_state["chat_view_mode"] = ""
        queue_query(submitted_query)

    query = st.session_state.get("pending_query", "")
    query_id = st.session_state.get("pending_query_id", "")
    queued_query_text = str(st.session_state.get("queued_query_text", "") or "").strip()
    if not query and queued_query_text:
        if st.button("Retry queued request", key="retry_queued_request_btn", width="stretch"):
            st.session_state["pending_query"] = queued_query_text
            st.session_state["pending_query_id"] = str(time.time_ns())
            st.rerun()
    if not query:
        return

    # Streamlit reruns can execute this function multiple times; process each query id once.
    # Guard against processing during active chat
    if st.session_state.get("chat_processing", False):
        return
    if query_id and st.session_state.get("last_processed_query_id") == query_id:
        return

    dataset_key = str(st.session_state.get("active_dataset_key") or st.session_state.get("dataset_name") or "dataset")
    dataset_cache_key = str(st.session_state.get("active_dataset_cache_key") or "")
    
    # Build cache key for this query
    query_hash = _query_cache_key(query, dataset_key)
    cache_key = f"chat_response_cache::{query_hash}"
    
    # Try session cache first (fast path)
    cached_outcome = st.session_state.get(cache_key)
    if isinstance(cached_outcome, dict):
        outcome = cached_outcome
    else:
        outcome = None
    
    # If not in session, try disk cache (persistent across restarts)
    if outcome is None and dataset_cache_key:
        disk_cached = get_cached_response(dataset_cache_key, query_hash)
        if disk_cached:
            outcome = disk_cached
            st.session_state[cache_key] = outcome  # Restore to session
    
    # If still not found, optionally check for similar queries in cache.
    # Disabled by default to favor correctness over cache hit-rate.
    if ENABLE_SIMILAR_QUERY_REUSE and outcome is None and dataset_cache_key:
        # Get all cached responses for this dataset to find similar ones
        # This uses a simple approach - in production, could optimize with vector DB
        all_dataset_responses = {}
        try:
            from modules.prompt_cache import _load_cache_data
            cache_data = _load_cache_data()
            dataset_entry = cache_data.get(dataset_cache_key, {})
            all_dataset_responses = dataset_entry.get("response_cache", {})
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("failed_loading_prompt_cache_responses", exc_info=True)
            all_dataset_responses = {}
        
        if all_dataset_responses:
            similar_cached_query, similar_response = find_similar_cached_response(
                query,
                all_dataset_responses,
                similarity_threshold=0.95,
            )
            if similar_response and similar_cached_query:
                outcome = similar_response
                st.session_state[cache_key] = outcome  # Cache this too
                # Log the deduplication
                if logger:
                    similarity = _similarity_score(query, similar_cached_query)
                    logger.info(
                        "query_deduplication_hit",
                        extra={
                            "original_query": query[:100],
                            "similar_cached_query": similar_cached_query[:100],
                            "similarity": similarity,
                        },
                    )
    
    # Track cache hit/miss metrics
    if outcome is not None:
        if dataset_cache_key:
            record_cache_hit(dataset_cache_key, query_hash)
        record_timing("chat_cache_lookup_ms", 0.0)
    else:
        if dataset_cache_key:
            record_cache_miss(dataset_cache_key, query_hash)

    add_recent_activity("question", query)
    logger.info("chat_query_received", extra={"query": query[:200], "rows": len(df), "cols": len(df.columns)})
    render_user_bubble(query)
    st.session_state["chat_processing"] = True

    query_started = time.perf_counter()
    should_preserve_pending_query = False
    status_placeholder = st.empty()
    status_placeholder.info("Analyzing your request...")
    preview_cols = schema.get("numeric_columns", []) if isinstance(schema, dict) else []
    preview_metric = preview_cols[0] if preview_cols else (df.select_dtypes(include="number").columns.tolist()[:1] or [None])[0]
    if preview_metric:
        try:
            preview_total = float(pd.to_numeric(df[preview_metric], errors="coerce").fillna(0).sum())
            st.caption(f"Quick preview: total {preview_metric} is approximately {preview_total:,.2f}.")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("preview_total_calculation_failed", exc_info=True)
    try:
        if outcome is None:
            status_placeholder.info("Reading dataset context...")
            with st.spinner("🔍 AI analyzing your dataset..."):
                outcome = chat_handler(
                    query=query,
                    df=df,
                    schema=schema,
                    dataset_name=st.session_state.get("dataset_name"),
                    logger=logger,
                    last_api_call_ts=float(st.session_state.get("last_api_call_ts", 0.0) or 0.0),
                    min_call_interval_seconds=1.0,
                    result_history=st.session_state.get("result_history", []),
                    result_history_details=st.session_state.get("result_history_details", []),
                )
            st.session_state[cache_key] = outcome
            record_timing("chat_handler_ms", (time.perf_counter() - query_started) * 1000)
            
            # Also save to disk cache for persistence across restarts
            if dataset_cache_key:
                save_cached_response(dataset_cache_key, query_hash, outcome)
        else:
            status_placeholder.success("Loaded from cache.")

        st.session_state["last_api_call_ts"] = float(outcome.get("last_api_call_ts", time.time()))

        ai_response = outcome.get("ai_response", "")
        result = outcome.get("result", ai_response)
        chart_data = outcome.get("chart_data")
        chart_figs = outcome.get("chart_figs", [])
        suggestions = outcome.get("suggestions", "")
        summary_list = _normalize_summary_lines(outcome.get("summary_list", []))
        query_rejected = bool(outcome.get("query_rejected", False))
        insight = outcome.get("insight", "")
        code = outcome.get("code", "# single-call chat pipeline")
        intent = outcome.get("intent", "analysis")
        structured_response = outcome.get("structured_response") or {}
        response_status = str(outcome.get("status", "ok"))  # "ok", "queued", "error"
        confidence = outcome.get("confidence", 0.0)  # Extracted from outcome
        source_columns = outcome.get("source_columns", [])  # Extracted from outcome

        if isinstance(result, pd.DataFrame) and not result.empty:
            chart_data = result
        elif isinstance(result, pd.Series):
            try:
                chart_data = result.reset_index()
            except ValueError:
                chart_data = result.reset_index(drop=True).to_frame()
            if chart_data.shape[1] == 2:
                chart_data.columns = ["Category", "Value"]

        # Handle queued requests (rate-limited but will retry automatically)
        if response_status == "queued":
            should_preserve_pending_query = True
            st.session_state["queued_query_text"] = query
            st.info(
                "⏳ **Working on your answer**\n\n"
                "We are preparing your insight. This can take a few extra seconds during busy times."
            )
            queue_stats = get_queue_stats()
            if queue_stats.get("length", 0) > 0:
                render_queue_status(queue_stats)
            retry_cols = st.columns([1, 1])
            with retry_cols[0]:
                if st.button("Retry now", key=f"retry_now_{query_id or hash(query)}", width="stretch"):
                    st.session_state["pending_query"] = query
                    st.session_state["pending_query_id"] = str(time.time_ns())
                    st.rerun()
            with retry_cols[1]:
                if st.button("Ask a simpler version", key=f"ask_simpler_{query_id or hash(query)}", width="stretch"):
                    st.session_state["pending_query"] = f"Summarize briefly: {query}"
                    st.session_state["pending_query_id"] = str(time.time_ns())
                    st.rerun()
            st.session_state["chat_processing"] = False
            return

        if ai_response:
            clean_response = clean_text(ai_response)
            if not summary_list and not query_rejected and not is_error_like_text(ai_response):
                summary_list = build_ai_summary_fallback(ai_response)

            clean_response = re.sub(r"<[^>]+>", "", clean_response)
            
            # Display queue status if requests are waiting
            queue_stats = get_queue_stats()
            render_queue_status(queue_stats)
            
            # Render quality badge with confidence and source columns
            render_quality_badge(confidence, source_columns)
            
            if structured_response and any(structured_response.values()):
                render_structured_response(structured_response)
            else:
                structured = structure_response(clean_response)
                if structured and any(structured.values()):
                    render_structured_response(structured)
                else:
                    render_assistant_bubble(clean_response)
            status_placeholder.success("Answer ready.")
            st.session_state["queued_query_text"] = ""



        chart_validation_warnings = []
        if isinstance(chart_data, pd.DataFrame) and chart_data.empty:
            st.warning("No outliers found in the dataset based on the current criteria.")
            chart_data = None

        if chart_data is not None:
            render_dataframe_result(chart_data, f"live_table_{hash(query)}")
            if not chart_figs:
                _, chart_validation_warnings = validate_chart_data(chart_data)
                chart_figs = auto_visualize(chart_data)

            if chart_figs:
                render_result_status(
                    "Chart generated",
                    "The result shape supports visualization, so charts are shown below with chart-type options and download tools.",
                    kind="success",
                )
                render_chart_collection(chart_figs)
            elif not query_rejected:
                if chart_validation_warnings:
                    for warning in chart_validation_warnings:
                        st.caption(warning)
                render_result_status(
                    "No chart shown",
                    "This result is valid, but it does not have a chart-friendly shape. Try grouping by a category or time column.",
                    kind="info",
                )

            if chart_data is not None and not insight:
                insight = generate_business_insight(chart_data)
            if insight:
                render_insight_card(insight)
        elif not ai_response and str(result) != "None":
            st.markdown('<div class="glass-card" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
            st.write(str(result))
            st.markdown("</div>", unsafe_allow_html=True)

        if summary_list:
            st.markdown('<div class="ai-theme-box">', unsafe_allow_html=True)
            with st.expander("Answer Summary", expanded=False):
                for line in summary_list:
                    st.write("-", line)
            st.markdown("</div>", unsafe_allow_html=True)

        if suggestions and not query_rejected:
            render_follow_up_section(suggestions, f"live_suggestion_{hash(query)}")

        rephrase_suggestions = outcome.get("rephrases") or []
        if (is_error_like_text(result) or is_error_like_text(ai_response)) and rephrase_suggestions:
            st.markdown('<div class="ai-theme-box">', unsafe_allow_html=True)
            st.markdown("**Suggested Rephrases**")
            for idx, suggestion in enumerate(rephrase_suggestions):
                if st.button(suggestion, key=f"rephrase_prompt_{hash(query)}_{idx}", width="stretch"):
                    queue_query(suggestion)
            st.markdown("</div>", unsafe_allow_html=True)

        intent_info = {"intent": intent}
        persist_analysis_cycle(
            query=query,
            result=result,
            chart_data=chart_data,
            chart_figs=chart_figs,
            code=code,
            insight=insight,
            ai_response=ai_response,
            summary_list=summary_list,
            suggestions=suggestions,
            query_rejected=query_rejected,
            is_axes_result=False,
            intent=intent,
            rephrases=rephrase_suggestions if (is_error_like_text(result) or is_error_like_text(ai_response)) else [],
            result_history_entry=build_result_history_entry(query, result, chart_data, intent_info, query_rejected),
            confidence=confidence,
            source_columns=source_columns,
        )
    finally:
        record_timing("chat_total_ms", (time.perf_counter() - query_started) * 1000)
        st.session_state["chat_processing"] = False
        st.session_state["last_processed_query_id"] = query_id
        # Preserve newly queued follow-up prompts clicked during this render pass.
        # If pending_query_id changed, another prompt was queued and must not be cleared.
        active_pending_id = str(st.session_state.get("pending_query_id", "") or "")
        if (not should_preserve_pending_query) and (not active_pending_id or active_pending_id == str(query_id or "")):
            st.session_state["pending_query"] = ""
            st.session_state["pending_query_id"] = ""


def render_forecasting_tab(df: pd.DataFrame):
    st.markdown(
        """
        <div class="forecast-hero">
            <div class="section-hero__eyebrow">Forecasting Studio</div>
            <div class="section-hero__title">Project your next business move</div>
            <div class="section-hero__subtitle">Generate a clean outlook with projected values, confidence bands, and a quick trend summary.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_section_header("🔮 Revenue / Sales Forecasting", "Predict future trends based on historical data patterns.")
    st.markdown('<div class="glass-card forecast-controls" style="margin-bottom: 24px;">', unsafe_allow_html=True)

    forecast_periods = st.slider("Forecast periods (months):", min_value=1, max_value=12, value=3)

    if st.button("Generate Forecast", key="forecast_btn"):
        with st.spinner("Running forecast analysis..."):
            forecast_result = forecast_revenue(df, periods=forecast_periods)

        if forecast_result["available"]:
            add_recent_activity("forecast", f"Forecast generated for {forecast_result['metric']}")
            st.success(forecast_result["message"])

            trend = forecast_result["trend"]
            metric = forecast_result["metric"]
            trend_icon = "📈" if trend == "increasing" else "📉" if trend == "declining" else "➡"
            fore_df = forecast_result["forecast_df"]
            latest_prediction = fore_df["Predicted"].iloc[-1]
            st.markdown(
                f"""
                <div class="forecast-stat-grid">
                    <div class="forecast-stat-card">
                        <div class="forecast-stat-label">Projected Metric</div>
                        <div class="forecast-stat-value">{html.escape(str(metric))}</div>
                        <div class="forecast-stat-subtle">Primary series selected for forecasting</div>
                    </div>
                    <div class="forecast-stat-card">
                        <div class="forecast-stat-label">Latest Prediction</div>
                        <div class="forecast-stat-value">{format_metric_value(latest_prediction)}</div>
                        <div class="forecast-stat-subtle">End of {forecast_periods}-month horizon</div>
                    </div>
                    <div class="forecast-stat-card">
                        <div class="forecast-stat-label">Trend Direction</div>
                        <div class="forecast-stat-value">{trend_icon} {html.escape(trend.title())}</div>
                        <div class="forecast-stat-subtle">Slope {forecast_result['slope']:,.2f} units per month</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.info(f"{trend_icon} The {metric} trend is **{trend}** (slope: {forecast_result['slope']:,.2f} per month)")

            st.subheader("📊 Forecast Visualization")
            hist_df = forecast_result["historical_df"]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_df["Date"], y=hist_df[metric], mode="lines+markers", name="Historical", line=dict(color="#2563EB", width=2)))
            fig.add_trace(go.Scatter(x=fore_df["Date"], y=fore_df["Predicted"], mode="lines+markers", name="Forecast", line=dict(color="#F59E0B", width=2, dash="dash")))
            fig.add_trace(
                go.Scatter(
                    x=pd.concat([fore_df["Date"], fore_df["Date"][::-1]]),
                    y=pd.concat([fore_df["Upper Bound"], fore_df["Lower Bound"][::-1]]),
                    fill="toself",
                    fillcolor="rgba(245,158,11,0.15)",
                    line=dict(color="rgba(255,255,255,0)"),
                    name="95% Confidence Interval",
                )
            )

            render_chart_card(fig, st)
            render_table_panel("Forecast Values", fore_df, "forecast_values")
        else:
            st.warning(forecast_result["message"])
            st.info("💡 Tip: Forecasting works best with datasets that have date columns and numeric metrics like revenue or sales.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_reports_tab():
    st.markdown(
        """
        <div class="report-hero">
            <div class="section-hero__eyebrow">Executive Reporting</div>
            <div class="section-hero__title">Package the analysis into a polished PDF</div>
            <div class="section-hero__subtitle">Bundle saved AI analyses, visuals, and insights into a report that feels presentation-ready.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="glass-card" style="margin-bottom: 24px; margin-top: 18px;">', unsafe_allow_html=True)

    history = st.session_state.get("analysis_history", [])

    if len(history) == 0:
        st.info("Your report is currently empty. Head over to the AI Data Analyst tab and ask a question to start building it.")
    else:
        report_stats = summarize_report_history(history)
        st.markdown(
            f"""
            <div class="report-stat-grid">
                <div class="report-stat-card">
                    <div class="report-stat-label">Saved Analyses</div>
                    <div class="report-stat-value">{report_stats["analyses"]}</div>
                    <div class="report-stat-subtle">Sections ready for export</div>
                </div>
                <div class="report-stat-card">
                    <div class="report-stat-label">AI Insights</div>
                    <div class="report-stat-value">{report_stats["insights"]}</div>
                    <div class="report-stat-subtle">Narrative findings collected</div>
                </div>
                <div class="report-stat-card">
                    <div class="report-stat-label">Charts Included</div>
                    <div class="report-stat-value">{report_stats["charts"]}</div>
                    <div class="report-stat-subtle">Visuals available for the brief</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns([1.8, 1.2], gap="large")

        with col1:
            st.markdown('<div class="report-list-card">', unsafe_allow_html=True)
            st.markdown(f"#### 📋 Report Contents ({len(history)} Analyses)")
            st.caption("Each saved analysis will become its own section in the final PDF.")
            for i, entry in enumerate(history, 1):
                st.markdown(
                    f'''
                <div class="report-query-item">
                    <div style="color: #94A3B8; font-size: 11px; font-weight: bold; margin-bottom: 4px;">
                        ANALYSIS #{i}
                    </div>
                    <div style="color: #E2E8F0; font-weight: 600; font-size: 15px;">
                        "{entry['query']}"
                    </div>
                </div>
                ''',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="report-config-card">', unsafe_allow_html=True)
            st.markdown("#### ⚙️ Report Configuration")
            st.markdown(
                """
            <div class="report-config-meta">
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 700; color: #E2E8F0;">Document Type</div>
                    <div>Executive PDF Briefing</div>
                </div>
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 700; color: #E2E8F0;">Included Features</div>
                    <div class="report-feature-list">
                        <div class="report-feature-item">Cover page and table of contents</div>
                        <div class="report-feature-item">High-resolution visualizations</div>
                        <div class="report-feature-item">Formatted data tables</div>
                        <div class="report-feature-item">AI business insights</div>
                        <div class="report-feature-item">Strategic recommendations</div>
                    </div>
                </div>
                <div class="report-actions">
            """,
                unsafe_allow_html=True,
            )

            if st.button("Generate Professional PDF", type="primary", width="stretch"):
                with st.spinner("Compiling and formatting your professional report..."):
                    file_path = generate_pdf(query=None, summary_text=None, dataframe=None, charts=None, analysis_history=history)
                add_recent_activity("report", "PDF report created")
                with open(file_path, "rb") as file:
                    st.download_button(
                        "Download PDF Report",
                        data=file,
                        file_name="AI_Executive_Report.pdf",
                        mime="application/pdf",
                        width="stretch",
                    )
                st.success("Report generated successfully!")
            st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard_header(df: pd.DataFrame):
    dataset_name = str(st.session_state.get("dataset_name", "Active Dataset"))
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        lead_metric = max(numeric_cols, key=lambda col: df[col].fillna(0).sum())
        lead_metric_label = lead_metric.replace("_", " ").title()
        lead_metric_value = format_metric_value(df[lead_metric].fillna(0).sum())
    else:
        lead_metric_label = "Numeric Signal"
        lead_metric_value = "N/A"

    st.markdown(
        f"""
        <div class="landing-hero">
            <div class="landing-hero__content">
                <div class="landing-hero__kicker">Apex Analytics Platform</div>
                <div class="landing-hero__title">Ask your data anything and turn raw records into executive-ready decisions.</div>
                <div class="landing-hero__subtitle">{html.escape(dataset_name)} is loaded and ready. Use the AI analyst, visual summaries, and forecasting workflows to move from question to action in minutes.</div>
                <div class="landing-hero__badges">
                    <span class="landing-hero__badge">Live dataset context</span>
                    <span class="landing-hero__badge">Executive-ready views</span>
                    <span class="landing-hero__badge">Signal-first layout</span>
                </div>
            </div>
            <div class="landing-hero__stats">
                <div class="landing-hero__stat">
                    <div class="landing-hero__stat-label">Rows</div>
                    <div class="landing-hero__stat-value">{df.shape[0]:,}</div>
                </div>
                <div class="landing-hero__stat">
                    <div class="landing-hero__stat-label">Columns</div>
                    <div class="landing-hero__stat-value">{df.shape[1]}</div>
                </div>
                <div class="landing-hero__stat">
                    <div class="landing-hero__stat-label">{html.escape(lead_metric_label)}</div>
                    <div class="landing-hero__stat-value">{html.escape(str(lead_metric_value))}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_section_header("📊 Data Intelligence Dashboard", "Live KPI, insight, and trend snapshot for your active business dataset.")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    kpis = augment_kpis_with_trends(generate_kpis(df), df)
    render_kpi_cards(kpis)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
