from typing import Any

import pandas as pd
import plotly.express as px

from modules.app_logging import get_logger


MAX_CATEGORY_POINTS = 12
logger = get_logger("auto_visualizer")


def _copy_as_dataframe(data: Any) -> pd.DataFrame | None:
    if data is None:
        return None
    if isinstance(data, pd.Series):
        df = data.reset_index()
        if df.shape[1] == 2:
            df.columns = ["Category", data.name or "Value"]
        return df
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return None


def _format_axis_name(name: str) -> str:
    return str(name).replace("_", " ").title()


def _format_metric_value(value: Any, metric_name: str = "") -> str:
    if not pd.notna(value):
        return "N/A"
    metric_name = str(metric_name).lower()
    if any(token in metric_name for token in ("rate", "margin", "share", "percent", "pct")):
        return f"{float(value):.1f}%"
    if any(token in metric_name for token in ("revenue", "sales", "profit", "cost", "price", "amount")):
        return f"${float(value):,.2f}"
    return f"{float(value):,.2f}"


def _find_datetime_columns(df: pd.DataFrame) -> list[str]:
    datetime_cols = df.select_dtypes(include=["datetime", "datetime64"]).columns.tolist()
    for col in df.columns:
        lowered = str(col).lower()
        if col in datetime_cols:
            continue
        if any(token in lowered for token in ("date", "month", "year", "quarter", "time")):
            try:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().sum() >= max(2, len(df) // 2):
                    df[col] = parsed
                    datetime_cols.append(col)
            except Exception as exc:
                continue
    return datetime_cols


def _coerce_numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def _build_chart_summary(df: pd.DataFrame, x_col: str, y_col: str, chart_type: str) -> list[str]:
    summary: list[str] = []
    numeric_series = _coerce_numeric(df, y_col).dropna()
    if numeric_series.empty:
        return summary

    highest_idx = numeric_series.idxmax()
    lowest_idx = numeric_series.idxmin()
    summary.append(
        f"Highest {_format_axis_name(y_col)} is {_format_metric_value(df.loc[highest_idx, y_col], y_col)} at {df.loc[highest_idx, x_col]}."
    )
    if len(numeric_series) > 1:
        summary.append(
            f"Lowest {_format_axis_name(y_col)} is {_format_metric_value(df.loc[lowest_idx, y_col], y_col)} at {df.loc[lowest_idx, x_col]}."
        )

    if chart_type == "line" and len(numeric_series) >= 2:
        change = numeric_series.iloc[-1] - numeric_series.iloc[0]
        direction = "upward" if change > 0 else "downward" if change < 0 else "flat"
        summary.append(f"Overall trend is {direction} across the plotted period.")
    elif chart_type in {"bar", "grouped_bar", "stacked_bar"}:
        total = numeric_series.sum()
        summary.append(f"Total plotted {_format_axis_name(y_col)} is {_format_metric_value(total, y_col)}.")

    return summary[:3]


def _base_chart_payload(
    fig,
    chart_type: str,
    title: str,
    rationale: str,
    data: pd.DataFrame,
    x_col: str,
    y_cols: list[str],
    warnings: list[str] | None = None,
    summary_override: list[str] | None = None,
) -> dict:
    payload = {
        "figure": fig,
        "chart_type": chart_type,
        "title": title,
        "rationale": rationale,
        "data": data.reset_index(drop=True),
        "x_col": x_col,
        "y_cols": y_cols,
        "warnings": warnings or [],
        "summary": summary_override if summary_override is not None else _build_chart_summary(data, x_col, y_cols[0], chart_type),
    }
    return payload


def validate_chart_data(data: Any) -> tuple[pd.DataFrame | None, list[str]]:
    warnings: list[str] = []
    df = _copy_as_dataframe(data)
    if df is None:
        logger.warning("Chart validation failed: unsupported data type")
        return None, ["Charting is only supported for dataframe-like results."]
    if df.empty:
        logger.warning("Chart validation failed: empty dataset")
        return None, ["No rows are available for charting."]
    if len(df) < 2:
        logger.warning("Chart validation failed: fewer than 2 rows")
        return None, ["At least 2 rows are needed to draw a meaningful chart."]

    working_df = df.copy().reset_index(drop=True)
    numeric_cols = working_df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        for col in working_df.columns:
            coerced = pd.to_numeric(working_df[col], errors="coerce")
            if coerced.notna().sum() >= 2:
                working_df[col] = coerced
                numeric_cols.append(col)

    if not numeric_cols:
        logger.warning("Chart validation failed: no numeric metric")
        return None, ["No numeric metric was found for graphing."]

    valid_numeric_cols = [col for col in numeric_cols if working_df[col].notna().any()]
    if not valid_numeric_cols:
        logger.warning("Chart validation failed: numeric columns contain no values")
        return None, ["Numeric columns were found, but every plotted value is empty."]

    return working_df, warnings


def _prepare_dimension_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    datetime_cols = _find_datetime_columns(df)
    categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    categorical_cols = [col for col in categorical_cols if df[col].nunique(dropna=True) > 0]
    return datetime_cols, categorical_cols


def _trim_for_categories(df: pd.DataFrame, x_col: str, y_col: str) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if df[x_col].nunique(dropna=True) <= MAX_CATEGORY_POINTS:
        return df, warnings
    trimmed = df.sort_values(y_col, ascending=False).head(MAX_CATEGORY_POINTS).copy()
    warnings.append(f"Showing top {MAX_CATEGORY_POINTS} {x_col} values for readability.")
    return trimmed, warnings


def _apply_common_layout(fig, x_col: str, y_cols: list[str]):
    fig.update_layout(
        title_font_size=22,
        height=460,
        xaxis_title=_format_axis_name(x_col),
        yaxis_title=_format_axis_name(y_cols[0]) if len(y_cols) == 1 else "Value",
        showlegend=len(y_cols) > 1,
    )
    fig.update_xaxes(tickangle=-30 if x_col else 0)


def _build_line_chart(df: pd.DataFrame, x_col: str, y_col: str, warnings: list[str]) -> dict:
    plot_df = df[[x_col, y_col]].dropna().sort_values(x_col).copy()
    fig = px.line(
        plot_df,
        x=x_col,
        y=y_col,
        markers=True,
        template="plotly_white",
        color_discrete_sequence=["#38bdf8"],
        title=f"{_format_axis_name(y_col)} Trend Over {_format_axis_name(x_col)}",
    )
    _apply_common_layout(fig, x_col, [y_col])
    return _base_chart_payload(
        fig,
        "line",
        fig.layout.title.text,
        "Using a line chart because a time field and a numeric metric were detected.",
        plot_df,
        x_col,
        [y_col],
        warnings,
    )


def _build_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, warnings: list[str]) -> dict:
    plot_df, trim_warnings = _trim_for_categories(df[[x_col, y_col]].dropna().copy(), x_col, y_col)
    fig = px.bar(
        plot_df,
        x=x_col,
        y=y_col,
        color=y_col,
        text_auto=True,
        template="plotly_white",
        color_continuous_scale=["#2563eb", "#60a5fa", "#93c5fd"],
        title=f"{_format_axis_name(y_col)} by {_format_axis_name(x_col)}",
    )
    _apply_common_layout(fig, x_col, [y_col])
    fig.update_layout(coloraxis_showscale=False)
    return _base_chart_payload(
        fig,
        "bar",
        fig.layout.title.text,
        "Using a bar chart because a categorical split and a numeric metric were detected.",
        plot_df,
        x_col,
        [y_col],
        warnings + trim_warnings,
    )


def _build_pie_chart(df: pd.DataFrame, x_col: str, y_col: str, warnings: list[str]) -> dict | None:
    plot_df = df[[x_col, y_col]].dropna().copy()
    if len(plot_df) > 8:
        return None
    fig = px.pie(
        plot_df,
        names=x_col,
        values=y_col,
        template="plotly_white",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        title=f"{_format_axis_name(y_col)} Share by {_format_axis_name(x_col)}",
    )
    return _base_chart_payload(
        fig,
        "pie",
        fig.layout.title.text,
        "Using a pie chart because the breakdown has a small number of categories.",
        plot_df,
        x_col,
        [y_col],
        warnings,
    )


def _build_scatter_chart(df: pd.DataFrame, x_col: str, y_cols: list[str], warnings: list[str]) -> dict | None:
    if len(y_cols) < 2:
        return None
    plot_df = df[[y_cols[0], y_cols[1]]].dropna().copy()
    if len(plot_df) < 2:
        return None
    fig = px.scatter(
        plot_df,
        x=y_cols[0],
        y=y_cols[1],
        template="plotly_white",
        color_discrete_sequence=["#22c55e"],
        title=f"{_format_axis_name(y_cols[0])} vs {_format_axis_name(y_cols[1])}",
    )
    _apply_common_layout(fig, y_cols[0], [y_cols[1]])
    payload = _base_chart_payload(
        fig,
        "scatter",
        fig.layout.title.text,
        "Using a scatter plot because two numeric metrics are available for comparison.",
        plot_df,
        y_cols[0],
        [y_cols[1]],
        warnings,
        summary_override=[
            f"Comparing {_format_axis_name(y_cols[0])} against {_format_axis_name(y_cols[1])}.",
            f"{len(plot_df):,} data points are plotted.",
        ],
    )
    return payload


def _build_histogram(df: pd.DataFrame, y_col: str, warnings: list[str]) -> dict:
    plot_df = df[[y_col]].dropna().copy()
    fig = px.histogram(
        plot_df,
        x=y_col,
        nbins=min(max(len(plot_df) // 2, 5), 20),
        template="plotly_white",
        color_discrete_sequence=["#f59e0b"],
        title=f"Distribution of {_format_axis_name(y_col)}",
    )
    _apply_common_layout(fig, y_col, [y_col])
    payload = _base_chart_payload(
        fig,
        "histogram",
        fig.layout.title.text,
        "Using a histogram to show the spread of the primary numeric metric.",
        plot_df,
        y_col,
        [y_col],
        warnings,
        summary_override=[
            f"Median {_format_axis_name(y_col)} is {_format_metric_value(plot_df[y_col].median(), y_col)}.",
            f"Average {_format_axis_name(y_col)} is {_format_metric_value(plot_df[y_col].mean(), y_col)}.",
        ],
    )
    return payload


def _build_grouped_bar_chart(df: pd.DataFrame, x_col: str, y_cols: list[str], warnings: list[str]) -> dict | None:
    if len(y_cols) < 2:
        return None
    plot_df = df[[x_col] + y_cols[:2]].dropna(how="all").copy()
    if plot_df.empty:
        return None
    plot_df, trim_warnings = _trim_for_categories(plot_df, x_col, y_cols[0])
    melted = plot_df.melt(id_vars=[x_col], value_vars=y_cols[:2], var_name="Metric", value_name="Value")
    fig = px.bar(
        melted,
        x=x_col,
        y="Value",
        color="Metric",
        barmode="group",
        template="plotly_white",
        title=f"{_format_axis_name(y_cols[0])} vs {_format_axis_name(y_cols[1])} by {_format_axis_name(x_col)}",
    )
    _apply_common_layout(fig, x_col, y_cols[:2])
    payload = _base_chart_payload(
        fig,
        "grouped_bar",
        fig.layout.title.text,
        "Using a grouped bar chart because multiple numeric metrics can be compared across the same categories.",
        melted,
        x_col,
        y_cols[:2],
        warnings + trim_warnings,
        summary_override=[
            f"Comparing {_format_axis_name(y_cols[0])} and {_format_axis_name(y_cols[1])} across {_format_axis_name(x_col)}.",
            f"Showing {plot_df[x_col].nunique(dropna=True)} categories.",
        ],
    )
    return payload


def _build_stacked_bar_chart(df: pd.DataFrame, x_col: str, y_cols: list[str], warnings: list[str]) -> dict | None:
    if len(y_cols) < 2:
        return None
    plot_df = df[[x_col] + y_cols[:2]].dropna(how="all").copy()
    if plot_df.empty:
        return None
    plot_df, trim_warnings = _trim_for_categories(plot_df, x_col, y_cols[0])
    melted = plot_df.melt(id_vars=[x_col], value_vars=y_cols[:2], var_name="Metric", value_name="Value")
    fig = px.bar(
        melted,
        x=x_col,
        y="Value",
        color="Metric",
        barmode="stack",
        template="plotly_white",
        title=f"Stacked {_format_axis_name(y_cols[0])} and {_format_axis_name(y_cols[1])} by {_format_axis_name(x_col)}",
    )
    _apply_common_layout(fig, x_col, y_cols[:2])
    payload = _base_chart_payload(
        fig,
        "stacked_bar",
        fig.layout.title.text,
        "Using a stacked bar chart to show total composition across categories.",
        melted,
        x_col,
        y_cols[:2],
        warnings + trim_warnings,
        summary_override=[
            f"Combined view of {_format_axis_name(y_cols[0])} and {_format_axis_name(y_cols[1])}.",
            f"Stack heights show total contribution by {_format_axis_name(x_col)}.",
        ],
    )
    return payload


def chart_download_bytes(chart: dict) -> bytes:
    data = chart.get("data")
    if isinstance(data, pd.DataFrame):
        return data.to_csv(index=False).encode("utf-8")
    return b""


def _dedupe_suggestion_items(items: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen_questions: set[str] = set()
    for item in items:
        question = str(item.get("question", "")).strip()
        if not question or question in seen_questions:
            continue
        deduped.append(item)
        seen_questions.add(question)
    return deduped


def build_graph_follow_up_suggestions(chart: dict) -> list[dict]:
    data = chart.get("data")
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame()
    x_col = chart.get("x_col") or "category"
    y_cols = chart.get("y_cols", []) or []
    primary_metric = y_cols[0] if y_cols else "value"
    chart_type = str(chart.get("chart_type", "")).lower()

    if df.empty or not y_cols or not x_col or x_col == "category" or primary_metric == "value":
        return []

    datetime_cols = _find_datetime_columns(df.copy()) if not df.empty else []
    numeric_cols = df.select_dtypes(include="number").columns.tolist() if not df.empty else []
    categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist() if not df.empty else []
    alternate_categories = [col for col in categorical_cols if col != x_col]
    secondary_metric = next((col for col in numeric_cols if col != primary_metric), None)

    suggestions: list[dict] = []

    if alternate_categories:
        category = alternate_categories[0]
        suggestions.append(
            {
                "question": f"Create a bar chart of {primary_metric} by {category}.",
                "expected_output": "chart",
                "chart_type": "bar",
                "confidence": 0.95,
                "reason": f"{category} is available as another categorical split.",
            }
        )

    if datetime_cols:
        time_col = datetime_cols[0]
        trend_question = f"Plot the trend of {primary_metric} over {time_col}."
        if chart_type == "line":
            trend_question = f"Forecast the next values of {primary_metric} using {time_col}."
        suggestions.append(
            {
                "question": trend_question,
                "expected_output": "chart",
                "chart_type": "line",
                "confidence": 0.93 if chart_type != "line" else 0.89,
                "reason": f"{time_col} looks like a time field.",
            }
        )

    if x_col and primary_metric and x_col != "category":
        suggestions.append(
            {
                "question": f"Create a bar chart of the top 5 {x_col} by {primary_metric}.",
                "expected_output": "chart",
                "chart_type": "bar",
                "confidence": 0.94,
                "reason": "Ranking prompts typically produce chartable grouped data.",
            }
        )

    if secondary_metric:
        suggestions.append(
            {
                "question": f"Create a scatter plot of {primary_metric} versus {secondary_metric}.",
                "expected_output": "chart",
                "chart_type": "scatter",
                "confidence": 0.88,
                "reason": f"Both {primary_metric} and {secondary_metric} are numeric.",
            }
        )

    return _dedupe_suggestion_items(suggestions)[:5]


def build_graph_follow_up_questions(chart: dict) -> list[str]:
    return [item["question"] for item in build_graph_follow_up_suggestions(chart)]


def auto_visualize(data: Any) -> list[dict]:
    validated_df, validation_warnings = validate_chart_data(data)
    if validated_df is None:
        return []

    df = validated_df.copy()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    datetime_cols, categorical_cols = _prepare_dimension_columns(df)

    charts: list[dict] = []

    if datetime_cols:
        charts.append(_build_line_chart(df, datetime_cols[0], numeric_cols[0], validation_warnings.copy()))

    if categorical_cols:
        charts.append(_build_bar_chart(df, categorical_cols[0], numeric_cols[0], validation_warnings.copy()))

        grouped = _build_grouped_bar_chart(df, categorical_cols[0], numeric_cols, validation_warnings.copy())
        if grouped:
            charts.append(grouped)

        stacked = _build_stacked_bar_chart(df, categorical_cols[0], numeric_cols, validation_warnings.copy())
        if stacked:
            charts.append(stacked)

        pie_chart = _build_pie_chart(df, categorical_cols[0], numeric_cols[0], validation_warnings.copy())
        if pie_chart:
            charts.append(pie_chart)

    scatter = _build_scatter_chart(df, categorical_cols[0] if categorical_cols else numeric_cols[0], numeric_cols, validation_warnings.copy())
    if scatter:
        charts.append(scatter)

    charts.append(_build_histogram(df, numeric_cols[0], validation_warnings.copy()))

    deduped: list[dict] = []
    seen_titles: set[str] = set()
    for chart in charts:
        title = chart.get("title", "")
        if title and title not in seen_titles:
            deduped.append(chart)
            seen_titles.add(title)

    logger.info("Auto-visualizer produced %s chart option(s)", len(deduped[:5]))
    return deduped[:5]
