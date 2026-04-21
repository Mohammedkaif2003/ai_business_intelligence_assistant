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
    """Force the model's reply into flowing prose: strip HTML, code fences,
    markdown headers/bold, bullet glyphs, and well-known section labels.
    Even when the system prompt is followed loosely, the user-facing
    bubble should still look like a paragraph from a senior analyst."""
    if not text:
        return ""

    # Convert HTML entities and strip tags / fences.
    text = unescape(str(text))
    text = re.sub(r"</?[^>]+>", "", text)
    text = text.replace("```", "")

    # Drop markdown headings and known scaffolding labels entirely.
    text = _HEADING_LINE.sub("", text)
    text = _KNOWN_SCAFFOLD.sub("", text)

    # Unwrap **bold** to plain text (no visual emphasis in chat bubble).
    text = _BOLD_HEADER.sub(r"\1", text)

    # Strip leading bullet glyphs / numbered-list markers from each line and
    # collapse the result into a flowing paragraph.
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = _BULLET_PREFIX.sub("", raw_line).strip()
        if not line:
            continue
        cleaned_lines.append(line)

    # Join sentence-fragment lines into prose. Preserve paragraph breaks
    # only where the model emitted truly blank lines (already filtered),
    # so the result reads as one or two natural paragraphs.
    joined = " ".join(cleaned_lines)
    joined = re.sub(r"\s{2,}", " ", joined).strip()
    return joined
GROQ_API_KEY = get_secret("GROQ_API_KEY")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")

# ═══════════════════════════════════════════════════
#  SENIOR DATA ANALYST SYSTEM PROMPT
# ═══════════════════════════════════════════════════

ANALYST_SYSTEM_PROMPT = """You are a Senior Business Intelligence Analyst
talking to a colleague. Answer in natural, flowing prose — exactly the way
you would explain the result out loud. Your reply must read like one or two
short conversational paragraphs.

ABSOLUTE FORMAT RULES (these override any habit you have):
- Never use bullet points, dashes, asterisks, or numbered lists. Not even one.
- Never use markdown headings (# / ## / ###) or bold (**word**).
- Never use section labels like "Executive Insight:", "Key Findings:",
  "Business Impact:", "Summary:", "Takeaways:", "Recommendations:".
- Never start with phrases like "Here is the analysis", "Based on the data",
  "To analyze ...", "Let me break this down". Just start with the answer.
- No HTML tags, no code fences, no tables.

CONTENT RULES:
- Write in complete sentences. Connect ideas with words, not punctuation.
- Reference the specific numbers, columns, and categories from the data
  provided — never give generic textbook commentary.
- If something is genuinely uncertain, say so in one clause, not a section.
- Keep the whole answer under ~120 words unless the question clearly demands more.
"""

def _build_data_context(result, insight=""):
    """Build a rich but size-capped data summary for the AI to analyze."""
    data_summary = ""
    if isinstance(result, pd.DataFrame):
        stats = ""
        numeric_cols = result.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            # Cap to first 6 numeric columns to avoid massive describe output
            desc_cols = numeric_cols[:6]
            desc = result[desc_cols].describe().to_string()
            if len(desc) > 1200:
                desc = desc[:1200] + "\n..."
            stats = f"\nStatistical summary:\n{desc}"

        head_str = result.head(5).to_string(index=False)
        if len(head_str) > 1200:
            head_str = head_str[:1200] + "\n..."

        data_summary = f"""Data returned: DataFrame with {result.shape[0]} rows and {result.shape[1]} columns.
Columns: {', '.join(str(c) for c in result.columns[:15])}
First rows:
{head_str}
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
    import logging
    logger = logging.getLogger("ai_conversation")

    # Build data summary (with optional dataset context)
    data_summary = _build_data_context(result, insight)

    # Add dataset preview if available — cap size to avoid token blowout
    if df is not None:
        try:
            preview = df.head(5).to_string()
            if len(preview) > 1500:
                preview = preview[:1500] + "\n... (truncated)"
            data_summary += f"\n\nDataset Preview (first 5 rows):\n{preview}"
            data_summary += f"\n\nDataset columns: {', '.join(str(c) for c in df.columns)}"
            data_summary += f"\nDataset shape: {df.shape[0]} rows × {df.shape[1]} columns"
        except Exception:
            pass

    # Hard cap on overall prompt data to prevent token limit errors
    if len(data_summary) > 4000:
        data_summary = data_summary[:4000] + "\n... (truncated for brevity)"

    prompt = f"""The user asked: "{query}"

Here is the analysis result:
{data_summary}

Analyze this data using your senior analyst framework. Be specific to THIS data — no generic responses."""

    # Choose the system prompt depending on concise flag
    system_prompt = ANALYST_CONCISE_PROMPT if concise else ANALYST_SYSTEM_PROMPT
    # Allow more tokens when the model is expected to produce code + insight
    max_tokens_gemini = 1200 if concise else 500
    max_tokens_groq = 1500 if concise else 800

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
            # response.text raises ValueError if the response was blocked
            # by safety filters. Check candidates first.
            if response and response.candidates:
                candidate = response.candidates[0]
                if candidate.finish_reason.name in ("STOP", "MAX_TOKENS"):
                    try:
                        raw_response = response.text
                    except ValueError:
                        # Safety filter or empty response
                        logger.warning("Gemini returned but text access failed (safety filter?)")
                else:
                    logger.warning(
                        "Gemini response blocked: finish_reason=%s",
                        candidate.finish_reason.name,
                    )
            elif response:
                # No candidates at all — usually a safety block
                logger.warning("Gemini returned no candidates (likely safety block)")
        except Exception as exc:
            logger.warning("Gemini API call failed: %s", exc)

    # Fallback: Groq (primary model)
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
        except Exception as exc:
            logger.warning("Groq primary model failed: %s", exc)

    # Fallback: Groq (smaller/cheaper model with separate rate limits)
    if raw_response is None and GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens_groq
            )
            raw_response = response.choices[0].message.content
        except Exception as exc:
            logger.warning("Groq fallback model failed: %s", exc)

    if raw_response is None:
        fallback_text = (
            "The AI language model is temporarily unavailable — this is usually "
            "caused by API rate limits being reached. The data analysis and charts "
            "above are still valid. Please wait a minute and try again, or check "
            "that your API keys (GOOGLE_API_KEY / GROQ_API_KEY) are configured in "
            "the .env file."
        )
        return {"text": fallback_text, "chart_code": ""} if concise else fallback_text

    # ── Post-process depending on mode ────────────────────────────────
    if concise:
        prose, chart_code = _split_insight_and_code(raw_response)
        return {"text": sanitize_ai_output(prose), "chart_code": chart_code}
    else:
        return sanitize_ai_output(raw_response)

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
