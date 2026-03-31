import pandas as pd

from modules.query_utils import (
    is_dataset_related_query,
    detect_simple_query,
    is_memory_query,
    extract_follow_up_questions,
    generate_follow_up_fallbacks,
    get_irrelevant_query_message,
)


def _sample_df():
    return pd.DataFrame(
        {
            "Region": ["North", "South"],
            "Revenue": [100, 200],
            "Date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        }
    )


def test_detect_simple_query_sum():
    df = _sample_df()
    code = detect_simple_query("total revenue", df)
    assert code is not None
    assert "sum" in code


def test_is_dataset_related_query_true_for_column_name():
    df = _sample_df()
    assert is_dataset_related_query("show revenue by region", df) is True


def test_is_memory_query():
    assert is_memory_query("compare with previous result")
    assert not is_memory_query("show total revenue")


def test_is_dataset_related_query_false_for_general_chitchat():
    df = _sample_df()
    assert is_dataset_related_query("how are you today", df) is False


def test_extract_follow_up_questions_filters_non_questions():
    raw = "Here are some follow-up questions:\n1. What is total revenue by region?\n- Compare revenue by month?\nThis is not a question"
    parsed = extract_follow_up_questions(raw)
    assert parsed == ["What is total revenue by region?", "Compare revenue by month?"]


def test_generate_follow_up_fallbacks_returns_question_list():
    df = _sample_df()
    schema = {
        "numeric_columns": ["Revenue"],
        "categorical_columns": ["Region"],
        "datetime_columns": ["Date"],
    }
    questions = generate_follow_up_fallbacks("show revenue", df, schema)
    assert len(questions) >= 4
    assert all(question.endswith("?") for question in questions)
    assert any("Revenue" in question for question in questions)


def test_get_irrelevant_query_message_mentions_columns():
    message = get_irrelevant_query_message({"column_names": ["Revenue", "Region", "Date"]})
    assert "Revenue" in message

