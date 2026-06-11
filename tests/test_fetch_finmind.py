import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_finmind as fetch_finmind
from scripts.fetch_finmind import (
    build_market_action_read,
    default_output_path,
    parse_args,
    resolve_token,
    summarize_institutional_flows,
)


PRICE_ROWS = [
    {"date": "2026-04-27", "stock_id": "2330", "Trading_Volume": 1000, "close": 100.0},
    {"date": "2026-04-28", "stock_id": "2330", "Trading_Volume": 1100, "close": 101.0},
    {"date": "2026-04-29", "stock_id": "2330", "Trading_Volume": 1200, "close": 102.0},
    {"date": "2026-04-30", "stock_id": "2330", "Trading_Volume": 1300, "close": 103.0},
    {"date": "2026-05-04", "stock_id": "2330", "Trading_Volume": 1400, "close": 104.0},
    {"date": "2026-05-05", "stock_id": "2330", "Trading_Volume": 2000, "close": 110.0},
]


INSTITUTIONAL_ROWS = [
    {"date": "2026-04-28", "stock_id": "2330", "name": "Foreign_Investor", "buy": 100, "sell": 50},
    {"date": "2026-04-29", "stock_id": "2330", "name": "Investment_Trust", "buy": 25, "sell": 50},
    {"date": "2026-04-30", "stock_id": "2330", "name": "Foreign_Investor", "buy": 200, "sell": 100},
    {"date": "2026-05-04", "stock_id": "2330", "name": "Foreign_Investor", "buy": 300, "sell": 100},
    {"date": "2026-05-05", "stock_id": "2330", "name": "Foreign_Investor", "buy": 5000, "sell": 3000},
    {"date": "2026-05-05", "stock_id": "2330", "name": "Investment_Trust", "buy": 1000, "sell": 1200},
    {"date": "2026-05-05", "stock_id": "2330", "name": "Dealer", "buy": 700, "sell": 400},
]


def make_price_rows(count, start_close=100.0, close_step=1.0, volume=1000):
    start = date(2026, 1, 1)
    return [
        {
            "date": (start + timedelta(days=index)).isoformat(),
            "stock_id": "2330",
            "Trading_Volume": volume,
            "Trading_turnover": 1.0,
            "close": start_close + index * close_step,
        }
        for index in range(count)
    ]


def make_holding_rows():
    return [
        {
            "date": "2026-01-01",
            "stock_id": "2330",
            "HoldingSharesLevel": "1-999",
            "people": 1000,
            "percent": 40.0,
            "unit": "股",
        },
        {
            "date": "2026-06-29",
            "stock_id": "2330",
            "HoldingSharesLevel": "1-999",
            "people": 700,
            "percent": 25.0,
            "unit": "股",
        },
    ]


def make_tdcc_holding_rows():
    return [
        {
            "date": "2026-06-05",
            "stock_id": "2330",
            "HoldingSharesLevel": "1",
            "people": 100,
            "shares": 100000,
            "percent": 1.0,
            "unit": "股",
        },
        {
            "date": "2026-06-05",
            "stock_id": "2330",
            "HoldingSharesLevel": "15",
            "people": 10,
            "shares": 7000000,
            "percent": 70.0,
            "unit": "股",
        },
        {
            "date": "2026-06-05",
            "stock_id": "2330",
            "HoldingSharesLevel": "17",
            "people": 1000,
            "shares": 10000000,
            "percent": 100.0,
            "unit": "股",
        },
    ]


class OutputPathTests(unittest.TestCase):
    def test_default_output_path_uses_unique_case_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)

            output_path = default_output_path("2330", repo_root=repo_root)

            self.assertEqual(output_path, repo_root / "companies" / "2330-tsmc" / "market-data.json")

    def test_default_output_path_falls_back_to_repo_root_without_unique_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()

            output_path = default_output_path("2330", repo_root=repo_root)

            self.assertEqual(output_path, repo_root / "2330_market_data.json")


class TokenTests(unittest.TestCase):
    def test_resolve_token_requires_fin_mind_token(self):
        with self.assertRaisesRegex(RuntimeError, 'export FIN_MIND_TOKEN="your_token_here"'):
            resolve_token(args_token=None, env={})

    def test_resolve_token_prefers_cli_token_over_environment(self):
        token = resolve_token(args_token="cli-token", env={"FIN_MIND_TOKEN": "env-token"})

        self.assertEqual(token, "cli-token")

    def test_resolve_token_reads_project_environment_name(self):
        token = resolve_token(args_token=None, env={"FIN_MIND_TOKEN": "env-token"})

        self.assertEqual(token, "env-token")

    def test_resolve_token_does_not_read_unconfigured_environment_name(self):
        with self.assertRaisesRegex(RuntimeError, 'export FIN_MIND_TOKEN="your_token_here"'):
            resolve_token(args_token=None, env={"FINMIND_TOKEN": "other-token"})


class ArgsTests(unittest.TestCase):
    def test_default_fetch_range_supports_swing_windows(self):
        args = parse_args(["2330"])

        self.assertEqual(args.days, 400)


class MarketActionReadTests(unittest.TestCase):
    def test_build_market_action_read_calculates_5d_price_volume_and_state(self):
        result = build_market_action_read(PRICE_ROWS, INSTITUTIONAL_ROWS)

        self.assertEqual(result["latest_date"], "2026-05-05")
        self.assertEqual(result["comparison_date"], "2026-04-27")
        self.assertAlmostEqual(result["price_5d_change_pct"], 10.0)
        self.assertAlmostEqual(result["volume_5d_change_pct"], 100.0)
        self.assertEqual(result["price_volume_read"], "price_up_volume_up")
        self.assertEqual(result["market_state"], "overheated")
        self.assertEqual(result["institutional_total_net_buy_sell"], 2425.0)

    def test_build_market_action_read_includes_1d_3d_5d_windows(self):
        result = build_market_action_read(PRICE_ROWS, INSTITUTIONAL_ROWS)

        one_day = result["windows"]["1d"]
        three_day = result["windows"]["3d"]
        five_day = result["windows"]["5d"]

        self.assertEqual(one_day["comparison_date"], "2026-05-04")
        self.assertAlmostEqual(one_day["price_change_pct"], 5.77)
        self.assertAlmostEqual(one_day["volume_change_pct"], 42.86)
        self.assertEqual(one_day["price_volume_read"], "price_up_volume_up")
        self.assertEqual(one_day["institutional_total_net_buy_sell"], 2100.0)

        self.assertEqual(three_day["comparison_date"], "2026-04-29")
        self.assertAlmostEqual(three_day["price_change_pct"], 7.84)
        self.assertAlmostEqual(three_day["volume_change_pct"], 66.67)
        self.assertEqual(three_day["institutional_total_net_buy_sell"], 2400.0)

        self.assertEqual(five_day["comparison_date"], "2026-04-27")
        self.assertAlmostEqual(five_day["price_change_pct"], 10.0)
        self.assertAlmostEqual(five_day["volume_change_pct"], 100.0)
        self.assertEqual(five_day["institutional_flows_by_name"]["Investment_Trust"]["net_buy_sell"], -225.0)

    def test_build_market_action_read_marks_insufficient_price_data(self):
        result = build_market_action_read(PRICE_ROWS[:2], INSTITUTIONAL_ROWS)

        self.assertEqual(result["market_state"], "insufficient_data")
        self.assertIn("Need at least 6 trading rows", result["warnings"])

    def test_summarize_institutional_flows_groups_by_name(self):
        result = summarize_institutional_flows(INSTITUTIONAL_ROWS)

        self.assertEqual(result["by_name"]["Foreign_Investor"]["net_buy_sell"], 2350.0)
        self.assertEqual(result["by_name"]["Investment_Trust"]["net_buy_sell"], -225.0)
        self.assertEqual(result["total_net_buy_sell"], 2425.0)


class EggTheoryReadTests(unittest.TestCase):
    def test_fetch_all_marks_egg_theory_windows_insufficient_with_less_than_60_price_rows(self):
        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None):
            if dataset == "TaiwanStockPrice":
                return PRICE_ROWS
            if dataset == "TaiwanStockInstitutionalInvestorsBuySell":
                return INSTITUTIONAL_ROWS
            return []

        with patch.object(fetch_finmind, "fetch_dataset", side_effect=fake_fetch_dataset):
            result = fetch_finmind.fetch_all(
                "2330",
                "2026-04-01",
                "2026-05-05",
                token="token",
            )

        self.assertIn("egg_theory_read", result["derived"])
        egg_read = result["derived"]["egg_theory_read"]

        self.assertEqual(egg_read["windows"]["1m"]["status"], "insufficient_data")
        self.assertIn("Need at least 60 trading rows", egg_read["windows"]["1m"]["warnings"])
        self.assertEqual(egg_read["windows"]["1m"]["signal"], "wait_for_confirmation")
        self.assertEqual(egg_read["windows"]["1m"]["confidence"], "low")

    def test_fetch_all_stores_extended_chip_datasets(self):
        requested = []

        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None):
            requested.append(dataset)
            if dataset == "TaiwanStockPrice":
                return PRICE_ROWS
            if dataset == "TaiwanStockInstitutionalInvestorsBuySell":
                return INSTITUTIONAL_ROWS
            return [{"date": "2026-05-05", "stock_id": stock_id, "dataset": dataset}]

        with patch.object(fetch_finmind, "fetch_dataset", side_effect=fake_fetch_dataset):
            result = fetch_finmind.fetch_all(
                "2330",
                "2026-04-01",
                "2026-05-05",
                token="token",
            )

        self.assertIn("TaiwanStockMarginPurchaseShortSale", requested)
        self.assertIn("TaiwanStockShareholding", requested)
        self.assertIn("TaiwanStockDayTrading", requested)
        self.assertIn("TaiwanStockHoldingSharesPer", requested)
        self.assertEqual(result["raw"]["margin_purchase_short_sale"][0]["dataset"], "TaiwanStockMarginPurchaseShortSale")
        self.assertEqual(result["raw"]["shareholding"][0]["dataset"], "TaiwanStockShareholding")
        self.assertEqual(result["raw"]["day_trading"][0]["dataset"], "TaiwanStockDayTrading")
        self.assertEqual(result["raw"]["holding_shares_per"][0]["dataset"], "TaiwanStockHoldingSharesPer")

    def test_fetch_all_uses_local_tdcc_snapshot_when_available(self):
        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None):
            if dataset == "TaiwanStockPrice":
                return PRICE_ROWS
            if dataset == "TaiwanStockInstitutionalInvestorsBuySell":
                return INSTITUTIONAL_ROWS
            return []

        with patch.object(fetch_finmind, "fetch_dataset", side_effect=fake_fetch_dataset):
            with patch.object(
                fetch_finmind,
                "load_tdcc_holding_distribution",
                return_value=(make_tdcc_holding_rows(), None),
            ):
                result = fetch_finmind.fetch_all(
                    "2330",
                    "2026-04-01",
                    "2026-05-05",
                    token="token",
                )

        self.assertEqual(len(result["raw"]["tdcc_holding_distribution"]), 3)
        self.assertEqual(result["raw"]["tdcc_holding_distribution"][0]["stock_id"], "2330")
        self.assertEqual(result["metadata"]["row_counts"]["TDCCHoldingDistributionSnapshot"], 3)

    def test_fetch_all_keeps_running_when_holding_shares_per_is_not_allowed(self):
        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None):
            if dataset == "TaiwanStockHoldingSharesPer":
                raise RuntimeError("FinMind request failed for TaiwanStockHoldingSharesPer: HTTP 402")
            if dataset == "TaiwanStockPrice":
                return PRICE_ROWS
            if dataset == "TaiwanStockInstitutionalInvestorsBuySell":
                return INSTITUTIONAL_ROWS
            return [{"date": "2026-05-05", "stock_id": stock_id}]

        with patch.object(fetch_finmind, "fetch_dataset", side_effect=fake_fetch_dataset):
            result = fetch_finmind.fetch_all(
                "2330",
                "2026-04-01",
                "2026-05-05",
                token="token",
            )

        self.assertEqual(result["raw"]["holding_shares_per"], [])
        self.assertIn(
            "TaiwanStockHoldingSharesPer unavailable",
            " ".join(result["metadata"]["warnings"]),
        )

    def test_egg_theory_uses_holding_shares_when_available(self):
        price_rows = make_price_rows(180, start_close=200.0, close_step=-0.5, volume=5000)

        result = fetch_finmind.build_egg_theory_read(
            price_rows,
            holding_shares_per_rows=make_holding_rows(),
        )

        six_month = result["windows"]["6m"]

        self.assertEqual(six_month["status"], "ready")
        self.assertEqual(six_month["stage"], "B3")
        self.assertEqual(six_month["signal"], "supply_demand_favorable")
        self.assertEqual(six_month["confidence"], "high")
        self.assertEqual(six_month["holder_count_state"], "decreasing")
        self.assertNotIn("holder_data_missing", six_month["warnings"])

    def test_egg_theory_uses_tdcc_snapshot_when_historical_holder_rows_are_unavailable(self):
        price_rows = make_price_rows(180, start_close=100.0, close_step=1.0, volume=5000)

        result = fetch_finmind.build_egg_theory_read(
            price_rows,
            tdcc_holding_distribution_rows=make_tdcc_holding_rows(),
        )

        six_month = result["windows"]["6m"]

        self.assertEqual(six_month["status"], "ready")
        self.assertEqual(six_month["confidence"], "medium")
        self.assertEqual(six_month["holder_count_state"], "snapshot_only")
        self.assertEqual(six_month["holder_total_count"], 1000)
        self.assertEqual(six_month["large_holder_percent"], 70.0)
        self.assertNotIn("holder_data_missing", six_month["warnings"])
        self.assertIn("holder_trend_insufficient", six_month["warnings"])


if __name__ == "__main__":
    unittest.main()
