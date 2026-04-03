import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modules.executive_summary import generate_executive_summary
from modules.groq_ai import suggest_business_questions
from modules.query_utils import extract_follow_up_questions, generate_follow_up_fallbacks
from modules.text_utils import clean_text


def format_metric_value(value):
    if isinstance(value, (int, float)):
        abs_value = abs(float(value))
        if abs_value >= 1_000_000_000:
            return f"{value / 1_000_000_000:,.2f}B"
        if abs_value >= 1_000_000:
            return f"{value / 1_000_000:,.2f}M"
        if abs_value >= 1_000:
            return f"{value:,.0f}"
        return f"{value:,.2f}"
    return str(value)


def augment_kpis_with_trends(kpis, dataframe):
    enhanced = []
    row_count = max(len(dataframe), 1)
    for index, kpi in enumerate(kpis):
        metric_value = kpi.get("total", 0)
        baseline = kpi.get("average", 0)
        if isinstance(metric_value, (int, float)) and isinstance(baseline, (int, float)) and baseline not in ("", 0):
            delta = ((float(metric_value) - float(baseline)) / max(abs(float(baseline)), 1)) * 100
            trend_label = "from dataset average"
        else:
            delta = ((index + 1) / row_count) * 100
            trend_label = "coverage signal"

        enhanced.append(
            {
                **kpi,
                "total": format_metric_value(metric_value),
                "average": format_metric_value(baseline) if baseline != "" else "N/A",
                "delta": round(delta, 1),
                "trend_label": trend_label,
            }
        )
    return enhanced


def generate_quick_insights(dataframe):
    insights = {
        "Highest Value Driver": "Not enough numeric data",
        "Lowest Performance Signal": "Not enough numeric data",
        "Key Anomaly": "No clear anomaly detected",
    }

    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    category_cols = dataframe.select_dtypes(exclude="number").columns.tolist()
    if not numeric_cols:
        return insights

    primary_metric = max(numeric_cols, key=lambda col: dataframe[col].fillna(0).sum())
    metric_sum = dataframe[primary_metric].fillna(0)

    if category_cols:
        primary_group = category_cols[0]
        grouped = dataframe.groupby(primary_group, dropna=False)[primary_metric].sum().sort_values(ascending=False)
        if not grouped.empty:
            insights["Highest Value Driver"] = f"{grouped.index[0]} leads {primary_metric} with {format_metric_value(grouped.iloc[0])}"
            insights["Lowest Performance Signal"] = f"{grouped.index[-1]} trails at {format_metric_value(grouped.iloc[-1])}"
    else:
        insights["Highest Value Driver"] = f"{primary_metric} totals {format_metric_value(metric_sum.sum())}"
        insights["Lowest Performance Signal"] = f"Lowest {primary_metric} value is {format_metric_value(metric_sum.min())}"

    std_dev = metric_sum.std()
    if std_dev and std_dev == std_dev and std_dev != 0:
        z_scores = (metric_sum - metric_sum.mean()) / std_dev
        if z_scores.abs().max() > 2:
            anomaly_idx = z_scores.abs().idxmax()
            insights["Key Anomaly"] = f"Row {anomaly_idx} spikes to {format_metric_value(metric_sum.loc[anomaly_idx])} in {primary_metric}"
        else:
            insights["Key Anomaly"] = f"{primary_metric} stays within a normal range for most rows"

    return insights


def summarize_report_history(history):
    insight_count = sum(1 for entry in history if entry.get("insight") or entry.get("ai_response"))
    chart_count = sum(len(entry.get("charts", [])) for entry in history)
    return {
        "analyses": len(history),
        "insights": insight_count,
        "charts": chart_count,
    }


def build_overview_hero_chart(dataframe):
    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    date_candidates = []
    for col in dataframe.columns:
        lowered = str(col).lower()
        if "date" in lowered or "month" in lowered or "year" in lowered or "quarter" in lowered:
            date_candidates.append(col)

    metric_col = max(numeric_cols, key=lambda col: dataframe[col].fillna(0).sum())

    for axis_col in date_candidates:
        try:
            grouped = dataframe.groupby(axis_col, dropna=False)[metric_col].sum().reset_index()
            if len(grouped) >= 2:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=grouped[axis_col],
                        y=grouped[metric_col],
                        mode="lines+markers",
                        name=metric_col,
                        line=dict(color="#60a5fa", width=3),
                        marker=dict(color="#22d3ee", size=8),
                    )
                )
                fig.update_layout(title=f"{metric_col} Trend by {axis_col}", height=360)
                return fig
        except Exception:
            continue

    category_cols = dataframe.select_dtypes(exclude="number").columns.tolist()
    for axis_col in category_cols:
        try:
            grouped = (
                dataframe.groupby(axis_col, dropna=False)[metric_col]
                .sum()
                .sort_values(ascending=False)
                .head(8)
                .reset_index()
            )
            if len(grouped) >= 2:
                fig = px.bar(
                    grouped,
                    x=axis_col,
                    y=metric_col,
                    color=metric_col,
                    color_continuous_scale=["#4338ca", "#6366f1", "#a78bfa"],
                    title=f"Top {axis_col} by {metric_col}",
                )
                fig.update_layout(height=360, coloraxis_showscale=False)
                return fig
        except Exception:
            continue

    return None


def is_error_like_text(value) -> bool:
    text = str(value).lower()
    error_markers = [
        "unsafe code detected",
        "unsupported code pattern",
        "code execution error",
        "traceback",
        "exception",
        "syntaxerror",
        "nameerror",
        "not defined",
        "could not generate ai report",
        "comparison failed",
        "comparison not supported",
        "need at least two results",
        "not applicable",
        "more data needed",
    ]
    return any(marker in text for marker in error_markers)


def result_type_label(result, chart_data):
    if chart_data is not None and isinstance(chart_data, pd.DataFrame) and not chart_data.empty:
        return "chartable_table"
    if isinstance(result, pd.DataFrame):
        return "dataframe"
    if isinstance(result, pd.Series):
        return "series"
    if isinstance(result, dict):
        return "dict"
    if isinstance(result, (int, float)):
        return "scalar"
    if isinstance(result, str):
        return "text"
    return type(result).__name__.lower()


def build_ai_summary_fallback(ai_response: str) -> list[str]:
    cleaned = clean_text(ai_response)
    if not cleaned:
        return []

    lines = [line.strip("- ").strip() for line in cleaned.splitlines() if line.strip()]
    summary = []
    for line in lines:
        lower = line.lower()
        if lower.endswith(":") or lower in {
            "executive insight",
            "key findings",
            "business impact",
            "limitations",
            "recommendations",
        }:
            continue
        summary.append(line)
        if len(summary) >= 3:
            break
    return summary


def build_result_history_entry(query, result, chart_data, intent_info, query_rejected):
    result_shape = None
    if isinstance(result, pd.DataFrame):
        result_shape = tuple(result.shape)
    elif isinstance(chart_data, pd.DataFrame):
        result_shape = tuple(chart_data.shape)

    key_columns = []
    if isinstance(result, pd.DataFrame):
        key_columns = [str(col) for col in result.columns[:4]]
    elif isinstance(chart_data, pd.DataFrame):
        key_columns = [str(col) for col in chart_data.columns[:4]]

    return {
        "query": query,
        "intent": intent_info.get("intent", "analysis"),
        "result_type": result_type_label(result, chart_data),
        "key_columns": key_columns,
        "chartable": bool(chart_data is not None and isinstance(chart_data, pd.DataFrame) and not chart_data.empty),
        "result_shape": result_shape,
        "query_rejected": query_rejected,
    }


def build_failure_message(query, intent_info, schema, rephrase_suggestions):
    intent_label = intent_info.get("intent", "analysis").replace("_", " ")
    message = f"I understood this as a {intent_label} request, but I could not answer it reliably with the current analysis path."
    if rephrase_suggestions:
        message += f" Try one of these instead: {rephrase_suggestions[0]}"
        if len(rephrase_suggestions) > 1:
            message += f" or {rephrase_suggestions[1]}"
    else:
        message += f" Try asking about columns like {', '.join(schema.get('column_names', [])[:3])}."
    return message


def build_summary_list(result, chart_data, query_rejected):
    if query_rejected:
        return []

    if is_error_like_text(result):
        return []

    summary_list = []

    try:
        if chart_data is not None and not chart_data.empty:
            summary_list = generate_executive_summary(chart_data)
        elif isinstance(result, pd.DataFrame) and not result.empty:
            numeric_cols = result.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                metric = numeric_cols[0]
                summary_list = [
                    f"The result includes {len(result):,} rows across {len(result.columns)} columns.",
                    f"Total {metric} is {result[metric].fillna(0).sum():,.2f}.",
                    f"Average {metric} is {result[metric].fillna(0).mean():,.2f}.",
                ]
            else:
                summary_list = [
                    f"The result includes {len(result):,} rows across {len(result.columns)} columns.",
                    f"Columns returned: {', '.join(str(col) for col in result.columns[:4])}.",
                ]
        elif isinstance(result, (int, float)):
            summary_list = [f"Result obtained: {result}"]
        elif isinstance(result, str):
            cleaned_result = str(result).strip()
            if cleaned_result:
                summary_list = [cleaned_result]
        elif isinstance(result, dict):
            summary_list = [f"{k}: {v}" for k, v in result.items() if not is_error_like_text(v)]
        elif isinstance(result, pd.Series):
            metric_name = result.name or "value"
            summary_list = [
                f"The result contains {len(result):,} {metric_name} entries.",
                f"Highest {metric_name} is {result.max():,.2f}." if pd.api.types.is_numeric_dtype(result) else "Series result generated with multiple values.",
                f"Lowest {metric_name} is {result.min():,.2f}." if pd.api.types.is_numeric_dtype(result) else "",
            ]
    except Exception as exc:
        summary_list = [f"Summary generation failed: {str(exc)}"]

    cleaned = [str(item).strip() for item in summary_list if item and not is_error_like_text(item)]
    return cleaned


def build_follow_up_suggestions(query, df, schema, dataset_name: str | None = None):
    try:
        raw_suggestions = suggest_business_questions(query, df, schema, dataset_name)
    except Exception as exc:
        raw_suggestions = f"AI suggestion failed: {str(exc)}"

    parsed = extract_follow_up_questions(raw_suggestions)
    simple_parsed = []
    for question in parsed:
        lowered = question.lower()
        if any(
            marker in lowered
            for marker in (
                "previous result",
                "previous one",
                "last result",
                "last two results",
                "compared to the overall average",
                "2 standard deviations",
                "if we assume",
                "consistently",
            )
        ):
            continue
        simple_parsed.append(question)

    if simple_parsed:
        return "\n".join(f"{idx}. {question}" for idx, question in enumerate(simple_parsed[:5], start=1))

    if parsed:
        return "\n".join(f"{idx}. {question}" for idx, question in enumerate(parsed[:5], start=1))

    fallback_questions = generate_follow_up_fallbacks(query, df, schema, dataset_name)
    return "\n".join(f"{idx}. {question}" for idx, question in enumerate(fallback_questions, start=1))


def build_graphable_query_suggestions(df, schema, dataset_name: str | None = None):
    fallback_questions = generate_follow_up_fallbacks("graph suggestions", df, schema, dataset_name)
    graphable = []
    for question in fallback_questions:
        lowered = question.lower()
        if any(token in lowered for token in ("trend", "compare", "total", "highest", "outlier", "forecast")):
            graphable.append(question)
    if not graphable:
        graphable = fallback_questions
    return graphable[:4]
