"""Period/unit/consolidation/restatement-aware source reconciliation.

Compares a canonical (official) metric value against a candidate (e.g.
FinMind secondary_aggregator) value only after unit, currency, period type,
consolidation scope, and restatement status all match. A conflict is
classified, never averaged. See docs/source-policy.md for the full
classification table and question-lifecycle rules.
"""

from decimal import Decimal

CLASSIFICATION_MATCH = "match"
CLASSIFICATION_ROUNDING = "rounding"
CLASSIFICATION_PERIOD_MISMATCH = "period_mismatch"
CLASSIFICATION_CONSOLIDATION_MISMATCH = "consolidation_mismatch"
CLASSIFICATION_RESTATEMENT = "restatement"
CLASSIFICATION_TRUE_CONFLICT = "true_conflict"
CLASSIFICATION_UNIT_MISMATCH = "unit_mismatch"


def reconcile_metric(canonical, candidate, tolerance):
    canonical_currency = canonical.get("currency", "TWD")
    candidate_currency = candidate.get("currency", "TWD")
    if canonical.get("unit") != candidate.get("unit") or canonical_currency != candidate_currency:
        return {
            "classification": CLASSIFICATION_UNIT_MISMATCH,
            "comparable": False,
            "detail": "unit or currency differs; cannot compare without conversion",
        }

    if canonical.get("period_type") != candidate.get("period_type") or canonical.get("period_key") != candidate.get(
        "period_key"
    ):
        return {
            "classification": CLASSIFICATION_PERIOD_MISMATCH,
            "comparable": False,
            "detail": "period type or period key differs",
        }

    if canonical.get("consolidation") != candidate.get("consolidation"):
        return {
            "classification": CLASSIFICATION_CONSOLIDATION_MISMATCH,
            "comparable": False,
            "detail": "consolidated vs. individual scope differs",
        }

    if bool(canonical.get("restated")) != bool(candidate.get("restated")):
        return {
            "classification": CLASSIFICATION_RESTATEMENT,
            "comparable": False,
            "detail": "restatement status differs; prefer the newer filing id, do not average",
        }

    canonical_value = Decimal(str(canonical["value"]))
    candidate_value = Decimal(str(candidate["value"]))

    if canonical_value == candidate_value:
        return {"classification": CLASSIFICATION_MATCH, "comparable": True, "diff_pct": Decimal("0")}

    if canonical_value == 0:
        diff_pct = None
    else:
        diff_pct = abs((candidate_value - canonical_value) / canonical_value)

    if diff_pct is not None and diff_pct <= tolerance:
        return {"classification": CLASSIFICATION_ROUNDING, "comparable": True, "diff_pct": diff_pct}

    return {"classification": CLASSIFICATION_TRUE_CONFLICT, "comparable": True, "diff_pct": diff_pct}
