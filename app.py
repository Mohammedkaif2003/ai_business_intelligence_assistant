import streamlit as st
import pandas as pd
import plotly.express as px

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
import os
from dotenv import load_dotenv
import streamlit as st
# Load environment variables
load_dotenv()

api_key = os.getenv("GROQ_API_KEY") or st.secrets["GROQ_API_KEY"]

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

</style>
""", unsafe_allow_html=True)
st.title("📊 AI Business Intelligence Assistant")
st.write("Upload data → Ask questions → Get insights, charts, and reports.")


@st.cache_data
def load_dataset(file):
    df = pd.read_csv(file)
    df = normalize_columns(df)
    return df

uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])

if uploaded_file:
    df = load_dataset(uploaded_file)
    st.session_state.df = df
    st.success("Dataset loaded successfully")

if "df" not in st.session_state:
    st.stop()

df = st.session_state.df

schema = analyze_dataset(df)

col1, col2, col3 = st.columns(3)
col1.metric("Rows", df.shape[0])
col2.metric("Columns", df.shape[1])
col3.metric("Numeric Columns", len(schema["numeric_columns"]))

st.divider()

st.subheader("📋 Dataset Overview")

st.write(
    f"This dataset contains **{schema['rows']} rows** and **{schema['columns']} columns**."
)

if schema["numeric_columns"]:
    st.write(
        f"Numeric metrics: {', '.join(schema['numeric_columns'][:5])}"
    )

if schema["categorical_columns"]:
    st.write(
        f"Categorical dimensions: {', '.join(schema['categorical_columns'][:5])}"
    )

st.divider()

st.subheader("📊 Key Performance Indicators")

kpis = generate_kpis(df)

if len(kpis) > 0:

    cols = st.columns(len(kpis))

    icons = ["💰","📦","📈","📊","🏷"]

    for i, kpi in enumerate(kpis):

        with cols[i]:

            st.markdown(f"""
            <div style="
                padding:16px;
                border-radius:12px;
                border:1px solid rgba(128,128,128,0.2);
                background: var(--secondary-background-color);
            ">

            <div style="font-size:14px;opacity:0.8">
            {icons[i % len(icons)]} {kpi['metric']}
            </div>

            <div style="font-size:28px;font-weight:700;margin-top:6px">
            {kpi['total']:,}
            </div>

            <div style="font-size:13px;color:#10B981;margin-top:4px">
            Avg {kpi['average']}
            </div>

            </div>
            """, unsafe_allow_html=True)

else:

    st.info("No numeric columns available for KPI metrics.")

date_cols = df.select_dtypes(include=["datetime","datetime64"]).columns
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

tab1, tab2, tab3 = st.tabs([
    "📊 Data Overview",
    "🤖 AI Data Analyst",
    "📑 Executive Reports"
])

with tab1:

    st.subheader("Dataset Preview")
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader("Statistics")
    st.dataframe(df.describe(), use_container_width=True)

with tab2:

    st.subheader("Ask Questions About Your Data")

    if st.button("Clear Chat"):

        st.session_state.messages = []

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

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    query = st.chat_input("Ask something about your dataset...")

    if query:

        with st.chat_message("user"):
            st.write(query)

        with st.spinner("AI analyzing dataset..."):

            code = generate_analysis_code(api_key, query, df, schema)
            result = execute_code(code, df)

        st.success("Analysis completed")

        with st.expander("Show AI generated code"):
            st.code(code, language="python")

        st.session_state.messages.append({"role": "user", "content": query})

        if isinstance(result, pd.DataFrame):

            preview = result.head(5).to_string(index=False)

            st.session_state.messages.append(
                {"role": "assistant", "content": f"Here are the top results:\n\n{preview}"}
            )

        else:

            st.session_state.messages.append(
                {"role": "assistant", "content": str(result)}
            )

        st.session_state.analysis_result = result
        st.session_state.analysis_query = query

        chart_data = None

        # -------- Handle DataFrame --------
        if isinstance(result, pd.DataFrame):

            chart_data = result

        # -------- Handle Series --------
        elif isinstance(result, pd.Series):

            chart_data = result.reset_index()
            chart_data.columns = ["Category", "Value"]

        # -------- Handle Dictionary --------
        elif isinstance(result, dict):

            st.subheader("📊 Analysis Results")

            for key, value in result.items():

                st.markdown(f"### {key}")

                try:

                    df_result = pd.DataFrame(value).reset_index()

                    if df_result.shape[1] == 2:
                        df_result.columns = ["Category", "Value"]

                    st.dataframe(df_result, use_container_width=True)

                    fig = px.bar(
                        df_result,
                        x=df_result.columns[0],
                        y=df_result.columns[1],
                        title=key
                    )

                    st.plotly_chart(fig, use_container_width=True)

                except:
                    st.write(value)

        # -------- Other Results --------
        else:

            st.subheader("📊 Result")
            st.success(str(result))
        if chart_data is not None:

            st.session_state.chart_data = chart_data

            col1, col2 = st.columns([1,2])

            with col1:
                st.subheader("Data Table")
                st.dataframe(chart_data, use_container_width=True)

            with col2:

                st.subheader("Visual Analysis")

                charts = auto_visualize(chart_data)

                st.session_state.report_charts = charts

                for i, fig in enumerate(charts):
                    st.plotly_chart(fig, use_container_width=True, key=f"analysis_chart_{i}")

            st.divider()

            insight = generate_business_insight(chart_data)
            st.session_state.analysis_insight = insight

            st.subheader("Business Insight")
            st.info(insight)

            st.subheader("Executive Summary")

            summary = generate_executive_summary(chart_data)

            for line in summary:
                st.write("•", line)

        with st.spinner("Generating AI follow-up questions..."):
            suggestions = suggest_business_questions(query, df, schema)

        st.subheader("Suggested Follow-Up Questions")
        st.markdown(suggestions)

with tab3:

    st.subheader("Generate Executive Report")

    if "analysis_result" not in st.session_state:

        st.info("Run an analysis first")

    else:

        if st.button("Generate PDF Report"):

            file_path = generate_pdf(
                query=st.session_state.get("analysis_query"),
                summary_text=st.session_state.get("analysis_insight"),
                dataframe=st.session_state.get("analysis_result"),
                charts=st.session_state.get("report_charts")
            )

            with open(file_path, "rb") as file:

                st.download_button(
                    "Download Executive Report",
                    data=file,
                    file_name="AI_Executive_Report.pdf",
                    mime="application/pdf"
                )
st.markdown("---")
st.caption("AI Business Intelligence Assistant • Powered by Groq + Streamlit")