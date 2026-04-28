"""Validation layer — runs before any analysis.

Every check returns a structured report. Nothing here ever prints a claim;
it produces evidence that the claim_verifier consumes downstream.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np
import pandas as pd


@dataclass
class ValidationReport:
    n_rows: int
    n_cols: int
    duplicates: int
    null_counts: dict[str, int]
    dtypes: dict[str, str]
    constant_columns: list[str]
    high_cardinality_columns: list[str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "duplicates": self.duplicates,
            "null_counts": self.null_counts,
            "dtypes": self.dtypes,
            "constant_columns": self.constant_columns,
            "high_cardinality_columns": self.high_cardinality_columns,
            "warnings": self.warnings,
        }


def validate_dataset(df: pd.DataFrame, high_card_threshold: float = 0.5) -> ValidationReport:
    """Inspect a dataframe for null/dup/constant/high-card issues.

    high_card_threshold: column flagged if unique_ratio > this fraction.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"expected pd.DataFrame, got {type(df).__name__}")
    if len(df) == 0:
        raise ValueError("dataframe has zero rows")

    nulls = df.isnull().sum()
    constants = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    high_card = [
        c for c in df.columns
        if df[c].nunique(dropna=True) / max(len(df), 1) > high_card_threshold
        and not pd.api.types.is_numeric_dtype(df[c])
    ]
    warnings: list[str] = []
    if df.duplicated().any():
        warnings.append(f"{int(df.duplicated().sum())} duplicate rows present")
    for col, n in nulls[nulls > 0].items():
        warnings.append(f"column '{col}' has {int(n)} nulls ({n/len(df):.2%})")
    for c in constants:
        warnings.append(f"column '{c}' is constant — drop before modeling")
    for c in high_card:
        warnings.append(f"column '{c}' is high-cardinality string (likely an ID)")

    return ValidationReport(
        n_rows=int(len(df)),
        n_cols=int(df.shape[1]),
        duplicates=int(df.duplicated().sum()),
        null_counts={k: int(v) for k, v in nulls[nulls > 0].items()},
        dtypes={c: str(df[c].dtype) for c in df.columns},
        constant_columns=constants,
        high_cardinality_columns=high_card,
        warnings=warnings,
    )


def detect_data_type(series: pd.Series) -> str:
    """Classify a column as 'numeric' | 'datetime' | 'categorical' | 'text'."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    sample = series.dropna().astype(str).head(50)
    parsed = pd.to_datetime(sample, errors="coerce", dayfirst=True)
    if parsed.notna().mean() > 0.9 and len(sample) > 0:
        return "datetime"
    avg_len = sample.str.len().mean() if len(sample) else 0
    n_unique = series.nunique(dropna=True)
    if n_unique > 100 and avg_len > 30:
        return "text"
    return "categorical"


@dataclass
class TemporalReport:
    has_temporal_structure: bool
    date_column: str | None
    n_unique_timestamps: int
    span_days: int
    monthly_buckets: int
    reason: str


def check_temporal_structure(
    df: pd.DataFrame,
    candidate_columns: list[str] | None = None,
    min_unique_dates: int = 30,
    min_span_days: int = 30,
    min_monthly_buckets: int = 12,
) -> TemporalReport:
    """Return True only if a real date column exists with sufficient variance.

    A column qualifies if:
      - >=90% of non-null values parse as dates,
      - it has >= min_unique_dates unique values,
      - the span is >= min_span_days,
      - and at least min_monthly_buckets distinct calendar months are present.
    """
    cols = candidate_columns or list(df.columns)
    best: tuple[str, pd.Series] | None = None
    for c in cols:
        s = df[c]
        if pd.api.types.is_datetime64_any_dtype(s):
            parsed = s
        else:
            # Skip pure numeric columns — pd.to_datetime would interpret floats
            # as nanosecond timestamps and falsely report a date column.
            if pd.api.types.is_numeric_dtype(s):
                continue
            try:
                parsed = pd.to_datetime(s, errors="coerce", dayfirst=True)
            except Exception:
                continue
        if parsed.notna().mean() < 0.9:
            continue
        if best is None or parsed.nunique() > best[1].nunique():
            best = (c, parsed)

    if best is None:
        return TemporalReport(False, None, 0, 0, 0, "no parseable date column")

    name, parsed = best
    n_unique = int(parsed.nunique())
    span = int((parsed.max() - parsed.min()).days) if n_unique > 0 else 0
    monthly = int(parsed.dt.to_period("M").nunique())

    if n_unique < min_unique_dates:
        return TemporalReport(False, name, n_unique, span, monthly,
                              f"only {n_unique} unique dates (< {min_unique_dates})")
    if span < min_span_days:
        return TemporalReport(False, name, n_unique, span, monthly,
                              f"span only {span} days (< {min_span_days})")
    if monthly < min_monthly_buckets:
        return TemporalReport(False, name, n_unique, span, monthly,
                              f"only {monthly} distinct months (< {min_monthly_buckets})")

    return TemporalReport(True, name, n_unique, span, monthly,
                          f"valid date column '{name}' spanning {span} days, "
                          f"{monthly} months, {n_unique} unique dates")


@dataclass
class SyntheticReport:
    is_likely_synthetic: bool
    max_abs_correlation: float
    max_mutual_info: float
    n_features_with_signal: int
    reason: str


def is_synthetic_or_random(
    df: pd.DataFrame,
    target: str,
    mi_threshold: float = 0.05,
    min_features_with_signal: int = 1,
) -> SyntheticReport:
    """Flag datasets where every feature is independent of the target.

    Uses sklearn mutual_info_classif/regression. A dataset where the maximum
    feature->target MI is below mi_threshold is treated as effectively random.
    """
    from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
    from sklearn.preprocessing import LabelEncoder

    if target not in df.columns:
        raise KeyError(f"target column '{target}' not in dataframe")

    X = df.drop(columns=[target]).copy()
    y = df[target]

    is_classification = (not pd.api.types.is_numeric_dtype(y)) or (y.nunique() <= 20)
    if not pd.api.types.is_numeric_dtype(y):
        y = LabelEncoder().fit_transform(y.astype(str))

    drop_cols = [c for c in X.columns if X[c].nunique(dropna=False) <= 1]
    X = X.drop(columns=drop_cols)
    for c in X.columns:
        if not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = LabelEncoder().fit_transform(X[c].astype(str).fillna("__NA__"))
        else:
            X[c] = X[c].fillna(X[c].median())

    if X.shape[1] == 0:
        return SyntheticReport(True, 0.0, 0.0, 0, "no usable features after dropping constants")

    try:
        if is_classification:
            mi = mutual_info_classif(X.values, y, random_state=0)
        else:
            mi = mutual_info_regression(X.values, y, random_state=0)
    except Exception as e:  # numerical edge cases
        return SyntheticReport(True, 0.0, 0.0, 0, f"mutual info failed: {e}")

    corr = np.array([
        abs(np.corrcoef(X[c].values.astype(float), y)[0, 1])
        if X[c].std() > 0 else 0.0
        for c in X.columns
    ])
    corr = np.nan_to_num(corr, nan=0.0)
    n_signal = int(np.sum(mi > mi_threshold))
    likely_synthetic = n_signal < min_features_with_signal

    reason = (
        f"max MI={mi.max():.4f}, max |corr|={corr.max():.4f}, "
        f"{n_signal}/{X.shape[1]} features above MI threshold {mi_threshold}"
    )
    return SyntheticReport(
        is_likely_synthetic=likely_synthetic,
        max_abs_correlation=float(corr.max()),
        max_mutual_info=float(mi.max()),
        n_features_with_signal=n_signal,
        reason=reason,
    )
