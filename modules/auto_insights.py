import pandas as pd


def generate_auto_insights(df):

    insights = []

    if df.empty:
        return insights

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

    # ---------- TOP CONTRIBUTOR ----------
    if numeric_cols and cat_cols:

        metric = numeric_cols[0]
        category = cat_cols[0]

        grouped = df.groupby(category, dropna=False)[metric].sum().sort_values(ascending=False)
        grouped = grouped.dropna()

        if not grouped.empty:
            top = grouped.index[0]
            total_grouped = grouped.sum()
            if total_grouped != 0:
                share = (grouped.iloc[0] / total_grouped) * 100
                insights.append(
                    f"{top} contributes {share:.1f}% of total {metric}."
                )
            else:
                insights.append(
                    f"{top} has the highest {metric}, but total {metric} is zero across categories."
                )

            # Bottom performer
            if len(grouped) > 1:
                bottom = grouped.index[-1]
                insights.append(
                    f"{bottom} has the lowest contribution in {metric}."
                )

    # ---------- MAX / MIN VALUE ----------
    if numeric_cols:

        metric = numeric_cols[0]

        max_value = df[metric].max()
        min_value = df[metric].min()
        avg_value = df[metric].mean()

        insights.append(
            f"Highest {metric} observed is {max_value:,.0f}."
        )

        insights.append(
            f"{metric} averages {avg_value:,.0f}, ranging from {min_value:,.0f} to {max_value:,.0f}."
        )

    # ---------- MISSING DATA CHECK ----------
    missing = df.isnull().sum()
    cols_with_missing = missing[missing > 0]
    if len(cols_with_missing) > 0:
        worst = cols_with_missing.idxmax()
        pct = (cols_with_missing.max() / len(df)) * 100
        insights.append(
            f"⚠ Column '{worst}' has {pct:.1f}% missing data."
        )

    # ---------- QUARTER-OVER-QUARTER COMPARISON ----------
    # Handle both Title-cased (from normalize_columns) and lowercase columns
    quarter_col = None
    revenue_col = None

    for col in df.columns:
        if col.lower() == "quarter":
            quarter_col = col
        if col.lower() in ["revenue", "sales", "profit"]:
            revenue_col = col

    if quarter_col and revenue_col:
        try:
            q_data = df.groupby(quarter_col)[revenue_col].sum().sort_index()
            if len(q_data) >= 2:
                last_q = q_data.iloc[-1]
                prev_q = q_data.iloc[-2]
                if prev_q != 0:
                    change_pct = ((last_q - prev_q) / prev_q) * 100
                    direction = "increased" if change_pct > 0 else "decreased"
                    insights.append(
                        f"{revenue_col} {direction} by {abs(change_pct):.1f}% compared to the previous quarter."
                    )
        except Exception:
            pass

    # ---------- TREND DETECTION ----------
    # Handle both Title-cased and lowercase column names
    time_cols_check = ["Date", "date", "Year", "year", "Month", "month"]

    for col in time_cols_check:

        if col in df.columns and numeric_cols:

            metric = numeric_cols[0]

            try:
                trend = df.sort_values(col)[metric].diff().mean()

                if trend > 0:
                    insights.append("📈 Overall trend shows an increasing trend.")
                elif trend < 0:
                    insights.append("📉 Overall trend shows the decreasing trend.")
            except Exception:
                pass

            break

    # ---------- UNIQUE COUNT INSIGHTS ----------
    if cat_cols:
        for cat in cat_cols[:2]:
            count = df[cat].nunique()
            insights.append(
                f"The dataset includes {count} unique {cat} values."
            )

    return insights
