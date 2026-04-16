import pandas as pd


def analyze_dataset(df):

    info = {}

    # Basic dataset information
    info["rows"] = df.shape[0]
    # Keep backward-compatible numeric column count under `column_count`
    info["column_count"] = df.shape[1]
    # Provide a list of column names under `columns` for callers/tests that expect an iterable
    info["columns"] = df.columns.tolist()
    info["column_names"] = df.columns.tolist()

    # Detect column types safely
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime", "datetime64"]).columns.tolist()

    info["numeric_columns"] = numeric_cols
    info["categorical_columns"] = categorical_cols
    info["datetime_columns"] = datetime_cols

    # Example values for each column
    examples = {}

    for col in df.columns:
        try:
            value = df[col].dropna().iloc[0]
            examples[col] = str(value)
        except (IndexError, KeyError, TypeError, ValueError):
            examples[col] = "N/A"

    info["examples"] = examples

    return info
