import pandas as pd


def generate_business_insight(data):

    # Convert Series → DataFrame
    if isinstance(data, pd.Series):
        df = data.reset_index()
        df.columns = ["Entity", "Value"]

    elif isinstance(data, pd.DataFrame):
        df = data.copy()
        # Flatten MultiIndex to avoid .astype(str) errors
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()

    else:
        return "No insight available."

    if df.empty:
        return "No data available for insight generation."

    insights = []

    # Detect numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if not numeric_cols:
        return "Dataset does not contain numeric values."

    metric = numeric_cols[0]

    # Detect entity column (first non-numeric column)
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    if non_numeric_cols:
        entity_col = non_numeric_cols[0]
    else:
        df["Entity"] = [str(x) for x in df.index]
        entity_col = "Entity"

    # Sort by metric
    df_sorted = df.sort_values(metric, ascending=False)

    top_row = df_sorted.iloc[0]
    bottom_row = df_sorted.iloc[-1]

    # ---------------- TOP PERFORMER ----------------
    insights.append(
        f"Highest contributor: **{top_row[entity_col]} leads with {top_row[metric]:,.0f}."
    )

    # ---------------- LOWEST PERFORMER ----------------
    insights.append(
        f"Lowest contributor: **{bottom_row[entity_col]}** with {bottom_row[metric]:,.0f}."
    )

    # ---------------- CONTRIBUTION ANALYSIS ----------------
    total = df[metric].sum()

    if total > 0:
        share = (top_row[metric] / total) * 100

        if share > 50:
            insights.append(
                f" High concentration risk: top entity contributes {share:.1f}% of total."
            )

        elif share > 35:
            insights.append(
                f" Moderate dependency detected: top entity contributes {share:.1f}%."
            )

    # ---------------- PERFORMANCE GAP ----------------
    if top_row[metric] > 0 and bottom_row[metric] > 0:
        gap = top_row[metric] / bottom_row[metric]

        if gap > 4:
            insights.append(
                "⚖ Significant performance gap between top and bottom entities."
            )

    # ---------------- TREND DETECTION ----------------
    possible_time_cols = ["date", "month", "year", "day"]

    for col in df.columns:
        col_name = str(col).lower()
        if col_name in possible_time_cols:

            try:
                trend = df.sort_values(col)[metric].diff().mean()

                if trend > 0:
                    insights.append("Overall trend shows an increase.")

                elif trend < 0:
                    insights.append("Overall trend shows a decline.")
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug("insight_generation_failed", exc_info=True)

            break

    return "\n• " + "\n• ".join(insights)
