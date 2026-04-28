"""Validation-layer tests.

These prove that:
  - check_temporal_structure refuses to invent time periods (Mistake #1).
  - is_synthetic_or_random flags purely random datasets (Mistake #7).
  - validate_dataset reports actual computed counts (Mistake #8).
"""
import numpy as np
import pandas as pd
import pytest
from pipeline.validation import (
    validate_dataset, detect_data_type, check_temporal_structure, is_synthetic_or_random,
)


def _random_df(n=200, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "x1": rng.normal(size=n),
        "x2": rng.normal(size=n),
        "cat": rng.choice(list("ABC"), size=n),
        "y": rng.integers(0, 2, size=n),
    })


def test_validate_dataset_counts_are_computed_not_estimated():
    df = _random_df(500)
    df.loc[0:9, "x1"] = np.nan
    rep = validate_dataset(df)
    assert rep.n_rows == 500
    assert rep.n_cols == 4
    assert rep.null_counts["x1"] == 10  # exact count, no estimation


def test_validate_dataset_flags_constant_columns():
    df = _random_df(100)
    df["constant"] = 7
    rep = validate_dataset(df)
    assert "constant" in rep.constant_columns


def test_validate_dataset_flags_high_cardinality_id_columns():
    df = _random_df(100)
    df["uid"] = [f"row-{i}" for i in range(100)]
    rep = validate_dataset(df)
    assert "uid" in rep.high_cardinality_columns


def test_validate_dataset_rejects_empty_frames():
    with pytest.raises(ValueError):
        validate_dataset(pd.DataFrame())


def test_detect_data_type_classifies_correctly():
    df = pd.DataFrame({
        "n": [1, 2, 3],
        "c": ["x", "y", "z"],
        "d": pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01"]),
        "ds": ["2020-01-01", "2020-02-01", "2020-03-01"],
    })
    assert detect_data_type(df["n"]) == "numeric"
    assert detect_data_type(df["c"]) == "categorical"
    assert detect_data_type(df["d"]) == "datetime"
    assert detect_data_type(df["ds"]) == "datetime"


def test_check_temporal_structure_rejects_when_no_date_column():
    df = _random_df(100)
    rep = check_temporal_structure(df)
    assert rep.has_temporal_structure is False
    assert "no parseable date column" in rep.reason


def test_check_temporal_structure_rejects_when_dates_are_few():
    df = pd.DataFrame({
        "date": ["2020-01-01"] * 50 + ["2020-01-02"] * 50,
        "y": np.zeros(100, int),
    })
    rep = check_temporal_structure(df, min_unique_dates=30)
    assert rep.has_temporal_structure is False  # only 2 unique dates


def test_check_temporal_structure_accepts_real_date_columns():
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    df = pd.DataFrame({"date": dates, "y": range(400)})
    rep = check_temporal_structure(df)
    assert rep.has_temporal_structure is True
    assert rep.n_unique_timestamps == 400
    assert rep.span_days >= 30


def test_is_synthetic_or_random_flags_pure_noise():
    """Random features vs random target -> must be flagged synthetic.

    This is the bedrock guardrail: if the system can't see this is junk,
    it can't be trusted to refuse to fabricate insight on real datasets.
    """
    df = _random_df(2000, seed=1)
    rep = is_synthetic_or_random(df, target="y")
    assert rep.is_likely_synthetic is True
    assert rep.max_mutual_info < 0.01


def test_is_synthetic_or_random_does_not_flag_real_signal():
    """When a feature is wired to the target, the detector must NOT flag it as synthetic."""
    rng = np.random.default_rng(42)
    n = 2000
    x = rng.normal(size=n)
    y = (x + rng.normal(scale=0.3, size=n) > 0).astype(int)
    df = pd.DataFrame({"x": x, "noise": rng.normal(size=n), "y": y})
    rep = is_synthetic_or_random(df, target="y")
    assert rep.is_likely_synthetic is False
    assert rep.n_features_with_signal >= 1
