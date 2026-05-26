import tempfile
import unittest
from pathlib import Path

from scripts.fetch_finmind import (
    build_market_action_read,
    default_output_path,
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


if __name__ == "__main__":
    unittest.main()
