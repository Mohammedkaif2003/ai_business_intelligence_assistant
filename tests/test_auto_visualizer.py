import pandas as pd

from modules.auto_visualizer import (
    auto_visualize,
    build_graph_follow_up_suggestions,
    build_graph_follow_up_questions,
    validate_chart_data,
)


def _sample_chart_df():
    return pd.DataFrame(
        {
            "Region": ["North", "South", "East", "West"],
            "Revenue": [1000, 1500, 900, 1700],
            "Profit": [120, 180, 90, 210],
            "Date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"]),
        }
    )


def test_validate_chart_data_rejects_non_numeric_frames():
    df = pd.DataFrame({"Region": ["North", "South"], "Category": ["A", "B"]})
    validated, warnings = validate_chart_data(df)
    assert validated is None
    assert warnings


def test_auto_visualize_returns_rich_chart_payloads():
    charts = auto_visualize(_sample_chart_df())
    assert charts
    assert all(isinstance(chart, dict) for chart in charts)
    assert all(chart.get("figure") is not None for chart in charts)
    assert any(chart.get("chart_type") == "line" for chart in charts)
    assert any(chart.get("chart_type") == "bar" for chart in charts)


def test_build_graph_follow_up_questions_returns_questions():
    chart = auto_visualize(_sample_chart_df())[0]
    follow_ups = build_graph_follow_up_questions(chart)
    assert len(follow_ups) >= 2
    assert all(question.endswith(".") or question.endswith("?") for question in follow_ups)


def test_build_graph_follow_up_suggestions_adds_graph_metadata():
    chart = auto_visualize(_sample_chart_df())[0]
    suggestions = build_graph_follow_up_suggestions(chart)

    assert suggestions
    assert all(isinstance(item, dict) for item in suggestions)
    assert all("question" in item for item in suggestions)
    assert any(item.get("expected_output") == "chart" for item in suggestions)
    assert any("Forecast" in item["question"] for item in suggestions)


def test_build_graph_follow_up_suggestions_returns_empty_for_generic_chart_payload():
    suggestions = build_graph_follow_up_suggestions(
        {
            "data": None,
            "x_col": "",
            "y_cols": [],
            "chart_type": "chart",
        }
    )
    assert suggestions == []
