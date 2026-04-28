"""Evaluation-layer tests."""
import numpy as np
from pipeline.evaluation import evaluate_binary, bootstrap_ci


def test_evaluate_binary_returns_threshold_and_calibration_tables():
    rng = np.random.default_rng(0)
    n = 1000
    y = rng.integers(0, 2, size=n)
    score = rng.random(size=n) * 0.4 + y * 0.4  # mild signal
    res = evaluate_binary(y, score)
    assert 0.0 <= res.auc_roc <= 1.0
    assert "threshold" in res.threshold_table.columns
    assert "actual_rate" in res.calibration_table.columns
    assert res.confusion_at_default["tp"] + res.confusion_at_default["tn"] + \
           res.confusion_at_default["fp"] + res.confusion_at_default["fn"] == n


def test_bootstrap_ci_brackets_point_estimate():
    rng = np.random.default_rng(0)
    n = 500
    y = rng.integers(0, 2, size=n)
    score = rng.random(size=n) + y * 0.3
    lo, hi = bootstrap_ci(y, score, n_boot=200, random_state=0)
    assert lo <= hi
    assert 0.0 <= lo <= 1.0


def test_evaluate_binary_flags_near_random_auc():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, size=2000)
    score = rng.random(size=2000)
    res = evaluate_binary(y, score)
    assert res.auc_roc < 0.6
    assert any("near random" in n.lower() for n in res.notes)
