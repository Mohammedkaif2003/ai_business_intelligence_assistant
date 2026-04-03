import pandas as pd

from modules.auto_insights import generate_auto_insights


def test_generate_auto_insights_basic():
    df = pd.DataFrame(
        {
            "Region": ["North", "South", "North", "East"],
            "Revenue": [100, 200, 50, 75],
            "Quarter": ["Q1", "Q1", "Q2", "Q2"],
        }
    )

    insights = generate_auto_insights(df)

    # Should generate at least a couple of insights
    assert len(insights) >= 2
    # Should mention the top contributor somewhere
    assert any("contributes" in s for s in insights)


def test_generate_auto_insights_empty_dataframe():
    df = pd.DataFrame(columns=["Region", "Revenue"])
    assert generate_auto_insights(df) == []


def test_generate_auto_insights_handles_zero_group_total_without_crash():
    df = pd.DataFrame(
        {
            "Region": ["North", "South"],
            "Revenue": [0, 0],
        }
    )

    insights = generate_auto_insights(df)

    assert len(insights) >= 1
    assert any("total Revenue is zero" in s for s in insights)

