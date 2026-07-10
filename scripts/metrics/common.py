"""Shared MetricResult type and validity helpers for deterministic metrics.

Every metric function in financial_quality.py / market_confirmation.py
returns a MetricResult rather than a bare number or raising an exception on
an invalid denominator. `state` distinguishes "unavailable" (a required
input is missing) from "not_meaningful" (inputs are present but the formula
does not produce a sensible answer, e.g. a non-positive denominator) so a
template can display an honest caveat instead of a fabricated zero.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import List, Optional

STATE_READY = "ready"
STATE_UNAVAILABLE = "unavailable"
STATE_NOT_MEANINGFUL = "not_meaningful"


@dataclass(frozen=True)
class MetricResult:
    metric_id: str
    evidence_family: str
    value: Optional[Decimal]
    unit: str
    period: str
    formula_version: str
    input_refs: List[str]
    state: str
    missing_reason: Optional[str]
    confidence: str


def to_decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def safe_divide(numerator, denominator):
    """Decimal quotient, or None when either input is missing or the
    denominator is exactly zero. Callers decide whether a zero/negative
    denominator makes the result merely unavailable or not_meaningful."""
    numerator = to_decimal(numerator)
    denominator = to_decimal(denominator)
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def ready(metric_id, evidence_family, value, unit, period, formula_version, input_refs, confidence="medium"):
    return MetricResult(
        metric_id=metric_id,
        evidence_family=evidence_family,
        value=value,
        unit=unit,
        period=period,
        formula_version=formula_version,
        input_refs=list(input_refs),
        state=STATE_READY,
        missing_reason=None,
        confidence=confidence,
    )


def unavailable(metric_id, evidence_family, unit, period, formula_version, input_refs, reason, confidence="low"):
    return MetricResult(
        metric_id=metric_id,
        evidence_family=evidence_family,
        value=None,
        unit=unit,
        period=period,
        formula_version=formula_version,
        input_refs=list(input_refs),
        state=STATE_UNAVAILABLE,
        missing_reason=reason,
        confidence=confidence,
    )


def not_meaningful(metric_id, evidence_family, unit, period, formula_version, input_refs, reason, confidence="low"):
    return MetricResult(
        metric_id=metric_id,
        evidence_family=evidence_family,
        value=None,
        unit=unit,
        period=period,
        formula_version=formula_version,
        input_refs=list(input_refs),
        state=STATE_NOT_MEANINGFUL,
        missing_reason=reason,
        confidence=confidence,
    )


def metric_result_to_dict(result):
    """JSON-serializable form of a MetricResult (Decimal -> float)."""
    return {
        "metric_id": result.metric_id,
        "evidence_family": result.evidence_family,
        "value": float(result.value) if result.value is not None else None,
        "unit": result.unit,
        "period": result.period,
        "formula_version": result.formula_version,
        "input_refs": list(result.input_refs),
        "state": result.state,
        "missing_reason": result.missing_reason,
        "confidence": result.confidence,
    }
