import unittest
from datetime import datetime, timezone

from scripts.data_contract import STATUS_BLOCKED, STATUS_DEGRADED
from scripts.fetch_fundamentals import (
    build_metadata,
    build_monthly_revenue,
    build_quarterly_cash_flow,
    build_quarterly_income,
    build_valuation_band,
    pivot_statement,
    resolve_token,
)


class FundamentalsDerivedTests(unittest.TestCase):
    def test_resolve_token_requires_finmind_token(self):
        with self.assertRaisesRegex(RuntimeError, "FIN_MIND_TOKEN is required"):
            resolve_token(args_token=None, env={})

    def test_monthly_revenue_requires_complete_cumulative_yoy_window(self):
        rows = [
            {"revenue_year": "2025", "revenue_month": "01", "revenue": 100},
            {"revenue_year": "2025", "revenue_month": "02", "revenue": 110},
            {"revenue_year": "2026", "revenue_month": "01", "revenue": 120},
            {"revenue_year": "2026", "revenue_month": "02", "revenue": 150},
        ]

        result = build_monthly_revenue(rows, months=2)

        self.assertEqual(result[-1]["month"], "2026/02")
        self.assertEqual(result[-1]["mom_pct"], 25.0)
        self.assertEqual(result[-1]["yoy_pct"], 36.36)
        self.assertEqual(result[-1]["cumulative_yoy_pct"], 28.57)

    def test_quarterly_income_derives_margins_and_yoy(self):
        rows = [
            {"date": "2025-03-31", "type": "Revenue", "value": 1000, "origin_name": "營業收入"},
            {"date": "2025-03-31", "type": "GrossProfit", "value": 400, "origin_name": "營業毛利"},
            {"date": "2025-03-31", "type": "OperatingIncome", "value": 300, "origin_name": "營業利益"},
            {"date": "2025-03-31", "type": "EquityAttributableToOwnersOfParent", "value": 250, "origin_name": "母公司業主淨利"},
            {"date": "2026-03-31", "type": "Revenue", "value": 1200, "origin_name": "營業收入"},
            {"date": "2026-03-31", "type": "GrossProfit", "value": 540, "origin_name": "營業毛利"},
            {"date": "2026-03-31", "type": "OperatingIncome", "value": 360, "origin_name": "營業利益"},
            {"date": "2026-03-31", "type": "EquityAttributableToOwnersOfParent", "value": 300, "origin_name": "母公司業主淨利"},
        ]

        result = build_quarterly_income(pivot_statement(rows))

        self.assertEqual(result[-1]["quarter"], "2026Q1")
        self.assertEqual(result[-1]["gross_margin_pct"], 45.0)
        self.assertEqual(result[-1]["revenue_yoy_pct"], 20.0)

    def test_cash_flow_derives_fcf_with_capex_outflow(self):
        rows = [
            {"date": "2026-03-31", "type": "CashFlowsFromOperatingActivities", "value": 500, "origin_name": "營業活動"},
            {"date": "2026-03-31", "type": "PropertyAndPlantAndEquipment", "value": -200, "origin_name": "取得不動產、廠房及設備"},
        ]

        result = build_quarterly_cash_flow(pivot_statement(rows))

        self.assertEqual(result[0]["free_cash_flow"], 300)

    def test_valuation_band_ignores_non_positive_multiples(self):
        rows = [
            {"date": "2026-01-02", "PER": 10.0, "PBR": 2.0, "dividend_yield": 3.0},
            {"date": "2026-01-03", "PER": 0.0, "PBR": 2.5, "dividend_yield": 3.0},
            {"date": "2026-01-04", "PER": 30.0, "PBR": 3.0, "dividend_yield": 3.0},
        ]

        result = build_valuation_band(rows)

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["windows"]["1y"]["per"]["min"], 10.0)
        self.assertEqual(result["windows"]["1y"]["per"]["max"], 30.0)

    def test_metadata_blocks_missing_required_dataset_and_degrades_missing_optional(self):
        counts = {
            "TaiwanStockMonthRevenue": 1,
            "TaiwanStockFinancialStatements": 1,
            "TaiwanStockBalanceSheet": 0,
            "TaiwanStockCashFlowsStatement": 0,
            "TaiwanStockPER": 0,
        }

        degraded = build_metadata(
            "2330",
            "2021-07-11",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in counts.items()},
            fetched_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        )
        blocked_counts = dict(counts, TaiwanStockMonthRevenue=0)
        blocked = build_metadata(
            "2330",
            "2021-07-11",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in blocked_counts.items()},
        )

        self.assertEqual(degraded["status"], STATUS_DEGRADED)
        self.assertEqual(blocked["status"], STATUS_BLOCKED)


if __name__ == "__main__":
    unittest.main()
