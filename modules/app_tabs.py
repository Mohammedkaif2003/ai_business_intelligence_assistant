import html
import re
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.ai_code_generator import generate_analysis_code
from modules.ai_conversation import generate_conversational_response
from modules.auto_insights import generate_auto_insights
from modules.auto_visualizer import auto_visualize, build_chart_from_query, validate_chart_data
from modules.code_executor import execute_code
from modules.forecasting import forecast_revenue
from modules.insight_engine import generate_business_insight
from modules.kpi_engine import generate_kpis
from modules.query_utils import (
    add_date_filter,
    add_filters,
    build_clarification_prompt,
    build_rephrase_suggestions,
    classify_query_intent,
    detect_simple_query,
    enhance_query,
    get_irrelevant_query_message,
    is_dataset_related_query,
    is_memory_query,
)
from modules.report_generator import generate_pdf
from modules.text_utils import clean_text, structure_response
from modules.app_state import add_recent_activity, persist_analysis_cycle
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
    render_chart_card,
    render_insight_card,
    render_kpi_cards,
    render_result_status,
    render_section_header,
    render_structured_response,
    render_table_panel,
    render_user_bubble,
)


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


def _render_try_asking_section(df: pd.DataFrame, schema: dict | None = None):
    suggestions = _generate_dynamic_query_suggestions(df, schema, st.session_state.get("dataset_name"))
    if not suggestions:
        return

    st.markdown('<div class="ai-theme-box">', unsafe_allow_html=True)
    st.markdown("#### Try asking")
    for start in range(0, len(suggestions), 3):
        row_items = suggestions[start:start + 3]
        chip_cols = st.columns(len(row_items))
        for offset, suggestion in enumerate(row_items):
            idx = start + offset
            with chip_cols[offset]:
                if st.button(suggestion, key=f"try_asking_{idx}", use_container_width=True):
                    st.session_state.auto_query = suggestion
    st.markdown("</div>", unsafe_allow_html=True)


def render_data_overview_tab(df: pd.DataFrame):
    quick_insights = generate_quick_insights(df)
    hero_fig = build_overview_hero_chart(df)
    st.markdown(
        f"""
        <div class="quick-insights-panel">
            <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#8fb4db;">Quick Insights Panel</div>
            <div style="font-size:24px; font-weight:800; color:#f8fbff; margin-top:6px;">AI signal summary for this dataset</div>
            <div style="color:#a8bad8; margin-top:6px;">The dashboard surfaces a standout driver, a weak point, and the strongest anomaly before you ask a question.</div>
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
        st.markdown("### Hero Chart")
        render_chart_card(hero_fig, st)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    render_table_panel("Dataset Preview", df, "dataset_preview", max_rows=200)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    col_info = pd.DataFrame(
        {
            "Column": df.columns,
            "Type": df.dtypes.astype(str).values,
            "Non-Null Count": df.count().values,
            "Null Count": df.isnull().sum().values,
            "Unique Values": df.nunique().values,
            "Example Value": [str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else "N/A" for col in df.columns],
        }
    )
    render_table_panel("Column Details", col_info, "column_details")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    render_table_panel("Statistics", df.describe().reset_index(), "statistics")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="glass-card" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    st.subheader("🔎 Automatic Dataset Insights")
    auto_insights = generate_auto_insights(df)
    for insight in auto_insights:
        st.write("•", insight)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def render_ai_analyst_tab(df: pd.DataFrame, schema: dict, api_key: str, logger):
    # Self-contained hero block — closes all its own tags so the typing-dots
    # animation renders correctly and the Clear Chat button below is not
    # swallowed into the flex container.
    st.markdown(
        """
        <div class="chat-hero-card">
            <div class="chat-hero-block">
                <div>
                    <div class="chat-hero__title">AI Analyst Workspace</div>
                    <div class="chat-hero__subtitle">Ask anything about your data, review structured answers, and move from question to insight fast.</div>
                </div>
                <div class="chat-status">
                    <span class="chat-status__pulse"></span>
                    <span class="typing-dots" aria-hidden="true"><span></span><span></span><span></span></span>
                    <span class="chat-status__label">Live analysis ready</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    clear_col, _ = st.columns([0.25, 0.75])
    with clear_col:
        if st.button("🗑️ Clear Chat", key="clear_chat_btn", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.messages = []
            st.session_state.analysis_history = []
            st.session_state.pop("_qctr", None)
            # No st.rerun() — the button click itself triggers a rerun; an extra
            # one would reset the active tab back to "Data Overview".

    init_analysis_state()

    # Unique query counter — prevents button key collisions across queries
    if "_qctr" not in st.session_state:
        st.session_state["_qctr"] = 0

    for entry_index, entry in enumerate(st.session_state.chat_history):
        render_chat_history_entry(entry, entry_index=entry_index)

    _render_try_asking_section(df, schema)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    query = st.chat_input("Ask anything about your data...", key="analyst_chat_input")

    if "auto_query" in st.session_state:
        query = st.session_state.auto_query
        del st.session_state.auto_query

    if not query:
        return

    # Increment unique key counter for this query cycle
    st.session_state["_qctr"] += 1
    qk = st.session_state["_qctr"]   # unique per query — use in all button keys

    add_recent_activity("question", query)
    logger.info("chat_query_received", extra={"query": query[:200], "rows": len(df), "cols": len(df.columns)})
    render_user_bubble(query)

    ai_response = ""
    suggestions = ""
    summary_list = []
    query_rejected = False
    intent_started = time.perf_counter()
    intent_info = classify_query_intent(query, df, schema)
    logger.info(
        "chat_intent_classified",
        extra={
            "intent": intent_info.get("intent"),
            "needs_clarification": intent_info.get("needs_clarification"),
            "intent_ms": round((time.perf_counter() - intent_started) * 1000, 2),
        },
    )
    record_timing("chat_intent_ms", (time.perf_counter() - intent_started) * 1000)
    rephrase_suggestions = build_rephrase_suggestions(query, df, schema, intent=intent_info.get("intent"))

    with st.spinner("🔍 AI analyzing your dataset..."):
        execution_started = time.perf_counter()
        # Safe defaults — prevent NameError if an exception fires mid-execution
        code = "# Analysis not executed"
        execution_output = "An unexpected error occurred. Please try rephrasing your question."
        ai_charts = []

        try:
            if intent_info.get("needs_clarification"):
                logger.info("chat_query_clarification_needed", extra={"intent": intent_info.get("intent")})
                ai_response = build_clarification_prompt(query, df, schema)
                code = "# Clarification requested before analysis"
                result = ai_response
                execution_output = result
                ai_charts = []
                chart_data = None
                insight = ""
                chart_figs = []
                query_rejected = True
            elif not is_dataset_related_query(query, df, schema):
                logger.info("chat_query_rejected_not_dataset_related", extra={"intent": intent_info.get("intent")})
                ai_response = get_irrelevant_query_message(schema)
                code = "# Query rejected as unrelated to the active dataset"
                result = ai_response
                execution_output = result
                ai_charts = []
                chart_data = None
                insight = ""
                chart_figs = []
                query_rejected = True
            else:
                enhanced_query = add_date_filter(add_filters(enhance_query(query, df), df), df)
                simple_code = detect_simple_query(query, df)

                if is_memory_query(query) and "result_history_details" in st.session_state:
                    logger.info("chat_query_memory_mode", extra={"history_len": len(st.session_state.get("result_history", []))})
                    history = st.session_state.get("result_history", [])
                    detailed_history = st.session_state.get("result_history_details", [])

                    if len(history) >= 2:
                        last = history[-1]
                        prev = history[-2]
                        last_meta = detailed_history[-1] if len(detailed_history) >= 1 else {}
                        prev_meta = detailed_history[-2] if len(detailed_history) >= 2 else {}

                        try:
                            if isinstance(last, (int, float)) and isinstance(prev, (int, float)):
                                result = last - prev
                            elif isinstance(last, pd.DataFrame) and isinstance(prev, pd.DataFrame):
                                result = last.copy()
                                num_cols = last.select_dtypes(include="number").columns
                                for col in num_cols:
                                    if col in prev.columns:
                                        result[f"{col}_diff"] = last[col] - prev[col]
                            else:
                                result = (
                                    f"Comparison not supported for the last two results. "
                                    f"The previous result type was {prev_meta.get('result_type', 'unknown')} and "
                                    f"the latest result type was {last_meta.get('result_type', 'unknown')}."
                                )
                        except Exception:
                            result = last

                        code = "# Compared last two results"
                        execution_output = result
                    else:
                        result = "Need at least two results to compare."
                        code = "# Only one result available"
                        execution_output = result
                else:
                    if simple_code:
                        logger.info("chat_query_simple_code_path", extra={"intent": intent_info.get("intent")})
                        code = simple_code
                        execution_output = execute_code(f"charts = []\nresult = {simple_code}", df)
                    else:
                        logger.info("chat_query_ai_code_path", extra={"intent": intent_info.get("intent")})
                        code = generate_analysis_code(api_key, enhanced_query, df, schema)
                        execution_output = execute_code(code, df)

                ai_charts = []

        except Exception as _exec_err:
            logger.error("chat_execution_error", extra={"error": str(_exec_err)[:300]})
            execution_output = f"Analysis failed: {str(_exec_err)[:200]}. Please try rephrasing."
            query_rejected = False  # Let the response path handle the error gracefully

        logger.info(
            "chat_execution_completed",
            extra={
                "intent": intent_info.get("intent"),
                "query_rejected": query_rejected,
                "execution_ms": round((time.perf_counter() - execution_started) * 1000, 2),
            },
        )
        record_timing("chat_execution_ms", (time.perf_counter() - execution_started) * 1000)

    if isinstance(execution_output, tuple):
        result, ai_charts = execution_output
    else:
        result = execution_output

    logger.info(
        "chat_query_executed",
        extra={
            "intent": intent_info.get("intent"),
            "query_rejected": query_rejected,
            "result_type": type(result).__name__,
            "has_charts": bool(ai_charts),
        },
    )

    chart_data = None
    insight = ""
    chart_figs = []
    chart_validation_warnings = []

    if isinstance(result, pd.DataFrame):
        chart_data = result
    elif isinstance(result, pd.Series):
        try:
            chart_data = result.reset_index()
        except ValueError:
            chart_data = result.reset_index(drop=True).to_frame()
        if chart_data.shape[1] == 2:
            chart_data.columns = ["Category", "Value"]

    result_str = str(result)
    is_axes_result = "<Axes:" in result_str or "<AxesSubplot" in result_str
    if is_axes_result and chart_data is None:
        result = "The analysis generated visual charts. Please see the AI response below for a summary of the data patterns."

    is_error = isinstance(result, str) and any(keyword in result.lower() for keyword in ["traceback", "exception", "syntaxerror"])
    if isinstance(result, pd.DataFrame) and not result.empty:
        chart_data = result

    if is_error:
        with st.spinner("💭 AI is thinking..."):
            ai_response = build_failure_message(query, intent_info, schema, rephrase_suggestions)
    else:
        if chart_data is not None:
            insight = generate_business_insight(chart_data)

        with st.spinner("💭 Preparing response..."):
            response_started = time.perf_counter()
            if is_memory_query(query):
                history = st.session_state.get("result_history", [])
                detailed_history = st.session_state.get("result_history_details", [])

                if len(history) < 2:
                    ai_response = build_failure_message(query, intent_info, schema, rephrase_suggestions)
                else:
                    try:
                        last = history[-1]
                        prev = history[-2]
                        last_meta = detailed_history[-1] if len(detailed_history) >= 1 else {}
                        prev_meta = detailed_history[-2] if len(detailed_history) >= 2 else {}

                        try:
                            last_val = float(last)
                            prev_val = float(prev)

                            diff = last_val - prev_val
                            growth = (diff / prev_val * 100) if prev_val != 0 else 0

                            if diff > 0:
                                trend = "Increasing 📈"
                            elif diff < 0:
                                trend = "Decreasing 📉"
                            else:
                                trend = "No change ➡"

                            ai_response = f"""
                📊 Difference: {diff:,.2f}

                📈 Growth: {growth:.2f}%

                📌 Trend: {trend}
                """
                        except (TypeError, ValueError):
                            if isinstance(last, pd.DataFrame) and isinstance(prev, pd.DataFrame):
                                ai_response = "📊 Comparison completed (difference columns added)."
                            else:
                                ai_response = (
                                    "I understood this as a comparison request, but the last two saved results "
                                    f"cannot be compared directly ({prev_meta.get('result_type', 'unknown')} vs "
                                    f"{last_meta.get('result_type', 'unknown')})."
                                )
                    except Exception:
                        ai_response = build_failure_message(query, intent_info, schema, rephrase_suggestions)

            if not ai_response:
                try:
                    ai_response = generate_conversational_response(query=query, result=result, insight=insight, df=df, concise=True)
                except Exception:
                    ai_response = build_failure_message(query, intent_info, schema, rephrase_suggestions)

            logger.info(
                "chat_response_prepared",
                extra={
                    "intent": intent_info.get("intent"),
                    "response_ms": round((time.perf_counter() - response_started) * 1000, 2),
                },
            )
            record_timing("chat_response_ms", (time.perf_counter() - response_started) * 1000)

    if ai_response:
        clean_response = clean_text(ai_response)
        summary_list = build_summary_list(result, chart_data, query_rejected)
        if not summary_list and not query_rejected and not is_error_like_text(ai_response):
            summary_list = build_ai_summary_fallback(ai_response)

        clean_response = re.sub(r"<[^>]+>", "", clean_response)
        structured = structure_response(clean_response)

        if structured and any(structured.values()):
            render_structured_response(structured)
        else:
            render_assistant_bubble(clean_response)

        # Inline chart rendered directly under the prose answer when the
        # AI's textual reply was the whole result. We only do this when no
        # explicit chart_data is in play — the chart_data path below already
        # owns its own visualization. Trend / distribution / ranking /
        # comparison questions otherwise leave the user with text only.
        if (
            chart_data is None
            and not ai_charts
            and not query_rejected
            and not is_error_like_text(ai_response)
        ):
            try:
                inline_chart = build_chart_from_query(query, df)
            except Exception:
                inline_chart = None
            if inline_chart is not None:
                render_chart_card(inline_chart, st, key_prefix=f"inline_chart_{qk}")
                chart_figs = [inline_chart]

    # Track inline charts separately so they can be persisted in chat history
    inline_chart_figs = chart_figs if (chart_data is None and not ai_charts and chart_figs) else []

    if isinstance(chart_data, pd.DataFrame) and chart_data.empty:
        st.warning("No outliers found in the dataset based on the current criteria.")
        chart_data = None

    if chart_data is not None:
        render_dataframe_result(chart_data, f"live_table_{qk}")

        if ai_charts:
            chart_figs = ai_charts

        if not chart_figs and chart_data is not None:
            try:
                _, chart_validation_warnings = validate_chart_data(chart_data)
                chart_figs = auto_visualize(chart_data)
            except Exception:
                chart_figs = []

        if chart_figs:
            render_result_status(
                "Chart generated",
                "The result shape supports visualization, so charts are shown below with chart-type options and download tools.",
                kind="success",
            )
            render_chart_collection(chart_figs, key_prefix=f"live_{qk}")
        elif not query_rejected:
            if chart_validation_warnings:
                for warning in chart_validation_warnings:
                    st.caption(warning)
            render_result_status(
                "No chart shown",
                "This result is valid, but it does not have a chart-friendly shape. Try grouping by a category or time column.",
                kind="info",
            )
            try:
                suggested_queries = build_graphable_query_suggestions(df, schema, st.session_state.get("dataset_name"))
            except Exception:
                suggested_queries = []
            if suggested_queries:
                st.markdown("**Try one of these graph-friendly questions:**")
                for idx, suggestion in enumerate(suggested_queries):
                    if st.button(suggestion, key=f"graphable_prompt_{qk}_{idx}", use_container_width=True):
                        st.session_state.auto_query = suggestion

        if insight:
            render_insight_card(insight)
    else:
        if isinstance(result, dict):
            has_displayable = render_dict_result(result, f"dict_result_{qk}")
            if not has_displayable and not ai_response:
                st.info("The AI analyzed the data but the result format couldn't be displayed as a table.")
        elif not ai_response and str(result) != "None":
            st.markdown('<div class="glass-card" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
            st.write(str(result))
            st.markdown("</div>", unsafe_allow_html=True)

    suggestions = ""
    if ai_response:
        if summary_list:
            with st.expander("Answer Summary", expanded=False):
                for line in summary_list:
                    st.write("-", line)

        if not query_rejected:
            try:
                with st.spinner("Generating follow-up questions..."):
                    suggestions = build_follow_up_suggestions(query, df, schema, st.session_state.get("dataset_name"))
            except Exception:
                suggestions = ""
            render_follow_up_section(suggestions, f"live_suggestion_{qk}")

            if is_error_like_text(result) or is_error_like_text(ai_response):
                st.markdown("**Suggested Rephrases**")
                for idx, suggestion in enumerate(rephrase_suggestions):
                    if st.button(suggestion, key=f"rephrase_prompt_{qk}_{idx}", use_container_width=True):
                        st.session_state.auto_query = suggestion

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
        is_axes_result=is_axes_result,
        intent=intent_info.get("intent"),
        rephrases=rephrase_suggestions if (is_error_like_text(result) or is_error_like_text(ai_response)) else [],
        result_history_entry=build_result_history_entry(query, result, chart_data, intent_info, query_rejected),
        inline_charts=inline_chart_figs,
    )


def render_forecasting_tab(df: pd.DataFrame):
    st.markdown(
        """
        <div class="forecast-hero">
            <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#8fb4db;">Forecasting Studio</div>
            <div style="font-size:28px; font-weight:800; color:#f8fbff; margin-top:6px;">Project your next business move</div>
            <div style="color:#a8bad8; margin-top:6px;">Generate a clean outlook with projected values, confidence bands, and a quick trend summary.</div>
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
            <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#8fb4db;">Executive Reporting</div>
            <div style="font-size:28px; font-weight:800; color:#f8fbff; margin-top:6px;">Package the analysis into a polished PDF</div>
            <div style="color:#a8bad8; margin-top:6px;">Bundle saved AI analyses, visuals, and insights into a report that feels presentation-ready.</div>
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
                    <div>Narrative Executive Briefing</div>
                </div>
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 700; color: #E2E8F0;">What's included</div>
                    <div class="report-feature-list">
                        <div class="report-feature-item">Cover page with dataset & session details</div>
                        <div class="report-feature-item">Executive summary written from AI replies</div>
                        <div class="report-feature-item">Per-question sections in readable prose</div>
                        <div class="report-feature-item">Supporting chart + compact reference table</div>
                        <div class="report-feature-item">Page numbers, proper typography, disclaimer</div>
                    </div>
                </div>
                <div class="report-actions">
            """,
                unsafe_allow_html=True,
            )

            if st.button("Generate Professional PDF", type="primary", use_container_width=True):
                with st.spinner("Compiling and formatting your professional report..."):
                    file_path = generate_pdf(query=None, summary_text=None, dataframe=None, charts=None, analysis_history=history)
                add_recent_activity("report", "PDF report created")
                with open(file_path, "rb") as file:
                    st.download_button(
                        "Download PDF Report",
                        data=file,
                        file_name="AI_Executive_Report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
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
            <div class="landing-hero__kicker">Apex Analytics Platform</div>
            <div class="landing-hero__title">Ask your data anything and turn raw records into executive-ready decisions.</div>
            <div class="landing-hero__subtitle">{html.escape(dataset_name)} is loaded and ready. Use the AI analyst, visual summaries, and forecasting workflows to move from question to action in minutes.</div>
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
