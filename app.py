import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import html
from dotenv import load_dotenv
from modules.app_secrets import get_secret

# New separate files
from config import *
from styles import inject_styles
from ui_components import (
    render_kpi_cards, render_section_header, render_chart_card,
    render_user_bubble, render_assistant_bubble,
    render_sidebar_dataset_badge, render_insight_card,
    render_sidebar_question_inspiration, render_result_status,
    render_table_panel
)

# Existing modules (do not rename)
from modules.dataset_analyzer import analyze_dataset
from modules.executive_summary import generate_executive_summary
from modules.groq_ai import suggest_business_questions
from modules.code_executor import execute_code
from modules.ai_code_generator import generate_analysis_code
from modules.report_generator import generate_pdf
from modules.insight_engine import generate_business_insight
from modules.data_loader import normalize_columns
from modules.auto_visualizer import auto_visualize, validate_chart_data
from modules.auto_insights import generate_auto_insights
from modules.kpi_engine import generate_kpis
from modules.forecasting import forecast_revenue
from modules.ai_conversation import generate_conversational_response, generate_error_response
from modules.text_utils import clean_text, structure_response
from modules.app_logging import get_logger
from modules.app_state import append_message_pair, ensure_analysis_state, reset_analysis_state, store_analysis_outputs
from ui_components import render_structured_response
from modules.query_utils import (
    build_clarification_prompt,
    build_rephrase_suggestions,
    classify_query_intent,
    clean_ai_response,
    is_memory_query,
    detect_simple_query,
    is_dataset_related_query,
    get_irrelevant_query_message,
    generate_sidebar_question_ideas,
    extract_follow_up_questions,
    generate_follow_up_fallbacks,
    enhance_query,
    add_date_filter,
    add_filters,
)
from modules.app_views import (
    init_analysis_state,
    render_chart_collection,
    render_chat_history_entry,
    render_dataframe_result,
    render_dict_result,
    render_follow_up_section,
    render_quick_prompt_buttons,
)
# Load environment variables
load_dotenv()
api_key = get_secret("GROQ_API_KEY")

if not api_key:
    st.error("Groq API key not found. Please check your .env file.")
    st.stop()

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide"
)
from styles import inject_styles
inject_styles(st)
logger = get_logger("app")
ensure_analysis_state()


def _format_metric_value(value):
    if isinstance(value, (int, float)):
        abs_value = abs(float(value))
        if abs_value >= 1_000_000_000:
            return f"{value / 1_000_000_000:,.2f}B"
        if abs_value >= 1_000_000:
            return f"{value / 1_000_000:,.2f}M"
        if abs_value >= 1_000:
            return f"{value:,.0f}"
        return f"{value:,.2f}"
    return str(value)


def _augment_kpis_with_trends(kpis, dataframe):
    enhanced = []
    row_count = max(len(dataframe), 1)
    for index, kpi in enumerate(kpis):
        metric_value = kpi.get("total", 0)
        baseline = kpi.get("average", 0)
        if isinstance(metric_value, (int, float)) and isinstance(baseline, (int, float)) and baseline not in ("", 0):
            delta = ((float(metric_value) - float(baseline)) / max(abs(float(baseline)), 1)) * 100
            trend_label = "from dataset average"
        else:
            delta = ((index + 1) / row_count) * 100
            trend_label = "coverage signal"

        enhanced.append(
            {
                **kpi,
                "total": _format_metric_value(metric_value),
                "average": _format_metric_value(baseline) if baseline != "" else "N/A",
                "delta": round(delta, 1),
                "trend_label": trend_label,
            }
        )
    return enhanced


def _generate_quick_insights(dataframe):
    insights = {
        "Highest Value Driver": "Not enough numeric data",
        "Lowest Performance Signal": "Not enough numeric data",
        "Key Anomaly": "No clear anomaly detected",
    }

    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    category_cols = dataframe.select_dtypes(exclude="number").columns.tolist()
    if not numeric_cols:
        return insights

    primary_metric = max(numeric_cols, key=lambda col: dataframe[col].fillna(0).sum())
    metric_sum = dataframe[primary_metric].fillna(0)

    if category_cols:
        primary_group = category_cols[0]
        grouped = dataframe.groupby(primary_group, dropna=False)[primary_metric].sum().sort_values(ascending=False)
        if not grouped.empty:
            insights["Highest Value Driver"] = f"{grouped.index[0]} leads {primary_metric} with {_format_metric_value(grouped.iloc[0])}"
            insights["Lowest Performance Signal"] = f"{grouped.index[-1]} trails at {_format_metric_value(grouped.iloc[-1])}"
    else:
        insights["Highest Value Driver"] = f"{primary_metric} totals {_format_metric_value(metric_sum.sum())}"
        insights["Lowest Performance Signal"] = f"Lowest {primary_metric} value is {_format_metric_value(metric_sum.min())}"

    std_dev = metric_sum.std()
    if std_dev and std_dev == std_dev and std_dev != 0:
        z_scores = (metric_sum - metric_sum.mean()) / std_dev
        if z_scores.abs().max() > 2:
            anomaly_idx = z_scores.abs().idxmax()
            insights["Key Anomaly"] = f"Row {anomaly_idx} spikes to {_format_metric_value(metric_sum.loc[anomaly_idx])} in {primary_metric}"
        else:
            insights["Key Anomaly"] = f"{primary_metric} stays within a normal range for most rows"

    return insights


def _summarize_report_history(history):
    insight_count = sum(1 for entry in history if entry.get("insight") or entry.get("ai_response"))
    chart_count = sum(len(entry.get("charts", [])) for entry in history)
    return {
        "analyses": len(history),
        "insights": insight_count,
        "charts": chart_count,
    }


def _build_overview_hero_chart(dataframe):
    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    date_candidates = []
    for col in dataframe.columns:
        lowered = str(col).lower()
        if "date" in lowered or "month" in lowered or "year" in lowered or "quarter" in lowered:
            date_candidates.append(col)

    metric_col = max(numeric_cols, key=lambda col: dataframe[col].fillna(0).sum())

    for axis_col in date_candidates:
        try:
            grouped = dataframe.groupby(axis_col, dropna=False)[metric_col].sum().reset_index()
            if len(grouped) >= 2:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=grouped[axis_col],
                        y=grouped[metric_col],
                        mode="lines+markers",
                        name=metric_col,
                        line=dict(color="#60a5fa", width=3),
                        marker=dict(color="#22d3ee", size=8),
                    )
                )
                fig.update_layout(title=f"{metric_col} Trend by {axis_col}", height=360)
                return fig
        except Exception:
            continue

    category_cols = dataframe.select_dtypes(exclude="number").columns.tolist()
    for axis_col in category_cols:
        try:
            grouped = (
                dataframe.groupby(axis_col, dropna=False)[metric_col]
                .sum()
                .sort_values(ascending=False)
                .head(8)
                .reset_index()
            )
            if len(grouped) >= 2:
                fig = px.bar(
                    grouped,
                    x=axis_col,
                    y=metric_col,
                    color=metric_col,
                    color_continuous_scale=["#2563eb", "#7c3aed", "#22d3ee"],
                    title=f"Top {axis_col} by {metric_col}",
                )
                fig.update_layout(height=360, coloraxis_showscale=False)
                return fig
        except Exception:
            continue

    return None


def _is_error_like_text(value) -> bool:
    text = str(value).lower()
    error_markers = [
        "unsafe code detected",
        "unsupported code pattern",
        "code execution error",
        "traceback",
        "exception",
        "syntaxerror",
        "nameerror",
        "not defined",
        "could not generate ai report",
        "comparison failed",
        "comparison not supported",
        "need at least two results",
        "not applicable",
        "more data needed",
    ]
    return any(marker in text for marker in error_markers)


def _result_type_label(result, chart_data):
    if chart_data is not None and isinstance(chart_data, pd.DataFrame) and not chart_data.empty:
        return "chartable_table"
    if isinstance(result, pd.DataFrame):
        return "dataframe"
    if isinstance(result, pd.Series):
        return "series"
    if isinstance(result, dict):
        return "dict"
    if isinstance(result, (int, float)):
        return "scalar"
    if isinstance(result, str):
        return "text"
    return type(result).__name__.lower()


def _build_ai_summary_fallback(ai_response: str) -> list[str]:
    cleaned = clean_text(ai_response)
    if not cleaned:
        return []

    lines = [line.strip("- ").strip() for line in cleaned.splitlines() if line.strip()]
    summary = []
    for line in lines:
        lower = line.lower()
        if lower.endswith(":") or lower in {
            "executive insight",
            "key findings",
            "business impact",
            "limitations",
            "recommendations",
        }:
            continue
        summary.append(line)
        if len(summary) >= 3:
            break
    return summary


def _build_result_history_entry(query, result, chart_data, intent_info, query_rejected):
    result_shape = None
    if isinstance(result, pd.DataFrame):
        result_shape = tuple(result.shape)
    elif isinstance(chart_data, pd.DataFrame):
        result_shape = tuple(chart_data.shape)

    key_columns = []
    if isinstance(result, pd.DataFrame):
        key_columns = [str(col) for col in result.columns[:4]]
    elif isinstance(chart_data, pd.DataFrame):
        key_columns = [str(col) for col in chart_data.columns[:4]]

    return {
        "query": query,
        "intent": intent_info.get("intent", "analysis"),
        "result_type": _result_type_label(result, chart_data),
        "key_columns": key_columns,
        "chartable": bool(chart_data is not None and isinstance(chart_data, pd.DataFrame) and not chart_data.empty),
        "result_shape": result_shape,
        "query_rejected": query_rejected,
    }


def _build_failure_message(query, intent_info, schema, rephrase_suggestions):
    intent_label = intent_info.get("intent", "analysis").replace("_", " ")
    message = f"I understood this as a {intent_label} request, but I could not answer it reliably with the current analysis path."
    if rephrase_suggestions:
        message += f" Try one of these instead: {rephrase_suggestions[0]}"
        if len(rephrase_suggestions) > 1:
            message += f" or {rephrase_suggestions[1]}"
    else:
        message += f" Try asking about columns like {', '.join(schema.get('column_names', [])[:3])}."
    return message


def _build_summary_list(result, chart_data, query_rejected):
    if query_rejected:
        return []

    if _is_error_like_text(result):
        return []

    summary_list = []

    try:
        if chart_data is not None and not chart_data.empty:
            summary_list = generate_executive_summary(chart_data)
        elif isinstance(result, pd.DataFrame) and not result.empty:
            numeric_cols = result.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                metric = numeric_cols[0]
                summary_list = [
                    f"The result includes {len(result):,} rows across {len(result.columns)} columns.",
                    f"Total {metric} is {result[metric].fillna(0).sum():,.2f}.",
                    f"Average {metric} is {result[metric].fillna(0).mean():,.2f}.",
                ]
            else:
                summary_list = [
                    f"The result includes {len(result):,} rows across {len(result.columns)} columns.",
                    f"Columns returned: {', '.join(str(col) for col in result.columns[:4])}.",
                ]
        elif isinstance(result, (int, float)):
            summary_list = [f"Result obtained: {result}"]
        elif isinstance(result, str):
            cleaned_result = str(result).strip()
            if cleaned_result:
                summary_list = [cleaned_result]
        elif isinstance(result, dict):
            summary_list = [f"{k}: {v}" for k, v in result.items() if not _is_error_like_text(v)]
        elif isinstance(result, pd.Series):
            metric_name = result.name or "value"
            summary_list = [
                f"The result contains {len(result):,} {metric_name} entries.",
                f"Highest {metric_name} is {result.max():,.2f}." if pd.api.types.is_numeric_dtype(result) else "Series result generated with multiple values.",
                f"Lowest {metric_name} is {result.min():,.2f}." if pd.api.types.is_numeric_dtype(result) else "",
            ]
    except Exception as e:
        summary_list = [f"Summary generation failed: {str(e)}"]

    cleaned = [str(item).strip() for item in summary_list if item and not _is_error_like_text(item)]
    return cleaned


def _build_follow_up_suggestions(query, df, schema):
    try:
        raw_suggestions = suggest_business_questions(query, df, schema)
    except Exception as e:
        raw_suggestions = f"AI suggestion failed: {str(e)}"

    parsed = extract_follow_up_questions(raw_suggestions)
    simple_parsed = []
    for question in parsed:
        lowered = question.lower()
        if any(
            marker in lowered
            for marker in (
                "previous result",
                "previous one",
                "last result",
                "last two results",
                "compared to the overall average",
                "2 standard deviations",
                "if we assume",
                "consistently",
            )
        ):
            continue
        simple_parsed.append(question)

    if simple_parsed:
        return "\n".join(f"{idx}. {question}" for idx, question in enumerate(simple_parsed[:5], start=1))

    if parsed:
        return "\n".join(f"{idx}. {question}" for idx, question in enumerate(parsed[:5], start=1))

    fallback_questions = generate_follow_up_fallbacks(query, df, schema)
    return "\n".join(f"{idx}. {question}" for idx, question in enumerate(fallback_questions, start=1))


def _build_graphable_query_suggestions(df, schema):
    fallback_questions = generate_follow_up_fallbacks("graph suggestions", df, schema)
    graphable = []
    for question in fallback_questions:
        lowered = question.lower()
        if any(token in lowered for token in ("trend", "compare", "total", "highest", "outlier", "forecast")):
            graphable.append(question)
    if not graphable:
        graphable = fallback_questions
    return graphable[:4]


def _clear_chat_state():
    reset_analysis_state()


def _persist_analysis(query, result, chart_data, chart_figs, code, insight, ai_response, summary_list, suggestions, query_rejected, is_axes_result):
    report_insight = insight if insight else (ai_response if ai_response else "Analysis completed.")
    if "<Axes:" in str(report_insight) or "<AxesSubplot" in str(report_insight):
        report_insight = ai_response if ai_response else "Analysis completed - see AI response for details."

    append_message_pair(query, result)
    store_analysis_outputs(
        query=query,
        result=result,
        chart_data=chart_data,
        chart_figs=chart_figs,
        code=code,
        report_insight=report_insight,
        ai_response=ai_response,
        summary_list=summary_list,
        suggestions=suggestions,
        query_rejected=query_rejected,
        is_axes_result=is_axes_result,
    )


# ---------- SIDEBAR & DATASET LOADING ----------

st.sidebar.markdown(f"""
<div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); padding: 24px 20px; border-radius: 16px; margin-bottom: 24px; backdrop-filter: blur(10px); position: relative; overflow: hidden;">
    <div style="position: absolute; top: -50%; right: -20%; width: 120px; height: 120px; background: radial-gradient(circle, #4F46E5 0%, transparent 70%); opacity: 0.4;"></div>
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px; position: relative; z-index: 1;">
        <div style="background: linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%); width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3);">
            {APP_ICON}
        </div>
        <div style="font-size: 22px; font-weight: 800; color: white; letter-spacing: -0.5px;">
            {APP_TITLE}
        </div>
    </div>
    <div style="color: #94A3B8; font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-left: 48px; position: relative; z-index: 1;">
        AI Intelligence Suite
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.subheader("📂 Select Data Source")
data_source = st.sidebar.radio(
    "Choose how to load data:",
    ["Upload CSV", "Use Pre-loaded Dataset"]
)
# ✅ ADD THIS HERE
if st.sidebar.button("🗑️ Clear Uploaded Dataset"):
    st.session_state.pop("uploaded_df", None)
    st.session_state.pop("uploaded_name", None)
    st.rerun()
@st.cache_data
def load_dataset(file):
    df = pd.read_csv(file)
    df = normalize_columns(df)
    return df

@st.cache_data
def load_local_dataset(path):
    df = pd.read_csv(path)
    df = normalize_columns(df)
    return df

selected_key = None
df_to_load = None

if data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload CSV Dataset", type=["csv"])

    if uploaded_file:
        selected_key = uploaded_file.name
        df_to_load = load_dataset(uploaded_file)

        # ✅ SAVE
        st.session_state["uploaded_df"] = df_to_load
        st.session_state["uploaded_name"] = selected_key

    # ✅ ADD THIS PART (MISSING)
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
            file_path_to_load = os.path.join(data_dir, selected_file)
            df_to_load = load_local_dataset(file_path_to_load)            
        else:
            st.sidebar.warning(f"No CSV files found in {DATA_DIR} folder.")
    else:
        st.sidebar.warning(f"{DATA_DIR} folder not found.")

if selected_key:
    if st.session_state.get("active_dataset_key") != selected_key:
        st.session_state["df"] = df_to_load
        st.session_state["active_dataset_key"] = selected_key
        st.session_state["dataset_name"] = selected_key
        st.session_state["schema"] = analyze_dataset(df_to_load)
        st.sidebar.success(f"✅ Dataset '{selected_key}' loaded successfully")

if "df" not in st.session_state or st.session_state["df"] is None:
    st.markdown("""
    <div style="
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.08);
    color: #E2E8F0;
    font-size: 14px;
    margin-top: 10px;
    ">
    📊 Please select a data source in the sidebar to get started.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

df = st.session_state["df"]
original_df = df.copy()
schema = st.session_state.get("schema", analyze_dataset(df))

render_sidebar_dataset_badge(st.session_state["dataset_name"], df.shape[0], df.shape[1])
sidebar_question = render_sidebar_question_inspiration(generate_sidebar_question_ideas(df, schema))
if sidebar_question:
    st.session_state.auto_query = sidebar_question
    st.rerun()

# ---------- MAIN AREA ----------

render_section_header("📊 Data Intelligence Dashboard", "Overview of your loaded dataset metrics and trends.")
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
kpis = _augment_kpis_with_trends(generate_kpis(df), df)
render_kpi_cards(kpis)
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Data Overview",
    "🤖 AI Analyst",
    "🔮 Forecasting",
    "📑 Reports"
])
st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
# ---------- TAB 1: DATA OVERVIEW ----------
with tab1:
    quick_insights = _generate_quick_insights(df)
    hero_fig = _build_overview_hero_chart(df)
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
    render_table_panel("Dataset Preview", df.head(200), "dataset_preview", max_rows=50)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    col_info = pd.DataFrame({
        "Column": df.columns,
        "Type": df.dtypes.astype(str).values,
        "Non-Null Count": df.count().values,
        "Null Count": df.isnull().sum().values,
        "Unique Values": df.nunique().values,
        "Example Value": [str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else "N/A" for col in df.columns]
    })
    render_table_panel("Column Details", col_info, "column_details")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    render_table_panel("Statistics", df.describe().reset_index(), "statistics")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    st.subheader("🔎 Automatic Dataset Insights")
    auto_insights = generate_auto_insights(df)
    for insight in auto_insights:
        st.write("•", insight)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
# ---------- TAB 2: AI ANALYST ----------
with tab2:
    st.markdown("""
    <div class="chat-shell">
        <div class="chat-hero">
            <div>
                <div class="chat-hero__title">AI Analyst Workspace</div>
                <div class="chat-hero__subtitle">Ask anything about your data, review structured answers, and move from question to insight fast.</div>
            </div>
            <div class="chat-status">
                <span class="typing-dots"><span></span><span></span><span></span></span>
                <span style="margin-left:8px;">Live analysis ready</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🗑️ Clear Chat", key="clear_chat_btn"):
        st.session_state.chat_history = []
        st.session_state.messages = []
        st.session_state.analysis_history = []
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    init_analysis_state()
    # Chat history
    for entry in st.session_state.chat_history:
        render_chat_history_entry(entry)
    # Onboarding hint when there is no prior chat
    if not st.session_state.chat_history:
        render_quick_prompt_buttons(df, schema)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    query = st.chat_input("Ask anything about your data...")

    # Auto-run when suggestion clicked
    if "auto_query" in st.session_state:
        query = st.session_state.auto_query
        del st.session_state.auto_query
    if query:
        render_user_bubble(query)
        ai_response = ""
        suggestions = ""
        summary_list = []
        query_rejected = False
        intent_info = classify_query_intent(query, df, schema)
        rephrase_suggestions = build_rephrase_suggestions(query, df, schema, intent=intent_info.get("intent"))

        with st.spinner("🔍 AI analyzing your dataset..."):
            if intent_info.get("needs_clarification"):
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
                enhanced_query = enhance_query(query, df)
                enhanced_query = add_filters(enhanced_query, df)
                enhanced_query = add_date_filter(enhanced_query, df)
                simple_code = detect_simple_query(query, df)
                # MEMORY LEVEL 2
                if is_memory_query(query) and "result_history_details" in st.session_state:
                    history = st.session_state.get("result_history", [])
                    detailed_history = st.session_state.get("result_history_details", [])

                    if len(history) >= 2:
                        last = history[-1]
                        prev = history[-2]
                        last_meta = detailed_history[-1] if len(detailed_history) >= 1 else {}
                        prev_meta = detailed_history[-2] if len(detailed_history) >= 2 else {}

                        try:
                            # numbers
                            if isinstance(last, (int, float)) and isinstance(prev, (int, float)):
                                result = last - prev

                            # dataframes
                            elif isinstance(last, pd.DataFrame) and isinstance(prev, pd.DataFrame):
                                result = last.copy()
                                num_cols = last.select_dtypes(include='number').columns

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
                        code = simple_code
                        execution_output = execute_code(
                            f"charts = []\nresult = {simple_code}",
                            df
                        )

                    else:
                        code = generate_analysis_code(api_key, enhanced_query, df, schema)
                        execution_output = execute_code(code, df)
                ai_charts = []

        if isinstance(execution_output, tuple):
            result, ai_charts = execution_output
        else:
            result = execution_output

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

        is_error = isinstance(result, str) and any(
            keyword in result.lower()
            for keyword in ["traceback", "exception", "syntaxerror"]
        )
        if isinstance(result, pd.DataFrame) and not result.empty:
            chart_data = result
        if is_error:
            with st.spinner("💭 AI is thinking..."):
                ai_response = _build_failure_message(query, intent_info, schema, rephrase_suggestions)
        else:
            if chart_data is not None:
                insight = generate_business_insight(chart_data)

            with st.spinner("💭 Preparing response..."):

                # ✅ MEMORY QUERY → FINAL CLEAN VERSION
                if is_memory_query(query):

                    history = st.session_state.get("result_history", [])
                    detailed_history = st.session_state.get("result_history_details", [])

                    if len(history) < 2:
                        ai_response = _build_failure_message(query, intent_info, schema, rephrase_suggestions)

                    else:
                        try:
                            last = history[-1]
                            prev = history[-2]
                            last_meta = detailed_history[-1] if len(detailed_history) >= 1 else {}
                            prev_meta = detailed_history[-2] if len(detailed_history) >= 2 else {}

                            # ✅ TRY NUMERIC CONVERSION FIRST
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

                            # ✅ IF NOT NUMERIC → HANDLE DATAFRAME
                            except (TypeError, ValueError):
                                if isinstance(last, pd.DataFrame) and isinstance(prev, pd.DataFrame):
                                    ai_response = "📊 Comparison completed (difference columns added)."
                                else:
                                    ai_response = (
                                        f"I understood this as a comparison request, but the last two saved results "
                                        f"cannot be compared directly ({prev_meta.get('result_type', 'unknown')} vs "
                                        f"{last_meta.get('result_type', 'unknown')})."
                                    )

                        except Exception as e:
                            ai_response = _build_failure_message(query, intent_info, schema, rephrase_suggestions)
                if not ai_response:
                    try:
                        ai_response = generate_conversational_response(
                            query=query,
                            result=result,
                            insight=insight,
                            df=df
                        )
                    except Exception:
                        ai_response = _build_failure_message(query, intent_info, schema, rephrase_suggestions)
        if ai_response:
            clean_response = clean_text(ai_response)
            # =========================
            # ✅ FINAL EXECUTIVE SUMMARY FIX
            # =========================

            summary_list = _build_summary_list(result, chart_data, query_rejected)
            if not summary_list and not query_rejected and not _is_error_like_text(ai_response):
                summary_list = _build_ai_summary_fallback(ai_response)
            suggestions = ""

            # DISPLAY
            if summary_list:
                with st.expander("Answer Summary", expanded=False):
                    for line in summary_list:
                        st.write("-", line)
            if not query_rejected:
                with st.spinner("Generating follow-up questions..."):
                    suggestions = _build_follow_up_suggestions(query, df, schema)
                render_follow_up_section(suggestions, f"live_suggestion_{hash(query)}")
                if _is_error_like_text(result) or _is_error_like_text(ai_response):
                    st.markdown("**Suggested Rephrases**")
                    for idx, suggestion in enumerate(rephrase_suggestions):
                        if st.button(suggestion, key=f"rephrase_prompt_{hash(query)}_{idx}", use_container_width=True):
                            st.session_state.auto_query = suggestion
                            st.rerun()
            # 🚨 REMOVE ANY HTML COMPLETELY
            import re
            clean_response = re.sub(r'<[^>]+>', '', clean_response)

            structured = structure_response(clean_response)

            if structured and any(structured.values()):
                render_structured_response(structured)
            else:
                render_assistant_bubble(clean_response)

        # ✅ ADD THIS BLOCK HERE
        if isinstance(chart_data, pd.DataFrame) and chart_data.empty:
            st.warning("No outliers found in the dataset based on the current criteria.")
            chart_data = None

        if chart_data is not None:
            render_dataframe_result(chart_data, f"live_table_{hash(query)}")
            
            if ai_charts:
                chart_figs = ai_charts

            if not chart_figs and chart_data is not None:
                _, chart_validation_warnings = validate_chart_data(chart_data)
                chart_figs = auto_visualize(chart_data)
            
            if chart_figs:
                render_result_status(
                    "Chart generated",
                    "The result shape supports visualization, so charts are shown below with chart-type options and download tools.",
                    kind="success"
                )
                render_chart_collection(chart_figs)
            elif not query_rejected:
                if chart_validation_warnings:
                    for warning in chart_validation_warnings:
                        st.caption(warning)
                render_result_status(
                    "No chart shown",
                    "This result is valid, but it does not have a chart-friendly shape. Try grouping by a category or time column.",
                    kind="info"
                )
                suggested_queries = _build_graphable_query_suggestions(df, schema)
                if suggested_queries:
                    st.markdown("**Try one of these graph-friendly questions:**")
                    for idx, suggestion in enumerate(suggested_queries):
                        if st.button(suggestion, key=f"graphable_prompt_{hash(query)}_{idx}", use_container_width=True):
                            st.session_state.auto_query = suggestion
                            st.rerun()

            if insight:
                render_insight_card(insight)

        else:
            if isinstance(result, dict):
                has_displayable = render_dict_result(result, f"dict_result_{hash(query)}")
                if not has_displayable and not ai_response:
                    st.info("The AI analyzed the data but the result format couldn't be displayed as a table.")
            elif not ai_response and str(result) != "None":
                st.markdown('<div class="glass-card" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
                st.write(str(result))
                st.markdown('</div>', unsafe_allow_html=True)

        st.session_state.messages.append({"role": "user", "content": query})
        if isinstance(result, pd.DataFrame):
            preview = result.head(5).to_string(index=False)
            st.session_state.messages.append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
        elif isinstance(result, pd.Series):
            preview = result.head(5).to_string()
            st.session_state.messages.append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
        else:
            st.session_state.messages.append({"role": "assistant", "content": str(result)})

        st.session_state.analysis_result = result
        st.session_state.last_result = result
        st.session_state.last_query = query

        # ✅ STORE HISTORY
        if "result_history" not in st.session_state:
            st.session_state.result_history = []
        if "result_history_details" not in st.session_state:
            st.session_state.result_history_details = []

        st.session_state.result_history.append(result)
        st.session_state.result_history_details.append(
            _build_result_history_entry(query, result, chart_data, intent_info, query_rejected)
        )
        st.session_state.analysis_query = query
        if chart_data is not None:
            st.session_state.chart_data = chart_data
            st.session_state.report_charts = chart_figs

        report_insight = insight if insight else (ai_response if ai_response else "Analysis completed.")
        if "<Axes:" in str(report_insight) or "<AxesSubplot" in str(report_insight):
            report_insight = ai_response if ai_response else "Analysis completed — see AI response for details."

        if not query_rejected:
            st.session_state.analysis_history.append({
                "query": query,
                "result": result if not is_axes_result else None,
                "code": code,
                "insight": report_insight,
                "ai_response": ai_response,
                "charts": chart_figs,
                "summary": summary_list,
                "intent": intent_info.get("intent"),
            })

        st.session_state.chat_history.append({
            "query": query,
            "result": result,
            "code": code if not query_rejected else "",
            "chart_data": chart_data if not query_rejected else None,
            "insight": insight if not query_rejected else "",
            "summary": summary_list if not query_rejected else [],
            "charts": chart_figs if not query_rejected else [],
            "ai_response": ai_response,
            "suggestions": suggestions if (not query_rejected and suggestions) else "",
            "query_rejected": query_rejected,
            "intent": intent_info.get("intent"),
            "rephrases": rephrase_suggestions if (_is_error_like_text(result) or _is_error_like_text(ai_response)) else [],
        })
        st.rerun()

# ---------- TAB 3: FORECASTING ----------
with tab3:
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
                        <div class="forecast-stat-value">{_format_metric_value(latest_prediction)}</div>
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
            fig.add_trace(go.Scatter(
                x=pd.concat([fore_df["Date"], fore_df["Date"][::-1]]),
                y=pd.concat([fore_df["Upper Bound"], fore_df["Lower Bound"][::-1]]),
                fill="toself",
                fillcolor="rgba(245,158,11,0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="95% Confidence Interval"
            ))

            render_chart_card(fig, st)
            render_table_panel("Forecast Values", fore_df, "forecast_values")
        else:
            st.warning(forecast_result["message"])
            st.info("💡 Tip: Forecasting works best with datasets that have date columns and numeric metrics like revenue or sales.")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- TAB 4: REPORTS ----------
with tab4:
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
        report_stats = _summarize_report_history(history)
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
                st.markdown(f'''
                <div class="report-query-item">
                    <div style="color: #94A3B8; font-size: 11px; font-weight: bold; margin-bottom: 4px;">
                        ANALYSIS #{i}
                    </div>
                    <div style="color: #E2E8F0; font-weight: 600; font-size: 15px;">
                        "{entry['query']}"
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="report-config-card">', unsafe_allow_html=True)
            st.markdown("#### ⚙️ Report Configuration")
            st.markdown("""
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
            """, unsafe_allow_html=True)
            
            if st.button("Generate Professional PDF", type="primary", use_container_width=True):
                with st.spinner("Compiling and formatting your professional report..."):
                    file_path = generate_pdf(query=None, summary_text=None, dataframe=None, charts=None, analysis_history=history)
                with open(file_path, "rb") as file:
                    st.download_button("Download PDF Report", data=file, file_name="AI_Executive_Report.pdf", mime="application/pdf", use_container_width=True)
                st.success("Report generated successfully!")
            st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
