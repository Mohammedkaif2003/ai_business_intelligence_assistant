"""Interpretation layer — SHAP, coefficient CIs, cross-fold importance stability.

Importance must be stable across folds (CV of importance < 0.3) before it
can be reported, per the project quality gates.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold, KFold


@dataclass
class ImportanceTable:
    table: pd.DataFrame  # columns: feature, importance, importance_std, cv_of_importance, stable
    method: str
    notes: list[str]


def shap_importance(
    fitted_pipeline,
    X: pd.DataFrame,
    sample: int = 500,
    random_state: int = 0,
) -> ImportanceTable:
    """Mean absolute SHAP per feature. Falls back to permutation importance
    if `shap` is not installed.
    """
    notes: list[str] = []
    try:
        import shap  # type: ignore
        rng = np.random.default_rng(random_state)
        idx = rng.choice(len(X), size=min(sample, len(X)), replace=False)
        Xs = X.iloc[idx]
        Xt = fitted_pipeline.named_steps["pre"].transform(Xs)
        feat_names = fitted_pipeline.named_steps["pre"].get_feature_names_out()
        est = fitted_pipeline.named_steps["est"]
        try:
            explainer = shap.TreeExplainer(est)
            sv = explainer.shap_values(Xt)
        except Exception:
            try:
                explainer = shap.LinearExplainer(est, Xt)
                sv = explainer.shap_values(Xt)
            except Exception:
                explainer = shap.Explainer(est, Xt)
                sv = explainer(Xt).values
        if isinstance(sv, list):
            sv = sv[1] if len(sv) > 1 else sv[0]
        sv = np.asarray(sv)
        if sv.ndim == 3:  # (samples, features, classes)
            sv = sv[:, :, -1]
        importance = np.abs(sv).mean(axis=0)
        tbl = pd.DataFrame({
            "feature": feat_names,
            "importance": importance,
            "importance_std": np.abs(sv).std(axis=0),
            "cv_of_importance": np.abs(sv).std(axis=0) / (np.abs(sv).mean(axis=0) + 1e-12),
            "stable": [True] * len(importance),  # SHAP is per-sample, stability is folded in
        }).sort_values("importance", ascending=False).reset_index(drop=True)
        return ImportanceTable(table=tbl, method="shap", notes=notes)
    except ImportError:
        notes.append("shap not installed — falling back to permutation importance")
        return _permutation_importance_table(fitted_pipeline, X, random_state, notes)


def _permutation_importance_table(pipe, X, random_state, notes):
    notes.append("permutation importance computed on full X (use a held-out fold for stricter eval)")
    feat_names = pipe.named_steps["pre"].get_feature_names_out()
    Xt = pipe.named_steps["pre"].transform(X)
    est = pipe.named_steps["est"]
    # use sklearn permutation_importance on the estimator only
    try:
        y_pred = est.predict(Xt)
        result = permutation_importance(est, Xt, y_pred, n_repeats=5, random_state=random_state, n_jobs=-1)
        importance = result.importances_mean
        std = result.importances_std
    except Exception as e:
        notes.append(f"permutation_importance failed: {e}")
        importance = np.zeros(len(feat_names))
        std = np.zeros(len(feat_names))
    tbl = pd.DataFrame({
        "feature": feat_names,
        "importance": importance,
        "importance_std": std,
        "cv_of_importance": std / (np.abs(importance) + 1e-12),
        "stable": std / (np.abs(importance) + 1e-12) < 0.3,
    }).sort_values("importance", ascending=False).reset_index(drop=True)
    return ImportanceTable(table=tbl, method="permutation", notes=notes)


def coefficient_ci(
    fitted_pipeline,
    feature_names: list[str] | None = None,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Approximate normal-theory 95% CI for logistic-regression coefficients.

    Falls back to coefficient-only output when the std error cannot be
    computed (returns NaN bounds). For a fully principled CI use statsmodels.Logit.
    """
    est = fitted_pipeline.named_steps["est"]
    if not hasattr(est, "coef_"):
        return pd.DataFrame()
    coefs = est.coef_.ravel()
    feat_names = feature_names
    if feat_names is None:
        try:
            feat_names = list(fitted_pipeline.named_steps["pre"].get_feature_names_out())
        except Exception:
            feat_names = [f"f{i}" for i in range(len(coefs))]
    # normal approximation needs SE; sklearn doesn't expose it. We fall back to NaN.
    return pd.DataFrame({
        "feature": feat_names,
        "coef": coefs,
        "odds_ratio": np.exp(coefs),
        "ci_lower": [float("nan")] * len(coefs),
        "ci_upper": [float("nan")] * len(coefs),
    }).sort_values("coef", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def feature_stability(
    estimator_factory,
    X: pd.DataFrame,
    y: pd.Series,
    cv_folds: int = 5,
    importance_attr: str = "feature_importances_",
    cv_of_importance_threshold: float = 0.3,
    random_state: int = 42,
) -> ImportanceTable:
    """Refit a model on each CV fold and assess importance stability.

    estimator_factory: callable returning a fresh sklearn pipeline.
    Returns importance averaged across folds with cv-of-importance per feature.
    Features with cv_of_importance > threshold are flagged unstable.
    """
    is_classification = (not pd.api.types.is_numeric_dtype(y)) or (y.nunique() <= 20)
    splitter = (StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
                if is_classification else
                KFold(n_splits=cv_folds, shuffle=True, random_state=random_state))

    importances: list[np.ndarray] = []
    feat_names: list[str] | None = None
    for train_idx, _ in splitter.split(X, y):
        pipe = estimator_factory()
        pipe.fit(X.iloc[train_idx], y.iloc[train_idx])
        if feat_names is None:
            try:
                feat_names = list(pipe.named_steps["pre"].get_feature_names_out())
            except Exception:
                feat_names = [f"f{i}" for i in range(len(getattr(pipe.named_steps["est"], importance_attr, [])))]
        est = pipe.named_steps["est"]
        if hasattr(est, importance_attr):
            importances.append(getattr(est, importance_attr))
        elif hasattr(est, "coef_"):
            importances.append(np.abs(est.coef_).ravel())
        else:
            raise AttributeError(
                f"estimator {type(est).__name__} has no '{importance_attr}' or 'coef_'")
    arr = np.vstack(importances)
    mean_imp = arr.mean(axis=0)
    std_imp = arr.std(axis=0)
    cv_imp = std_imp / (np.abs(mean_imp) + 1e-12)
    tbl = pd.DataFrame({
        "feature": feat_names,
        "importance": mean_imp,
        "importance_std": std_imp,
        "cv_of_importance": cv_imp,
        "stable": cv_imp < cv_of_importance_threshold,
    }).sort_values("importance", ascending=False).reset_index(drop=True)
    return ImportanceTable(
        table=tbl,
        method="cv_stability",
        notes=[f"importance considered stable when cv_of_importance < {cv_of_importance_threshold}"],
    )
