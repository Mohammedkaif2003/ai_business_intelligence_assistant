import pandas as pd

from modules.app_tabs import _generate_dynamic_query_suggestions
from modules.app_views import _generate_quick_prompts
from modules.query_utils import generate_follow_up_fallbacks


def _sample_df():
    return pd.DataFrame(
        {
            "Region": ["North", "South"],
            "Revenue": [100, 200],
            "Date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        }
    )


def test_dynamic_suggestions_change_with_active_dataset_name():
    df = _sample_df()
    schema = {
        "numeric_columns": ["Revenue"],
        "categorical_columns": ["Region"],
        "datetime_columns": ["Date"],
        "column_names": ["Region", "Revenue", "Date"],
    }

    sales_prompts = _generate_dynamic_query_suggestions(df, schema, dataset_name="sales_data.csv")
    hr_prompts = _generate_dynamic_query_suggestions(df, schema, dataset_name="hr_data.csv")

    assert sales_prompts != hr_prompts
    assert any("Sales Data" in prompt for prompt in sales_prompts)
    assert any("Hr Data" in prompt for prompt in hr_prompts)


def test_quick_prompts_change_with_active_dataset_name():
    df = _sample_df()
    schema = {
        "numeric_columns": ["Revenue"],
        "categorical_columns": ["Region"],
        "datetime_columns": ["Date"],
        "column_names": ["Region", "Revenue", "Date"],
    }

    sales_prompts = _generate_quick_prompts(df, schema, dataset_name="sales_data.csv")
    finance_prompts = _generate_quick_prompts(df, schema, dataset_name="finance_data.csv")

    assert sales_prompts != finance_prompts
    assert any("Sales Data" in prompt for prompt in sales_prompts)
    assert any("Finance Data" in prompt for prompt in finance_prompts)


def test_follow_up_fallbacks_change_with_active_dataset_name():
    df = _sample_df()
    schema = {
        "numeric_columns": ["Revenue"],
        "categorical_columns": ["Region"],
        "datetime_columns": ["Date"],
        "column_names": ["Region", "Revenue", "Date"],
    }

    sales_fallbacks = generate_follow_up_fallbacks("show revenue", df, schema, dataset_name="sales_data.csv")
    hr_fallbacks = generate_follow_up_fallbacks("show revenue", df, schema, dataset_name="hr_data.csv")

    assert sales_fallbacks != hr_fallbacks
    assert any("Sales Data" in question for question in sales_fallbacks)
    assert any("Hr Data" in question for question in hr_fallbacks)