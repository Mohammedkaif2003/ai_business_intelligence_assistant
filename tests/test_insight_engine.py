import pandas as pd

from modules.insight_engine import generate_business_insight


def test_generate_business_insight_skips_gap_for_negative_bottom_value():
    df = pd.DataFrame(
        {
            "Department": ["Top", "Bottom"],
            "Revenue": [100, -20],
        }
    )

    insight = generate_business_insight(df)

    assert "Significant performance gap" not in insight


def test_generate_business_insight_reports_gap_for_positive_values():
    df = pd.DataFrame(
        {
            "Department": ["Top", "Bottom"],
            "Revenue": [500, 50],
        }
    )

    insight = generate_business_insight(df)

    assert "Significant performance gap" in insight