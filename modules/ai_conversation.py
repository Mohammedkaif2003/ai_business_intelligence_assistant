import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
from modules.app_secrets import get_secret

load_dotenv()
import re
from html import unescape

_BULLET_PREFIX = re.compile(r"^\s*([-*•·]|\d+[.)])\s+")
_BOLD_HEADER = re.compile(r"\*\*(.+?)\*\*")
_HEADING_LINE = re.compile(r"^\s*#{1,6}\s+", flags=re.MULTILINE)
_KNOWN_SCAFFOLD = re.compile(
    r"^\s*(executive insight|key findings|business impact|"
    r"limitations|recommendations|summary|takeaways?|insights?|"
    r"analysis)\s*:\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def sanitize_ai_output(text: str) -> str:
    """Loosen sanitization to preserve helpful Markdown like bolding and lists, 
    while still cleaning up redundant labels and code fences."""
    if not text:
        return ""

    # Convert HTML entities and strip tags.
    text = unescape(str(text))
    text = re.sub(r"</?[^>]+>", "", text)
    text = text.replace("```", "")

    # Drop redundant section labels but keep the content.
    text = _KNOWN_SCAFFOLD.sub("", text)

    # We NO LONGER collapse everything into a single paragraph. 
    # We preserve lines to allow lists and paragraph breaks to work with st.markdown.
    return text.strip()
GROQ_API_KEY = get_secret("GROQ_API_KEY")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")

# ═══════════════════════════════════════════════════
#  SENIOR DATA ANALYST SYSTEM PROMPT
# ═══════════════════════════════════════════════════

ANALYST_SYSTEM_PROMPT = """You are a Senior Business Intelligence Analyst 
talking to a colleague. Answer in a professional, structured, and insightful manner.

FORMAT RULES:
- Use bullet points for lists and key findings to improve readability.
- Use **bold** to emphasize important metrics, trends, or insights.
- Use paragraph breaks to separate different ideas.
- Avoid large markdown headings (# / ##).
- Never use section labels like "Executive Insight:", "Summary:", etc. Just start with the answer.
- No HTML tags, no code fences, no tables (unless specifically requested).

CONTENT RULES:
- Reference specific numbers, columns, and categories from the data provided.
- Identify the "Why" behind the numbers (e.g., why a certain category is leading).
- Keep the response concise but comprehensive (~150 words max).
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


ANALYST_CONCISE_PROMPT = """You are a Senior Data Analyst and Data Visualization Engineer.

You receive a pandas DataFrame named `df` and a user question.
Your job is to:
1. Answer the question with specific numbers and insights (3-5 sentences).
2. Generate a Plotly chart that best visualises the answer.

ANALYSIS RULES:
- Reference actual column names and real values from the data.
- Identify trends, patterns, anomalies, or comparisons.
- Be direct — no filler phrases like "Based on the data" or "Here is the analysis".

VISUALIZATION RULES:
- ALWAYS generate a chart when the data has a visual angle.
- Use plotly.express (already imported as `px`) — do NOT import anything.
- Choose the best chart type automatically:
    Line chart for time series, bar chart for category comparisons,
    scatter for relationships, box for distributions, heatmap for intensity.
- Label axes clearly and add a descriptive title.
- Store the figure(s) in: charts = [fig]
- Optionally store a computed DataFrame in: result = ...

CODE RULES:
- Do NOT write `import` statements — px, pd, np are pre-loaded.
- Do NOT redefine `df`.
- Do NOT use print().
- Always define `charts = []` at the top of your code block.
- Always define `result = ...` somewhere in the code.

OUTPUT FORMAT (STRICT — follow exactly):

Insight:
<your 3-5 sentence analytical answer>

Code:
```python
charts = []
result = df.groupby('Category')['Value'].sum().reset_index()
fig = px.bar(result, x='Category', y='Value', title='Value by Category')
charts = [fig]
```
"""

# ── Helpers for splitting insight from code in the concise response ──────

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n?(.*?)```", re.DOTALL)


def _split_insight_and_code(raw_text: str) -> tuple[str, str]:
    """Split an AI response that may contain a fenced code block into
    (insight_prose, chart_code).  If no code block is found, chart_code
    is returned as an empty string."""
    if not raw_text:
        return "", ""

    code_match = _CODE_BLOCK_RE.search(raw_text)
    if not code_match:
        return raw_text.strip(), ""

    chart_code = code_match.group(1).strip()
    # Everything outside the code fence is the insight prose
    prose = _CODE_BLOCK_RE.sub("", raw_text).strip()
    # Strip the "Insight:" / "Code:" labels the prompt asks for
    prose = re.sub(r"(?i)^\s*(insight|code)\s*:\s*", "", prose, flags=re.MULTILINE).strip()
    return prose, chart_code


def generate_conversational_response(query, result, insight="", df=None, concise: bool = False):
    """Generate a professional AI response using Google Gemini (primary)
    with Groq LLaMA as fallback.

    Returns
    -------
    - When ``concise=False``: a plain sanitized string (narrative prose).
    - When ``concise=True``: a dict ``{"text": str, "chart_code": str}``
      where *text* is the sanitized insight paragraph and *chart_code*
      is executable Python (may be empty if the model didn't produce one).
    """

    # Build data summary (with optional dataset context)
    data_summary = _build_data_context(result, insight)

    # Add dataset preview if available
    if df is not None:
        try:
            df_preview = df.head(10).to_string()
            data_summary += f"\n\nFull Dataset Preview:\n{df_preview}"
        except Exception:
            pass

    prompt = f"""The user asked: "{query}"

Here is the analysis result:
{data_summary}

Analyze this data using your senior analyst framework. Be specific to THIS data — no generic responses."""

    # Choose the system prompt depending on concise flag
    system_prompt = ANALYST_CONCISE_PROMPT if concise else ANALYST_SYSTEM_PROMPT
    # Allow more tokens when the model is expected to produce code + insight
    max_tokens_gemini = 800 if concise else 350
    max_tokens_groq = 1000 if concise else 600

    raw_response = None

    # Try Google Gemini first
    if GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=system_prompt
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=max_tokens_gemini
                )
            )
            if response and response.text:
                raw_response = response.text
        except Exception:
            pass  # fallback

    # Fallback: Groq
    if raw_response is None and GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens_groq
            )
            raw_response = response.choices[0].message.content
        except Exception:
            pass

    if raw_response is None:
        fallback_text = (
            "I couldn't generate an AI response for this query right now — the "
            "language model didn't return a usable answer. Try rephrasing the "
            "question, or pointing it at a specific column or time range in the "
            "dataset."
        )
        return {"text": fallback_text, "chart_code": ""} if concise else fallback_text

    # ── Post-process depending on mode ────────────────────────────────
    if concise:
        prose, chart_code = _split_insight_and_code(raw_response)
        return {"text": sanitize_ai_output(prose), "chart_code": chart_code}
    else:
        return sanitize_ai_output(raw_response)


# ═════════════════════════════════════════════════════════════════════════════
# Narration-only mode (used by smart_analysis pipeline)
# ═════════════════════════════════════════════════════════════════════════════

_NARRATE_SYSTEM = """You are a Senior Business Intelligence Analyst.
You receive a user question and a PRE-COMPUTED analysis summary.
The numbers are already correct — do NOT recalculate or second-guess them.

Your only job is to explain the results in 3-5 natural, conversational sentences.
Reference the actual numbers given. Point out which values stand out and why
they matter from a business perspective.

RULES:
- No bullet points, no numbered lists, no markdown, no section headers.
- No phrases like "Based on the analysis" or "The data shows". Just start.
- Keep it under 100 words.
- Sound like a colleague explaining results over coffee."""


def narrate_result(query: str, computed_summary: str) -> str:
    """Ask the LLM to narrate a pre-computed analysis in natural prose.

    Unlike generate_conversational_response, this function never asks the
    model to do any computation — the numbers are already calculated by
    pandas and passed in via `computed_summary`.
    """
    prompt = f"""Question: "{query}"

Computed results:
{computed_summary}

Explain these results to a business colleague in 3-5 sentences."""

    # Try Groq first (user's preferred LLM)
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": _NARRATE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=250,
            )
            raw = response.choices[0].message.content
            if raw:
                return sanitize_ai_output(raw)
        except Exception:
            pass

    # Fallback: Google Gemini
    if GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=_NARRATE_SYSTEM,
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3, max_output_tokens=250,
                ),
            )
            if response and response.text:
                return sanitize_ai_output(response.text)
        except Exception:
            pass

    # If both LLMs fail, the computed summary is already human-readable
    return computed_summary

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
