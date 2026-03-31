import pandas as pd
import numpy as np

from modules.app_logging import get_logger


logger = get_logger("forecasting")


def forecast_revenue(df, periods=3):
    """
    Simple revenue/sales forecasting using linear trend projection.
    Returns a dict with forecast values, trend info, and confidence bounds.
    """

    result = {
        "available": False,
        "message": "Forecasting requires a date-like column (e.g. Date, Order Date) and a numeric metric (e.g. Revenue or Sales).",
        "forecast_df": None,
        "trend": None,
    }
    logger.info("Starting forecast generation for %s rows and %s periods", len(df), periods)

    # Detect date column
    date_col = None
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["date", "order date", "transaction date"]:
            date_col = col
            break
        if "date" in col_lower:
            date_col = col
            break

    if date_col is None:
        # Try year_month or year+month
        if "Year Month" in df.columns or "Year_Month" in df.columns:
            date_col = "Year Month" if "Year Month" in df.columns else "Year_Month"
        elif "Year" in df.columns and "Month" in df.columns:
            df["_forecast_date"] = pd.to_datetime(
                df["Year"].astype(str)
                + "-"
                + df["Month"].astype(str).str.zfill(2)
                + "-01"
            )
            date_col = "_forecast_date"

    if date_col is None:
        result["message"] = (
            "No suitable date column was found. "
            "Add a column named Date / Order Date / Transaction Date, or a Year + Month combination."
        )
        logger.warning("Forecasting aborted: no suitable date column")
        return result

    # Detect revenue/numeric column
    metric_col = None
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["revenue", "sales", "total sales", "profit", "amount"]:
            metric_col = col
            break

    if metric_col is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            metric_col = numeric_cols[0]
        else:
            result["message"] = (
                "No numeric metric column found for forecasting. "
                "Include a column such as Revenue, Sales, Amount, or another numeric field."
            )
            logger.warning("Forecasting aborted: no numeric metric column")
            return result

    try:
        # Ensure date is datetime
        if df[date_col].dtype == "object":
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        # Aggregate by month
        monthly = df.set_index(date_col).resample("ME")[metric_col].sum().reset_index()
        monthly.columns = ["Date", "Value"]
        monthly = monthly.dropna()

        if len(monthly) < 3:
            result["message"] = "Not enough monthly data points for forecasting (need at least 3)."
            logger.warning("Forecasting aborted: only %s monthly points available", len(monthly))
            return result

        # Create numeric index for regression
        monthly["Index"] = range(len(monthly))

        # Linear regression
        x = monthly["Index"].values
        y = monthly["Value"].values

        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs[0], coeffs[1]

        # Calculate residuals for confidence interval
        fitted = np.polyval(coeffs, x)
        residuals = y - fitted
        std_err = np.std(residuals)

        # Generate forecast
        forecast_indices = np.arange(len(monthly), len(monthly) + periods)
        forecast_values = np.polyval(coeffs, forecast_indices)

        # Create forecast dates
        last_date = monthly["Date"].iloc[-1]
        forecast_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=periods, freq="ME")

        forecast_df = pd.DataFrame({
            "Date": forecast_dates,
            "Predicted": forecast_values.round(2),
            "Lower Bound": (forecast_values - 1.96 * std_err).round(2),
            "Upper Bound": (forecast_values + 1.96 * std_err).round(2)
        })

        # Determine trend
        if slope > 0:
            trend = "increasing"
        elif slope < 0:
            trend = "declining"
        else:
            trend = "stable"

        # Build historical + forecast combined df for charting
        historical_df = monthly[["Date", "Value"]].copy()
        historical_df.rename(columns={"Value": metric_col}, inplace=True)

        result["available"] = True
        result["message"] = f"Forecast generated for next {periods} months."
        result["forecast_df"] = forecast_df
        result["historical_df"] = historical_df
        result["trend"] = trend
        result["slope"] = round(slope, 2)
        result["metric"] = metric_col
        result["std_error"] = round(std_err, 2)
        logger.info("Forecast generated successfully for metric %s with trend %s", metric_col, trend)

    except Exception as e:
        result["message"] = f"Forecasting error: {str(e)}"
        logger.exception("Forecasting failed")

    return result
