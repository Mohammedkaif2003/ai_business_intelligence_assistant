import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
from modules.app_secrets import get_secret
from groq import Groq

load_dotenv(override=True)
import re
from html import unescape

def sanitize_ai_output(text: str) -> str:
    if not text:
        return ""

    # Convert HTML entities
    text = unescape(str(text))

    # Remove ALL HTML tags
    text = re.sub(r'</?[^>]+>', '', text)

    # Remove weird leftover formatting
    text = text.replace("```", "")

    return text.strip()
def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text

# ═══════════════════════════════════════════════════
#  SENIOR DATA ANALYST SYSTEM PROMPT
# ═══════════════════════════════════════════════════

ANALYST_SYSTEM_PROMPT = """You are a Senior Business Intelligence Analyst.

You MUST strictly follow the output format below.

----------------------------------------
OUTPUT FORMAT (MANDATORY)
----------------------------------------

EXECUTIVE INSIGHT:
- Point 1
- Point 2

KEY FINDINGS:
- Point 1
- Point 2

BUSINESS IMPACT:
- Point 1
- Point 2

LIMITATIONS:
- Only if necessary (1–2 points)

RECOMMENDATIONS:
- Only if supported by data

----------------------------------------
STRICT RULES
----------------------------------------

- ALWAYS include ALL sections
- NEVER skip any section
- Use ONLY bullet points
- DO NOT write paragraphs
- DO NOT change section names
- DO NOT add extra sections
- Keep it concise and data-driven

IMPORTANT:
- Do NOT return HTML tags (no <div>, <span>, etc.)
- Return only clean plain text or markdown
- Use bullet points instead of HTML formatting
"""

def _build_data_context(result, insight=""):
    """Build a rich data summary for the AI to analyze."""
    data_summary = ""
    if isinstance(result, pd.DataFrame):
        numeric_cols = list(result.select_dtypes(include="number").columns[:6])
        stats = ""
        if len(numeric_cols) > 0:
            desc = result[numeric_cols].describe().round(2).to_string()
            stats = f"\nNumeric summary:\n{desc}"

        data_summary = f"""Data returned: DataFrame with {result.shape[0]} rows and {result.shape[1]} columns.
Columns: {', '.join(str(c) for c in result.columns)}
First rows:
{result.head(3).to_string(index=False)}
{stats}
"""
    elif isinstance(result, pd.Series):
        data_summary = f"""Data returned: Series with {len(result)} values.
Name: {result.name}
{result.head(6).to_string()}
"""
    elif isinstance(result, str):
        data_summary = f"Result: {result[:350]}"
    else:
        data_summary = f"Result: {str(result)[:350]}"

    if insight:
        data_summary += f"\nPreliminary insight: {insight}"

    return data_summary


def generate_conversational_response(query, result, insight="", df=None):
    """
    Generate a professional, rigorous AI response using Groq.
    """
    # 🔹 Build data summary (with optional dataset context)
    data_summary = _build_data_context(result, insight)

    # 🔹 Add dataset preview if available (FIX)
    if df is not None:
        try:
            df_preview = df.head(3).to_string()
            data_summary += f"\n\nFull Dataset Preview:\n{df_preview}"
        except Exception:
            pass

    prompt = f"""The user asked: "{query}"

Here is the analysis result:
{data_summary}

Analyze this data using your senior analyst framework. Be specific to THIS data — no generic responses."""
    groq_api_key = get_secret("GROQ_API_KEY")
    if groq_api_key:
        try:
            client = Groq(api_key=groq_api_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.15,
                max_tokens=220,
            )
            if response and response.choices:
                return sanitize_ai_output(response.choices[0].message.content)
        except Exception as e:
            if _is_rate_limit_error(e):
                return (
                    "EXECUTIVE INSIGHT\n"
                    "- AI response paused because Groq rate limit was reached.\n\n"
                    "KEY FINDINGS\n"
                    "- This is temporary and not related to your dataset quality.\n\n"
                    "BUSINESS IMPACT\n"
                    "- Follow-up analysis is delayed until the limit resets.\n\n"
                    "LIMITATIONS\n"
                    "- Groq API returned HTTP 429 Too Many Requests.\n\n"
                    "RECOMMENDATIONS\n"
                    "- Wait 30-60 seconds and run the same query again."
                )

    return """EXECUTIVE INSIGHT
    - Unable to generate AI response for this query.

    KEY FINDINGS
    - The system could not process the result properly.

    BUSINESS IMPACT
    - No actionable insights available.

    LIMITATIONS
    - This may be due to insufficient data or unclear query.

    RECOMMENDATIONS
    - Try rephrasing your question or selecting specific columns."""
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

    groq_api_key = get_secret("GROQ_API_KEY")
    if groq_api_key:
        try:
            client = Groq(api_key=groq_api_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.15,
                max_tokens=80,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if _is_rate_limit_error(e):
                return "I hit a temporary Groq rate limit (HTTP 429). Please wait about a minute and try again."
    return (
        f"I had some trouble analyzing that. Could you try "
        f"rephrasing your question? For example, try asking about "
        f"specific columns or simpler aggregations."
    )
