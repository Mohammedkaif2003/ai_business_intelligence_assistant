"""Statistical test layer.

Every test returns a StatResult with: statistic, p_value, effect_size,
effect_size_name, n, is_significant, interpretation. No claim is ever
returned without all of these populated.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats as _sp


@dataclass
class StatResult:
    test_name: str
    feature: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    n: int
    is_significant: bool
    direction: str  # "positive" / "negative" / "none"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------- Effect size utilities ----------

def cohens_d(group1: np.ndarray, group0: np.ndarray) -> float:
    n1, n0 = len(group1), len(group0)
    if n1 < 2 or n0 < 2:
        return float("nan")
    s1, s0 = group1.std(ddof=1), group0.std(ddof=1)
    pooled_var = ((n1 - 1) * s1 ** 2 + (n0 - 1) * s0 ** 2) / (n1 + n0 - 2)
    if pooled_var <= 0:
        return 0.0
    return float((group1.mean() - group0.mean()) / np.sqrt(pooled_var))


def cramers_v(contingency: np.ndarray) -> tuple[float, float, float, int]:
    """Return (chi2, p, V, dof)."""
    chi2, p, dof, _ = _sp.chi2_contingency(contingency)
    n = contingency.sum()
    k = min(contingency.shape) - 1
    v = float(np.sqrt(chi2 / (n * k))) if k > 0 and n > 0 else 0.0
    return float(chi2), float(p), v, int(dof)


# ---------- Public API ----------

def numeric_vs_binary(
    x: pd.Series,
    y: pd.Series,
    alpha: float = 0.05,
    min_effect_size: float = 0.1,
) -> StatResult:
    """Welch t-test + Cohen's d + point-biserial r between numeric x and binary y.

    A predictor is flagged significant only if BOTH p < alpha and |d| >= min_effect_size.
    """
    mask = x.notna() & y.notna()
    x_, y_ = x[mask].astype(float).values, y[mask].astype(int).values
    if set(np.unique(y_)) - {0, 1}:
        raise ValueError(f"y must be 0/1 binary, got values {set(np.unique(y_))}")
    g1 = x_[y_ == 1]
    g0 = x_[y_ == 0]
    if len(g1) < 2 or len(g0) < 2:
        return StatResult("welch_t", x.name or "?", float("nan"), 1.0, 0.0,
                          "cohen_d", int(mask.sum()), False, "none",
                          "insufficient samples in one group")
    t_stat, p = _sp.ttest_ind(g1, g0, equal_var=False)
    d = cohens_d(g1, g0)
    r_pb, _ = _sp.pointbiserialr(y_, x_)
    sig = (p < alpha) and (abs(d) >= min_effect_size)
    direction = "positive" if d > 0 else ("negative" if d < 0 else "none")
    return StatResult(
        test_name="welch_t",
        feature=str(x.name),
        statistic=float(t_stat),
        p_value=float(p),
        effect_size=float(d),
        effect_size_name="cohen_d",
        n=int(mask.sum()),
        is_significant=bool(sig),
        direction=direction,
        notes=f"point-biserial r={r_pb:.4f}; mean(y=1)={g1.mean():.4f}, mean(y=0)={g0.mean():.4f}",
    )


def categorical_vs_binary(
    x: pd.Series,
    y: pd.Series,
    alpha: float = 0.05,
    min_effect_size: float = 0.1,
) -> StatResult:
    """Chi-square + Cramér's V between categorical x and binary y."""
    mask = x.notna() & y.notna()
    x_, y_ = x[mask], y[mask].astype(int)
    ct = pd.crosstab(x_, y_).values
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return StatResult("chi2", x.name or "?", 0.0, 1.0, 0.0,
                          "cramers_v", int(mask.sum()), False, "none",
                          "needs at least 2x2 contingency")
    chi2, p, v, dof = cramers_v(ct)
    sig = (p < alpha) and (v >= min_effect_size)
    return StatResult(
        test_name="chi2",
        feature=str(x.name),
        statistic=chi2,
        p_value=p,
        effect_size=v,
        effect_size_name="cramers_v",
        n=int(mask.sum()),
        is_significant=bool(sig),
        direction="none",
        notes=f"dof={dof}, levels={ct.shape[0]}",
    )


def numeric_vs_numeric(x: pd.Series, y: pd.Series, alpha: float = 0.05) -> dict[str, StatResult]:
    """Pearson + Spearman, both with p-values."""
    mask = x.notna() & y.notna()
    x_, y_ = x[mask].astype(float).values, y[mask].astype(float).values
    if len(x_) < 3:
        empty = StatResult("pearson", x.name or "?", float("nan"), 1.0, 0.0,
                           "pearson_r", int(mask.sum()), False, "none", "n<3")
        return {"pearson": empty, "spearman": empty}
    pr, pp = _sp.pearsonr(x_, y_)
    sr, sp_ = _sp.spearmanr(x_, y_)
    return {
        "pearson": StatResult("pearson", str(x.name), float(pr), float(pp), float(pr),
                              "pearson_r", int(mask.sum()), bool(pp < alpha and abs(pr) >= 0.1),
                              "positive" if pr > 0 else "negative" if pr < 0 else "none"),
        "spearman": StatResult("spearman", str(x.name), float(sr), float(sp_), float(sr),
                               "spearman_rho", int(mask.sum()),
                               bool(sp_ < alpha and abs(sr) >= 0.1),
                               "positive" if sr > 0 else "negative" if sr < 0 else "none"),
    }


def trend_test(series: pd.Series, alpha: float = 0.05) -> StatResult:
    """Mann-Kendall + linear regression on a time-ordered series.

    A trend is reportable only if BOTH Mann-Kendall p < alpha and the linear
    slope is non-trivial. Used to gate any 'trending up/down' language.
    """
    s = pd.Series(series).dropna().astype(float).values
    n = len(s)
    if n < 8:
        return StatResult("mann_kendall", series.name or "?", 0.0, 1.0, 0.0,
                          "mk_tau", n, False, "none",
                          "need n>=8 for Mann-Kendall")
    # Mann-Kendall S statistic
    S = 0
    for i in range(n - 1):
        S += np.sum(np.sign(s[i + 1:] - s[i]))
    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    z = (S - np.sign(S)) / np.sqrt(var_s) if var_s > 0 else 0.0
    p_mk = 2 * (1 - _sp.norm.cdf(abs(z)))
    tau = S / (0.5 * n * (n - 1))

    x = np.arange(n)
    slope, intercept, r, p_lin, se = _sp.linregress(x, s)

    sig = bool((p_mk < alpha) and (p_lin < alpha))
    direction = "positive" if slope > 0 else "negative" if slope < 0 else "none"

    return StatResult(
        test_name="mann_kendall+linregress",
        feature=str(series.name) if series.name is not None else "series",
        statistic=float(z),
        p_value=float(max(p_mk, p_lin)),  # conservative — both must agree
        effect_size=float(tau),
        effect_size_name="kendall_tau",
        n=n,
        is_significant=sig,
        direction=direction,
        notes=(f"slope={slope:.6f}/step (p={p_lin:.4g}, R^2={r**2:.4f}); "
               f"MK z={z:.3f} p={p_mk:.4g} tau={tau:.4f}"),
    )
