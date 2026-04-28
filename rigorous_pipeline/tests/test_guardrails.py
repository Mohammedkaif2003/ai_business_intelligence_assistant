"""Headline guardrail tests.

This file maps directly to the 8 mistakes in MISTAKES_PREVENTED.md and is
intended to be the first place a reviewer reads. Each test names the mistake
in its docstring.
"""
import numpy as np
import pandas as pd
from pipeline.validation import check_temporal_structure, is_synthetic_or_random, validate_dataset
from pipeline.stats import trend_test, numeric_vs_binary
from pipeline.claim_verifier import verify_claim, format_finding
from pipeline.modeling import train_models, baseline_score
from pipeline.evaluation import evaluate_binary
from pipeline.interpret import feature_stability
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ---------- Mistake #1: hallucinated time series ----------

def test_mistake1_no_date_column_means_no_temporal_claim():
    df = pd.DataFrame({"x": np.random.default_rng(0).normal(size=100), "y": [0, 1] * 50})
    assert check_temporal_structure(df).has_temporal_structure is False


# ---------- Mistake #2: spurious trend on shuffled / random data ----------

def test_mistake2_trend_on_shuffled_data_is_rejected():
    # Run across multiple seeds — accept up to 1/10 nominal false positives.
    false_positives = 0
    for seed in range(10):
        rng = np.random.default_rng(seed)
        s = pd.Series(rng.permutation(rng.normal(size=300)))
        r = trend_test(s)
        if r.is_significant:
            false_positives += 1
        if not r.is_significant:
            msg = format_finding(r)
            assert "no statistically significant" in msg.lower()
            assert verify_claim(msg, evidence=r).accepted is True
    assert false_positives <= 1, f"{false_positives}/10 false trends — guardrail too loose"


def test_mistake2_directional_phrase_alone_blocked_by_verifier():
    res = verify_claim("Admissions are trending upward.")
    assert res.accepted is False


# ---------- Mistake #3: correlation-as-causation ----------

def test_mistake3_causal_claim_without_stats_is_blocked():
    res = verify_claim("Bill amount drives readmission.")
    assert res.accepted is False


# ---------- Mistake #4: EDA narration vs prediction ----------

def test_mistake4_summary_stats_alone_do_not_pass_verifier():
    res = verify_claim("Average length of stay is 4.1 days, which predicts readmission.")
    # 'predicts' is a directional word; without p-value/effect-size it must fail
    assert res.accepted is False


# ---------- Mistake #5: unvalidated feature importance ----------

def _factory():
    pre = ColumnTransformer([
        ("num", StandardScaler(), ["x1", "x2", "x3"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["c"]),
    ])
    return Pipeline([("pre", pre),
                     ("est", RandomForestClassifier(n_estimators=80, random_state=0, n_jobs=-1))])


def test_mistake5_importance_must_carry_stability_metadata():
    rng = np.random.default_rng(0)
    n = 800
    df = pd.DataFrame({
        "x1": rng.normal(size=n),
        "x2": rng.normal(size=n),
        "x3": rng.normal(size=n),
        "c": rng.choice(["a", "b"], size=n),
    })
    y = pd.Series((df["x1"] + rng.normal(size=n) > 0).astype(int))
    out = feature_stability(_factory, df, y, cv_folds=3)
    assert {"feature", "importance", "importance_std",
            "cv_of_importance", "stable"}.issubset(out.table.columns)
    # Real signal feature x1 should show up among the higher-importance entries
    top = out.table.head(2)["feature"].astype(str).tolist()
    assert any("x1" in t for t in top)


# ---------- Mistake #6: vague hedging ----------

def test_mistake6_all_listed_hedge_phrases_blocked():
    for phrase in ("could indicate", "may suggest", "appears to",
                   "trending upward", "may impact"):
        assert verify_claim(f"X {phrase} Y").accepted is False


# ---------- Mistake #7: silent failure on synthetic data ----------

def test_mistake7_synthetic_data_is_flagged_loudly():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({f"x{i}": rng.normal(size=2000) for i in range(8)})
    df["y"] = rng.integers(0, 2, size=2000)
    rep = is_synthetic_or_random(df, target="y")
    assert rep.is_likely_synthetic is True
    # AUC on this dataset must collapse to ~0.5 — confirm no model fakes a win
    results = train_models(df.drop(columns=["y"]), df["y"], cv_folds=3)
    assert all(r.cv_mean < 0.6 for r in results.values())


# ---------- Mistake #8: invented numbers ----------

def test_mistake8_validation_report_numbers_match_actual_dataframe():
    """Every reported count must be a real computation, not an estimate."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "x": rng.normal(size=137),  # an unusual count to make estimation obvious
        "y": rng.integers(0, 2, size=137),
    })
    rep = validate_dataset(df)
    assert rep.n_rows == 137
    assert rep.n_cols == 2
    base = baseline_score(df["y"], "binary")
    expected = df["y"].value_counts(normalize=True).iloc[0]
    assert abs(base["baseline_accuracy"] - expected) < 1e-9


# ---------- End-to-end: pipeline says "no signal" rather than fabricating one ----------

def test_endtoend_pipeline_refuses_to_fabricate_insight_on_noise():
    rng = np.random.default_rng(7)
    n = 1500
    df = pd.DataFrame({f"x{i}": rng.normal(size=n) for i in range(6)})
    df["y"] = rng.integers(0, 2, size=n)

    rep = is_synthetic_or_random(df, target="y")
    assert rep.is_likely_synthetic is True

    # Per-feature univariate tests must come back non-significant
    for c in [c for c in df.columns if c != "y"]:
        r = numeric_vs_binary(df[c], df["y"])
        msg = format_finding(r)
        assert verify_claim(msg, evidence=r).accepted is True
        assert r.is_significant is False

    # And the model evaluator must annotate near-random AUC
    results = train_models(df.drop(columns=["y"]), df["y"], cv_folds=3)
    best = max(results.values(), key=lambda r: r.cv_mean)
    eval_res = evaluate_binary(df["y"].values, best.oof_predictions)
    assert eval_res.auc_roc < 0.6
    assert any("near random" in n.lower() for n in eval_res.notes)
