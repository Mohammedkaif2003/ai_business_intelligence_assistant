# ⚡ Apex Analytics — Enterprise Data Suite Documentation

---

## 1. Project Overview

**Apex Analytics** is an enterprise-grade, Streamlit-based Business Intelligence application. It allows users to upload business datasets (CSV files) and interact with them using natural language queries. The application uses a **compute-first architecture** where pandas handles all computation deterministically, and Groq's LLaMA models are used only for narrating pre-computed results.

The application transforms raw data into actionable business intelligence by providing:

- **Deterministic Smart Analysis** — 9 analytical patterns computed with pandas, charts selected by Python
- **Natural Language Narration** — Groq explains pre-computed results in conversational prose
- **10+ Chart Types** — bar, grouped bar, stacked bar, pie, line, scatter, boxplot, heatmap, outlier detection, forecast overlay
- **Automated KPI Generation** — Key Performance Indicators extracted automatically from any dataset
- **Revenue/Sales Forecasting** — Linear trend projection with confidence intervals
- **Professional PDF Reports** — Multi-query executive reports with branded styling and print-safe charts
- **Auto-Insights** — Automatic detection of trends, anomalies, and performance patterns

### Technology Stack

| Component        | Technology                          |
|------------------|-------------------------------------|
| Frontend / UI    | Streamlit, Custom CSS               |
| AI Engine        | Groq API (LLaMA 3.3 70B Versatile) |
| Smart Analysis   | Pandas, NumPy (deterministic)       |
| Visualizations   | Plotly Express, Plotly Graph Objects |
| Static Charting  | Kaleido (Plotly → PNG Export)        |
| PDF Generation   | ReportLab                           |
| Forecasting      | NumPy polyfit, scikit-learn         |
| Environment      | Python 3.10+, python-dotenv         |

### Runtime Requirements

```
streamlit, pandas, numpy, plotly, scikit-learn, statsmodels,
groq, python-dotenv, reportlab, kaleido
```

---

## 2. Project Structure

```
ai_business_intelligence_assistant/
│
├── .env                              # Stores API keys (GROQ_API_KEY)
├── .gitignore                        # Files to ignore in version control
├── app.py                            # Main Streamlit application
├── auth.py                           # Login gate (SHA-256 hashed credentials)
├── config.py                         # App constants, layout, & branding config
├── requirements.txt                  # Python package dependencies
├── styles.py                         # Custom CSS injections for the Streamlit UI
├── ui_components.py                  # Reusable UI elements (cards, headers, chat bubbles)
├── README.md                         # Main project readme
├── PROJECT_DOCUMENTATION.md          # In-depth technical architecture documentation
├── CHANGELOG.md                      # Version history
│
├── data/                             # Directory for local CSV datasets
│   └── raw/
│       ├── sales_data.csv            # Sales dataset (464 KB)
│       ├── hr_data.csv               # HR/Employee dataset (35 KB)
│       └── finance_data.csv          # Finance dataset (2.7 KB)
│
├── modules/                          # CORE BACKEND: Logic & Intelligence Engines
│   ├── __init__.py                   # Package initializer
│   ├── smart_analysis.py             # ★ Deterministic pandas analysis engine
│   ├── ai_code_generator.py          # AI-powered code generation (fallback path)
│   ├── ai_conversation.py            # Conversational AI + narrate_result()
│   ├── app_tabs.py                   # Tab rendering & orchestration
│   ├── app_views.py                  # UI view components
│   ├── app_state.py                  # Session state management
│   ├── app_perf.py                   # Performance timing
│   ├── app_logging.py                # Structured logging
│   ├── app_secrets.py                # API key management
│   ├── auto_insights.py              # Automated business insight detection
│   ├── auto_visualizer.py            # Chart builders (10+ types)
│   ├── code_executor.py              # Sandboxed Python code execution
│   ├── data_loader.py                # Loading & column normalization
│   ├── dataset_analyzer.py           # Dataset schema analysis
│   ├── executive_summary.py          # Executive summary bullet points
│   ├── forecasting.py                # Revenue/sales forecasting engine
│   ├── groq_ai.py                    # Groq API integration for suggestions
│   ├── insight_engine.py             # Business insight generation
│   ├── kpi_engine.py                 # KPI extraction engine
│   ├── query_utils.py                # Query classification, relevance, intent detection
│   ├── report_generator.py           # Professional PDF report generator
│   └── text_utils.py                 # Text cleaning & structuring
│
└── tests/
    ├── test_auto_insights.py
    ├── test_forecasting.py
    ├── test_kpi_engine.py
    └── test_query_utils.py
```

---

## 3. Core Architecture — Compute First, Narrate Second

The central design principle: **pandas computes, Python picks the chart, the LLM only narrates.**

### Query Execution Pipeline

```
User Query
    │
    ▼
classify_query_intent()           ← Intent detection (chart, ranking, forecast, etc.)
    │
    ▼
is_dataset_related_query()        ← Relevance filter (rejects unrelated questions)
    │
    ├─① run_smart_analysis()      ← DETERMINISTIC pandas computation
    │   ├─ _detect_query_type()     Classify: ranking / comparison / trend / etc.
    │   ├─ _find_metrics()          Match user words → numeric columns
    │   ├─ _find_group_col()        Match user words → categorical columns
    │   ├─ _analyze_ranking()       groupby → mean → sort (+ horizontal bar chart)
    │   ├─ _analyze_comparison()    Compare column averages (+ grouped bar chart)
    │   ├─ _analyze_trend()         groupby(date) → mean (+ line chart with markers)
    │   ├─ _analyze_distribution()  describe() (+ boxplot with mean+SD)
    │   ├─ _analyze_correlation()   .corr() (+ RdBu_r heatmap)
    │   ├─ _analyze_outlier()       IQR method (+ scatter with highlights)
    │   ├─ _analyze_forecast()      Linear extrapolation (+ solid + dashed overlay)
    │   └─ _analyze_aggregate()     sum/mean/count (+ bar chart)
    │   Then: narrate_result()      Groq explains pre-computed numbers (narration only)
    │
    ├─② detect_simple_query()     ← Pattern-matched pandas one-liners
    │   Then: generate_conversational_response()
    │
    └─③ generate_analysis_code()  ← LLM code generation (LAST RESORT)
        code_executor.py          ← Sandboxed execution
        Then: generate_conversational_response()
    │
    ▼
Chart rendering                   ← ai_charts (from smart/AI) or auto_visualize(result)
    │
    ▼
build_chart_from_query()          ← Fallback: deterministic chart from query + full df
    │
    ▼
Chat bubble + Plotly chart + follow-up suggestions
```

### Why This Works

| Old Architecture | New Architecture |
|---|---|
| Groq generates Python code | Pandas runs deterministic computation |
| Groq decides chart type | Python picks chart based on query pattern |
| Groq narrates raw data | Groq narrates pre-computed results |
| Both steps can fail → fallback message | Computation never fails; narration has graceful fallback |
| "I couldn't generate an AI response" | Always shows a useful answer |

---

## 4. File-by-File Documentation

### 4.1 `modules/smart_analysis.py` — ★ Deterministic Analysis Engine

**Purpose:** Handles ~90% of analytical queries without any LLM involvement. Pandas does all computation, Python selects the chart.

**Main Function:** `run_smart_analysis(query, df) → dict | None`

**Returns:**
```python
{
    "result": DataFrame | Series | scalar,  # The computed answer
    "chart": plotly.graph_objects.Figure,    # Ready-to-render chart
    "summary": str,                          # Human-readable computation summary
    "query_type": str,                       # ranking, comparison, trend, etc.
}
```

**9 Analytical Patterns:**

| Pattern | Trigger Words | Computation | Chart Type |
|---|---|---|---|
| ranking | highest, lowest, top, bottom, best, worst | `groupby → mean → sort` | Horizontal bar |
| comparison | vary, compare, vs, day type, weekday | Compare column averages | Grouped bar |
| trend | over time, trend, monthly, time series | `groupby(date) → mean` | Line with markers |
| distribution | distribution, boxplot, histogram, quartile | `describe()` | Boxplot w/ mean+SD |
| correlation | correlation, heatmap, relationship | `.corr()` | RdBu_r heatmap |
| outlier | outlier, anomaly, unusual, extreme | IQR: Q1-1.5×IQR, Q3+1.5×IQR | Scatter with highlights |
| forecast | forecast, predict, projection, future | `np.polyfit` + extrapolation | Line + dashed overlay |
| aggregate | total, sum, average, count, how many | `groupby → agg` | Bar |
| general | (catch-all) | Best-fit groupby or trend | Auto-selected |

**Column Matching:** Three-stage resolution:
1. Exact column name match
2. Substring match (column tokens in query)
3. Stem match ("ridership" ↔ "rides", "revenue" ↔ "rev")

---

### 4.2 `modules/ai_conversation.py` — Conversational AI

**Purpose:** Manages system prompts and LLM communication. Two modes:

**Mode 1 — `generate_conversational_response()`:**
Full analysis + optional code generation. Used when smart analysis doesn't apply.
- Dual-purpose prompt (prose + code blocks)
- Extracts insight text and chart code separately
- Sanitizes output to flowing prose

**Mode 2 — `narrate_result(query, computed_summary)`:** ★ NEW
Narration-only mode. Receives pre-computed numbers from `smart_analysis.py` and asks Groq to explain them in 3-5 sentences.
- Groq-first with Google Gemini fallback
- If both LLMs fail, returns the computed summary as-is (already human-readable)
- Never produces the "I couldn't generate" fallback message

**Key Functions:**
- `sanitize_ai_output(text)` — Strips HTML, code fences, markdown, section labels; flattens to prose
- `_split_insight_and_code(raw)` — Separates AI text from Python code blocks
- `narrate_result(query, summary)` — Narration-only LLM call

---

### 4.3 `modules/auto_visualizer.py` — Chart Builders (10+ Types)

**Purpose:** Generates charts both automatically and from query intent.

**Chart Builders:**

| Function | Chart Type | When Used |
|---|---|---|
| `_build_bar_chart()` | Vertical bar | Category aggregation |
| `_build_grouped_bar_chart()` | Grouped bar | Multi-metric comparison |
| `_build_stacked_bar_chart()` | Stacked bar | Composition analysis |
| `_build_line_chart()` | Line with markers | Time series |
| `_build_scatter_chart()` | Scatter plot | Relationships |
| `_build_histogram()` | Histogram | Frequency distribution |
| `_build_pie_chart()` | Pie / donut | Small-category breakdown |
| `_build_boxplot()` | Boxplot | Distribution with outlier whiskers |
| `_build_heatmap()` | Correlation heatmap | RdBu_r diverging scale |
| `_build_outlier_chart()` | Scatter + highlights | IQR-based outlier detection |

**Entry Points:**
- `auto_visualize(data)` — Generates up to 8 chart options from a DataFrame
- `build_chart_from_query(query, data)` — Intent-based chart from natural-language query (9 intents)

---

### 4.4 `modules/ai_code_generator.py` — AI Code Generation (Fallback)

**Purpose:** Sends user queries to Groq's LLaMA model and receives executable Python/Pandas code. Used only when `smart_analysis` returns None.

**Function:** `generate_analysis_code(api_key, query, df, dataset_context)`

**Prompt includes:**
- Dataset schema, column names, column types
- Chart type selection guidance (new): trend → `px.line`, comparison → `px.bar`, boxplot → `px.box`, scatter → `px.scatter`, heatmap → `px.imshow`, outlier → scatter with color
- IQR outlier method template
- Example with chart figure creation

---

### 4.5 `modules/code_executor.py` — Sandboxed Code Execution

**Purpose:** Safely executes AI-generated Python code in a restricted environment.

**Function:** `execute_code(code, df)`

**Security Features:**
- **Forbidden keyword scanner** — blocks: `import`, `os.`, `sys.`, `subprocess`, `open(`, `__`, `eval(`, `exec(`, `write(`, `read(`, `shutil`, `pathlib`, `socket`, `requests`, `http`
- **Sandboxed execution** — code runs with only `pd`, `np`, `px`, `go`, `plt` in scope
- **Result extraction** — safely retrieves `result` and `charts` variables
- **Error handling** — returns user-friendly error messages

---

### 4.6 `modules/query_utils.py` — Query Classification & Relevance

**Purpose:** Detects query intent, validates dataset relevance, and generates follow-up suggestions.

**Key Functions:**
- `classify_query_intent(query, df, schema)` — Returns intent (chart, comparison, forecast, summary, table, analysis), clarification needs, and confidence score. Recognizes 20+ chart-related tokens.
- `is_dataset_related_query(query, df, schema)` — Validates that the question is relevant to the loaded dataset. Uses fuzzy stem matching for column names.
- `detect_simple_query(query, df)` — Pattern-matches common queries to one-liner pandas expressions.
- `build_rephrase_suggestions(query, df, schema)` — Generates rephrased query suggestions when the original is ambiguous.

---

### 4.7 `modules/app_tabs.py` — Tab Rendering & Orchestration

**Purpose:** Renders the four main tabs (Data Overview, AI Analyst, Forecasting, Reports) and orchestrates the query execution pipeline.

**Query Execution Flow (AI Analyst tab):**
1. Classify intent via `classify_query_intent()`
2. Check relevance via `is_dataset_related_query()`
3. Try `run_smart_analysis(query, df)` — deterministic pandas
4. If smart analysis succeeds: use `narrate_result()` for AI response
5. Else try `detect_simple_query()` — pattern-matched code
6. Else use `generate_analysis_code()` → `execute_code()` — LLM fallback
7. Render result, chart, and follow-up suggestions

---

### 4.8 `modules/app_logic.py` — Business Logic Helpers

**Purpose:** KPI augmentation, quick insights, result formatting.

**Key Functions:**
- `augment_kpis_with_trends(kpis, df)` — Adds period-over-period delta percentages to KPI cards
- `_compute_period_delta(df, column)` — Recent-window vs overall-mean comparison. Handles edge case where metric column IS the date column.
- `generate_quick_insights(df)` — Dashboard-level insights (top performer, lowest signal, anomaly)
- `build_overview_hero_chart(df)` — Generates the hero chart for the dashboard

---

### 4.9 `modules/report_generator.py` — Professional PDF Generator

**Purpose:** Generates a fully branded, narrative executive PDF report.

**Function:** `generate_pdf(query, summary_text, dataframe, charts, analysis_history)`

**PDF Features:**
- **Cover Page** — Title with accent bar, metadata table, classification
- **Executive Summary** — Key takeaways from AI responses, grouped and deduped
- **Per-Query Sections** — Question quote, AI prose, supporting chart, compact reference table
- **Print-Safe Charts** — `_plotly_to_bytes()` deep-copies figures and resets colors for white paper. Heatmaps preserve their coloraxis; non-heatmaps strip it.
- **Page Decorations** — Header band, accent strip, confidentiality footer, page numbers

**Chart Export Handling:**
- `_reset_trace_colors_for_light_bg()` — Handles bar, scatter, line, pie, heatmap, and box trace types individually
- Heatmap traces get `RdBu_r` colorscale and dark annotation text
- Non-heatmap figures get `coloraxis=dict(showscale=False)`

---

### 4.10 Other Modules

| Module | Purpose |
|---|---|
| `data_loader.py` | CSV loading, column normalization (Revenue, Product, Region, Date synonyms) |
| `dataset_analyzer.py` | Schema analysis: row/col count, column classification, example values |
| `kpi_engine.py` | Auto-KPI extraction (Total, Average, Max, Min) + special KPIs (Attrition Rate, Profit Margin) |
| `auto_insights.py` | Dashboard-level insights: top contributor, bottom performer, trends, missing data |
| `insight_engine.py` | Business insight generation from analysis results |
| `executive_summary.py` | Executive summary bullet points |
| `forecasting.py` | Linear trend forecasting with confidence intervals |
| `groq_ai.py` | Groq API for follow-up question suggestions |
| `text_utils.py` | Text cleaning, markdown stripping, response structuring |
| `app_state.py` | Session state management, activity tracking |
| `app_perf.py` | Performance timing instrumentation |
| `app_logging.py` | Structured logging |
| `app_secrets.py` | API key management (env, secrets, dotenv) |

---

## 5. Session State Management

| Key                     | Type    | Purpose                                        |
|-------------------------|---------|------------------------------------------------|
| `active_tab`            | String  | Currently selected tab (session-persistent)    |
| `messages`              | List    | Basic chat history (text only)                 |
| `chat_history`          | List    | Rich chat history (results, charts, insights)  |
| `analysis_history`      | List    | All queries + results for PDF report           |
| `result_history`        | List    | Raw results for memory/comparison queries      |
| `result_history_details`| List    | Metadata about each result                     |
| `analysis_result`       | Various | Latest query's raw result                      |
| `analysis_query`        | String  | Latest query text                              |
| `analysis_insight`      | String  | Latest query's business insight                |
| `chart_data`            | DF      | Latest query's chart-ready data                |
| `report_charts`         | List    | Latest query's Plotly figure objects            |

---

## 6. Security Model

1. **Smart Analysis** — Most queries bypass code generation entirely (deterministic pandas)
2. **Prompt Engineering** — AI is instructed not to import libraries or use system calls
3. **Import Stripping** — `ai_code_generator.py` removes any `import` / `from` lines
4. **Forbidden Keywords** — `code_executor.py` blocks 15+ dangerous patterns
5. **Sandboxed Execution** — Code runs with only `pd`, `np`, `px`, `go`, `plt` in scope
6. **Error Isolation** — All exceptions are caught and returned as user-friendly strings

---

## 7. API Configuration

| Parameter     | Value                         |
|---------------|-------------------------------|
| Model         | `llama-3.3-70b-versatile`     |
| Temperature   | 0.1 (code gen) / 0.3 (narration + suggestions) |
| API Key       | Stored in `.env` as `GROQ_API_KEY` |
| Fallback      | Computed summary returned as-is if LLM fails |

---

## 8. How to Run

```bash
# 1. Clone the repository
git clone https://github.com/Mohammedkaif2003/ai_business_intelligence_assistant.git

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1          # Windows PowerShell
# source venv/bin/activate          # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your Groq API key
# Create a .env file with: GROQ_API_KEY=your_key_here

# 5. Run the application
streamlit run app.py
```

The app will open at `http://localhost:8501`.

Login credentials: `admin / admin123` or `analyst / analyst123`.

---

*Document Updated: April 2026*
*Apex Analytics — Version 3.0 Compute-First Architecture*
