"""Claim-verifier tests — prove the gatekeeper catches Mistakes #2, #3, #6:
banned hedging language, unsupported directional claims, and asserting a
relationship when the evidence says non-significant.
"""
import pytest
from pipeline.claim_verifier import (
    verify_claim, format_finding, ClaimRejectedError, BANNED_PHRASES,
)
from pipeline.stats import StatResult


def _sig_evidence():
    return StatResult(
        test_name="welch_t", feature="age", statistic=4.2, p_value=1e-5,
        effect_size=0.45, effect_size_name="cohen_d", n=1000,
        is_significant=True, direction="positive",
    )


def _nonsig_evidence():
    return StatResult(
        test_name="welch_t", feature="age", statistic=0.2, p_value=0.84,
        effect_size=0.005, effect_size_name="cohen_d", n=1000,
        is_significant=False, direction="none",
    )


def test_rejects_banned_hedging_phrase():
    """Mistake #6: vague hedging without supporting numbers."""
    res = verify_claim("Age could indicate higher readmission rates.")
    assert res.accepted is False
    assert any("banned hedging" in r for r in res.reasons)


def test_rejects_each_listed_banned_phrase():
    for phrase in ("could indicate", "may suggest", "appears to", "trending upward"):
        res = verify_claim(f"This metric {phrase} something.")
        assert res.accepted is False, f"failed for phrase: {phrase}"


def test_rejects_directional_claim_without_supporting_stats():
    """Mistake #3: correlation-as-causation without coefficients/p-values."""
    res = verify_claim("Length of stay increases readmission risk.")
    assert res.accepted is False
    assert any("without supporting" in r for r in res.reasons)


def test_accepts_directional_claim_with_inline_pvalue():
    res = verify_claim("Length of stay is positively associated with readmission (p=0.001, r=0.42).")
    assert res.accepted is True


def test_accepts_directional_claim_when_evidence_supplied():
    res = verify_claim(
        "Age has a positive association with the target.",
        evidence=_sig_evidence(),
    )
    assert res.accepted is True


def test_rejects_relationship_claim_when_evidence_is_nonsignificant():
    """Mistake #2: refusing to assert a relationship when stats say no."""
    res = verify_claim(
        "Age is associated with readmission.",
        evidence=_nonsig_evidence(),
    )
    assert res.accepted is False
    assert any("non-significant" in r for r in res.reasons)


def test_rewritten_finding_is_offered_when_claim_fails_with_evidence():
    res = verify_claim(
        "Age trends upward with readmission.",
        evidence=_sig_evidence(),
    )
    # banned phrase still trips it, but a rewritten compliant version is offered
    assert res.accepted is False
    assert res.rewritten is not None
    assert "p=" in res.rewritten


def test_format_finding_significant():
    out = format_finding(_sig_evidence())
    assert "p=" in out and "cohen_d=" in out and "n=1000" in out
    # the formatted output must itself pass the verifier
    assert verify_claim(out, evidence=_sig_evidence()).accepted is True


def test_format_finding_nonsignificant_uses_correct_framing():
    out = format_finding(_nonsig_evidence())
    assert "no statistically significant" in out.lower()
    assert verify_claim(out, evidence=_nonsig_evidence()).accepted is True


def test_raise_on_failure_raises():
    with pytest.raises(ClaimRejectedError):
        verify_claim("X may impact Y.", raise_on_failure=True)
