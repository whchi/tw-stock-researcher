"""Strict data-availability metadata shared by generated research artifacts."""

import re
from datetime import date


DATE_FIELDS = {
    "date",
    "data_date",
    "observation_date",
    "period",
    "periods",
    "report_date",
    "release_date",
    "year",
    "years",
}


def _period_candidate(value):
    text = str(value).strip()
    patterns = (
        (r"^(20\d{2})[-/](\d{2})[-/](\d{2})", 3),
        (r"^(20\d{2})(\d{2})(\d{2})$", 3),
        (r"^(20\d{2})[-/](\d{2})$", 2),
        (r"^(20\d{2})\s*Q([1-4])$", 1),
        (r"^(20\d{2})$", 0),
    )
    for pattern, kind in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if not match:
            continue
        parts = tuple(int(part) for part in match.groups())
        if kind == 3:
            year, month, day = parts
            try:
                date(year, month, day)
            except ValueError:
                return None
            return (year, month, day), f"{year:04d}-{month:02d}-{day:02d}"
        if kind == 2:
            year, month = parts
            if month < 1 or month > 12:
                return None
            return (year, month, 0), f"{year:04d}-{month:02d}"
        if kind == 1:
            year, quarter = parts
            return (year, quarter * 3, 0), f"{year:04d}Q{quarter}"
        year = parts[0]
        return (year, 0, 0), f"{year:04d}"
    return None


def latest_observation_date(*values):
    candidates = []

    def collect(value, *, allow_scalar):
        if isinstance(value, dict):
            year = value.get("revenue_year")
            month = value.get("revenue_month")
            if year is not None and month is not None:
                collect(
                    f"{int(year):04d}-{int(month):02d}",
                    allow_scalar=True,
                )
            for key, nested in value.items():
                key_name = str(key).lower()
                is_date_field = key_name in DATE_FIELDS or key_name.endswith("_date")
                collect(nested, allow_scalar=is_date_field)
            return
        if isinstance(value, (list, tuple, set)):
            for nested in value:
                collect(nested, allow_scalar=allow_scalar)
            return
        if not allow_scalar:
            return
        candidate = _period_candidate(value)
        if candidate is not None:
            candidates.append(candidate)

    for value in values:
        collect(value, allow_scalar=not isinstance(value, dict))

    return max(candidates, default=(None, None))[1]


def build_data_availability(
    *,
    observation_date,
    source,
    missing_inputs=None,
    failure_reasons=None,
):
    missing = list(missing_inputs or [])
    failures = list(failure_reasons or [])
    is_partial = bool(missing or failures)
    status = (
        "unavailable"
        if observation_date is None
        else "partial"
        if is_partial
        else "available"
    )

    return {
        "status": status,
        "observation_date": observation_date,
        "source": source,
        "missing_inputs": missing,
        "failure_reasons": failures,
        "confidence_impact": (
            "none"
            if status == "available"
            else "downgrade"
            if status == "partial"
            else "block"
        ),
    }
