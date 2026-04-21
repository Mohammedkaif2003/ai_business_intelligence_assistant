# Apex Analytics

AI-powered business intelligence assistant built with Streamlit, Pandas, Plotly, and Groq. Upload any CSV and get KPI cards, auto-insights, deterministic analytics, 10+ chart types, revenue forecasts, and a narrative executive PDF — all through a chat-style analyst interface.

## What This Project Does

`Apex Analytics` is designed for analysts, founders, and business teams who want to explore tabular data without writing SQL or Python for every question.

Core workflows:

- Sign in (hashed-credential demo auth, per-user sidebar badge)
- Upload a CSV or choose a bundled sample dataset (Sales, HR, Finance)
- Review KPIs with trend deltas, statistics, and auto-generated insights
- Ask business questions in plain English — get tables, charts, and prose answers
- Charts are generated deterministically using pandas + plotly (no unreliable LLM code)
- Run a linear revenue or sales forecast with confidence intervals
- Export a narrative-style executive PDF report written from the AI's replies

## Why It Stands Out

- **Compute-first architecture** — pandas does all computation, Groq only narrates pre-computed results. No unreliable LLM code generation for standard analytical patterns.
- **10+ chart types** — bar, grouped bar, stacked bar, pie, line with markers, scatter, boxplot, correlation heatmap, outlier detection, and linear forecast overlay — all selected automatically based on query intent.
- **Strong dark-mode dashboard UI** with polished interactions and session-persistent tab navigation.
- **Narrative executive PDF** — cover page, exec summary, per-question prose, supporting visuals — not a dashboard dump.
- Built-in business insight generation, forecasting, and PDF reporting in the same product flow.

## Feature Overview

### Dashboard

- KPI cards with period-over-period trend deltas and dataset-aware quick insights
- Dataset preview, column details, descriptive statistics
- Hero chart for the loaded dataset when suitable dimensions are available
- Search, sort, and filter controls for table views

### AI Analyst

- Chat-style interface for dataset questions
- **Smart Analysis Engine**: deterministic pandas computation for 9 query patterns (ranking, comparison, trend, distribution, correlation, outlier, forecast, aggregate, general)
- Python selects the chart type based on query intent — no LLM code generation needed
- Groq narrates results in natural prose using a focused narration-only prompt
- Falls back to AI code generation only for truly novel queries
- Follow-up suggestions rendered as clickable buttons
- Charts persist in session state across reruns

### Supported Chart Types

| Query Pattern | Chart Type | Example Query |
|---|---|---|
| Ranking | Horizontal bar | "Which routes have the highest ridership?" |
| Comparison | Grouped bar | "How does ridership vary by day type?" |
| Trend | Line with markers | "Show ridership over time" |
| Distribution | Boxplot | "Show spread of rides by route" |
| Correlation | Heatmap (RdBu_r) | "Show correlation heatmap" |
| Outlier | Scatter with highlights | "Detect outliers in rides" |
| Forecast | Line + dashed overlay | "Forecast ridership for next year" |
| Aggregate | Bar | "Total revenue by region" |
| General | Auto-selected | Any analytical question |

### Forecasting

- Trend projection from date-like and numeric columns
- Forecast table, confidence bounds, and chart output
- Works best with monthly or date-driven revenue and sales data

### Reports

- Narrative executive briefing exported as PDF (not a dashboard printout)
- Cover page with dataset, analyst, and timestamp metadata
- Executive summary drafted from the AI's own replies
- Per-question sections: original question quote, AI analyst prose, supporting chart, compact reference table
- Bright, print-safe chart palette so bars and heatmaps read clearly on white paper
- Page numbers, proper typography, and confidentiality disclaimer

### Login & Session

- Hashed-credential login gate (SHA-256)
- Default demo users: `admin / admin123` and `analyst / analyst123`
- Sidebar user badge with sign-out
- `users.json` is local-only and git-ignored

## Tech Stack

- Python 3.10+
- Streamlit
- Pandas / NumPy
- Plotly Express / Plotly Graph Objects
- Groq API (LLaMA 3.3 70B)
- ReportLab / Kaleido (PDF + chart export)
- scikit-learn / statsmodels (forecasting)

## Project Structure

```text
.
|-- app.py                    # Main Streamlit application
|-- auth.py                   # Login gate (SHA-256 hashed credentials)
|-- config.py                 # App constants, layout, branding
|-- requirements.txt
|-- styles.py                 # Custom CSS injections
|-- ui_components.py          # Reusable UI elements (cards, chat bubbles)
|-- PROJECT_DOCUMENTATION.md  # Full technical architecture docs
|-- CHANGELOG.md              # Version history
|-- data/
|   `-- raw/
|       |-- finance_data.csv
|       |-- hr_data.csv
|       `-- sales_data.csv
|-- modules/
|   |-- smart_analysis.py     # Deterministic pandas analysis engine (NEW)
|   |-- ai_code_generator.py  # AI-powered code generation (fallback)
|   |-- ai_conversation.py    # Conversational AI + narrate_result()
|   |-- app_tabs.py           # Tab rendering + orchestration
|   |-- app_views.py          # UI view components
|   |-- app_state.py          # Session state management
|   |-- app_perf.py           # Performance tracking
|   |-- app_logging.py        # Structured logging
|   |-- app_secrets.py        # API key management
|   |-- auto_insights.py      # Automated business insight detection
|   |-- auto_visualizer.py    # Chart builders (10+ types)
|   |-- code_executor.py      # Sandboxed Python code execution
|   |-- data_loader.py        # Loading & column normalization
|   |-- dataset_analyzer.py   # Dataset schema analysis
|   |-- executive_summary.py  # Executive summary bullets
|   |-- forecasting.py        # Revenue/sales forecasting
|   |-- groq_ai.py            # Groq API integration
|   |-- insight_engine.py     # Business insight generation
|   |-- kpi_engine.py         # KPI extraction engine
|   |-- query_utils.py        # Query classification & relevance
|   |-- report_generator.py   # Professional PDF report generator
|   `-- text_utils.py         # Text cleaning & structuring
`-- tests/
    |-- test_auto_insights.py
    |-- test_forecasting.py
    |-- test_kpi_engine.py
    `-- test_query_utils.py
```

## Architecture — Compute First, Narrate Second

```
User Query
    │
    ├─① smart_analysis.py      Deterministic pandas computation (handles ~90% of queries)
    │   ├─ Classify intent       ranking / comparison / trend / distribution / etc.
    │   ├─ Match columns         exact name, substring, stem matching
    │   ├─ Compute with pandas   groupby, sort, mean, quantile, corr, IQR
    │   ├─ Pick chart in Python  bar, line, boxplot, heatmap, scatter, etc.
    │   └─ narrate_result()      Groq explains the pre-computed numbers (narration only)
    │
    ├─② detect_simple_query()   Pattern-matched code for simple aggregations
    │
    └─③ generate_analysis_code() LLM code generation (last resort for novel queries)
```

## Quick Start

### 1. Create a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Add your Groq API key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key_here
```

### 4. Run the app

```powershell
streamlit run app.py
```

Open `http://localhost:8501` and sign in with one of the demo users:

- `admin / admin123`
- `analyst / analyst123`

## Demo Flow

Recommended walkthrough for a recruiter, teammate, or portfolio review:

1. Sign in (demo credentials above).
2. Load `Sales Data` from the sidebar.
3. Show the KPI row, quick insights panel, and hero chart.
4. Open `AI Analyst` and ask:
   - `Which routes have the highest and lowest average ridership?`
   - `How does ridership vary by day type?`
   - `Show a boxplot of rides by route`
   - `Detect outliers in revenue`
   - `Show correlation heatmap`
   Click a follow-up suggestion — the nav stays on AI Analyst (session-persistent).
5. Open `Forecasting` and generate a 6-month forecast.
6. Open `Reports` and generate the narrative PDF — download and open it to show the cover page, executive summary, and per-question prose sections.

## Sample Datasets

- `sales_data.csv`: revenue-style business analytics
- `hr_data.csv`: workforce and attrition analytics
- `finance_data.csv`: budget and variance analysis

## Testing

Run the automated tests from the project root:

```powershell
python -m pytest -q
```

Current coverage focuses on:

- KPI generation
- Auto-insight generation
- Forecasting behavior
- Dataset query routing helpers

## Security and Guardrails

- API keys are read from environment variables or `.env`
- AI-generated code is filtered before execution (import stripping, forbidden keyword scanner)
- Smart analysis engine uses deterministic pandas — no code generation for standard patterns
- Irrelevant questions are rejected before code generation
- Result rendering falls back safely for unsupported outputs

## Known Limitations

- Forecasting is intentionally simple and trend-based, not a full ARIMA/Prophet pipeline
- AI narration quality depends on Groq API availability (429 rate limits handled gracefully)
- PDF output is optimized for summary reporting, not raw data export
- Code execution is guarded, but this is still a local prototype application

## Recommended Next Improvements

- Add deployment instructions for Streamlit Community Cloud or Render
- Expand tests around report generation and chart builders
- Add screenshots or a GIF demo to the repository
- Add user-configurable chart preferences (color themes, default chart types)

## Documentation

See [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for the full technical walkthrough.
