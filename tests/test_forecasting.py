import pandas as pd

from modules.forecasting import forecast_revenue


def test_forecast_revenue_happy_path():
    # Build simple monthly revenue data
    dates = pd.date_range("2023-01-01", periods=6, freq="ME")
    df = pd.DataFrame(
        {
            "Date": dates,
            "Revenue": [100, 120, 140, 160, 180, 200],
        }
    )

    result = forecast_revenue(df, periods=3)

    assert result["available"] is True
    assert result["forecast_df"] is not None
    assert len(result["forecast_df"]) == 3
    assert result["trend"] in {"increasing", "declining", "stable"}


def test_forecast_revenue_missing_date_column():
    df = pd.DataFrame({"Revenue": [100, 120, 140]})

    result = forecast_revenue(df, periods=3)

    assert result["available"] is False
    assert "date column" in result["message"].lower()


def test_forecast_revenue_uses_year_and_month_columns():
    df = pd.DataFrame(
        {
            "Year": [2024, 2024, 2024, 2024],
            "Month": [1, 2, 3, 4],
            "Sales": [10, 20, 30, 40],
        }
    )

    result = forecast_revenue(df, periods=2)

    assert result["available"] is True
    assert result["metric"] == "Sales"
    assert len(result["forecast_df"]) == 2


def test_forecast_revenue_fails_without_numeric_metric():
    df = pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=4, freq="ME"),
            "Region": ["North", "South", "East", "West"],
        }
    )

    result = forecast_revenue(df, periods=2)

    assert result["available"] is False
    assert "numeric metric" in result["message"].lower()


def test_forecast_revenue_does_not_mutate_input_dataframe_columns():
    df = pd.DataFrame(
        {
            "Year": [2024, 2024, 2024, 2024],
            "Month": [1, 2, 3, 4],
            "Sales": [10, 20, 30, 40],
        }
    )
    original_columns = df.columns.tolist()

    _ = forecast_revenue(df, periods=2)

    assert df.columns.tolist() == original_columns
    assert "_forecast_date" not in df.columns

