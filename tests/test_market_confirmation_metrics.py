import unittest
from decimal import Decimal

from scripts.metrics.common import STATE_NOT_MEANINGFUL, STATE_READY, STATE_UNAVAILABLE
from scripts.metrics.market_confirmation import (
    days_to_cover,
    normalized_short_pressure,
    sector_relative_total_return,
    tdcc_concentration_change,
)

REFS = ["market-data.json#/raw/margin_purchase_short_sale"]


class NormalizedShortPressureTests(unittest.TestCase):
    def test_ready_with_positive_free_float(self):
        result = normalized_short_pressure(
            short_balance=1000, securities_lending_sold_balance=500, free_float_shares=100000,
            period="2026-07-09", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("1500") / Decimal("100000"))

    def test_unavailable_when_free_float_missing(self):
        result = normalized_short_pressure(
            short_balance=1000, securities_lending_sold_balance=500, free_float_shares=None,
            period="2026-07-09", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_UNAVAILABLE)

    def test_unavailable_when_free_float_non_positive(self):
        result = normalized_short_pressure(
            short_balance=1000, securities_lending_sold_balance=500, free_float_shares=0,
            period="2026-07-09", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class DaysToCoverTests(unittest.TestCase):
    def test_ready(self):
        result = days_to_cover(short_balance=2000, median_20d_volume=500, period="2026-07-09", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("4"))

    def test_unavailable_when_volume_zero(self):
        result = days_to_cover(short_balance=2000, median_20d_volume=0, period="2026-07-09", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class SectorRelativeTotalReturnTests(unittest.TestCase):
    def test_ready_labeled_as_price_return_when_unadjusted(self):
        result = sector_relative_total_return(
            stock_return_pct=12.5, sector_return_pct=8.0, window_days=63, period="2026-07-09",
            input_refs=REFS, corporate_action_adjusted=False,
        )
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("4.5"))
        self.assertEqual(result.unit, "pct_price_return")

    def test_ready_labeled_as_total_return_when_adjusted(self):
        result = sector_relative_total_return(
            stock_return_pct=12.5, sector_return_pct=8.0, window_days=126, period="2026-07-09",
            input_refs=REFS, corporate_action_adjusted=True,
        )
        self.assertEqual(result.unit, "pct_total_return")

    def test_unavailable_when_returns_missing(self):
        result = sector_relative_total_return(
            stock_return_pct=None, sector_return_pct=8.0, window_days=63, period="2026-07-09",
            input_refs=REFS, corporate_action_adjusted=False,
        )
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class TdccConcentrationChangeTests(unittest.TestCase):
    def test_ready_when_capital_action_adjusted(self):
        result = tdcc_concentration_change(
            current_large_holder_pct=45.2, previous_large_holder_pct=43.0, weeks=4, period="2026-07-09",
            input_refs=REFS, capital_action_adjusted=True,
        )
        self.assertEqual(result.state, STATE_READY)
        self.assertAlmostEqual(float(result.value), 2.2, places=4)

    def test_not_meaningful_when_not_capital_action_adjusted(self):
        result = tdcc_concentration_change(
            current_large_holder_pct=45.2, previous_large_holder_pct=43.0, weeks=4, period="2026-07-09",
            input_refs=REFS, capital_action_adjusted=False,
        )
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)

    def test_unavailable_when_missing_input(self):
        result = tdcc_concentration_change(
            current_large_holder_pct=None, previous_large_holder_pct=43.0, weeks=4, period="2026-07-09",
            input_refs=REFS, capital_action_adjusted=True,
        )
        self.assertEqual(result.state, STATE_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
