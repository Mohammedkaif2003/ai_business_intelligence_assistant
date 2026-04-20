from dotenv import load_dotenv

from modules.app_secrets import get_secret
from modules.ai_service_new import get_groq_client

load_dotenv(override=False)

# Central Groq configuration so changes are in one place
GROQ_MODEL_NAME = "llama-3.3-70b-versatile"
GROQ_SUGGESTION_TEMPERATURE = 0.4


def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text


def _format_dataset_label(dataset_name) -> str:
    if not dataset_name:
        return "this dataset"

    label = str(dataset_name)
    label = label.rsplit(".", 1)[0]
    label = label.replace("_", " ").replace("-", " ").strip()
    return label.title() if label else "this dataset"


def _build_dataset_info(query, df, schema, dataset_name=None) -> str:
    """Create a rich textual summary of the dataset for the LLM."""
    sample_values = ""
    for col in schema.get("categorical_columns", [])[:3]:
        try:
            unique_vals = df[col].dropna().unique()[:5]
            sample_values += f"  {col}: {', '.join(str(v) for v in unique_vals)}\n"
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("build_dataset_info_sample_error", exc_info=True)
            continue

    dataset_label = _format_dataset_label(dataset_name)

    dataset_info = f"""
Active Dataset: {dataset_label}

Dataset Overview
Rows: {schema['rows']}
Columns: {schema['columns']}

Column Names:
{schema['column_names']}

Numeric Columns:
{schema['numeric_columns']}

Categorical Columns:
{schema['categorical_columns']}

Sample Category Values:
{sample_values}
"""
    return dataset_info


def suggest_business_questions(query, df, schema, dataset_name=None):
    """
    Use Groq to generate follow‑up business questions.

    This is intentionally kept as a separate, optional call because it can
    add noticeable latency and token usage.
    """
    client = get_groq_client()
    if not client:
        return "AI suggestion failed: Groq API key is not configured."

    dataset_info = _build_dataset_info(query, df, schema, dataset_name)
    dataset_label = _format_dataset_label(dataset_name)

    prompt = f"""You are a senior business intelligence analyst advising an executive.

The user just asked this question about their dataset:
"{query}"

The active dataset is:
"{dataset_label}"

Dataset Information:
{dataset_info}

Generate exactly 5 follow-up questions that a business executive would naturally ask next.

RULES:
- Each question must reference SPECIFIC column names from the dataset
- Include one question about trends over time (if date data exists)
- Include one question about rankings or top/bottom performers
- Include one question about comparisons between categories
- Include one predictive/forward-looking question
- Include one question about anomalies or outlier detection
- Make questions progressively deeper (start simple, end complex)
- Use the actual column names and category values where possible
- Keep each question short and easy to execute
- Prefer one analytic step per question
- Avoid requiring prior results, multiple separate comparisons, or extra assumptions
- Format as numbered list (1. 2. 3. 4. 5.)
- Each question should be self-contained and specific enough to get a direct answer
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior business analyst. Generate specific, "
                        "actionable follow-up questions using actual column names "
                        "from the dataset and keep them aligned to the active dataset."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=GROQ_SUGGESTION_TEMPERATURE,
            max_tokens=400,
        )

        return response.choices[0].message.content

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("suggest_business_questions_failed", exc_info=True)
        if _is_rate_limit_error(e):
            return "AI suggestion paused: Groq rate limit reached. Please wait a moment and try again."
        return f"AI suggestion failed: {str(e)}"

