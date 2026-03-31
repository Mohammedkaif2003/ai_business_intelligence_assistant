import re
from typing import Optional

import pandas as pd

from modules.dataset_analyzer import analyze_dataset


def clean_ai_response(text: str) -> str:
    """Remove HTML and extra spacing from an AI response."""
    from html import unescape

    if not text:
        return ""

    text = unescape(str(text))
    text = re.sub(r"</?[^>]+>", "", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)

    return text.strip()


def is_memory_query(query: str) -> bool:
    """Detect if the user is referring to previous results."""
    q = str(query).lower()
    return any(
        phrase in q
        for phrase in (
            "previous",
            "last result",
            "compare",
            "earlier",
            "difference",
        )
    )


def detect_simple_query(query: str, df: pd.DataFrame) -> Optional[str]:
    """
    Detect simple aggregation queries that can be answered without the LLM.

    Returns a Python expression using the dataframe `df` or None.
    """
    q = str(query).lower()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    for col in numeric_cols:
        col_lower = col.lower()
        if col_lower not in q:
            continue

        if "total" in q or "sum" in q or q.strip() == col_lower:
            return f"df['{col}'].sum()"
        if "average" in q or "mean" in q:
            return f"df['{col}'].mean()"
        if "max" in q or "highest" in q:
            return f"df['{col}'].max()"
        if "min" in q or "lowest" in q:
            return f"df['{col}'].min()"

    return None


def _tokenize_query_text(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", str(text).lower()))


def is_dataset_related_query(query: str, df: pd.DataFrame, schema: dict | None = None) -> bool:
    """
    Decide if a user query is about the active dataset vs. general chit‑chat.
    """
    q = str(query).strip().lower()
    if not q:
        return False

    analytics_keywords = {
        "sum",
        "total",
        "average",
        "avg",
        "mean",
        "max",
        "min",
        "highest",
        "lowest",
        "top",
        "bottom",
        "count",
        "trend",
        "compare",
        "difference",
        "distribution",
        "forecast",
        "predict",
        "growth",
        "decline",
        "increase",
        "decrease",
        "revenue",
        "sales",
        "profit",
        "cost",
        "region",
        "date",
        "month",
        "year",
        "department",
        "employee",
        "category",
        "product",
        "segment",
        "kpi",
        "metric",
        "show",
        "list",
        "group",
        "filter",
        "by",
        "across",
        "over",
        "outlier",
    }

    stopwords = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "for",
        "in",
        "on",
        "and",
        "or",
        "with",
        "me",
        "my",
        "please",
        "what",
        "which",
        "who",
        "when",
        "where",
        "why",
        "how",
        "tell",
        "give",
        "about",
        "from",
        "into",
        "than",
    }

    query_tokens = _tokenize_query_text(q)
    meaningful_tokens = query_tokens - stopwords

    # Memory / comparison queries are considered dataset‑related
    if is_memory_query(q):
        return True

    schema = schema or analyze_dataset(df)
    dataset_tokens: set[str] = set()

    for col in schema.get("column_names", []):
        dataset_tokens.update(_tokenize_query_text(col))

    for col in schema.get("numeric_columns", []):
        dataset_tokens.update(_tokenize_query_text(col))

    for col in schema.get("categorical_columns", [])[:5]:
        dataset_tokens.update(_tokenize_query_text(col))
        try:
            sample_values = df[col].dropna().astype(str).unique()[:10]
            for value in sample_values:
                dataset_tokens.update(_tokenize_query_text(value))
        except Exception:
            continue

    matched_dataset_terms = meaningful_tokens & dataset_tokens
    matched_analytics_terms = meaningful_tokens & analytics_keywords

    if matched_dataset_terms:
        return True

    if detect_simple_query(query, df):
        return True

    if "top" in q and len(df.columns) > 0:
        return True

    return len(matched_analytics_terms) >= 2 and len(meaningful_tokens) <= 8


def get_irrelevant_query_message(schema: dict) -> str:
    """Friendly message when a question is not about the dataset."""
    example_cols = ", ".join(schema.get("column_names", [])[:4])
    if example_cols:
        return (
            "That question does not look related to the current dataset. "
            f"Try asking about columns like {example_cols}."
        )
    return (
        "That question does not look related to the current dataset. "
        "Try asking about the uploaded columns or metrics."
    )


def generate_sidebar_question_ideas(df: pd.DataFrame, schema: dict) -> list[str]:
    """Generate example questions shown in the sidebar."""
    questions: list[str] = []

    numeric_cols = schema.get("numeric_columns", [])
    categorical_cols = schema.get("categorical_columns", [])
    datetime_cols = schema.get("datetime_columns", [])

    if numeric_cols and categorical_cols:
        questions.append(
            f"What is the total {numeric_cols[0]} by {categorical_cols[0]}?"
        )
        questions.append(
            f"Which {categorical_cols[0]} has the highest {numeric_cols[0]}?"
        )

    if len(numeric_cols) >= 2:
        questions.append(
            f"How does {numeric_cols[0]} compare with {numeric_cols[1]}?"
        )

    if datetime_cols and numeric_cols:
        questions.append(f"What is the trend of {numeric_cols[0]} over time?")
    elif "Date" in df.columns and numeric_cols:
        questions.append(f"Show the monthly trend of {numeric_cols[0]}.")

    if categorical_cols and numeric_cols:
        questions.append(
            f"Are there any outliers in {numeric_cols[0]} across {categorical_cols[0]}?"
        )

    if not questions and numeric_cols:
        questions.append(f"What is the average {numeric_cols[0]}?")
        questions.append(f"What is the maximum {numeric_cols[0]}?")

    if not questions:
        example_cols = schema.get("column_names", [])[:3]
        if example_cols:
            questions.append(f"Show records grouped by {example_cols[0]}.")
            questions.append(
                f"Summarize the dataset using {', '.join(example_cols)}."
            )

    return questions[:4]


def extract_follow_up_questions(raw_suggestions: str) -> list[str]:
    """Parse a numbered or bulleted list of follow‑up questions from the LLM."""
    questions: list[str] = []

    for line in str(raw_suggestions).split("\n"):
        cleaned = line.strip()
        if not cleaned:
            continue

        cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
        cleaned = cleaned.strip("- ").strip()

        lower = cleaned.lower()
        if lower.startswith("here are") or lower.startswith("follow-up questions"):
            continue
        if "?" not in cleaned:
            continue

        questions.append(cleaned)

    return questions


def generate_follow_up_fallbacks(query: str, df: pd.DataFrame, schema: dict) -> list[str]:
    """Build deterministic follow-up questions when the LLM output is empty or malformed."""
    follow_ups: list[str] = []

    numeric_cols = schema.get("numeric_columns", []) or df.select_dtypes(include="number").columns.tolist()
    categorical_cols = schema.get("categorical_columns", []) or df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = schema.get("datetime_columns", [])

    primary_metric = numeric_cols[0] if numeric_cols else None
    primary_category = categorical_cols[0] if categorical_cols else None
    secondary_category = categorical_cols[1] if len(categorical_cols) > 1 else primary_category
    primary_time = datetime_cols[0] if datetime_cols else ("Date" if "Date" in df.columns else None)

    if primary_metric and primary_category:
        follow_ups.append(f"What is the total {primary_metric} by {primary_category}?")
        follow_ups.append(f"Which {primary_category} has the highest {primary_metric}?")

    if primary_metric and primary_time:
        follow_ups.append(f"What is the trend of {primary_metric} over {primary_time}?")

    if primary_metric and secondary_category:
        follow_ups.append(f"How does {primary_metric} compare across {secondary_category}?")

    if primary_metric:
        follow_ups.append(f"Are there any outliers in {primary_metric}?")
        follow_ups.append(f"What is the forecast for {primary_metric} based on recent patterns?")

    if not follow_ups:
        follow_ups = generate_sidebar_question_ideas(df, schema)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in follow_ups:
        cleaned = str(item).strip()
        if not cleaned:
            continue
        if "?" not in cleaned:
            cleaned = f"{cleaned.rstrip('.')}?"
        if cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)

    return deduped[:5]


def enhance_query(query: str, df: pd.DataFrame) -> str:
    """Intelligently refine vague queries into more structured ones."""
    q = str(query).lower()

    columns = df.columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    # Generic "top" queries for any dataset
    if "top" in q:
        group_col = None
        metric_col = None

        for col in categorical_cols:
            if col.lower() in q:
                group_col = col
                break

        for col in numeric_cols:
            if col.lower() in q:
                metric_col = col
                break

        if not group_col and categorical_cols:
            group_col = categorical_cols[0]

        if not metric_col and numeric_cols:
            metric_col = numeric_cols[0]

        if group_col and metric_col:
            return f"Top 5 {group_col} by {metric_col}"

    return query


def add_date_filter(query: str, df: pd.DataFrame) -> str:
    """Try to enrich the query with a detected year or month filter."""
    q = str(query).lower()

    date_cols = [col for col in df.columns if "date" in col.lower()]
    if not date_cols:
        return query

    year_match = re.search(r"(20\d{2})", q)
    if year_match:
        year = year_match.group(1)
        return f"{query} for year {year}"

    months = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    for m in months:
        if m in q:
            return f"{query} for {m}"

    return query


def add_filters(query: str, df: pd.DataFrame) -> str:
    """
    Attempt to infer simple equality filters from values mentioned in the query.
    """
    q = str(query).lower()

    for col in df.columns:
        for val in df[col].astype(str).unique():
            if str(val).lower() in q:
                return f"{query} where {col} = '{val}'"

    return query

