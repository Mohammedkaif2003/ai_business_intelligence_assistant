"""Dataset-agnostic statistical pipeline with hallucination guardrails."""
from .validation import (
    validate_dataset,
    detect_data_type,
    check_temporal_structure,
    is_synthetic_or_random,
)
from .stats import (
    numeric_vs_binary,
    categorical_vs_binary,
    numeric_vs_numeric,
    trend_test,
    StatResult,
)
from .claim_verifier import (
    verify_claim,
    format_finding,
    BANNED_PHRASES,
    ClaimRejectedError,
)
from .modeling import detect_task_type, train_models, baseline_score
from .evaluation import evaluate_binary, bootstrap_ci
from .interpret import shap_importance, coefficient_ci, feature_stability

__all__ = [
    "validate_dataset", "detect_data_type", "check_temporal_structure", "is_synthetic_or_random",
    "numeric_vs_binary", "categorical_vs_binary", "numeric_vs_numeric", "trend_test", "StatResult",
    "verify_claim", "format_finding", "BANNED_PHRASES", "ClaimRejectedError",
    "detect_task_type", "train_models", "baseline_score",
    "evaluate_binary", "bootstrap_ci",
    "shap_importance", "coefficient_ci", "feature_stability",
]
