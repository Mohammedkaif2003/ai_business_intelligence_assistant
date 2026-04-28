"""Modeling layer — auto-detect task type, train multiple algorithms, return
a uniform result object. Works for any tabular dataset.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold, KFold, cross_val_score, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def detect_task_type(y: pd.Series) -> str:
    """Return 'binary' | 'multiclass' | 'regression'."""
    if pd.api.types.is_numeric_dtype(y) and y.nunique() > 20:
        return "regression"
    n_classes = y.nunique()
    if n_classes == 2:
        return "binary"
    if n_classes > 2:
        return "multiclass"
    raise ValueError("y has fewer than 2 distinct values")


@dataclass
class ModelResult:
    name: str
    cv_scores: np.ndarray
    cv_mean: float
    cv_std: float
    metric: str
    fitted_pipeline: Any = None
    oof_predictions: np.ndarray | None = None  # out-of-fold probabilities (binary)
    feature_names_out: list[str] = field(default_factory=list)


def _build_preprocessor(X: pd.DataFrame) -> tuple[ColumnTransformer, list[str], list[str]]:
    num_cols = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    cat_cols = [c for c in X.columns if c not in num_cols]
    transformers = []
    if num_cols:
        transformers.append(("num", StandardScaler(), num_cols))
    if cat_cols:
        try:
            ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        except TypeError:
            ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)
        transformers.append(("cat", ohe, cat_cols))
    pre = ColumnTransformer(transformers, remainder="drop")
    return pre, num_cols, cat_cols


def baseline_score(y: pd.Series, task: str) -> dict[str, float]:
    """Return baseline scores for the chosen task: majority class for
    classification, mean for regression.
    """
    if task in ("binary", "multiclass"):
        majority = y.value_counts(normalize=True).iloc[0]
        return {"baseline_accuracy": float(majority),
                "baseline_recall_positive": 0.0 if task == "binary" else float("nan")}
    y_ = y.astype(float).values
    rmse = float(np.sqrt(((y_ - y_.mean()) ** 2).mean()))
    return {"baseline_rmse": rmse, "baseline_mae": float(np.mean(np.abs(y_ - y_.mean())))}


def train_models(
    X: pd.DataFrame,
    y: pd.Series,
    task: str | None = None,
    cv_folds: int = 5,
    random_state: int = 42,
    handle_imbalance: bool = True,
) -> dict[str, ModelResult]:
    """Train Logistic/Ridge, RandomForest, GradientBoosting with CV.

    Returns dict keyed by algorithm name. Out-of-fold probabilities are
    captured for binary classification so calibration can be measured.
    """
    task = task or detect_task_type(y)
    pre, num_cols, cat_cols = _build_preprocessor(X)

    if task == "binary":
        cw = "balanced" if handle_imbalance else None
        models = {
            "logistic_l2": LogisticRegression(
                penalty="l2", C=1.0, solver="liblinear",
                class_weight=cw, max_iter=1000, random_state=random_state),
            "random_forest": RandomForestClassifier(
                n_estimators=300, max_depth=None, n_jobs=-1,
                class_weight=cw, random_state=random_state),
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=200, max_depth=3, learning_rate=0.1,
                random_state=random_state),
        }
        metric = "roc_auc"
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    elif task == "multiclass":
        cw = "balanced" if handle_imbalance else None
        models = {
            "logistic_l2": LogisticRegression(
                penalty="l2", C=1.0, solver="lbfgs",
                class_weight=cw, max_iter=1000, multi_class="auto",
                random_state=random_state),
            "random_forest": RandomForestClassifier(
                n_estimators=300, n_jobs=-1, class_weight=cw,
                random_state=random_state),
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=200, max_depth=3, random_state=random_state),
        }
        metric = "f1_macro"
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    else:
        models = {
            "ridge": Ridge(alpha=1.0, random_state=random_state),
            "random_forest": RandomForestRegressor(
                n_estimators=300, n_jobs=-1, random_state=random_state),
            "gradient_boosting": GradientBoostingRegressor(
                n_estimators=200, random_state=random_state),
        }
        metric = "neg_root_mean_squared_error"
        cv = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)

    results: dict[str, ModelResult] = {}
    for name, est in models.items():
        pipe = Pipeline([("pre", pre), ("est", est)])
        scores = cross_val_score(pipe, X, y, scoring=metric, cv=cv, n_jobs=-1)
        oof = None
        if task == "binary":
            try:
                oof = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba", n_jobs=-1)[:, 1]
            except Exception:
                oof = None
        pipe.fit(X, y)
        try:
            feature_names = list(pipe.named_steps["pre"].get_feature_names_out())
        except Exception:
            feature_names = []
        results[name] = ModelResult(
            name=name,
            cv_scores=scores,
            cv_mean=float(scores.mean()),
            cv_std=float(scores.std()),
            metric=metric,
            fitted_pipeline=pipe,
            oof_predictions=oof,
            feature_names_out=feature_names,
        )
    return results
