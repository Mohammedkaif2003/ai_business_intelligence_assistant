"""Modeling-layer tests — prove auto-detect, baseline, and CV training work
on synthetic data. These cover Mistake #4 (EDA-vs-prediction) by ensuring
the modeling layer is the only path that produces a 'prediction' artifact.
"""
import numpy as np
import pandas as pd
import pytest
from pipeline.modeling import detect_task_type, train_models, baseline_score


def _classification_df(n=600, signal=True, seed=0):
    rng = np.random.default_rng(seed)
    age = rng.integers(20, 80, size=n)
    cat = rng.choice(["A", "B", "C"], size=n)
    if signal:
        logits = -2 + 0.04 * age + np.where(cat == "A", 1.0, 0.0)
        p = 1 / (1 + np.exp(-logits))
        y = rng.binomial(1, p)
    else:
        y = rng.integers(0, 2, size=n)
    return pd.DataFrame({"age": age, "cat": cat}), pd.Series(y, name="y")


def test_detect_task_type_binary():
    y = pd.Series([0, 1, 0, 1, 0])
    assert detect_task_type(y) == "binary"


def test_detect_task_type_regression():
    y = pd.Series(np.linspace(0, 100, 200))
    assert detect_task_type(y) == "regression"


def test_detect_task_type_multiclass():
    y = pd.Series(["a", "b", "c", "a", "b", "c"] * 5)
    assert detect_task_type(y) == "multiclass"


def test_baseline_score_binary_reports_majority_share():
    y = pd.Series([0] * 80 + [1] * 20)
    b = baseline_score(y, "binary")
    assert abs(b["baseline_accuracy"] - 0.8) < 1e-9
    assert b["baseline_recall_positive"] == 0.0


def test_train_models_returns_three_algorithms_with_cv_scores():
    X, y = _classification_df(signal=True)
    results = train_models(X, y, cv_folds=3)
    assert set(results.keys()) == {"logistic_l2", "random_forest", "gradient_boosting"}
    for r in results.values():
        assert r.cv_scores.shape == (3,)
        assert 0.0 <= r.cv_mean <= 1.0
        assert r.metric == "roc_auc"
        assert r.oof_predictions is not None
        assert r.oof_predictions.shape == (len(X),)


def test_models_outperform_baseline_on_signal_data():
    X, y = _classification_df(n=2000, signal=True, seed=1)
    results = train_models(X, y, cv_folds=3)
    for r in results.values():
        assert r.cv_mean > 0.55, f"{r.name} AUC {r.cv_mean} suggests no signal captured"


def test_models_collapse_to_baseline_on_pure_noise():
    """Mistake #7: Without signal, models must NOT magically score well."""
    X, y = _classification_df(n=2000, signal=False, seed=2)
    results = train_models(X, y, cv_folds=3)
    for r in results.values():
        assert r.cv_mean < 0.6, f"{r.name} AUC {r.cv_mean} suspiciously high on noise"
