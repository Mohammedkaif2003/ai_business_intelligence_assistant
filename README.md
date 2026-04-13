# Apex Analytics

AI-powered business intelligence assistant built with Streamlit, Pandas, Plotly, and Groq. The app turns uploaded CSV data into KPI cards, quick insights, natural-language analysis, forecasts, and exportable executive reports.

## What This Project Does

`Apex Analytics` is designed for analysts, founders, and business teams who want to explore tabular data without writing SQL or Python for every question.

Core workflows:

- Upload a CSV or choose a bundled sample dataset
- Review KPIs, statistics, and auto-generated insights
- Ask business questions in plain English
- Get tables, charts, summaries, and follow-up suggestions
- Run a simple revenue or sales forecast
- Export a multi-analysis PDF report

## Why It Stands Out

- Strong dark-mode dashboard UI with polished interactions
- Plain-English data analysis powered by Groq-backed code generation
- Built-in business insight generation, not just raw chart output
- Forecasting and PDF reporting included in the same product flow
- Sample datasets and tests included for quick evaluation

## Feature Overview

### Dashboard

- KPI cards with trend treatment and dataset-aware quick insights
- Dataset preview, column details, descriptive statistics
- Hero chart for the loaded dataset when suitable dimensions are available
- Search, sort, and filter controls for table views

### AI Analyst

- Chat-style interface for dataset questions
- Structured AI responses, summaries, and follow-up prompts
- Auto-generated charts when the result shape supports visualization
- Guardrails to reject irrelevant questions and handle failures cleanly

### Forecasting

- Trend projection from date-like and numeric columns
- Forecast table, confidence bounds, and chart output
- Works best with monthly or date-driven revenue and sales data

### Reports

- Export multiple saved analyses into a single PDF
- Includes insights, tables, and charts from prior AI sessions

## Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- Groq API
- ReportLab
- NumPy
- scikit-learn
- statsmodels

## Project Structure

```text
.
|-- app.py
|-- config.py
|-- requirements.txt
|-- styles.py
|-- ui_components.py
|-- PROJECT_DOCUMENTATION.md
|-- data/
|   `-- raw/
|       |-- finance_data.csv
|       |-- hr_data.csv
|       `-- sales_data.csv
|-- modules/
|   |-- ai_code_generator.py
|   |-- ai_conversation.py
|   |-- app_secrets.py
|   |-- auto_insights.py
|   |-- auto_visualizer.py
|   |-- code_executor.py
|   |-- data_loader.py
|   |-- dataset_analyzer.py
|   |-- executive_summary.py
|   |-- forecasting.py
|   |-- groq_ai.py
|   |-- insight_engine.py
|   |-- kpi_engine.py
|   |-- query_utils.py
|   |-- report_generator.py
|   `-- text_utils.py
`-- tests/
    |-- test_auto_insights.py
    |-- test_forecasting.py
    |-- test_kpi_engine.py
    `-- test_query_utils.py
```

## Streamlit Deployment

This project is designed to run on Streamlit Community Cloud or any Streamlit-hosted deployment with secrets configured.

### Secrets

Add your Groq API key in Streamlit secrets for deployment, or in a local `.env` file for development:

```env
GROQ_API_KEY=your_groq_key_here
```

At runtime, the app checks `st.secrets` first, then `.env`, then shell environment variables.

### Deployment Checklist

- Set the Groq API key.
- Keep `requirements.txt` pinned and install dependencies before deploying.
- Test one dataset load, one AI question, one follow-up click, and one PDF export after deployment.

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

Open `http://localhost:8501`.

## Demo Flow

Recommended walkthrough for a recruiter, teammate, or portfolio review:

1. Load `Sales Data` from the sidebar.
2. Show the KPI row, quick insights panel, and hero chart.
3. Open `AI Analyst` and ask:
   - `Top 5 regions by revenue`
   - `Revenue trend`
   - `Profit by category`
4. Open `Forecasting` and generate a 6-month forecast.
5. Open `Reports` and generate the PDF.

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
- auto-insight generation
- forecasting behavior
- dataset query routing helpers

## Security and Guardrails

- API keys are read from Streamlit secrets, `.env`, or environment variables
- AI-generated code is filtered before execution
- Irrelevant questions are rejected before code generation
- Result rendering falls back safely for unsupported outputs

## Production Readiness

- Dataset loading is cached for reruns
- Query response caching reduces repeated API calls
- Startup is lightweight for Streamlit deployment

## Known Limitations

- Forecasting is intentionally simple and trend-based, not a full forecasting pipeline
- AI quality depends on dataset cleanliness and question phrasing
- PDF output is optimized for summary reporting, not raw data export
- Code execution is guarded, but this is still a local prototype application

## Recommended Next Improvements

- Split `app.py` into page-level feature modules
- Expand tests around report generation and data loading
- Add screenshots or a GIF demo to the repository
- Add deployment instructions for Streamlit Community Cloud or Render

## Documentation

See [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for the full technical walkthrough.
