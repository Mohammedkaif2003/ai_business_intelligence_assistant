import time
from typing import Any

import pandas as pd

from services.llm_service import call_groq_json, safe_json_loads
from modules.query_utils import is_memory_query
from modules.query_optimizer import compress_dataset_context


def _build_dataset_context(df: pd.DataFrame, schema: dict, max_rows: int = 8) -> str:
    numeric_cols = schema.get("numeric_columns", []) or df.select_dtypes(include="number").columns.tolist()
    categorical_cols = schema.get("categorical_columns", []) or df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = schema.get("datetime_columns", []) or []

    sample_df = df.head(max_rows).copy()
    for col in sample_df.columns:
        sample_df[col] = sample_df[col].astype(str)

    numeric_profile_lines: list[str] = []
    for col in numeric_cols[:6]:
        try:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if series.empty:
                continue
            numeric_profile_lines.append(
                f"{col}: min={series.min():,.3f}, max={series.max():,.3f}, mean={series.mean():,.3f}, median={series.median():,.3f}"
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("numeric_profile_build_error", exc_info=True)
            continue

    categorical_profile_lines: list[str] = []
    for col in categorical_cols[:4]:
        try:
            top_values = (
                df[col]
                .astype(str)
                .fillna("")
                .value_counts(dropna=False)
                .head(5)
            )
            if top_values.empty:
                continue
            parts = [f"{idx} ({count})" for idx, count in top_values.items()]
            categorical_profile_lines.append(f"{col}: {', '.join(parts)}")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("categorical_profile_build_error", exc_info=True)
            continue

    return (
        f"Rows: {len(df)}\n"
        f"Columns: {len(df.columns)}\n"
        f"Column Names: {list(df.columns)}\n"
        f"Numeric Columns: {numeric_cols}\n"
        f"Categorical Columns: {categorical_cols}\n"
        f"Datetime Columns: {datetime_cols}\n"
        f"Numeric Profile:\n" + ("\n".join(numeric_profile_lines) if numeric_profile_lines else "None") + "\n"
        f"Categorical Top Values:\n" + ("\n".join(categorical_profile_lines) if categorical_profile_lines else "None") + "\n"
        f"Sample Rows:\n{sample_df.to_string(index=False)}"
    )


def _format_followups(items: list[str]) -> str:
    clean = [str(item).strip() for item in items if str(item).strip()]
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(clean[:5], start=1))


def generate_try_asking_suggestions(df: pd.DataFrame, schema: dict | None = None, dataset_name: str | None = None) -> list[str]:
    """
    Generate practical 'Try Asking' suggestions based on dataset structure.
    
    Uses rule-based logic to create relevant questions dynamically.
    Number of suggestions scales with dataset size (more columns = more suggestions).
    
    Args:
        df: DataFrame to analyze
        schema: Optional schema dict with column classifications
        dataset_name: Optional dataset name for context
    
    Returns:
        List of suggestion questions (scaled to dataset complexity)
    """
    if df.empty:
        return []
    
    schema = schema or {}
    numeric_cols = schema.get("numeric_columns", []) or df.select_dtypes(include="number").columns.tolist()
    categorical_cols = schema.get("categorical_columns", []) or df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = schema.get("datetime_columns", [])
    
    # Determine number of suggestions based on dataset size
    total_cols = len(df.columns)
    if total_cols <= 3:
        max_suggestions = 3
    elif total_cols <= 5:
        max_suggestions = 5
    else:
        max_suggestions = 8
    
    suggestions = []
    
    # Trend/total analysis
    if numeric_cols:
        primary_metric = numeric_cols[0]
        suggestions.append(f"What's the total {primary_metric}?")
        
        if len(numeric_cols) > 1:
            suggestions.append(f"Compare {numeric_cols[0]} vs {numeric_cols[1]}")
    
    # Category breakdown
    if categorical_cols and numeric_cols:
        suggestions.append(f"Which {categorical_cols[0]} has the highest {numeric_cols[0]}?")
        
        if len(categorical_cols) > 1:
            suggestions.append(f"Compare {categorical_cols[0]} vs {categorical_cols[1]} on {numeric_cols[0]}")
    
    # Top performers
    if numeric_cols:
        suggestions.append(f"Show top 10 by {numeric_cols[0]}")
    
    # Time-based if available
    if datetime_cols and numeric_cols:
        suggestions.append(f"Trend of {numeric_cols[0]} over {datetime_cols[0]}")
    
    # Low performers
    if numeric_cols and len(suggestions) < max_suggestions:
        suggestions.append(f"Bottom 5 performers by {numeric_cols[0]}")
    
    # Additional comparison
    if categorical_cols and numeric_cols and len(suggestions) < max_suggestions:
        suggestions.append(f"Average {numeric_cols[0]} by {categorical_cols[0]}")
    
    # Filter out None values and trim to max
    suggestions = [s for s in suggestions if s][:max_suggestions]
    
    return suggestions


def _is_question_like(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return True

    lowered = cleaned.lower()
    question_starts = (
        "what ",
        "how ",
        "why ",
        "when ",
        "where ",
        "which ",
        "who ",
        "can ",
        "could ",
        "should ",
        "would ",
        "is ",
        "are ",
        "do ",
        "does ",
        "did ",
    )
    return cleaned.endswith("?") or lowered.startswith(question_starts)


def _fallback_summary_from_response(response_text: str, max_items: int = 3) -> list[str]:
    cleaned = str(response_text or "").strip()
    if not cleaned:
        return []

    lines = []
    for raw_line in cleaned.replace("\r", "").splitlines():
        line = raw_line.strip("-•\t ")
        if not line:
            continue
        if line.endswith(":"):
            continue
        if _is_question_like(line):
            continue
        if line.lower() in {"executive insight", "key findings", "business impact", "limitations", "recommendations"}:
            continue
        lines.append(line)

    if not lines:
        sentences = [segment.strip() for segment in cleaned.replace("!", ".").split(".") if segment.strip()]
        lines = [sentence for sentence in sentences if not _is_question_like(sentence)]

    summary_items: list[str] = []
    for item in lines:
        if item not in summary_items:
            summary_items.append(item)
        if len(summary_items) >= max_items:
            break
    return summary_items


def _normalize_text_items(items: Any) -> list[str]:
    if items is None:
        return []

    if isinstance(items, str):
        text = items.strip()
        if not text:
            return []
        lines = [segment.strip("-•\t ") for segment in text.replace("\r", "").splitlines() if segment.strip()]
        return lines or [text]

    if isinstance(items, (list, tuple, set)):
        normalized: list[str] = []
        for value in items:
            value_text = str(value or "").strip()
            if value_text:
                normalized.append(value_text)
        return normalized

    text = str(items).strip()
    return [text] if text else []


def _clean_summary_items(summary_items: Any, response_text: str) -> list[str]:
    normalized_items = _normalize_text_items(summary_items)
    clean_items = []
    for item in normalized_items:
        text = str(item).strip()
        if not text or _is_question_like(text):
            continue
        clean_items.append(text)

    if clean_items:
        return clean_items[:5]

    return _fallback_summary_from_response(response_text)


def _clean_section_items(items: Any) -> list[str]:
    normalized_items = _normalize_text_items(items)
    clean_items: list[str] = []
    for item in normalized_items:
        text = str(item).strip()
        if not text or _is_question_like(text):
            continue
        clean_items.append(text)
    return clean_items[:5]


def _build_structured_response(payload: dict[str, Any]) -> dict[str, list[str]]:
    structured = {
        "EXECUTIVE INSIGHT": _clean_section_items(payload.get("executive_insight", [])),
        "KEY FINDINGS": _clean_section_items(payload.get("key_findings", [])),
        "BUSINESS IMPACT": _clean_section_items(payload.get("business_impact", [])),
        "RECOMMENDED NEXT STEPS": _clean_section_items(payload.get("recommended_next_steps", [])),
        "LIMITATIONS": _clean_section_items(payload.get("limitations", [])),
    }

    return {key: value for key, value in structured.items() if value}


def _coerce_and_validate_payload(payload: Any, raw_content: str) -> dict[str, Any]:
    """Ensure payload is a dict with expected keys and sensible types.

    If fields are missing or malformed, coerce them and reduce confidence.
    """
    # Preserve the original payload to detect which keys were present
    original_payload = payload if isinstance(payload, dict) else {}
    if not isinstance(payload, dict):
        payload = {}

    # Expected keys with default types
    keys_defaults = {
        "intent": "analysis",
        "query_rejected": False,
        "needs_clarification": False,
        "confidence": 0.0,
        "source_columns": [],
        "response": "",
        "summary": [],
        "follow_ups": [],
        "rephrases": [],
        "executive_insight": [],
        "key_findings": [],
        "business_impact": [],
        "recommended_next_steps": [],
        "limitations": [],
    }

    result: dict[str, Any] = {}
    malformed = False
    for k, default in keys_defaults.items():
        v = payload.get(k, default)
        # Basic type normalization
        if isinstance(default, list):
            if isinstance(v, (str, dict)):
                # If model returned a single string, split into lines
                v = _normalize_text_items(v)
            elif not isinstance(v, (list, tuple, set)):
                v = []
            else:
                v = [str(x).strip() for x in v if str(x).strip()]
        elif isinstance(default, bool):
            v = bool(v)
        elif isinstance(default, float) or k == "confidence":
            try:
                v = float(v)
            except Exception as exc:
                v = 0.0
        else:
            v = str(v or "").strip()

        result[k] = v
        # Heuristic: if required fields are empty or wrong type, mark malformed
        if k == "response" and not result[k]:
            malformed = True

    # If payload looked malformed, try to extract a fallback response from raw content
    if malformed:
        fallback_lines = _fallback_summary_from_response(raw_content, max_items=3)
        result["response"] = raw_content.strip() or ("\n".join(fallback_lines) if fallback_lines else "")
        # lower confidence to reflect uncertainty
        try:
            # If the original payload did not include a confidence field,
            # use a conservative default of 0.3; otherwise respect/clamp the provided value.
            if "confidence" not in original_payload:
                result["confidence"] = 0.3
            else:
                result["confidence"] = min(0.5, float(original_payload.get("confidence", 0.0)))
        except Exception as exc:
            result["confidence"] = 0.3

    # Clamp confidence
    try:
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("clamp_confidence_failed", exc_info=True)
        result["confidence"] = 0.0

    return result


def _augment_structured_response_from_data(df: pd.DataFrame, payload: dict[str, Any]) -> dict[str, list[str]]:
    """Create a lightweight, deterministic structured response from the dataset.

    This is used when the LLM returns minimal or empty structured fields.
    The output shape matches `_build_structured_response`.
    """
    structured: dict[str, list[str]] = {}

    # Executive insight: year with largest absolute variance sum
    try:
        if "variance" in df.columns and "year" in df.columns:
            by_year = df.groupby("year").variance.apply(lambda s: s.abs().sum())
            top_year = int(by_year.idxmax())
            structured.setdefault("EXECUTIVE INSIGHT", []).append(f"Year with largest absolute variance: {top_year}")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("failed_parsing_user_intent", exc_info=True)

    # Key findings: top 3 departments by absolute variance
    try:
        if "department" in df.columns and "variance" in df.columns:
            by_dept = df.groupby("department").variance.apply(lambda s: s.abs().sum()).sort_values(ascending=False)
            top_depts = list(by_dept.index[:3])
            structured.setdefault("KEY FINDINGS", []).append(f"Top departments by absolute variance: {', '.join(top_depts)}")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("failed_building_prompt", exc_info=True)

    # Business impact: departments with average large variance_pct
    try:
        if "department" in df.columns and "variance_pct" in df.columns:
            dept_avg = df.groupby("department").variance_pct.mean()
            worst = dept_avg.idxmax()
            structured.setdefault("BUSINESS IMPACT", []).append(f"{worst} shows the highest average variance percent")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("failed_extracting_result", exc_info=True)

    # Recommended next steps: simple, actionable items
    structured.setdefault("RECOMMENDED NEXT STEPS", []).extend(
        [
            "Investigate top departments with largest variance.",
            "Compare budget vs actual by quarter for the top departments.",
            "Implement monthly variance monitoring and root-cause analysis.",
        ]
    )

    # Limitations
    structured.setdefault("LIMITATIONS", []).append("Derived programmatically — may lack context the LLM could provide.")

    return structured


def _clean_list_field(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for item in values:
        text = str(item).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:5]


def _format_structured_response(structured_response: dict[str, list[str]]) -> str:
    if not structured_response:
        return ""

    lines: list[str] = []
    for heading, items in structured_response.items():
        lines.append(f"{heading}:")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip()


def generate_ai_dataset_questions(df: pd.DataFrame, schema: dict, dataset_name: str | None, logger=None) -> list[str]:
    dataset_label = str(dataset_name or "this dataset")
    numeric_cols = schema.get("numeric_columns", []) or df.select_dtypes(include="number").columns.tolist()
    categorical_cols = schema.get("categorical_columns", []) or df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = schema.get("datetime_columns", [])

    prompt = f"""You are a senior business intelligence analyst.

Create exactly 5 short, practical questions that a business user should ask next about the active dataset.

Dataset name:
{dataset_label}

Numeric columns:
{numeric_cols}

Categorical columns:
{categorical_cols}

Date/time columns:
{datetime_cols}

Rules:
- Use actual column names when possible.
- Questions should be specific, actionable, and easy to answer.
- Mix trend, comparison, top/bottom, segmentation, and anomaly style questions when possible.
- Do not include explanations.
- Return only valid JSON.

Return this schema exactly:
{{
  "questions": ["question 1", "question 2", "question 3", "question 4", "question 5"]
}}"""

    llm_result = call_groq_json(prompt, logger=logger)
    if not llm_result.get("ok"):
        return []

    try:
        payload = safe_json_loads(llm_result.get("content", "{}"))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("parse_llm_json_safe_failed", exc_info=True)
        return []

    questions = payload.get("questions", []) or []
    clean_questions: list[str] = []
    for question in questions:
        text = str(question).strip().strip("-").strip()
        if not text:
            continue
        if not text.endswith("?"):
            text += "?"
        if text not in clean_questions:
            clean_questions.append(text)
    return clean_questions[:5]


def _memory_compare_response(query: str, result_history: list[Any], result_history_details: list[dict[str, Any]]) -> dict[str, Any]:
    if len(result_history) < 2:
        return {
            "intent": "comparison",
            "query_rejected": False,
            "ai_response": "I need at least two previous results to compare. Please run another analysis first.",
            "summary_list": ["Comparison requires at least two historical results."],
            "suggestions": "",
            "rephrases": [],
            "result": "Need at least two results to compare.",
            "code": "# memory compare: insufficient history",
            "chart_data": None,
            "chart_figs": [],
            "insight": "",
            "status": "ok",
        }

    last = result_history[-1]
    prev = result_history[-2]
    last_meta = result_history_details[-1] if len(result_history_details) >= 1 else {}
    prev_meta = result_history_details[-2] if len(result_history_details) >= 2 else {}

    try:
        last_val = float(last)
        prev_val = float(prev)
        diff = last_val - prev_val
        growth = (diff / prev_val * 100) if prev_val != 0 else 0
        trend = "Increasing" if diff > 0 else "Decreasing" if diff < 0 else "No change"

        response = (
            "EXECUTIVE INSIGHT:\n"
            f"- Difference: {diff:,.2f}\n"
            f"- Growth: {growth:.2f}%\n\n"
            "KEY FINDINGS:\n"
            f"- Trend direction: {trend}\n"
            f"- Latest value: {last_val:,.2f}\n"
        )
        return {
            "intent": "comparison",
            "query_rejected": False,
            "ai_response": response,
            "summary_list": [f"Difference: {diff:,.2f}", f"Growth: {growth:.2f}%", f"Trend: {trend}"],
            "suggestions": "",
            "rephrases": [],
            "result": response,
            "code": "# memory compare: numeric diff",
            "chart_data": None,
            "chart_figs": [],
            "insight": "",
            "status": "ok",
        }
    except Exception as exc:
        fallback = (
            "I recognized this as a comparison request, but the last two results cannot "
            f"be compared directly ({prev_meta.get('result_type', 'unknown')} vs {last_meta.get('result_type', 'unknown')})."
        )
        return {
            "intent": "comparison",
            "query_rejected": False,
            "ai_response": fallback,
            "summary_list": [fallback],
            "suggestions": "",
            "rephrases": [],
            "result": fallback,
            "code": "# memory compare: unsupported types",
            "chart_data": None,
            "chart_figs": [],
            "insight": "",
            "status": "ok",
        }


def chat_handler(
    *,
    query: str,
    df: pd.DataFrame,
    schema: dict,
    dataset_name: str | None,
    logger,
    last_api_call_ts: float,
    min_call_interval_seconds: float = 1.0,
    result_history: list[Any] | None = None,
    result_history_details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Single-query orchestrator.

    Exactly one LLM call for non-memory queries.
    """
    result_history = result_history or []
    result_history_details = result_history_details or []

    if is_memory_query(query):
        return {
            **_memory_compare_response(query, result_history, result_history_details),
            "last_api_call_ts": last_api_call_ts,
        }

    elapsed = time.time() - (last_api_call_ts or 0)
    if elapsed < min_call_interval_seconds:
        wait_seconds = min_call_interval_seconds - elapsed
        if logger:
            logger.info("groq_rate_limit_wait", extra={"wait_seconds": round(wait_seconds, 2)})
        time.sleep(wait_seconds)

    dataset_context = _build_dataset_context(df, schema)
    # Keep context compact and scale down for large datasets.
    context_max_length = 1200 if len(df) <= 1000 else 900 if len(df) <= 10000 else 700
    dataset_context = compress_dataset_context(dataset_context, max_length=context_max_length)
    dataset_label = str(dataset_name or "Active Dataset")

    prompt = f"""Answer the user and classify intent in one JSON response.

Query: {query}
Dataset: {dataset_label}
Context: {dataset_context}

Return JSON with keys (use arrays for list fields):
intent, query_rejected, needs_clarification, confidence, source_columns, executive_insight,
key_findings, business_impact, recommended_next_steps, limitations, response, summary,
follow_ups, rephrases

Rules:
- Be concise, data-grounded, and specific.
- Use actual column names only.
- If unrelated, set query_rejected=true.
- Keep response under 120 words unless user asks for detail.
- Return empty arrays for list fields if no data applies.
- When the question concerns the dataset, include at least one item in `executive_insight` and `key_findings` when possible; otherwise add a brief note in `limitations` explaining why.
""".strip()

    if logger:
        logger.info("chat_handler_llm_call", extra={"query": query[:200]})

    llm_result = call_groq_json(prompt, logger=logger)
    now_ts = time.time()

    if not llm_result.get("ok"):
        error_text = llm_result.get("error", "Unknown API error")
        rate_limited = llm_result.get("rate_limited", False)

        if rate_limited:
            # Gracefully handle rate limits - return queued status instead of error
            return {
                "intent": "analysis",
                "query_rejected": False,
                "ai_response": "",
                "summary_list": [],
                "suggestions": "",
                "rephrases": [],
                "result": "",
                "code": "# queued due to rate limit",
                "chart_data": None,
                "chart_figs": [],
                "insight": "",
                "last_api_call_ts": now_ts,
                "status": "queued",  # Flag to indicate request is queued
                "confidence": 0.0,
                "source_columns": [],
            }
        else:
            message = f"AI request failed: {error_text}"

        return {
            "intent": "analysis",
            "query_rejected": False,
            "ai_response": message,
            "summary_list": ["The assistant could not complete this request right now."],
            "suggestions": "",
            "rephrases": [],
            "result": message,
            "code": "# single-call pipeline failed",
            "chart_data": None,
            "chart_figs": [],
            "insight": "",
            "last_api_call_ts": now_ts,
            "status": "error",
        }

    raw_content = llm_result.get("content", "{}")
    try:
        parsed = safe_json_loads(raw_content)
    except Exception as exc:
        parsed = {}

    payload = _coerce_and_validate_payload(parsed, raw_content)

    response_text = str(payload.get("response", "")).strip()
    summary = _clean_summary_items(payload.get("summary", []) or [], response_text)
    follow_ups = payload.get("follow_ups", []) or []
    rephrases = payload.get("rephrases", []) or []
    structured_response = _build_structured_response(payload)

    # If the LLM returned no structured content, augment deterministically using the dataset
    if not structured_response:
        try:
            augmented = _augment_structured_response_from_data(df, payload)
            # Only set keys that are missing
            for k, v in augmented.items():
                if k not in structured_response or not structured_response.get(k):
                    structured_response[k] = v
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("failed_handling_result_chunk", exc_info=True)
    source_columns = _clean_list_field(payload.get("source_columns", []) or [])
    confidence = payload.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except Exception as exc:
        confidence = 0.0

    if not response_text and structured_response:
        response_text = _format_structured_response(structured_response)
    if not response_text:
        response_text = "Analysis completed successfully."

    return {
        "intent": str(payload.get("intent", "analysis")),
        "query_rejected": bool(payload.get("query_rejected", False)),
        "ai_response": response_text,
        "summary_list": summary[:5],
        "suggestions": _format_followups([str(item) for item in follow_ups]),
        "rephrases": [str(item).strip() for item in rephrases if str(item).strip()][:3],
        "result": response_text,
        "structured_response": structured_response,
        "confidence": confidence,
        "source_columns": source_columns,
        "code": "# single-call chat pipeline",
        "chart_data": None,
        "chart_figs": [],
        "insight": "",
        "last_api_call_ts": now_ts,
        "status": "ok",
    }
