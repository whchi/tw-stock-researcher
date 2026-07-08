import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_fundamentals as fetch_fundamentals
from scripts.fetch_fundamentals import (
    build_monthly_revenue,
    build_quarterly_cash_flow,
    build_quarterly_income,
    build_quarterly_key_items,
    build_valuation_band,
    default_output_path,
    pick_value,
    pivot_statement,
    resolve_token,
)


def make_income_rows():
    def quarter(date_str, revenue, gross, operating, net, eps):
        return [
            {"date": date_str, "stock_id": "2330", "type": "Revenue", "value": revenue, "origin_name": "營業收入"},
            {"date": date_str, "stock_id": "2330", "type": "GrossProfit", "value": gross, "origin_name": "營業毛利（毛損）"},
            {"date": date_str, "stock_id": "2330", "type": "OperatingIncome", "value": operating, "origin_name": "營業利益（損失）"},
            {"date": date_str, "stock_id": "2330", "type": "EquityAttributableToOwnersOfParent", "value": net, "origin_name": "母公司業主（淨利／損）"},
            {"date": date_str, "stock_id": "2330", "type": "EPS", "value": eps, "origin_name": "基本每股盈餘"},
        ]

    return quarter("2024-03-31", 1000.0, 400.0, 300.0, 250.0, 1.0) + quarter(
        "2025-03-31", 1200.0, 540.0, 380.0, 300.0, 1.2
    )


def make_cash_flow_rows():
    return [
        {
            "date": "2025-03-31",
            "stock_id": "2330",
            "type": "NetCashInflowFromOperatingActivities",
            "value": 999.0,
            "origin_name": "營運產生之現金流入（流出）",
        },
        {
            "date": "2025-03-31",
            "stock_id": "2330",
            "type": "CashFlowsFromOperatingActivities",
            "value": 500.0,
            "origin_name": "營業活動之淨現金流入（流出）",
        },
        {
            "date": "2025-03-31",
            "stock_id": "2330",
            "type": "PropertyAndPlantAndEquipment",
            "value": -200.0,
            "origin_name": "取得不動產、廠房及設備",
        },
    ]


def make_per_rows():
    values = [("2026-01-02", 10.0), ("2026-01-03", 0.0), ("2026-01-05", 20.0), ("2026-01-06", 30.0), ("2026-01-07", 40.0)]
    return [
        {"date": row_date, "stock_id": "2330", "PER": per, "PBR": 2.0, "dividend_yield": 3.0}
        for row_date, per in values
    ]


class OutputPathTests(unittest.TestCase):
    def test_default_output_path_uses_unique_case_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)

            output_path = default_output_path("2330", repo_root=repo_root)

            self.assertEqual(
                output_path,
                repo_root / "companies" / "2330-tsmc" / "fundamentals-data.json",
            )

    def test_default_output_path_falls_back_to_repo_root_without_unique_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()

            output_path = default_output_path("2330", repo_root=repo_root)

            self.assertEqual(output_path, repo_root / "2330_fundamentals_data.json")


class TokenTests(unittest.TestCase):
    def test_resolve_token_requires_fin_mind_token(self):
        with self.assertRaisesRegex(RuntimeError, 'export FIN_MIND_TOKEN="your_token_here"'):
            resolve_token(args_token=None, env={})


class PickValueTests(unittest.TestCase):
    def test_type_match_requires_origin_terms_to_disambiguate(self):
        by_date = pivot_statement(make_cash_flow_rows())
        items = by_date["2025-03-31"]

        value = pick_value(
            items,
            [{"type": "CashFlowsFromOperatingActivities", "origin_includes": ["營業活動"]}],
        )

        self.assertEqual(value, 500.0)

    def test_origin_fallback_matches_keywords_and_skips_percentage_rows(self):
        items = {
            "TotalAssetsCustom": {"value": 5000.0, "origin_name": "資產總額"},
            "TotalAssetsCustom_per": {"value": 100.0, "origin_name": "資產總額"},
        }

        value = pick_value(
            items,
            [{"type": "TotalAssets", "origin_includes": ["資產總額"]}],
        )

        self.assertEqual(value, 5000.0)


class QuarterlyIncomeTests(unittest.TestCase):
    def test_build_quarterly_income_derives_margins_and_yoy(self):
        by_date = pivot_statement(make_income_rows())

        rows = build_quarterly_income(by_date)

        self.assertEqual(rows[-1]["quarter"], "2025Q1")
        self.assertEqual(rows[-1]["revenue"], 1200.0)
        self.assertEqual(rows[-1]["gross_margin_pct"], 45.0)
        self.assertEqual(rows[-1]["operating_margin_pct"], 31.67)
        self.assertEqual(rows[-1]["net_margin_pct"], 25.0)
        self.assertEqual(rows[-1]["eps"], 1.2)
        self.assertEqual(rows[-1]["revenue_yoy_pct"], 20.0)
        self.assertEqual(rows[-1]["net_income_yoy_pct"], 20.0)
        self.assertIsNone(rows[0]["revenue_yoy_pct"])


class QuarterlyCashFlowTests(unittest.TestCase):
    def test_build_quarterly_cash_flow_derives_free_cash_flow(self):
        by_date = pivot_statement(make_cash_flow_rows())

        rows = build_quarterly_cash_flow(by_date)

        self.assertEqual(rows[-1]["operating_cash_flow"], 500.0)
        self.assertEqual(rows[-1]["capex"], -200.0)
        self.assertEqual(rows[-1]["free_cash_flow"], 300.0)


class MonthlyRevenueTests(unittest.TestCase):
    def test_build_monthly_revenue_derives_mom_yoy_and_cumulative(self):
        rows = [
            {"revenue_year": 2025, "revenue_month": month, "revenue": 100.0}
            for month in range(1, 13)
        ]
        rows += [
            {"revenue_year": 2026, "revenue_month": 1, "revenue": 120.0},
            {"revenue_year": 2026, "revenue_month": 2, "revenue": 130.0},
        ]

        result = build_monthly_revenue(rows)

        latest = result[-1]
        self.assertEqual(latest["month"], "2026/02")
        self.assertEqual(latest["mom_pct"], 8.33)
        self.assertEqual(latest["yoy_pct"], 30.0)
        self.assertEqual(latest["cumulative_revenue"], 250.0)
        self.assertEqual(latest["cumulative_yoy_pct"], 25.0)

    def test_cumulative_yoy_is_withheld_when_either_year_is_partial(self):
        rows = [
            {"revenue_year": 2025, "revenue_month": month, "revenue": 100.0}
            for month in range(6, 13)
        ]
        rows += [
            {"revenue_year": 2026, "revenue_month": 1, "revenue": 120.0},
            {"revenue_year": 2026, "revenue_month": 2, "revenue": 130.0},
        ]

        result = build_monthly_revenue(rows)

        latest = result[-1]
        self.assertEqual(latest["month"], "2026/02")
        self.assertIsNone(latest["cumulative_revenue"])
        self.assertIsNone(latest["cumulative_yoy_pct"])


class ValuationBandTests(unittest.TestCase):
    def test_build_valuation_band_excludes_non_positive_values(self):
        result = build_valuation_band(make_per_rows())

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["current"]["per"], 40.0)

        one_year = result["windows"]["1y"]
        self.assertEqual(one_year["trading_days"], 5)
        self.assertEqual(one_year["per"]["min"], 10.0)
        self.assertEqual(one_year["per"]["max"], 40.0)
        self.assertEqual(one_year["per"]["median"], 25.0)
        self.assertEqual(one_year["per"]["current_percentile"], 100.0)

    def test_build_valuation_band_without_rows(self):
        self.assertEqual(build_valuation_band([]), {"status": "no_data"})


class FetchAllTests(unittest.TestCase):
    def test_fetch_all_builds_derived_layers_and_warns_on_empty_datasets(self):
        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None, session=None):
            if dataset == "TaiwanStockMonthRevenue":
                return [
                    {
                        "date": "2026-05-01",
                        "stock_id": stock_id,
                        "revenue": 100.0,
                        "revenue_month": 4,
                        "revenue_year": 2026,
                    }
                ]
            if dataset == "TaiwanStockPER":
                return [
                    {
                        "date": "2026-05-05",
                        "stock_id": stock_id,
                        "PER": 15.0,
                        "PBR": 2.0,
                        "dividend_yield": 3.0,
                    }
                ]
            return []

        with patch.object(
            fetch_fundamentals, "fetch_dataset", side_effect=fake_fetch_dataset
        ):
            result = fetch_fundamentals.fetch_all(
                "2330", "2021-05-05", "2026-05-05", token="token"
            )

        self.assertIn(
            "TaiwanStockFinancialStatements returned no rows",
            result["metadata"]["warnings"],
        )
        self.assertEqual(result["raw"]["financial_statements"], [])
        self.assertEqual(result["derived"]["monthly_revenue_6m"][0]["month"], "2026/04")
        self.assertEqual(result["derived"]["valuation_band"]["current"]["per"], 15.0)
        self.assertEqual(result["derived"]["quarterly_income_8q"], [])


if __name__ == "__main__":
    unittest.main()
