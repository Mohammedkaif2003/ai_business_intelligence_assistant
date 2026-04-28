"""Stats-layer tests — prove the test functions return the right structure
and that trend_test refuses to find a trend in noise (Mistake #2).
"""
import numpy as np
import pandas as pd
from pipeline.stats import (
    numeric_vs_binary, categorical_vs_binary, numeric_vs_numeric, trend_test, cohens_d,
)


def test_cohens_d_zero_for_identical_groups():
    a = np.array([1.0, 2, 3, 4, 5] * 10)
    assert abs(cohens_d(a, a)) < 1e-9


def test_numeric_vs_binary_returns_full_evidence():
    rng = np.random.default_rng(0)
    n = 1000
    y = pd.Series(rng.integers(0, 2, size=n))
    x = pd.Series(rng.normal(size=n) + y * 0.8, name="signal")
    r = numeric_vs_binary(x, y)
    assert r.is_significant is True
    assert r.p_value < 0.05
    assert abs(r.effect_size) >= 0.1
    assert r.n == n
    assert r.effect_size_name == "cohen_d"


def test_numeric_vs_binary_flags_noise_as_non_significant():
    # Average across multiple seeds — at α=0.05 with min |d|=0.1 we expect
    # most random splits to come back non-significant. Allow at most 1 false
    # positive across 10 seeds (~10% upper bound, well above the joint nominal rate).
    false_positives = 0
    for seed in range(10):
        rng = np.random.default_rng(seed)
        n = 2000  # larger n shrinks |d| under H0 so false positives are rarer
        y = pd.Series(rng.integers(0, 2, size=n))
        x = pd.Series(rng.normal(size=n), name="noise")
        r = numeric_vs_binary(x, y)
        if r.is_significant:
            false_positives += 1
    assert false_positives <= 1, f"{false_positives}/10 false positives — guardrail too loose"


def test_categorical_vs_binary_returns_full_evidence():
    rng = np.random.default_rng(0)
    n = 2000
    y = pd.Series(rng.integers(0, 2, size=n))
    cats = np.where(y == 1,
                    rng.choice(["A", "B"], size=n, p=[0.8, 0.2]),
                    rng.choice(["A", "B"], size=n, p=[0.2, 0.8]))
    x = pd.Series(cats, name="cat")
    r = categorical_vs_binary(x, y)
    assert r.is_significant is True
    assert r.effect_size_name == "cramers_v"
    assert r.p_value < 0.05


def test_numeric_vs_numeric_returns_pearson_and_spearman():
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(size=500))
    y = pd.Series(2 * x + rng.normal(size=500))
    out = numeric_vs_numeric(x, y)
    assert out["pearson"].is_significant is True
    assert out["spearman"].is_significant is True


def test_trend_test_refuses_to_find_trend_in_noise():
    """Mistake #2: Spurious trend claims. With pure noise the test must
    return is_significant=False. This is the canonical guardrail test."""
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(size=200))
    r = trend_test(s)
    assert r.is_significant is False


def test_trend_test_detects_a_real_trend():
    s = pd.Series(np.linspace(0, 10, 200) + np.random.default_rng(0).normal(scale=0.5, size=200))
    r = trend_test(s)
    assert r.is_significant is True
    assert r.direction == "positive"


def test_trend_test_handles_short_series_gracefully():
    s = pd.Series([1.0, 2, 3])
    r = trend_test(s)
    assert r.is_significant is False
    assert "n>=8" in r.notes or r.n < 8
