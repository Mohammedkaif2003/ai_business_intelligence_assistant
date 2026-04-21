import re
from typing import Any

import pandas as pd
import plotly.express as px

from modules.app_logging import get_logger


MAX_CATEGORY_POINTS = 12
logger = get_logger("auto_visualizer")

# Unified palette — one primary accent + supporting shades for multi-series
PRIMARY       = "#4F46E5"
PRIMARY_SOFT  = "#818CF8"
SECONDARY     = "#10B981"
TERTIARY      = "#F59E0B"
SERIES_PALETTE = [PRIMARY, SECONDARY, TERTIARY, "#EC4899", "#06B6D4", "#8B5CF6"]
SEQUENTIAL    = ["#EEF2FF", "#C7D2FE", "#818CF8", "#4F46E5", "#3730A3"]


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
            except Exception:
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
        title=dict(font=dict(size=18, family="Manrope, Segoe UI, sans-serif")),
        height=460,
        xaxis_title=_format_axis_name(x_col),
        yaxis_title=_format_axis_name(y_cols[0]) if len(y_cols) == 1 else "Value",
        showlegend=len(y_cols) > 1,
        margin=dict(l=70, r=30, t=60, b=70),
        font=dict(family="Manrope, Segoe UI, sans-serif", size=12),
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor=PRIMARY_SOFT,
            font=dict(color="#F8FAFC", family="Manrope, Segoe UI, sans-serif"),
        ),
    )
    fig.update_xaxes(
        tickangle=-30 if x_col else 0,
        showgrid=False,
        showline=True,
        linecolor="rgba(148, 163, 184, 0.25)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.12)",
        gridwidth=1,
        zerolinecolor="rgba(148, 163, 184, 0.18)",
    )


def _build_line_chart(df: pd.DataFrame, x_col: str, y_col: str, warnings: list[str]) -> dict:
    plot_df = df[[x_col, y_col]].dropna().sort_values(x_col).copy()
    fig = px.line(
        plot_df,
        x=x_col,
        y=y_col,
        markers=True,
        template="plotly_white",
        color_discrete_sequence=[PRIMARY],
        title=f"{_format_axis_name(y_col)} Trend Over {_format_axis_name(x_col)}",
    )
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8, line=dict(width=2, color="#FFFFFF")),
        hovertemplate=f"<b>%{{x}}</b><br>{_format_axis_name(y_col)}: %{{y:,.2f}}<extra></extra>",
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
    plot_df = plot_df.sort_values(y_col, ascending=False)
    # Distinct color per bar by treating x as categorical — much more vibrant than
    # a continuous scale, which collapses to a single color when values are equal.
    fig = px.bar(
        plot_df,
        x=x_col,
        y=y_col,
        color=x_col,
        template="plotly_white",
        color_discrete_sequence=SERIES_PALETTE,
        title=f"{_format_axis_name(y_col)} by {_format_axis_name(x_col)}",
    )
    fig.update_traces(
        texttemplate="%{y:,.0f}",
        textposition="outside",
        textfont=dict(size=11, color="#E2E8F0"),
        cliponaxis=False,
        marker=dict(line=dict(color="#FFFFFF", width=1)),
        hovertemplate=f"<b>%{{x}}</b><br>{_format_axis_name(y_col)}: %{{y:,.2f}}<extra></extra>",
    )
    _apply_common_layout(fig, x_col, [y_col])
    fig.update_layout(showlegend=False, bargap=0.28)
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
        hole=0.45,
        template="plotly_white",
        color_discrete_sequence=SERIES_PALETTE,
        title=f"{_format_axis_name(y_col)} Share by {_format_axis_name(x_col)}",
    )
    fig.update_traces(
        textinfo="percent+label",
        textposition="outside",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
        hovertemplate=f"<b>%{{label}}</b><br>{_format_axis_name(y_col)}: %{{value:,.2f}}<br>Share: %{{percent}}<extra></extra>",
    )
    fig.update_layout(
        title=dict(font=dict(size=18, family="Manrope, Segoe UI, sans-serif")),
        font=dict(family="Manrope, Segoe UI, sans-serif", size=12),
        margin=dict(l=30, r=30, t=60, b=30),
        showlegend=True,
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
        color_discrete_sequence=[SECONDARY],
        title=f"{_format_axis_name(y_cols[0])} vs {_format_axis_name(y_cols[1])}",
    )
    fig.update_traces(
        marker=dict(size=10, opacity=0.78, line=dict(width=1, color="#FFFFFF")),
        hovertemplate=f"{_format_axis_name(y_cols[0])}: %{{x:,.2f}}<br>{_format_axis_name(y_cols[1])}: %{{y:,.2f}}<extra></extra>",
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
        color_discrete_sequence=[PRIMARY],
        title=f"Distribution of {_format_axis_name(y_col)}",
    )
    fig.update_traces(
        marker=dict(
            color=PRIMARY,
            line=dict(width=1.5, color="#FFFFFF"),
        ),
        hovertemplate=f"Range: %{{x}}<br>Count: %{{y}}<extra></extra>",
    )
    _apply_common_layout(fig, y_col, [y_col])
    fig.update_layout(bargap=0.08, yaxis_title="Count", showlegend=False)
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
        color_discrete_sequence=[PRIMARY, SECONDARY],
        title=f"{_format_axis_name(y_cols[0])} vs {_format_axis_name(y_cols[1])} by {_format_axis_name(x_col)}",
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f}<extra></extra>")
    _apply_common_layout(fig, x_col, y_cols[:2])
    fig.update_layout(bargap=0.22)
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
        color_discrete_sequence=[PRIMARY, SECONDARY],
        title=f"Stacked {_format_axis_name(y_cols[0])} and {_format_axis_name(y_cols[1])} by {_format_axis_name(x_col)}",
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f}<extra></extra>")
    _apply_common_layout(fig, x_col, y_cols[:2])
    fig.update_layout(bargap=0.22)
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


def _build_boxplot(df: pd.DataFrame, y_col: str, x_col: str | None, warnings: list[str]) -> dict:
    """Box-and-whisker plot — optionally grouped by a categorical column."""
    import plotly.graph_objects as go

    if x_col and x_col in df.columns and df[x_col].nunique(dropna=True) <= MAX_CATEGORY_POINTS:
        plot_df = df[[x_col, y_col]].dropna().copy()
        fig = px.box(
            plot_df,
            x=x_col,
            y=y_col,
            color=x_col,
            template="plotly_white",
            color_discrete_sequence=SERIES_PALETTE,
            title=f"Distribution of {_format_axis_name(y_col)} by {_format_axis_name(x_col)}",
        )
        x_label = x_col
    else:
        plot_df = df[[y_col]].dropna().copy()
        fig = px.box(
            plot_df,
            y=y_col,
            template="plotly_white",
            color_discrete_sequence=[PRIMARY],
            title=f"Distribution of {_format_axis_name(y_col)}",
        )
        x_label = y_col

    fig.update_traces(
        marker=dict(size=5, opacity=0.6),
        boxmean="sd",
    )
    _apply_common_layout(fig, x_label, [y_col])
    fig.update_layout(showlegend=False)

    numeric_series = pd.to_numeric(plot_df[y_col], errors="coerce").dropna()
    summary = [
        f"Median {_format_axis_name(y_col)} is {_format_metric_value(numeric_series.median(), y_col)}.",
        f"IQR spans {_format_metric_value(numeric_series.quantile(0.25), y_col)} to {_format_metric_value(numeric_series.quantile(0.75), y_col)}.",
    ]
    return _base_chart_payload(
        fig, "boxplot", fig.layout.title.text,
        "Using a box plot to show the median, quartiles, and potential outliers.",
        plot_df, x_label, [y_col], warnings,
        summary_override=summary,
    )


def _build_heatmap(df: pd.DataFrame, numeric_cols: list[str], warnings: list[str]) -> dict | None:
    """Correlation heatmap across all numeric columns (needs >= 2)."""
    if len(numeric_cols) < 2:
        return None

    corr_cols = numeric_cols[:8]  # cap at 8 to keep the chart readable
    corr_df = df[corr_cols].apply(pd.to_numeric, errors="coerce")
    corr_matrix = corr_df.corr()
    if corr_matrix.empty:
        return None

    fig = px.imshow(
        corr_matrix,
        text_auto=".2f",
        color_continuous_scale=["#312E81", "#4F46E5", "#818CF8", "#C7D2FE",
                                "#FDE68A", "#F59E0B", "#DC2626"],
        aspect="auto",
        template="plotly_white",
        title="Correlation Heatmap",
    )
    fig.update_layout(
        title=dict(font=dict(size=18, family="Manrope, Segoe UI, sans-serif")),
        height=520,
        margin=dict(l=70, r=30, t=60, b=70),
        font=dict(family="Manrope, Segoe UI, sans-serif", size=12),
    )

    # Find strongest correlation (excluding self-correlations)
    import numpy as np
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    tri = corr_matrix.where(mask)
    max_corr = tri.stack().abs().idxmax() if not tri.stack().empty else None
    summary = []
    if max_corr:
        val = corr_matrix.loc[max_corr[0], max_corr[1]]
        summary.append(f"Strongest correlation: {_format_axis_name(max_corr[0])} ↔ {_format_axis_name(max_corr[1])} ({val:.2f}).")
    summary.append(f"Showing {len(corr_cols)} numeric columns.")

    return _base_chart_payload(
        fig, "heatmap", "Correlation Heatmap",
        "Using a heatmap to show the strength of linear relationships between numeric variables.",
        corr_matrix.reset_index().rename(columns={"index": "Variable"}),
        "Variable", corr_cols[:1], warnings,
        summary_override=summary,
    )


def _build_outlier_chart(df: pd.DataFrame, y_col: str, x_col: str | None, warnings: list[str]) -> dict | None:
    """IQR-based outlier detection rendered as a scatter with outliers highlighted."""
    numeric_series = pd.to_numeric(df[y_col], errors="coerce").dropna()
    if len(numeric_series) < 4:
        return None

    q1 = numeric_series.quantile(0.25)
    q3 = numeric_series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    plot_df = df.loc[numeric_series.index].copy()
    plot_df["_outlier"] = ((numeric_series < lower) | (numeric_series > upper)).map({True: "Outlier", False: "Normal"})
    outlier_count = (plot_df["_outlier"] == "Outlier").sum()

    if outlier_count == 0:
        return None

    x_axis = x_col if (x_col and x_col in plot_df.columns) else plot_df.index.name or "Index"
    if x_axis == "Index":
        plot_df["Index"] = range(len(plot_df))

    fig = px.scatter(
        plot_df,
        x=x_axis,
        y=y_col,
        color="_outlier",
        color_discrete_map={"Normal": PRIMARY_SOFT, "Outlier": "#EF4444"},
        template="plotly_white",
        title=f"Outlier Detection — {_format_axis_name(y_col)} ({outlier_count} outlier{'s' if outlier_count != 1 else ''})",
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color="#FFFFFF")))
    # Draw IQR bounds
    fig.add_hline(y=upper, line_dash="dash", line_color="#F59E0B", annotation_text="Upper bound")
    fig.add_hline(y=lower, line_dash="dash", line_color="#F59E0B", annotation_text="Lower bound")
    _apply_common_layout(fig, x_axis, [y_col])
    fig.update_layout(legend_title_text="")

    summary = [
        f"{outlier_count} outlier{'s' if outlier_count != 1 else ''} detected in {_format_axis_name(y_col)}.",
        f"IQR bounds: {_format_metric_value(lower, y_col)} – {_format_metric_value(upper, y_col)}.",
    ]
    return _base_chart_payload(
        fig, "outlier", fig.layout.title.text,
        "Using a scatter plot with IQR-based outlier highlighting.",
        plot_df.drop(columns=["_outlier"], errors="ignore"),
        x_axis, [y_col], warnings,
        summary_override=summary,
    )


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


_TREND_TOKENS = (
    "over time", "trend", "trends", "by month", "by year", "by date",
    "by quarter", "by week", "by day", "history", "historical",
    "evolution", "evolved", "changed over", "change over", "growth",
    "monthly", "yearly", "quarterly", "weekly", "daily", "time series",
    "line chart", "line graph",
)
_DISTRIBUTION_TOKENS = (
    "distribution", "distributions", "spread", "histogram", "frequency",
    "how often", "shape of",
)
_RANKING_TOKENS = (
    "top ", "bottom ", "rank", "highest", "lowest", "biggest", "smallest",
    "best", "worst", "leading", "trailing", "most ", "least ",
)
_COMPARISON_TOKENS = (
    "compare", "comparison", " vs ", "versus", "across", "between",
    "broken down", "breakdown", "by category",
)
_BOXPLOT_TOKENS = (
    "boxplot", "box plot", "box-plot", "whisker", "quartile", "iqr",
    "interquartile",
)
_SCATTER_TOKENS = (
    "scatter", "scatter plot", "scatterplot", "relationship between",
    "correlation between", "cluster", "clustering",
)
_HEATMAP_TOKENS = (
    "heatmap", "heat map", "correlation matrix", "correlation heatmap",
    "correlations",
)
_OUTLIER_TOKENS = (
    "outlier", "outliers", "anomaly", "anomalies", "abnormal",
    "unusual", "extreme value", "extreme values", "detect outlier",
)
_FORECAST_TOKENS = (
    "forecast", "predict", "projection", "future", "next month",
    "next year", "extrapolat", "forecast overlay",
)


def _normalize_token(value: str) -> str:
    return re.sub(r"[_\s]+", " ", str(value).lower()).strip()


def _column_mentioned(query_lc: str, column: str) -> bool:
    norm = _normalize_token(column)
    if not norm:
        return False
    if norm in query_lc:
        return True
    # Strip very short suffixes like "id" / single-letter tokens to avoid noise
    parts = [p for p in norm.split() if len(p) > 2]
    if not parts:
        return False
    # All meaningful tokens of the column name appear in the query
    return all(p in query_lc for p in parts)


def build_chart_from_query(query: str, data: Any) -> dict | None:
    """
    Detect chart intent from a natural-language query and produce the right
    chart directly from the dataframe — even when the AI's textual reply
    didn't return a chartable result.  Supports: trend / line, boxplot,
    heatmap, scatter, outlier, forecast, distribution, ranking, comparison.
    """
    df = _copy_as_dataframe(data)
    if df is None or df.empty:
        return None

    query_lc = (query or "").lower()
    if not query_lc:
        return None

    is_trend       = any(tok in query_lc for tok in _TREND_TOKENS)
    is_distribution = any(tok in query_lc for tok in _DISTRIBUTION_TOKENS)
    is_ranking     = any(tok in query_lc for tok in _RANKING_TOKENS)
    is_comparison  = any(tok in query_lc for tok in _COMPARISON_TOKENS)
    is_boxplot     = any(tok in query_lc for tok in _BOXPLOT_TOKENS)
    is_scatter     = any(tok in query_lc for tok in _SCATTER_TOKENS)
    is_heatmap     = any(tok in query_lc for tok in _HEATMAP_TOKENS)
    is_outlier     = any(tok in query_lc for tok in _OUTLIER_TOKENS)
    is_forecast    = any(tok in query_lc for tok in _FORECAST_TOKENS)

    has_intent = any([
        is_trend, is_distribution, is_ranking, is_comparison,
        is_boxplot, is_scatter, is_heatmap, is_outlier, is_forecast,
    ])
    if not has_intent:
        return None

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    # Pick the metric the user named, falling back to the heaviest numeric col.
    target_metric = next(
        (col for col in numeric_cols if _column_mentioned(query_lc, col)),
        None,
    )
    if target_metric is None:
        target_metric = max(
            numeric_cols,
            key=lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0).sum(),
        )

    datetime_cols, categorical_cols = _prepare_dimension_columns(df)

    # ── Outlier detection chart ──────────────────────────────────────
    if is_outlier:
        cat_col = categorical_cols[0] if categorical_cols else None
        outlier_chart = _build_outlier_chart(df, target_metric, cat_col, [])
        if outlier_chart:
            return outlier_chart
        # No outliers found — fall through to boxplot which still shows the spread
        return _build_boxplot(df, target_metric, cat_col, [])

    # ── Boxplot ──────────────────────────────────────────────────────
    if is_boxplot:
        cat_col = categorical_cols[0] if categorical_cols else None
        return _build_boxplot(df, target_metric, cat_col, [])

    # ── Heatmap / correlation matrix ─────────────────────────────────
    if is_heatmap:
        heatmap = _build_heatmap(df, numeric_cols, [])
        if heatmap:
            return heatmap
        # Fallback: if only 1 numeric col, show distribution instead
        return _build_histogram(df, target_metric, [])

    # ── Scatter / clustering ─────────────────────────────────────────
    if is_scatter:
        # Find second numeric column
        other_numerics = [c for c in numeric_cols if c != target_metric]
        if other_numerics:
            second_metric = other_numerics[0]
            scatter = _build_scatter_chart(
                df,
                categorical_cols[0] if categorical_cols else target_metric,
                [target_metric, second_metric],
                [],
            )
            if scatter:
                return scatter
        # Fallback: show boxplot if only one numeric column
        cat_col = categorical_cols[0] if categorical_cols else None
        return _build_boxplot(df, target_metric, cat_col, [])

    # ── Forecast with linear extrapolation overlay ───────────────────
    if is_forecast and datetime_cols:
        import numpy as np
        date_col = datetime_cols[0]
        trend_df = df[[date_col, target_metric]].dropna().copy()
        try:
            trend_df[date_col] = pd.to_datetime(trend_df[date_col], errors="coerce")
            trend_df = trend_df.dropna(subset=[date_col])
        except Exception:
            pass
        if len(trend_df) >= 4:
            grouped = (
                trend_df.groupby(date_col)[target_metric]
                .mean()
                .reset_index()
                .sort_values(date_col)
            )
            # Simple linear forecast
            x_num = np.arange(len(grouped)).astype(float)
            y_vals = grouped[target_metric].values.astype(float)
            coeffs = np.polyfit(x_num, y_vals, 1)
            # Forecast next 20% of existing range
            n_forecast = max(int(len(grouped) * 0.2), 3)
            future_x = np.arange(len(grouped), len(grouped) + n_forecast).astype(float)
            future_y = np.polyval(coeffs, future_x)
            # Build future dates
            last_date = grouped[date_col].max()
            try:
                freq = pd.infer_freq(grouped[date_col])
            except Exception:
                freq = None
            if freq:
                future_dates = pd.date_range(start=last_date, periods=n_forecast + 1, freq=freq)[1:]
            else:
                avg_delta = (grouped[date_col].diff().mean())
                future_dates = [last_date + avg_delta * (i + 1) for i in range(n_forecast)]
            forecast_df = pd.DataFrame({date_col: future_dates, target_metric: future_y})

            fig = px.line(
                grouped, x=date_col, y=target_metric,
                markers=True, template="plotly_white",
                color_discrete_sequence=[PRIMARY],
                title=f"{_format_axis_name(target_metric)} — Actual + Forecast",
            )
            fig.update_traces(
                line=dict(width=3),
                marker=dict(size=8, line=dict(width=2, color="#FFFFFF")),
                name="Actual",
            )
            fig.add_scatter(
                x=forecast_df[date_col], y=forecast_df[target_metric],
                mode="lines+markers",
                line=dict(dash="dash", width=3, color=TERTIARY),
                marker=dict(size=8, line=dict(width=2, color="#FFFFFF"), color=TERTIARY),
                name="Forecast",
            )
            _apply_common_layout(fig, date_col, [target_metric])
            fig.update_layout(showlegend=True)
            return _base_chart_payload(
                fig, "forecast", fig.layout.title.text,
                "Line chart with linear forecast overlay (dashed).",
                pd.concat([grouped, forecast_df], ignore_index=True),
                date_col, [target_metric], [],
                summary_override=[
                    f"Forecasting {n_forecast} future periods for {_format_axis_name(target_metric)}.",
                    f"Linear trend slope: {coeffs[0]:,.2f} per period.",
                ],
            )

    # ── Trend → line chart over the best date column ─────────────────
    if is_trend and datetime_cols:
        date_col = datetime_cols[0]
        trend_df = df[[date_col, target_metric]].dropna().copy()
        try:
            trend_df[date_col] = pd.to_datetime(trend_df[date_col], errors="coerce")
            trend_df = trend_df.dropna(subset=[date_col])
        except Exception:
            pass
        if not trend_df.empty:
            grouped = (
                trend_df.groupby(date_col)[target_metric]
                .mean()
                .reset_index()
                .sort_values(date_col)
            )
            if len(grouped) >= 2:
                return _build_line_chart(grouped, date_col, target_metric, [])

    # ── Distribution → histogram ─────────────────────────────────────
    if is_distribution:
        return _build_histogram(df, target_metric, [])

    # ── Ranking / comparison → bar chart ─────────────────────────────
    if is_ranking or is_comparison:
        target_cat = next(
            (col for col in categorical_cols if _column_mentioned(query_lc, col)),
            None,
        )
        if target_cat is None and categorical_cols:
            target_cat = categorical_cols[0]
        if target_cat is not None:
            grouped = (
                df.groupby(target_cat, dropna=False)[target_metric]
                .sum()
                .reset_index()
                .sort_values(target_metric, ascending=False)
                .head(MAX_CATEGORY_POINTS)
            )
            if not grouped.empty:
                return _build_bar_chart(grouped, target_cat, target_metric, [])

    # ── Fallback: forecast without date → histogram ──────────────────
    if (is_forecast or is_trend) and not datetime_cols:
        return _build_histogram(df, target_metric, [])

    return None


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

    # Boxplot — shows quartiles & outlier whiskers
    cat_col = categorical_cols[0] if categorical_cols else None
    charts.append(_build_boxplot(df, numeric_cols[0], cat_col, validation_warnings.copy()))

    # Heatmap — correlation matrix when there are multiple numeric columns
    heatmap = _build_heatmap(df, numeric_cols, validation_warnings.copy())
    if heatmap:
        charts.append(heatmap)

    # Outlier detection
    outlier = _build_outlier_chart(df, numeric_cols[0], cat_col, validation_warnings.copy())
    if outlier:
        charts.append(outlier)

    deduped: list[dict] = []
    seen_titles: set[str] = set()
    for chart in charts:
        title = chart.get("title", "")
        if title and title not in seen_titles:
            deduped.append(chart)
            seen_titles.add(title)

    logger.info("Auto-visualizer produced %s chart option(s)", len(deduped[:8]))
    return deduped[:8]
