"""Claim verification layer — gatekeeper for any text describing the data.

Every human-readable finding must pass `verify_claim(claim, evidence)` before
being printed or written to a report. The verifier enforces three things:

  1. Banned hedging phrases without supporting test statistics are rejected.
  2. A relationship/trend claim must carry p_value, effect_size, and n.
  3. p > 0.05 claims must be framed as "no significant relationship found"
     rather than asserted.

Use `format_finding(stat_result)` to produce a guardrail-compliant string
directly from a StatResult — this is the recommended path.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any
from .stats import StatResult


BANNED_PHRASES: tuple[str, ...] = (
    "could indicate",
    "may indicate",
    "may suggest",
    "could suggest",
    "appears to",
    "seems to",
    "trending up",
    "trending down",
    "trending upward",
    "trending downward",
    "trends up",
    "trends down",
    "trends upward",
    "trends downward",
    "tends to",
    "may impact",
    "could impact",
    "likely impacts",
    "is correlated with",  # without numbers; safe form is "r=... p=..."
)

# Words that imply a directional / temporal claim — these REQUIRE supporting stats.
DIRECTIONAL_WORDS: tuple[str, ...] = (
    "increase", "increases", "increasing", "increased",
    "decrease", "decreases", "decreasing", "decreased",
    "trend", "trends", "trending",
    "impact", "impacts", "drives", "causes", "leads to",
    "correlated", "correlation",
    "associated", "association",
    "predicts", "predictive",
)

_NUMBER_RE = re.compile(r"\b\d+\.?\d*([eE][+-]?\d+)?\b")
_PVAL_RE = re.compile(r"\bp\s*[=<>]\s*\d", re.IGNORECASE)


class ClaimRejectedError(ValueError):
    """Raised when a claim fails guardrail verification."""


@dataclass
class VerificationResult:
    accepted: bool
    reasons: list[str]
    rewritten: str | None = None


def _has_banned_phrase(text: str) -> list[str]:
    lower = text.lower()
    return [p for p in BANNED_PHRASES if p in lower]


def _is_directional_claim(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in DIRECTIONAL_WORDS)


def _has_supporting_stats(text: str, evidence: dict[str, Any] | None) -> bool:
    """A claim is supported if either the text itself contains p-value/effect-size
    numbers, or the evidence dict supplies them (and is_significant=True).
    """
    if evidence is not None:
        required = {"p_value", "effect_size", "n"}
        if required.issubset(evidence.keys()) and evidence.get("is_significant", False):
            return True
    return bool(_PVAL_RE.search(text)) and bool(_NUMBER_RE.search(text))


def verify_claim(
    claim: str,
    evidence: dict[str, Any] | StatResult | None = None,
    raise_on_failure: bool = False,
) -> VerificationResult:
    """Check a claim against guardrails. Returns VerificationResult.

    evidence: a StatResult or dict with at least p_value, effect_size, n,
    is_significant. If absent, claim is verified by text content only.
    """
    if isinstance(evidence, StatResult):
        evidence = evidence.to_dict()

    reasons: list[str] = []

    banned = _has_banned_phrase(claim)
    if banned:
        reasons.append(f"banned hedging phrase(s): {banned}")

    directional = _is_directional_claim(claim)
    if directional and not _has_supporting_stats(claim, evidence):
        reasons.append(
            "directional/causal claim without supporting p-value, effect size, or n"
        )

    # If evidence says NOT significant but the claim asserts a relationship, reject.
    _NEG_PATTERNS = ("no significant", "not significant", "non-significant",
                     "no statistically significant", "not statistically significant",
                     "no relationship", "no association")
    if evidence is not None and not evidence.get("is_significant", False):
        lower = claim.lower()
        has_negation = any(p in lower for p in _NEG_PATTERNS)
        if directional and not has_negation:
            reasons.append(
                "evidence shows non-significant result but claim asserts a relationship; "
                "reframe as 'no significant relationship found'"
            )

    accepted = not reasons
    rewritten = None
    if not accepted and isinstance(evidence, dict) and {"p_value", "effect_size", "n"}.issubset(evidence):
        rewritten = format_finding(StatResult(**{
            **{k: evidence[k] for k in
               ("test_name", "feature", "statistic", "p_value", "effect_size",
                "effect_size_name", "n", "is_significant", "direction")},
            "notes": evidence.get("notes", "")
        }))

    if not accepted and raise_on_failure:
        raise ClaimRejectedError("; ".join(reasons))

    return VerificationResult(accepted=accepted, reasons=reasons, rewritten=rewritten)


def format_finding(r: StatResult) -> str:
    """Produce a guardrail-compliant one-line finding from a StatResult."""
    if not r.is_significant:
        return (
            f"No statistically significant association between '{r.feature}' and target "
            f"({r.test_name}: stat={r.statistic:.3f}, p={r.p_value:.4g}, "
            f"{r.effect_size_name}={r.effect_size:.4f}, n={r.n}). "
            f"Effect size below threshold or p>=0.05."
        )
    direction_phrase = (f"a {r.direction} association"
                        if r.direction in ("positive", "negative")
                        else "an association")
    return (
        f"Feature '{r.feature}' has {direction_phrase} with target "
        f"({r.test_name}: stat={r.statistic:.3f}, p={r.p_value:.4g}, "
        f"{r.effect_size_name}={r.effect_size:.4f}, n={r.n})."
        + (f" {r.notes}" if r.notes else "")
    )
