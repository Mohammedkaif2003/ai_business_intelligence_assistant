# 🤖 AI Business Intelligence Assistant

An **AI-powered conversational analytics system** that allows users to upload datasets, ask questions in natural language, and automatically generate **data insights, visualizations, and business reports**.

This project acts like an **AI Data Analyst**, helping users explore and understand company data without writing complex queries.

---

# 🚀 Features

* 📊 Natural Language Data Analysis
* 📈 Automatic Chart Generation
* 📉 KPI Dashboard
* 🧠 AI-Generated Business Insights
* 💡 Smart Query Suggestions
* 📄 Downloadable PDF Analytics Report
* 🌐 Interactive Streamlit Web Interface

---

# 🏗️ System Architecture

```
User Question
      ↓
Streamlit Interface
      ↓
AI Query Processing
      ↓
Analytics Engine (Pandas)
      ↓
Visualization Engine (Plotly)
      ↓
Business Insight Generator
      ↓
PDF Report Generator
```

The system converts **natural language queries into data analysis and visual insights automatically**.

---

# 📁 Project Structure

```
AI-Business-Intelligence-Assistant
│
├── app.py                     # Main Streamlit application
│
├── modules/
│   ├── dataset_analyzer.py   # Dataset structure analysis
│   ├── auto_visualizer.py    # Automatic chart generation
│   ├── insight_engine.py     # Business insight generation
│   ├── auto_insights.py      # Automatic trend detection
│   ├── kpi_engine.py         # KPI calculation
│   ├── report_generator.py   # PDF report creation
│   ├── ai_code_generator.py  # AI-generated analysis code
│   ├── code_executor.py      # Secure code execution
│   ├── groq_ai.py            # AI query suggestion engine
│   └── data_loader.py        # Dataset loading and normalization
│
├── requirements.txt
├── README.md
```

---

# ⚙️ Installation

Clone the repository:

```
git clone https://github.com/Mohammedkaif2003/Mohammedkaif2003-ai_business_intelligence_assistant
cd Mohammedkaif2003-ai_business_intelligence_assistant
```

Install dependencies:

```
pip install -r requirements.txt
```

---

# ▶️ Running the Application

Start the Streamlit app:

```
streamlit run app.py
```

The application will open in your browser.

---

# 🔑 API Key Setup

This project uses an **AI API key (Groq API)** for generating insights and suggestions.

## Local Development

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_api_key_here
```

Install dotenv:

```
pip install python-dotenv
```

Access it in Python:

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
```

---

## Streamlit Cloud Deployment

Go to **Streamlit App Settings → Secrets** and add:

```
GROQ_API_KEY = "your_api_key_here"
```

Access in code:

```python
import streamlit as st
api_key = st.secrets["GROQ_API_KEY"]
```

---

# 💬 Example Queries

Users can ask questions such as:

```
What are the top 5 products by revenue?
Show monthly sales trends
Which region has the highest revenue?
What is the average sales value?
Predict next month's revenue
```

The system will generate **charts, tables, and insights automatically**.

---

# 📊 Example Outputs

The assistant can generate:

* Revenue charts
* Product ranking analysis
* Regional performance comparison
* KPI summaries
* Executive business insights
* Downloadable analytics reports

---

# 🧠 Technologies Used

* **Python**
* **Streamlit**
* **Pandas**
* **Plotly**
* **Groq API**
* **ReportLab**

---

# 🔮 Future Improvements

Possible upgrades for the system:

* Chat history and conversation memory
* Forecasting and prediction models
* Anomaly detection
* PowerPoint report generation
* Voice query input
* Multi-dataset analysis
* Interactive dashboard filters

---

# 👨‍💻 Author

**Mohammed Kaif**

AI Business Intelligence Assistant Project
Developed as part of an **AI/Data Analytics Internship Project**

---

# ⭐ Project Goal

The goal of this project is to build an **AI-powered Business Intelligence Assistant** that allows organizations to analyze data through **natural language interaction instead of complex dashboards or queries**.

---

If you find this project useful, consider giving it a ⭐ on GitHub!
