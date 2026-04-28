"""Evaluation layer — task-appropriate metrics, calibration, bootstrap CIs."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_recall_fscore_support,
    confusion_matrix, brier_score_loss,
)


@dataclass
class BinaryEvalResult:
    auc_roc: float
    auc_pr: float
    brier: float
    threshold_table: pd.DataFrame
    confusion_at_default: dict[str, int]
    calibration_table: pd.DataFrame
    auc_roc_ci95: tuple[float, float]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "auc_roc": self.auc_roc,
            "auc_pr": self.auc_pr,
            "brier": self.brier,
            "auc_roc_ci95": self.auc_roc_ci95,
            "threshold_table": self.threshold_table.to_dict(orient="records"),
            "confusion_at_default": self.confusion_at_default,
            "calibration_table": self.calibration_table.to_dict(orient="records"),
            "notes": self.notes,
        }


def bootstrap_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    metric_fn=roc_auc_score,
    n_boot: int = 500,
    alpha: float = 0.05,
    random_state: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI for any binary scoring metric."""
    rng = np.random.default_rng(random_state)
    n = len(y_true)
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        try:
            stats.append(metric_fn(y_true[idx], y_score[idx]))
        except Exception:
            continue
    if not stats:
        return (float("nan"), float("nan"))
    lo = float(np.quantile(stats, alpha / 2))
    hi = float(np.quantile(stats, 1 - alpha / 2))
    return (lo, hi)


def evaluate_binary(
    y_true: np.ndarray | pd.Series,
    y_score: np.ndarray | pd.Series,
    thresholds: tuple[float, ...] = (0.2, 0.3, 0.4, 0.5, 0.6),
    n_calibration_bins: int = 10,
) -> BinaryEvalResult:
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score).astype(float)

    auc = float(roc_auc_score(y_true, y_score))
    auc_pr = float(average_precision_score(y_true, y_score))
    brier = float(brier_score_loss(y_true, y_score))
    auc_ci = bootstrap_ci(y_true, y_score, roc_auc_score)

    rows = []
    for t in thresholds:
        y_pred = (y_score >= t).astype(int)
        p, r, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", zero_division=0)
        rows.append({"threshold": t, "precision": p, "recall": r, "f1": f1,
                     "n_predicted_positive": int(y_pred.sum())})
    th_tbl = pd.DataFrame(rows)

    cm = confusion_matrix(y_true, (y_score >= 0.5).astype(int), labels=[0, 1])
    cm_dict = {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]),
               "fn": int(cm[1, 0]), "tp": int(cm[1, 1])}

    bins = np.linspace(0, 1, n_calibration_bins + 1)
    bin_idx = np.clip(np.digitize(y_score, bins) - 1, 0, n_calibration_bins - 1)
    cal_rows = []
    for b in range(n_calibration_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        cal_rows.append({
            "bin_lower": float(bins[b]),
            "bin_upper": float(bins[b + 1]),
            "n": int(mask.sum()),
            "mean_predicted": float(y_score[mask].mean()),
            "actual_rate": float(y_true[mask].mean()),
        })
    cal_tbl = pd.DataFrame(cal_rows)

    notes = []
    base_rate = y_true.mean()
    if auc < 0.55:
        notes.append(
            f"AUC={auc:.3f} is near random (0.5). Predictive value is minimal — "
            "treat any feature ranking with skepticism."
        )
    if abs(brier - base_rate * (1 - base_rate)) < 0.005:
        notes.append(
            f"Brier score ({brier:.4f}) is near the trivial floor "
            f"({base_rate * (1 - base_rate):.4f}); calibration carries little information."
        )

    return BinaryEvalResult(
        auc_roc=auc,
        auc_pr=auc_pr,
        brier=brier,
        threshold_table=th_tbl,
        confusion_at_default=cm_dict,
        calibration_table=cal_tbl,
        auc_roc_ci95=auc_ci,
        notes=notes,
    )
