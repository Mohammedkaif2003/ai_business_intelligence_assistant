import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY", None)

# ═══════════════════════════════════════════════════
#  SENIOR DATA ANALYST SYSTEM PROMPT
# ═══════════════════════════════════════════════════

ANALYST_SYSTEM_PROMPT = """You are a senior Data Analyst and BI Engineer.

Your task is to generate a HIGH-QUALITY, INDUSTRY-LEVEL analytics report from a CSV dataset.
DO NOT produce generic AI summaries. Your output must be precise, critical, and data-driven.

----------------------------------------
🔍 1. DATA VALIDATION (MANDATORY)
----------------------------------------
- Inspect dataset structure
- Identify missing values, ambiguous columns (e.g., 'Amount'), and data inconsistencies
- Clearly state if an 'Amount' column indicates Revenue, Profit, or is Unknown
- If the column's meaning is unclear → DO NOT assume
- If dataset is incomplete → explicitly say so

----------------------------------------
📊 2. CORRECT ANALYSIS REQUIREMENTS
----------------------------------------
A. Category Analysis
- Aggregate by category
- Rank categories correctly
- Calculate % contribution
- Identify concentration risk

B. Top 10% Products (STRICT)
- Compute actual percentile (90th percentile)
- Define threshold clearly
- Filter products ABOVE threshold
- Do NOT just list top rows

----------------------------------------
📈 3. VISUALIZATION RULES
----------------------------------------
- Specify meaningful axes when referencing charts (e.g., "Category vs Revenue")
- NO "index vs index"
- Ensure proper labels, correct scaling, and clean alignment are recommended

----------------------------------------
🧠 4. ANALYTICAL THINKING
----------------------------------------
For each analysis, include:
A. Data Validation
B. Key Findings
C. What Cannot Be Concluded
D. Business Interpretation
E. Risks (e.g., concentration risk)
F. Recommendations (ONLY if justified)

----------------------------------------
⚠️ 5. STRICT RULES
----------------------------------------
- DO NOT confuse revenue and profit
- DO NOT assume missing data
- DO NOT generate fake insights
- DO NOT recommend discontinuation without margin/context

----------------------------------------
📦 6. OUTPUT FORMAT
----------------------------------------
Respond in a clean, executive style structure. Use highly professional language avoiding redundant filler such as "Based on the data..."
"""


def _build_data_context(result, insight=""):
    """Build a rich data summary for the AI to analyze."""
    data_summary = ""
    if isinstance(result, pd.DataFrame):
        stats = ""
        numeric_cols = result.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            desc = result[numeric_cols].describe().to_string()
            stats = f"\nStatistical summary:\n{desc}"

        data_summary = f"""Data returned: DataFrame with {result.shape[0]} rows and {result.shape[1]} columns.
Columns: {', '.join(str(c) for c in result.columns)}
First rows:
{result.head(8).to_string(index=False)}
{stats}
"""
    elif isinstance(result, pd.Series):
        data_summary = f"""Data returned: Series with {len(result)} values.
Name: {result.name}
{result.head(15).to_string()}
"""
    elif isinstance(result, str):
        data_summary = f"Result: {result[:800]}"
    else:
        data_summary = f"Result: {str(result)[:800]}"

    if insight:
        data_summary += f"\nPreliminary insight: {insight}"

    return data_summary


def generate_conversational_response(query, result, insight=""):
    """
    Generate a professional, rigorous AI response using Google Gemini
    (primary) with Groq LLaMA as fallback.
    """

    data_summary = _build_data_context(result, insight)

    prompt = f"""The user asked: "{query}"

Here is the analysis result:
{data_summary}

Analyze this data using your senior analyst framework. Be specific to THIS data — no generic responses."""

    # Try Google Gemini first (deeper analysis capability)
    if GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=ANALYST_SYSTEM_PROMPT
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=600
                )
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            pass  # Fall through to Groq

    # Fallback: Groq LLaMA
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    return ""


def generate_greeting(dataset_name="", row_count=0, col_count=0):
    """Generate a professional greeting when the user first loads a dataset."""

    if row_count > 0:
        return (
            f"📊 **Dataset loaded: {dataset_name}** — "
            f"**{row_count:,} rows** × **{col_count} columns**. "
            f"Ready for analysis. Ask me about trends, distributions, "
            f"top performers, comparisons, or forecasts."
        )
    return "📊 Upload a dataset and I'll provide professional-grade analysis."


def generate_error_response(query, error_text):
    """Generate a helpful response when the analysis fails."""

    prompt = f"""The user asked: "{query}"
But the analysis code failed with error: "{error_text[:300]}"

Write a SHORT, professional message (2-3 sentences) that:
1. Acknowledges the question
2. Explains simply what went wrong (no technical jargon)
3. Suggests how to rephrase the question

Keep it helpful and direct. Under 60 words."""

    # Try Gemini first
    if GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception:
            pass

    # Fallback: Groq
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    return (
        f"I had some trouble analyzing that. Could you try "
        f"rephrasing your question? For example, try asking about "
        f"specific columns or simpler aggregations."
    )
