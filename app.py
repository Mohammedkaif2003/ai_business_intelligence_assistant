import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv

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
load_dotenv()

api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)

if not api_key:
    st.error("Groq API key not found. Please check your .env file.")
    st.stop()

st.set_page_config(
    page_title="AI Business Intelligence Assistant",
    page_icon="📊",
    layout="wide"
)

# ---------- UI STYLE ----------

st.markdown("""
<style>
/* Dataframe styling */
[data-testid="stDataFrame"] {
    border-radius:12px;
}

/* Tabs container */
.stTabs [data-baseweb="tab-list"] {
    gap:10px;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    background: var(--secondary-background-color);
    padding:10px 22px;
    border-radius:8px;
    font-weight:600;
}

/* Active tab */
.stTabs [aria-selected="true"] {
    background-color:#2563EB;
    color:white;
}

/* Hover */
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(128,128,128,0.15);
}

/* KPI card */
.kpi-card {
    padding:16px;
    border-radius:12px;
    border:1px solid rgba(128,128,128,0.2);
    background: var(--secondary-background-color);
}

/* Section headers */
.section-header {
    color: #2563EB;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)

st.title("📊 AI Business Intelligence Assistant")
st.write("Upload data → Ask questions → Get insights, charts, forecasts, and reports.")


# ---------- DATASET LOADING ----------

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


# ---------- DATA SOURCE SELECTION ----------

st.subheader("📂 Select Data Source")

data_source = st.radio(
    "Choose how to load data:",
    ["Upload CSV", "Use Pre-loaded Dataset"],
    horizontal=True
)

df = None

if data_source == "Upload CSV":
    uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])
    if uploaded_file:
        df = load_dataset(uploaded_file)
        st.session_state.df = df
        st.session_state.dataset_name = uploaded_file.name
        st.success(f"✅ Dataset '{uploaded_file.name}' loaded successfully")

elif data_source == "Use Pre-loaded Dataset":

    data_dir = os.path.join(os.path.dirname(__file__), "data", "raw")

    if os.path.exists(data_dir):

        csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

        if csv_files:

            # Display friendly names
            friendly_names = {
                "sales_data.csv": "📈 Sales Data (5000 records — products, revenue, profit)",
                "hr_data.csv": "👥 HR Data (500 records — employees, salary, attrition)",
                "finance_data.csv": "💰 Finance Data (56 records — budget, actuals, variance)"
            }

            display_names = [friendly_names.get(f, f) for f in csv_files]

            selected_display = st.selectbox("Select a dataset:", display_names)
            selected_file = csv_files[display_names.index(selected_display)]

            file_path = os.path.join(data_dir, selected_file)
            df = load_local_dataset(file_path)
            st.session_state.df = df
            st.session_state.dataset_name = selected_file
            st.success(f"✅ Dataset '{selected_file}' loaded successfully")

        else:
            st.warning("No CSV files found in data/raw/ folder.")
    else:
        st.warning("data/raw/ folder not found. Please create it and add CSV files.")

if "df" not in st.session_state:
    st.info("👆 Please select a data source above to get started.")
    st.stop()

df = st.session_state.df

schema = analyze_dataset(df)

# ---------- DATASET METRICS ----------

col1, col2, col3, col4 = st.columns(4)
col1.metric("📋 Rows", f"{df.shape[0]:,}")
col2.metric("📊 Columns", df.shape[1])
col3.metric("🔢 Numeric Columns", len(schema["numeric_columns"]))
col4.metric("🏷 Categorical Columns", len(schema["categorical_columns"]))

st.divider()

st.subheader("📋 Dataset Overview")

st.write(
    f"This dataset contains **{schema['rows']:,} rows** and **{schema['columns']} columns**."
)

if schema["numeric_columns"]:
    st.write(
        f"📊 Numeric metrics: `{', '.join(schema['numeric_columns'][:5])}`"
    )

if schema["categorical_columns"]:
    st.write(
        f"🏷 Categorical dimensions: `{', '.join(schema['categorical_columns'][:5])}`"
    )

if schema["datetime_columns"]:
    st.write(
        f"📅 Date columns: `{', '.join(schema['datetime_columns'])}`"
    )

st.divider()

# ---------- KPI SECTION ----------

st.subheader("📊 Key Performance Indicators")

kpis = generate_kpis(df)

if len(kpis) > 0:

    cols = st.columns(len(kpis))

    icons = ["💰", "📦", "📈", "📊", "🏷"]

    for i, kpi in enumerate(kpis):

        with cols[i]:

            st.markdown(f"""
            <div class="kpi-card">

            <div style="font-size:14px;opacity:0.8">
            {icons[i % len(icons)]} {kpi['metric']}
            </div>

            <div style="font-size:28px;font-weight:700;margin-top:6px">
            {kpi['total']:,.2f}
            </div>

            <div style="font-size:13px;color:#10B981;margin-top:4px">
            Avg {kpi['average']:,.2f}
            </div>

            </div>
            """, unsafe_allow_html=True)

else:

    st.info("No numeric columns available for KPI metrics.")

# ---------- TREND ANALYSIS ----------

date_cols = df.select_dtypes(include=["datetime", "datetime64"]).columns
num_cols = df.select_dtypes(include="number").columns

if len(date_cols) > 0 and len(num_cols) > 0:

    st.subheader("📈 Trend Analysis")

    trend_col = num_cols[0]

    fig = px.line(
        df,
        x=date_cols[0],
        y=trend_col,
        title=f"{trend_col} Trend Over Time"
    )

    st.plotly_chart(fig, use_container_width=True)

st.subheader("🔎 Automatic Dataset Insights")

auto_insights = generate_auto_insights(df)

for insight in auto_insights:
    st.write("•", insight)

st.divider()

st.subheader("🧠 AI Executive Insight")

if len(schema["numeric_columns"]) > 0:

    metric = schema["numeric_columns"][0]

    top_value = df[metric].max()
    avg_value = df[metric].mean()

    st.info(
        f"The dataset shows a peak {metric} value of {top_value:,.2f}. "
        f"The average performance is {avg_value:,.2f}, indicating potential "
        f"opportunities to improve lower-performing segments."
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

# ---------- MAIN TABS ----------

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Data Overview",
    "🤖 AI Data Analyst",
    "🔮 Forecasting",
    "📑 Executive Reports"
])

with tab1:

    st.subheader("Dataset Preview")
    st.dataframe(df.head(20), use_container_width=True)

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

    st.subheader("Statistics")
    st.dataframe(df.describe(), use_container_width=True)

with tab2:

    st.subheader("Ask Questions About Your Data")

    # Initialize chat history with rich content support
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Clear Chat button at the top
    if st.button("🗑️ Clear Chat", key="clear_chat_btn"):
        st.session_state.chat_history = []
        st.session_state.messages = []
        st.session_state.analysis_history = []

        for key in [
            "analysis_result",
            "analysis_query",
            "analysis_insight",
            "chart_data",
            "report_charts"
        ]:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()

    # ── Render the full chat history ──
    for entry in st.session_state.chat_history:

        # User message
        with st.chat_message("user"):
            st.markdown(entry["query"])

        # Assistant message with rich content
        with st.chat_message("assistant"):

            # ── Conversational AI response (shown first) ──
            if entry.get("ai_response"):
                st.markdown(entry["ai_response"])
                st.divider()

            # Show the AI code in a collapsible
            if entry.get("code"):
                with st.expander("📝 View AI Generated Code", expanded=False):
                    st.code(entry["code"], language="python")

            result = entry.get("result")
            chart_data = entry.get("chart_data")
            insight = entry.get("insight", "")
            summary = entry.get("summary", [])

            # ── Dictionary results ──
            if isinstance(result, dict):
                for key, value in result.items():
                    try:
                        if "<Axes:" in str(value) or "<AxesSubplot" in str(value):
                            continue  # Skip Axes objects
                        df_result = pd.DataFrame(value).reset_index()
                        if df_result.shape[1] == 2:
                            df_result.columns = ["Category", "Value"]
                        st.markdown(f"**{key}**")
                        st.dataframe(df_result, use_container_width=True)
                        fig = px.bar(
                            df_result,
                            x=df_result.columns[0],
                            y=df_result.columns[1],
                            title=str(key)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except:
                        pass

            # ── DataFrame / Series results ──
            elif chart_data is not None:

                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown("**📋 Data Table**")
                    st.dataframe(chart_data, use_container_width=True)

                with col2:
                    st.markdown("**📊 Visual Analysis**")
                    charts = entry.get("charts", [])
                    for i, fig in enumerate(charts):
                        st.plotly_chart(fig, use_container_width=True, key=f"hist_chart_{id(entry)}_{i}")

                # Insight
                if insight:
                    st.info(f"🧠 **Business Insight:** {insight}")

                # Executive summary bullets
                if summary:
                    with st.expander("📑 Executive Summary", expanded=False):
                        for line in summary:
                            st.write("•", line)

            # ── Simple text / error results ──
            else:
                if not entry.get("ai_response"):
                    st.write(str(result))

            # Follow-up questions
            if entry.get("suggestions"):
                with st.expander("💡 Suggested Follow-Up Questions", expanded=False):
                    st.markdown(entry["suggestions"])

    # ── Chat input (always at bottom) ──
    query = st.chat_input("Ask something about your dataset...")

    if query:

        # Show user message immediately
        with st.chat_message("user"):
            st.markdown(query)

        # Show assistant thinking
        with st.chat_message("assistant"):
            with st.spinner("🔍 AI analyzing your dataset..."):
                code = generate_analysis_code(api_key, query, df, schema)
                result = execute_code(code, df)

            # Determine chart_data
            chart_data = None
            insight = ""
            summary_list = []
            chart_figs = []
            ai_response = ""

            if isinstance(result, pd.DataFrame):
                chart_data = result
            elif isinstance(result, pd.Series):
                chart_data = result.reset_index()
                if chart_data.shape[1] == 2:
                    chart_data.columns = ["Category", "Value"]

            # Detect matplotlib Axes objects (from .hist(), .plot(), etc.)
            # These are non-displayable — convert to a friendly message
            result_str = str(result)
            is_axes_result = "<Axes:" in result_str or "<AxesSubplot" in result_str
            if is_axes_result and chart_data is None:
                result = "The analysis generated visual charts. Please see the AI response below for a summary of the data patterns."

            # Check if result is an error
            is_error = isinstance(result, str) and (
                "error" in result.lower() or "failed" in result.lower()
                or "traceback" in result.lower()
            )

            # ── Generate conversational AI response ──
            if is_error:
                with st.spinner("💭 Thinking..."):
                    ai_response = generate_error_response(query, str(result))
            else:
                if chart_data is not None:
                    insight = generate_business_insight(chart_data)
                    st.session_state.analysis_insight = insight
                with st.spinner("💭 Preparing response..."):
                    ai_response = generate_conversational_response(query, result, insight)

            # ── Show the conversational response first ──
            if ai_response:
                st.markdown(ai_response)
                st.divider()

            # Show the code
            with st.expander("📝 View AI Generated Code", expanded=False):
                st.code(code, language="python")

            # ── Dictionary results ──
            if isinstance(result, dict):
                # Check if dict contains displayable data (not Axes objects)
                has_displayable = False
                for key, value in result.items():
                    try:
                        if "<Axes:" in str(value) or "<AxesSubplot" in str(value):
                            continue  # Skip Axes objects
                        df_result = pd.DataFrame(value).reset_index()
                        if df_result.shape[1] == 2:
                            df_result.columns = ["Category", "Value"]
                        st.markdown(f"**{key}**")
                        st.dataframe(df_result, use_container_width=True)
                        fig = px.bar(
                            df_result,
                            x=df_result.columns[0],
                            y=df_result.columns[1],
                            title=str(key)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        has_displayable = True
                    except:
                        pass
                if not has_displayable and not ai_response:
                    st.info("The AI analyzed the data but the result format couldn't be displayed as a table. See the AI response above for insights.")

            # ── DataFrame / Series results ──
            elif chart_data is not None:

                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown("**📋 Data Table**")
                    st.dataframe(chart_data, use_container_width=True)

                with col2:
                    st.markdown("**📊 Visual Analysis**")
                    chart_figs = auto_visualize(chart_data)
                    for i, fig in enumerate(chart_figs):
                        st.plotly_chart(fig, use_container_width=True, key=f"new_chart_{i}")

                # Business insight
                if insight:
                    st.info(f"🧠 **Business Insight:** {insight}")

                # Executive summary
                summary_list = generate_executive_summary(chart_data)
                if summary_list:
                    with st.expander("📑 Executive Summary", expanded=False):
                        for line in summary_list:
                            st.write("•", line)

            # ── Simple text / error results ──
            elif not ai_response:
                st.write(str(result))

            # Follow-up questions
            with st.expander("💡 Suggested Follow-Up Questions", expanded=False):
                with st.spinner("Generating follow-up questions..."):
                    suggestions = suggest_business_questions(query, df, schema)
                st.markdown(suggestions)

        # ── Persist everything to session state ──
        st.session_state.messages.append({"role": "user", "content": query})
        if isinstance(result, pd.DataFrame):
            preview = result.head(5).to_string(index=False)
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Here are the top results:\n\n{preview}"}
            )
        elif isinstance(result, pd.Series):
            preview = result.head(5).to_string()
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Here are the top results:\n\n{preview}"}
            )
        else:
            st.session_state.messages.append(
                {"role": "assistant", "content": str(result)}
            )

        st.session_state.analysis_result = result
        st.session_state.analysis_query = query
        if chart_data is not None:
            st.session_state.chart_data = chart_data
            st.session_state.report_charts = chart_figs

        # Save to analysis history (for PDF report)
        # Use ai_response as fallback insight instead of raw str(result)
        report_insight = insight if insight else (ai_response if ai_response else "Analysis completed.")
        # Sanitize: remove any Axes object representations
        if "<Axes:" in str(report_insight) or "<AxesSubplot" in str(report_insight):
            report_insight = ai_response if ai_response else "Analysis completed — see AI response for details."

        history_entry = {
            "query": query,
            "result": result if not is_axes_result else None,
            "code": code,
            "insight": report_insight,
            "ai_response": ai_response,
        }
        st.session_state.analysis_history.append(history_entry)

        # Save to chat_history (for rendering on rerun)
        chat_entry = {
            "query": query,
            "result": result,
            "code": code,
            "chart_data": chart_data,
            "insight": insight,
            "summary": summary_list,
            "charts": chart_figs,
            "ai_response": ai_response,
            "suggestions": suggestions if 'suggestions' in dir() else "",
        }
        st.session_state.chat_history.append(chat_entry)


# ---------- FORECASTING TAB (NEW) ----------

with tab3:

    st.subheader("🔮 Revenue / Sales Forecasting")
    st.write("Predict future trends based on historical data patterns.")

    forecast_periods = st.slider("Forecast periods (months):", min_value=1, max_value=12, value=3)

    if st.button("Generate Forecast", key="forecast_btn"):

        with st.spinner("Running forecast analysis..."):
            forecast_result = forecast_revenue(df, periods=forecast_periods)

        if forecast_result["available"]:

            st.success(forecast_result["message"])

            # Forecast table
            st.subheader("📋 Forecast Values")
            st.dataframe(forecast_result["forecast_df"], use_container_width=True)

            # Trend info
            trend = forecast_result["trend"]
            metric = forecast_result["metric"]
            trend_icon = "📈" if trend == "increasing" else "📉" if trend == "declining" else "➡"
            st.info(f"{trend_icon} The {metric} trend is **{trend}** (slope: {forecast_result['slope']:,.2f} per month)")

            # Combined chart: historical + forecast
            st.subheader("📊 Forecast Visualization")

            hist_df = forecast_result["historical_df"]
            fore_df = forecast_result["forecast_df"]

            fig = go.Figure()

            # Historical line
            fig.add_trace(go.Scatter(
                x=hist_df["Date"],
                y=hist_df[metric],
                mode="lines+markers",
                name="Historical",
                line=dict(color="#2563EB", width=2)
            ))

            # Forecast line
            fig.add_trace(go.Scatter(
                x=fore_df["Date"],
                y=fore_df["Predicted"],
                mode="lines+markers",
                name="Forecast",
                line=dict(color="#F59E0B", width=2, dash="dash")
            ))

            # Confidence interval
            fig.add_trace(go.Scatter(
                x=pd.concat([fore_df["Date"], fore_df["Date"][::-1]]),
                y=pd.concat([fore_df["Upper Bound"], fore_df["Lower Bound"][::-1]]),
                fill="toself",
                fillcolor="rgba(245,158,11,0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="95% Confidence Interval"
            ))

            fig.update_layout(
                title=f"{metric} — Historical + Forecast",
                xaxis_title="Date",
                yaxis_title=metric,
                template="plotly_white",
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

        else:

            st.warning(forecast_result["message"])
            st.info("💡 Tip: Forecasting works best with datasets that have date columns and numeric metrics like revenue or sales.")


# ---------- EXECUTIVE REPORTS TAB ----------

with tab4:

    st.markdown("<h3 style='color: #1E293B; margin-bottom: 0px;'>📑 Executive Report Generator</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 14px;'>Compile your entire AI analysis session into a branded, professional PDF report.</p>", unsafe_allow_html=True)
    
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
                st.markdown(f"""
                <div style="
                    background: #F8FAFC; 
                    border-left: 4px solid #F59E0B; 
                    padding: 12px 16px; 
                    margin-bottom: 12px; 
                    border-radius: 4px;
                    border-top: 1px solid #E2E8F0;
                    border-bottom: 1px solid #E2E8F0;
                    border-right: 1px solid #E2E8F0;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                ">
                    <div style="color: #64748B; font-size: 11px; font-weight: bold; margin-bottom: 4px;">ANALYSIS #{i}</div>
                    <div style="color: #1E293B; font-weight: 600; font-size: 15px;">"{entry['query']}"</div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### ⚙️ Report Configuration")
            
            st.markdown("""
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 600; color: #1E293B;">Document Type</div>
                    <div style="color: #64748B; font-size: 13px;">Executive PDF Briefing</div>
                </div>
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 600; color: #1E293B;">Included Features</div>
                    <ul style="color: #64748B; font-size: 13px; padding-left: 20px; margin-top: 5px;">
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

                    file_path = generate_pdf(
                        query=None,
                        summary_text=None,
                        dataframe=None,
                        charts=None,
                        analysis_history=history
                    )

                with open(file_path, "rb") as file:

                    st.download_button(
                        "📥 Download PDF Report",
                        data=file,
                        file_name="AI_Executive_Report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

                st.success("✅ Report generated successfully!")
                
            st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94A3B8; font-size: 12px; margin-top: 20px;">
    <strong>AI Business Intelligence Assistant</strong> • Powered by Groq AI + Streamlit
</div>
""", unsafe_allow_html=True)