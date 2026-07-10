import unittest
from decimal import Decimal

from scripts.metrics.common import STATE_NOT_MEANINGFUL, STATE_READY, STATE_UNAVAILABLE
from scripts.metrics.financial_quality import (
    cash_conversion,
    cash_flow_accrual,
    cash_conversion_cycle,
    dilution_adjusted_owner_earnings_cagr,
    diluted_share_growth,
    dio,
    dpo,
    dso,
    governance_disclosure_vector,
    incremental_roic,
    interest_coverage,
    net_debt_to_ebitda,
    owner_earnings,
)

REFS = ["fundamentals-data.json#/derived/quarterly_income_8q"]


class DsoDioDpoTests(unittest.TestCase):
    def test_dso_ready_with_positive_inputs(self):
        result = dso(accounts_receivable=100, revenue=1000, days_in_period=90, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("9"))

    def test_dso_unavailable_when_revenue_missing(self):
        result = dso(accounts_receivable=100, revenue=None, days_in_period=90, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)

    def test_dso_unavailable_when_revenue_zero(self):
        result = dso(accounts_receivable=100, revenue=0, days_in_period=90, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)

    def test_dio_ready(self):
        result = dio(inventories=200, cost_of_goods_sold=800, days_in_period=90, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("22.5"))

    def test_dpo_ready(self):
        result = dpo(accounts_payable=150, cost_of_goods_sold=800, days_in_period=90, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)

    def test_cash_conversion_cycle_sums_ready_components(self):
        result = cash_conversion_cycle(
            dso_days=Decimal("9"), dio_days=Decimal("22.5"), dpo_days=Decimal("16.875"), period="2026Q1", input_refs=REFS
        )
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("9") + Decimal("22.5") - Decimal("16.875"))

    def test_cash_conversion_cycle_unavailable_when_a_component_is_missing(self):
        result = cash_conversion_cycle(dso_days=Decimal("9"), dio_days=None, dpo_days=Decimal("5"), period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class IncrementalRoicTests(unittest.TestCase):
    def test_ready_with_positive_denominator(self):
        result = incremental_roic(
            nopat_t=150, nopat_t_minus_3=100, capex=200, depreciation_amortization=50, change_in_nowc=10,
            period="2026", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("50") / Decimal("160"))

    def test_not_meaningful_when_denominator_non_positive(self):
        result = incremental_roic(
            nopat_t=150, nopat_t_minus_3=100, capex=10, depreciation_amortization=50, change_in_nowc=0,
            period="2026", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)

    def test_unavailable_when_input_missing(self):
        result = incremental_roic(
            nopat_t=None, nopat_t_minus_3=100, capex=10, depreciation_amortization=50, change_in_nowc=0,
            period="2026", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class InterestCoverageTests(unittest.TestCase):
    def test_ready_with_positive_interest_expense(self):
        result = interest_coverage(ebit=500, interest_expense=50, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("10"))

    def test_not_meaningful_when_interest_expense_zero(self):
        result = interest_coverage(ebit=500, interest_expense=0, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)

    def test_unavailable_when_ebit_missing(self):
        result = interest_coverage(ebit=None, interest_expense=50, period="2026Q1", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class NetDebtToEbitdaTests(unittest.TestCase):
    def test_ready_with_positive_ebitda(self):
        result = net_debt_to_ebitda(net_debt=1000, ttm_ebitda=500, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("2"))

    def test_not_meaningful_when_ebitda_non_positive(self):
        result = net_debt_to_ebitda(net_debt=1000, ttm_ebitda=0, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)

    def test_not_meaningful_when_ebitda_negative(self):
        result = net_debt_to_ebitda(net_debt=1000, ttm_ebitda=-100, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)


class DilutedShareGrowthTests(unittest.TestCase):
    def test_ready_cagr(self):
        result = diluted_share_growth(diluted_shares_t=121, diluted_shares_t0=100, years=2, period="2024-2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertAlmostEqual(float(result.value), 0.10, places=4)

    def test_unavailable_when_base_shares_non_positive(self):
        result = diluted_share_growth(diluted_shares_t=121, diluted_shares_t0=0, years=2, period="2024-2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)

    def test_unavailable_when_years_non_positive(self):
        result = diluted_share_growth(diluted_shares_t=121, diluted_shares_t0=100, years=0, period="2024-2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class OwnerEarningsAndCashConversionTests(unittest.TestCase):
    def test_owner_earnings_ready(self):
        result = owner_earnings(operating_cash_flow=500, maintenance_capex_estimate=100, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("400"))

    def test_owner_earnings_unavailable_when_missing(self):
        result = owner_earnings(operating_cash_flow=None, maintenance_capex_estimate=100, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)

    def test_cash_conversion_ready(self):
        result = cash_conversion(free_cash_flow=300, net_income=250, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("300") / Decimal("250"))

    def test_cash_conversion_not_meaningful_when_net_income_non_positive(self):
        result = cash_conversion(free_cash_flow=300, net_income=0, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)

    def test_cash_conversion_not_meaningful_when_net_income_negative(self):
        result = cash_conversion(free_cash_flow=300, net_income=-50, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)


class CashFlowAccrualTests(unittest.TestCase):
    def test_ready(self):
        result = cash_flow_accrual(ttm_net_income=500, ttm_cfo=350, average_total_assets=2000, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_READY)
        self.assertEqual(result.value, Decimal("150") / Decimal("2000"))

    def test_unavailable_when_assets_non_positive(self):
        result = cash_flow_accrual(ttm_net_income=500, ttm_cfo=350, average_total_assets=0, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)

    def test_unavailable_when_missing_input(self):
        result = cash_flow_accrual(ttm_net_income=None, ttm_cfo=350, average_total_assets=2000, period="2026", input_refs=REFS)
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class DilutionAdjustedCompoundingTests(unittest.TestCase):
    def test_ready(self):
        result = dilution_adjusted_owner_earnings_cagr(
            owner_earnings_per_share_t=Decimal("12.1"), owner_earnings_per_share_t0=Decimal("10"), years=2,
            period="2024-2026", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_READY)
        self.assertAlmostEqual(float(result.value), 0.10, places=4)

    def test_not_meaningful_when_base_non_positive(self):
        result = dilution_adjusted_owner_earnings_cagr(
            owner_earnings_per_share_t=Decimal("12.1"), owner_earnings_per_share_t0=Decimal("-5"), years=2,
            period="2024-2026", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_NOT_MEANINGFUL)

    def test_unavailable_when_years_non_positive(self):
        result = dilution_adjusted_owner_earnings_cagr(
            owner_earnings_per_share_t=Decimal("12.1"), owner_earnings_per_share_t0=Decimal("10"), years=0,
            period="2024-2026", input_refs=REFS,
        )
        self.assertEqual(result.state, STATE_UNAVAILABLE)


class GovernanceDisclosureVectorTests(unittest.TestCase):
    def test_returns_independent_flags_not_a_collapsed_score(self):
        vector = governance_disclosure_vector(
            pledge_ratio=15.5,
            pre_announced_transfer_flag=False,
            modified_audit_opinion_flag=False,
            restatement_flag=True,
            penalty_flag=False,
            period="2026",
            input_refs=REFS,
        )
        self.assertIsInstance(vector, dict)
        self.assertIn("pledge_ratio", vector)
        self.assertIn("restatement", vector)
        # Every entry is its own MetricResult; there is no combined "score" key.
        self.assertNotIn("score", vector)
        self.assertNotIn("composite", vector)
        self.assertEqual(vector["pledge_ratio"].state, STATE_READY)
        self.assertEqual(vector["restatement"].value, Decimal("1"))

    def test_unavailable_flags_stay_independent_of_available_ones(self):
        vector = governance_disclosure_vector(
            pledge_ratio=None,
            pre_announced_transfer_flag=True,
            modified_audit_opinion_flag=None,
            restatement_flag=False,
            penalty_flag=False,
            period="2026",
            input_refs=REFS,
        )
        self.assertEqual(vector["pledge_ratio"].state, STATE_UNAVAILABLE)
        self.assertEqual(vector["modified_audit_opinion"].state, STATE_UNAVAILABLE)
        self.assertEqual(vector["pre_announced_transfer"].state, STATE_READY)


if __name__ == "__main__":
    unittest.main()
