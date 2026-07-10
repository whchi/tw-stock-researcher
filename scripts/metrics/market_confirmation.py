"""Deterministic normalized market/ownership metric families.

Same MetricResult contract as scripts/metrics/financial_quality.py: explicit
`ready` / `unavailable` / `not_meaningful` states instead of exceptions or
fabricated zeroes.
"""

from decimal import Decimal

from scripts.metrics.common import not_meaningful, ready, safe_divide, to_decimal, unavailable

FORMULA_VERSION = "1"

FAMILY_SHORT_PRESSURE = "short_interest_pressure"
FAMILY_RELATIVE_PERFORMANCE = "relative_performance"
FAMILY_OWNERSHIP_CONCENTRATION = "ownership_concentration"


def normalized_short_pressure(short_balance, securities_lending_sold_balance, free_float_shares, period, input_refs):
    short_v = to_decimal(short_balance)
    lending_v = to_decimal(securities_lending_sold_balance)
    free_float_v = to_decimal(free_float_shares)
    if short_v is None or lending_v is None or free_float_v is None:
        return unavailable(
            "NormalizedShortPressure", FAMILY_SHORT_PRESSURE, "ratio", period, FORMULA_VERSION, input_refs,
            "missing short balance, securities-lending sold balance, or free-float shares",
        )
    if free_float_v <= 0:
        return unavailable(
            "NormalizedShortPressure", FAMILY_SHORT_PRESSURE, "ratio", period, FORMULA_VERSION, input_refs,
            "insufficient free float",
        )
    return ready("NormalizedShortPressure", FAMILY_SHORT_PRESSURE, (short_v + lending_v) / free_float_v, "ratio", period, FORMULA_VERSION, input_refs)


def days_to_cover(short_balance, median_20d_volume, period, input_refs):
    quotient = safe_divide(short_balance, median_20d_volume)
    if quotient is None:
        return unavailable(
            "DaysToCover", FAMILY_SHORT_PRESSURE, "days", period, FORMULA_VERSION, input_refs,
            "missing short balance or 20-day median volume, or volume is zero",
        )
    return ready("DaysToCover", FAMILY_SHORT_PRESSURE, quotient, "days", period, FORMULA_VERSION, input_refs)


def sector_relative_total_return(stock_return_pct, sector_return_pct, window_days, period, input_refs, corporate_action_adjusted):
    stock_v = to_decimal(stock_return_pct)
    sector_v = to_decimal(sector_return_pct)
    if stock_v is None or sector_v is None:
        return unavailable(
            "SectorRelativeReturn", FAMILY_RELATIVE_PERFORMANCE, "pct_total_return", period, FORMULA_VERSION, input_refs,
            "missing stock or sector return",
        )
    unit = "pct_total_return" if corporate_action_adjusted else "pct_price_return"
    return ready(f"SectorRelativeReturn{window_days}d", FAMILY_RELATIVE_PERFORMANCE, stock_v - sector_v, unit, period, FORMULA_VERSION, input_refs)


def tdcc_concentration_change(current_large_holder_pct, previous_large_holder_pct, weeks, period, input_refs, capital_action_adjusted):
    current_v = to_decimal(current_large_holder_pct)
    previous_v = to_decimal(previous_large_holder_pct)
    if current_v is None or previous_v is None:
        return unavailable(
            f"TDCCConcentrationChange{weeks}w", FAMILY_OWNERSHIP_CONCENTRATION, "pct", period, FORMULA_VERSION, input_refs,
            "missing current or previous large-holder custody share",
        )
    if not capital_action_adjusted:
        return not_meaningful(
            f"TDCCConcentrationChange{weeks}w", FAMILY_OWNERSHIP_CONCENTRATION, "pct", period, FORMULA_VERSION, input_refs,
            "not adjusted for capital actions; change would be misleading",
        )
    return ready(f"TDCCConcentrationChange{weeks}w", FAMILY_OWNERSHIP_CONCENTRATION, current_v - previous_v, "pct", period, FORMULA_VERSION, input_refs)
