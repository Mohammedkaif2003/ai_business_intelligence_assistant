import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv

# New separate files
from config import *
from styles import inject_styles
from ui_components import (
    render_kpi_cards, render_section_header, render_chart_card,
    render_user_bubble, render_assistant_bubble,
    render_sidebar_dataset_badge, render_insight_card
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
from modules.auto_visualizer import auto_visualize
from modules.auto_insights import generate_auto_insights
from modules.kpi_engine import generate_kpis
from modules.forecasting import forecast_revenue
from modules.ai_conversation import generate_conversational_response, generate_error_response

# Load environment variables
load_dotenv(override=True)
api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)

if not api_key:
    st.error("Groq API key not found. Please check your .env file.")
    st.stop()

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide"
)

inject_styles(st)

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
    st.info("Please select a data source in the sidebar to get started.")
    st.stop()

df = st.session_state["df"]
schema = st.session_state.get("schema", analyze_dataset(df))

render_sidebar_dataset_badge(st.session_state["dataset_name"], df.shape[0], df.shape[1])

# ---------- MAIN AREA ----------

render_section_header("📊 Data Intelligence Dashboard", "Overview of your loaded dataset metrics and trends.")

kpis = generate_kpis(df)
render_kpi_cards(kpis)

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Data Overview",
    "🤖 AI Analyst",
    "🔮 Forecasting",
    "📑 Reports"
])

# ---------- TAB 1: DATA OVERVIEW ----------
with tab1:
    st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    st.subheader("Dataset Preview")
    st.dataframe(df.head(20), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    st.subheader("Column Details")
    col_info = pd.DataFrame({
        "Column": df.columns,
        "Type": df.dtypes.astype(str).values,
        "Non-Null Count": df.count().values,
        "Null Count": df.isnull().sum().values,
        "Unique Values": df.nunique().values,
        "Example Value": [str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else "N/A" for col in df.columns]
    })
    st.dataframe(col_info, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    st.subheader("Statistics")
    st.dataframe(df.describe(), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    st.subheader("🔎 Automatic Dataset Insights")
    auto_insights = generate_auto_insights(df)
    for insight in auto_insights:
        st.write("•", insight)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- TAB 2: AI ANALYST ----------
with tab2:
    col_header, col_btn = st.columns([4, 1])
    with col_header:
        render_section_header("🤖 AI Data Analyst", "Chat with your data using Groq AI.")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat", key="clear_chat_btn", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.messages = []
            st.session_state.analysis_history = []
            for key in ["analysis_result", "analysis_query", "analysis_insight", "chart_data", "report_charts"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []

    # Chat history
    for entry in st.session_state.chat_history:
        render_user_bubble(entry["query"])

        if entry.get("ai_response") or entry.get("chart_data") is not None or entry.get("result") is not None:
            ai_msg_html = ""
            if entry.get("ai_response"):
                ai_msg_html += entry["ai_response"] + "<br><br>"
            
            if ai_msg_html:
                render_assistant_bubble(ai_msg_html)

            # Code
            if entry.get("code"):
                with st.expander("📝 View AI Generated Code", expanded=False):
                    st.code(entry["code"], language="python")

            # Chart Data
            chart_data = entry.get("chart_data")
            if chart_data is not None:
                st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
                st.markdown("**📋 Data Table**")
                st.dataframe(chart_data, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                charts = entry.get("charts", [])
                if charts:
                    if len(charts) == 2:
                        c1, c2 = st.columns(2)
                        with c1: render_chart_card(charts[0], c1)
                        with c2: render_chart_card(charts[1], c2)
                    else:
                        for fig in charts:
                            render_chart_card(fig, st)
            else:
                result = entry.get("result")
                if isinstance(result, dict):
                    st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
                    for key, value in result.items():
                        try:
                            if "<Axes:" in str(value) or "<AxesSubplot" in str(value):
                                continue
                            df_result = pd.DataFrame(value).reset_index()
                            if df_result.shape[1] == 2:
                                df_result.columns = ["Category", "Value"]
                            st.markdown(f"**{key}**")
                            st.dataframe(df_result, use_container_width=True)
                            fig = px.bar(df_result, x=df_result.columns[0], y=df_result.columns[1], title=str(key))
                            render_chart_card(fig, st)
                        except:
                            pass
                    st.markdown('</div>', unsafe_allow_html=True)
                elif not entry.get("ai_response"):
                    if str(result) != "None":
                        st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
                        st.write(str(result))
                        st.markdown('</div>', unsafe_allow_html=True)

            insight = entry.get("insight", "")
            if insight:
                render_insight_card(insight)
                
            summary = entry.get("summary", [])
            if summary:
                with st.expander("📑 Executive Summary", expanded=False):
                    for line in summary:
                        st.write("•", line)

            if entry.get("suggestions"):
                with st.expander("💡 Suggested Follow-Up Questions", expanded=False):
                    st.markdown(entry["suggestions"])

    query = st.chat_input("Ask something about your dataset...")
    if query:
        render_user_bubble(query)

        with st.spinner("🔍 AI analyzing your dataset..."):
            code = generate_analysis_code(api_key, query, df, schema)
            execution_output = execute_code(code, df)
            
        ai_charts = []
        if isinstance(execution_output, tuple):
            result, ai_charts = execution_output
        else:
            result = execution_output

        chart_data = None
        insight = ""
        summary_list = []
        chart_figs = []
        ai_response = ""

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

        is_error = isinstance(result, str) and ("error" in result.lower() or "failed" in result.lower() or "traceback" in result.lower())

        if is_error:
            with st.spinner("💭 Thinking..."):
                ai_response = generate_error_response(query, str(result))
        else:
            if chart_data is not None:
                insight = generate_business_insight(chart_data)
                st.session_state.analysis_insight = insight
            with st.spinner("💭 Preparing response..."):
                ai_response = generate_conversational_response(query, result, insight)

        if ai_response:
            render_assistant_bubble(ai_response)

        with st.expander("📝 View AI Generated Code", expanded=False):
            st.code(code, language="python")

        if chart_data is not None:
            st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
            st.markdown("**📋 Data Table**")
            st.dataframe(chart_data, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if ai_charts:
                chart_figs = ai_charts
            else:
                chart_figs = auto_visualize(chart_data)
            
            if chart_figs:
                if len(chart_figs) == 2:
                    c1, c2 = st.columns(2)
                    with c1: render_chart_card(chart_figs[0], c1)
                    with c2: render_chart_card(chart_figs[1], c2)
                else:
                    for fig in chart_figs:
                        render_chart_card(fig, st)

            if insight:
                render_insight_card(insight)

            summary_list = generate_executive_summary(chart_data)
            if summary_list:
                with st.expander("📑 Executive Summary", expanded=False):
                    for line in summary_list:
                        st.write("•", line)
        else:
            if isinstance(result, dict):
                has_displayable = False
                st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
                for key, value in result.items():
                    try:
                        if "<Axes:" in str(value) or "<AxesSubplot" in str(value):
                            continue
                        df_result = pd.DataFrame(value).reset_index()
                        if df_result.shape[1] == 2:
                            df_result.columns = ["Category", "Value"]
                        st.markdown(f"**{key}**")
                        st.dataframe(df_result, use_container_width=True)
                        fig = px.bar(df_result, x=df_result.columns[0], y=df_result.columns[1], title=str(key))
                        render_chart_card(fig, st)
                        has_displayable = True
                    except:
                        pass
                st.markdown('</div>', unsafe_allow_html=True)
                if not has_displayable and not ai_response:
                    st.info("The AI analyzed the data but the result format couldn't be displayed as a table.")
            elif not ai_response and str(result) != "None":
                st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
                st.write(str(result))
                st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("💡 Suggested Follow-Up Questions", expanded=False):
            with st.spinner("Generating follow-up questions..."):
                suggestions = suggest_business_questions(query, df, schema)
            st.markdown(suggestions)

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
        st.session_state.analysis_query = query
        if chart_data is not None:
            st.session_state.chart_data = chart_data
            st.session_state.report_charts = chart_figs

        report_insight = insight if insight else (ai_response if ai_response else "Analysis completed.")
        if "<Axes:" in str(report_insight) or "<AxesSubplot" in str(report_insight):
            report_insight = ai_response if ai_response else "Analysis completed — see AI response for details."

        st.session_state.analysis_history.append({
            "query": query,
            "result": result if not is_axes_result else None,
            "code": code,
            "insight": report_insight,
            "ai_response": ai_response,
            "charts": chart_figs,
            "summary": summary_list,
        })

        st.session_state.chat_history.append({
            "query": query,
            "result": result,
            "code": code,
            "chart_data": chart_data,
            "insight": insight,
            "summary": summary_list,
            "charts": chart_figs,
            "ai_response": ai_response,
            "suggestions": suggestions if 'suggestions' in dir() else "",
        })
        st.rerun()

# ---------- TAB 3: FORECASTING ----------
with tab3:
    render_section_header("🔮 Revenue / Sales Forecasting", "Predict future trends based on historical data patterns.")
    st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    
    forecast_periods = st.slider("Forecast periods (months):", min_value=1, max_value=12, value=3)

    if st.button("Generate Forecast", key="forecast_btn"):
        with st.spinner("Running forecast analysis..."):
            forecast_result = forecast_revenue(df, periods=forecast_periods)

        if forecast_result["available"]:
            st.success(forecast_result["message"])

            st.subheader("📋 Forecast Values")
            st.dataframe(forecast_result["forecast_df"], use_container_width=True)

            trend = forecast_result["trend"]
            metric = forecast_result["metric"]
            trend_icon = "📈" if trend == "increasing" else "📉" if trend == "declining" else "➡"
            st.info(f"{trend_icon} The {metric} trend is **{trend}** (slope: {forecast_result['slope']:,.2f} per month)")

            st.subheader("📊 Forecast Visualization")
            hist_df = forecast_result["historical_df"]
            fore_df = forecast_result["forecast_df"]

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
        else:
            st.warning(forecast_result["message"])
            st.info("💡 Tip: Forecasting works best with datasets that have date columns and numeric metrics like revenue or sales.")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- TAB 4: REPORTS ----------
with tab4:
    st.markdown('<div class="glass-card animate-slide" style="margin-bottom: 24px;">', unsafe_allow_html=True)
    st.markdown("<h3 style='color: #f8fbff; margin-bottom: 0px;'>📑 Executive Report Generator</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #a8bad8; font-size: 14px;'>Compile your entire AI analysis session into a branded, professional PDF report.</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

    history = st.session_state.get("analysis_history", [])

    if len(history) == 0:
        st.info("💡 **Your report is currently empty.** Head over to the 'AI Data Analyst' tab and ask a question to start building your report!")
    else:
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown(f"#### 📋 Report Contents ({len(history)} Analyses)")
            st.write("The following queries will be included as dedicated sections in your PDF report:")
            for i, entry in enumerate(history, 1):
                st.markdown(f'''
                <div style="background: rgba(255,255,255,0.04); border-left: 4px solid #F59E0B; padding: 12px 16px; margin-bottom: 12px; border-radius: 4px; border: 1px solid #E2E8F0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <div style="color: #a8bad8; font-size: 11px; font-weight: bold; margin-bottom: 4px;">ANALYSIS #{i}</div>
                    <div style="color: #f8fbff; font-weight: 600; font-size: 15px;">"{entry['query']}"</div>
                </div>
                ''', unsafe_allow_html=True)

        with col2:
            st.markdown("#### ⚙️ Report Configuration")
            st.markdown("""
            <div style="background: rgba(255,255,255,0.04); padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 600; color: #f8fbff;">Document Type</div>
                    <div style="color: #a8bad8; font-size: 13px;">Executive PDF Briefing</div>
                </div>
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 600; color: #f8fbff;">Included Features</div>
                    <ul style="color: #a8bad8; font-size: 13px; padding-left: 20px; margin-top: 5px;">
                        <li>Cover Page & Table of Contents</li>
                        <li>High-Resolution Visualizations</li>
                        <li>Formatted Data Tables</li>
                        <li>AI Business Insights</li>
                        <li>Strategic Recommendations</li>
                    </ul>
                </div>
                <div style="margin-top: 25px;">
            """, unsafe_allow_html=True)
            
            if st.button("📄 Generate Professional PDF", type="primary", use_container_width=True):
                with st.spinner("Compiling and formatting your professional report..."):
                    file_path = generate_pdf(query=None, summary_text=None, dataframe=None, charts=None, analysis_history=history)
                with open(file_path, "rb") as file:
                    st.download_button("📥 Download PDF Report", data=file, file_name="AI_Executive_Report.pdf", mime="application/pdf", use_container_width=True)
                st.success("✅ Report generated successfully!")
            st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align:center; color:#94A3B8; font-size:12px; margin-top:2rem; padding:1rem; border-top: 1px solid #E2E8F0;">
  {APP_TITLE} v{APP_VERSION} · Powered by Groq AI
</div>
""", unsafe_allow_html=True)