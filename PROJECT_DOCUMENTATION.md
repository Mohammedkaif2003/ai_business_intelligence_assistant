# ⚡ Apex Analytics — Enterprise Data Suite Documentation

---

## 1. Project Overview

**Apex Analytics** is an enterprise-grade, Streamlit-based Business Intelligence application. It allows users to upload business datasets (CSV files) and interact with them using natural language queries powered by **Groq's advanced LLaMA models**, functioning natively as a Senior Data Analyst.

The application transforms raw data into actionable business intelligence by providing:

- **Natural Language Data Analysis** — Ask questions in plain English, get data tables, charts, and insights
- **Automated KPI Generation** — Key Performance Indicators extracted automatically from any dataset
- **Revenue/Sales Forecasting** — Linear trend projection with confidence intervals
- **Professional PDF Reports** — Multi-query executive reports with branded styling
- **Auto-Insights** — Automatic detection of trends, anomalies, and performance patterns

### Technology Stack

| Component        | Technology                        |
|------------------|-----------------------------------|
| Frontend / UI    | Streamlit, Tailwind CSS (Injected)|
| AI Engine        | Groq API (LLaMA Models)           |
| Data Processing  | Pandas, NumPy                     |
| Visualizations   | Plotly Express, Plotly Graph Objects |
| Static Charting  | Kaleido (Plotly → PNG Export)    |
| PDF Generation   | ReportLab                         |
| Environment      | Python 3.10+, python-dotenv       |

### Runtime Requirements

```
streamlit, pandas, numpy, matplotlib, seaborn, plotly
scikit-learn, statsmodels, joblib, groq, python-dotenv, reportlab, kaleido
```

---

## 2. Project Structure

```
ai_chatbat_cam_anaylz/
│
├── .env                              # Stores API keys (GROQ_API_KEY, GOOGLE_API_KEY)
├── .gitignore                        # Files to ignore in version control
├── app.py                            # Main Streamlit application
├── config.py                         # App constants, layout, & branding config
├── requirements.txt                  # Python package dependencies
├── styles.py                         # Custom CSS injections for the Streamlit UI
├── ui_components.py                  # Reusable UI elements (cards, headers, chat bubbles)
├── calc_report.py                    # Legacy/Utility helper script
├── README.md                         # Main generic project read-me
├── PROJECT_DOCUMENTATION.md          # In-depth technical architecture documentation
├── INITIAL_VS_ENHANCED.md            # Document tracking UI/UX enhancement history
│
├── data/                             # Directory for local CSV datasets
│   └── raw/
│       ├── sales_data.csv          # Sales dataset (464 KB)
│       ├── hr_data.csv             # HR/Employee dataset (35 KB)
│       └── finance_data.csv        # Finance dataset (2.7 KB)
│
├── modules/                          # CORE BACKEND: Logic & Intelligence Engines
│   ├── __init__.py                   # Package initializer
│   ├── ai_code_generator.py          # AI-powered code generation via Groq
│   ├── ai_conversation.py            # Manages conversational logic & system prompts for AI answers
│   ├── auto_insights.py              # Automated business insight detection
│   ├── auto_visualizer.py            # Automatic chart generation (bar, line, pie)
│   ├── code_executor.py              # Sandboxed Python code execution
│   ├── data_loader.py                # Loading & column normalization
│   ├── dataset_analyzer.py           # Dataset schema analysis
│   ├── executive_summary.py          # Executive summary bullet points
│   ├── forecasting.py                # Revenue/sales forecasting engine
│   ├── groq_ai.py                    # Groq API integration for suggestions
│   ├── insight_engine.py             # Business insight generation
│   ├── kpi_engine.py                 # KPI extraction engine
│   └── report_generator.py           # Professional PDF report generator
│
├── improvements_and_changes_report.txt   # Detailed changelog
└── setup_commands_explained.txt          # Setup guide with explanations
```

---

## 3. File-by-File Documentation

### 3.1 `app.py` — Main Application Route

The central Streamlit application that ties all modules together. It contains:

**Configuration & Setup**
- Imports all modules, configs, and UI libraries
- Loads Groq API key from `.env`
- Sets page config and mounts the modular design logic
- Injects custom CSS for tabs, KPI cards, and section headers

**Dataset Loading (Lines 90–175)**
- `load_dataset(file)` — Loads uploaded CSV files
- `load_local_dataset(path)` — Loads pre-loaded datasets from `data/raw/`
- Data input options: Upload CSV or use pre-loaded datasets (Sales, HR, Finance)
- After loading: normalizes columns, analyzes schema, generates KPIs, auto-insights

**Tab 1: Data Overview**
- Dataset preview (first 20 rows)
- Column details table (type, null count, unique values, example values)
- Descriptive statistics (`df.describe()`)

**Tab 2: AI Data Analyst (Chat Interface)**
- Full chat interface using `st.chat_message` and `st.chat_input`
- User types questions → AI generates Python code → code executes on data
- Results shown inline: data tables, Plotly charts, business insights, executive summaries
- Complete chat history persisted via `st.session_state.chat_history`
- "Clear Chat" button resets all state

**Tab 3: Forecasting**
- Revenue/sales forecasting with configurable periods (1–12 months)
- Displays: forecast table, trend indicator, combined historical + forecast chart
- Confidence intervals shown as shaded regions

**Tab 4: Executive Reports**
- Professional two-column layout with styled query cards
- Shows all queries queued for the report
- "Generate Professional PDF" button → downloads branded PDF
- Report includes: cover page, table of contents, per-query sections, disclaimer

---

### 3.2 `modules/ai_code_generator.py` — AI Code Generation

**Purpose:** Sends user queries to Groq's LLaMA model and receives executable Python/Pandas code.

**Function:** `generate_analysis_code(api_key, query, df, dataset_context)`

**How it works:**
1. Takes the user's natural language question
2. Constructs a detailed prompt including dataset schema, column names, and strict rules
3. Sends to Groq API (LLaMA 3.3 70B, temperature=0.1 for consistent output)
4. Post-processes the response:
   - Strips markdown code blocks
   - Removes conversational text ("Here is the code...")
   - **Strips `import` statements** to prevent security block triggers
   - Adds fallback if no `result` variable is found

**Key Rules in Prompt:**
- Must use `df` as the DataFrame name
- Must store output in `result`
- No imports allowed (pandas and numpy pre-loaded)
- Must use correct `nlargest(n, columns=...)` syntax

---

### 3.3 `modules/code_executor.py` — Sandboxed Code Execution

**Purpose:** Safely executes AI-generated Python code in a restricted environment.

**Function:** `execute_code(code, df)`

**Security Features:**
- **Forbidden keyword scanner** — blocks: `import`, `os.`, `sys.`, `subprocess`, `open(`, `__`, `eval(`, `exec(`, `write(`, `read(`, `shutil`, `pathlib`, `socket`, `requests`, `http`
- **Sandboxed execution** — code runs with only `pd` (pandas) and `np` (numpy) in global scope
- **Result extraction** — safely retrieves the `result` variable from the execution scope
- **Error handling** — returns user-friendly error messages instead of crashing

---

### 3.4 `modules/data_loader.py` — Data Loading & Normalization

**Purpose:** Standardizes column names across different datasets so the rest of the app can work with consistent naming.

**Functions:**
- `normalize_columns(df)` — Cleans column names (strips whitespace, replaces underscores/hyphens, converts to Title Case). Maps common synonyms:
  - Sales / Sales Amount / Revenue Amount → `Revenue`
  - Product Name / Item → `Product`
  - Location / Area → `Region`
  - Order Date / Transaction Date → `Date`
  - Auto-converts Date columns to datetime

- `detect_columns(df)` — Detects key business columns (Product, Region, Revenue, Date) by scanning column names

---

### 3.5 `modules/dataset_analyzer.py` — Schema Analysis

**Purpose:** Analyzes the structure of a loaded dataset.

**Function:** `analyze_dataset(df)`

**Returns a dictionary with:**
- Row count, column count
- Column names list
- Classified columns: numeric, categorical, datetime
- Example values for each column

This schema is used throughout the app (AI prompts, report generators, etc.)

---

### 3.6 `modules/groq_ai.py` — Groq API / Follow-Up Questions

**Purpose:** Uses the Groq API to suggest intelligent follow-up business questions.

**Function:** `suggest_business_questions(query, df, schema)`

**How it works:**
1. Takes the user's last query + dataset metadata
2. Asks LLaMA to suggest 5 useful follow-up questions executives might ask
3. Focuses on: trends, performance comparisons, rankings, future predictions
4. Returns formatted bullet-point suggestions

---

### 3.7 `modules/auto_visualizer.py` — Automatic Chart Generation

**Purpose:** Automatically generates appropriate Plotly charts based on the data structure.

**Function:** `auto_visualize(data)`

**Chart types generated:**
1. **Bar Charts** — for each numeric column vs. the first categorical column
2. **Line Charts** — if a time/date column is detected (trend visualization)
3. **Pie Charts** — only for small datasets (≤10 rows) showing distribution

All charts use `plotly_white` template with professional font sizes and layout.

---

### 3.8 `modules/insight_engine.py` — Business Insight Generator

**Purpose:** Generates natural-language business insights from analysis results.

**Function:** `generate_business_insight(data)`

**Insights detected:**
- 🏆 Top performer identification
- 📉 Lowest performer identification
- ⚠ Revenue concentration risk (>50% or >35% from single entity)
- ⚖ Performance gap analysis (top vs. bottom)
- 📈/📉 Trend detection (increasing/declining)

**Special handling:** Flattens MultiIndex DataFrames, handles both Series and DataFrame inputs.

---

### 3.9 `modules/executive_summary.py` — Executive Summary Bullets

**Purpose:** Generates concise executive summary bullet points.

**Function:** `generate_executive_summary(data)`

**Output includes:**
- Top and bottom performer identification with values
- Contribution percentage of the top performer
- Total metric value across all categories

**Special handling:** MultiIndex flattening, Series → DataFrame conversion.

---

### 3.10 `modules/auto_insights.py` — Automated Dataset Insights

**Purpose:** Scans the entire dataset and generates a comprehensive list of insights, displayed on the dashboard when data is first loaded.

**Function:** `generate_auto_insights(df)`

**Insight categories:**
- 🏆 Top contributor and market share
- 📉 Bottom performer identification
- 📈 Max/min/average values for numeric columns
- ⚠ Missing data detection with percentage
- 📊 Quarter-over-quarter revenue comparison
- 📈/📉 Overall trend detection
- 🏷 Unique category counts

---

### 3.11 `modules/kpi_engine.py` — KPI Extraction

**Purpose:** Automatically extracts Key Performance Indicators from any dataset.

**Function:** `generate_kpis(df)`

**Standard KPIs (for first 4 numeric columns):**
- Total, Average, Max, Min

**Special KPIs:**
- **Attrition Rate** — detected for HR datasets (column named "Attrition")
- **Average Profit Margin** — detected for sales datasets (column containing "margin")

Returns up to 5 KPIs, displayed as styled cards on the dashboard.

---

### 3.12 `modules/forecasting.py` — Revenue/Sales Forecasting

**Purpose:** Performs time-series forecasting using linear trend projection.

**Function:** `forecast_revenue(df, periods=3)`

**How it works:**
1. Auto-detects date column and revenue/sales metric
2. Aggregates data by month
3. Fits a linear regression using `numpy.polyfit`
4. Generates forecast values with 95% confidence intervals (±1.96 × std error)
5. Determines trend direction (increasing/declining/stable)

**Returns:** forecast DataFrame, historical DataFrame, trend info, slope, standard error.

**Requirements:** At least 3 monthly data points. Falls back gracefully if conditions aren't met.

---

### 3.13 `modules/report_generator.py` — PDF Report Generator (639 lines)

**Purpose:** Generates a fully branded, professional PDF executive report.

**Function:** `generate_pdf(query, summary_text, dataframe, charts, analysis_history)`

**PDF Features:**
- **Cover Page** — Title with blue accent bar, metadata table (report type, date, analyses count, classification)
- **Table of Contents** — Lists all queries with analysis numbers
- **Per-Query Sections** — Each query gets:
  - Analysis number header
  - Gold-bordered query box
  - AI Business Insight in blue highlight box
  - High-resolution bar charts (200 DPI) with value labels
  - Professionally styled data tables (alternating rows, deep blue headers)
  - Strategic recommendations with triangle bullet points
- **Disclaimer Page** — AI-generated content disclaimer
- **Page Decorations** — Blue accent bar (header), dark footer with page number + "Confidential"

**Brand Colors:**
- Navy: `#1E293B`, Blue: `#2563EB`, Gold: `#F59E0B`, Green: `#10B981`

---

## 4. Data Flow Architecture

```
User Input (CSV/Pre-loaded)
        │
        ▼
   data_loader.py          ← normalize_columns()
        │
        ▼
   dataset_analyzer.py     ← analyze_dataset() → schema dict
        │
        ├──────────────────────┐
        ▼                      ▼
   kpi_engine.py          auto_insights.py
   (KPI cards)            (dashboard insights)
        │
        ▼
   ┌─────────────────────────────────────────┐
   │           USER ASKS A QUESTION          │
   │                                          │
   │  ai_code_generator.py                   │
   │    └─ Groq API → Python code             │
   │                                          │
   │  code_executor.py                       │
   │    └─ Sandboxed execution → result       │
   │                                          │
   │  auto_visualizer.py                     │
   │    └─ result → Plotly charts             │
   │                                          │
   │  insight_engine.py                      │
   │    └─ result → business insights         │
   │                                          │
   │  executive_summary.py                   │
   │    └─ result → summary bullets           │
   │                                          │
   │  groq_ai.py                             │
   │    └─ suggest follow-up questions        │
   └─────────────────────────────────────────┘
        │
        ▼
   report_generator.py     ← All queries accumulated
        │                     into analysis_history[]
        ▼
   AI_Executive_Report.pdf
```

---

## 5. Session State Management

The app uses Streamlit's `st.session_state` to persist data across interactions:

| Key                  | Type    | Purpose                                        |
|----------------------|---------|------------------------------------------------|
| `messages`           | List    | Basic chat history (text only)                 |
| `chat_history`       | List    | Rich chat history (results, charts, insights)  |
| `analysis_history`   | List    | All queries + results for PDF report generation|
| `analysis_result`    | Various | Latest query's raw result                      |
| `analysis_query`     | String  | Latest query text                              |
| `analysis_insight`   | String  | Latest query's business insight                |
| `chart_data`         | DF      | Latest query's chart-ready data                |
| `report_charts`      | List    | Latest query's Plotly figure objects            |

---

## 6. Security Model

The application executes AI-generated code, which requires careful security:

1. **Prompt Engineering** — AI is instructed not to import libraries or use system calls
2. **Import Stripping** — `ai_code_generator.py` removes any `import` / `from` lines before passing to executor
3. **Forbidden Keywords** — `code_executor.py` blocks 13 dangerous patterns:
   `import`, `os.`, `sys.`, `subprocess`, `open(`, `__`, `eval(`, `exec(`, `write(`, `read(`, `shutil`, `pathlib`, `socket`, `requests`, `http`
4. **Sandboxed Execution** — Code runs with only `pd` and `np` in scope (no file system, no network)
5. **Error Isolation** — All exceptions are caught and returned as user-friendly strings

---

## 7. API Configuration

The app uses **Groq's LLaMA 3.3 70B Versatile** model:

| Parameter     | Value                      |
|---------------|----------------------------|
| Model         | `llama-3.3-70b-versatile`  |
| Temperature   | 0.1 (code gen) / 0.3 (suggestions) |
| API Key       | Stored in `.env` as `GROQ_API_KEY` |
| Fallback      | `st.secrets.get("GROQ_API_KEY", None)` for Streamlit Cloud |

---

## 8. How to Run

```bash
# 1. Clone the repository
git clone https://github.com/Mohammedkaif2003/Mohammedkaif2003-ai_business_intelligence_assistant.git

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

---

*Document Updated: March 2026*
*Apex Analytics — Version 2.0 Enterprise Data Suite*
