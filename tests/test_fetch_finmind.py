import contextlib
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_finmind as fetch_finmind
from scripts.fetch_finmind import (
    build_market_action_read,
    build_metadata,
    main,
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
    # Dates must fall inside the 6m window (last 120 of 180 daily rows that
    # start on 2026-01-01, so the window opens on 2026-03-02).
    return [
        {
            "date": "2026-03-15",
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


def make_shareholding_rows(issued_shares=100000):
    return [
        {
            "date": "2026-06-29",
            "stock_id": "2330",
            "NumberOfSharesIssued": issued_shares,
        }
    ]


def make_tdcc_trend_rows():
    # Two accumulated weekly level-17 totals inside the 6m window, plus a
    # non-total level row that must not affect the holder trend.
    return [
        {
            "date": "2026-03-20",
            "stock_id": "2330",
            "HoldingSharesLevel": "17",
            "people": 1000,
            "shares": 10000000,
            "percent": 100.0,
            "unit": "股",
        },
        {
            "date": "2026-06-20",
            "stock_id": "2330",
            "HoldingSharesLevel": "17",
            "people": 700,
            "shares": 10000000,
            "percent": 100.0,
            "unit": "股",
        },
        {
            "date": "2026-06-20",
            "stock_id": "2330",
            "HoldingSharesLevel": "1",
            "people": 50,
            "shares": 100000,
            "percent": 1.0,
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


class BuildMetadataTests(unittest.TestCase):
    def test_blocked_when_required_price_dataset_is_empty(self):
        raw_rows_by_dataset = {dataset: [{"date": "2026-06-01"}] for dataset in fetch_finmind.DATASETS}
        raw_rows_by_dataset["TaiwanStockPrice"] = []

        result = build_metadata("2330", "2026-01-01", "2026-07-01", raw_rows_by_dataset)

        self.assertEqual(result["status"], "blocked")

    def test_degraded_when_only_optional_datasets_are_empty(self):
        raw_rows_by_dataset = {dataset: [] for dataset in fetch_finmind.DATASETS}
        raw_rows_by_dataset["TaiwanStockPrice"] = [{"date": "2026-06-01"}]
        raw_rows_by_dataset["TaiwanStockInstitutionalInvestorsBuySell"] = [{"date": "2026-06-01"}]

        result = build_metadata("2330", "2026-01-01", "2026-07-01", raw_rows_by_dataset)

        self.assertEqual(result["status"], "degraded")

    def test_pass_when_required_and_optional_datasets_have_rows(self):
        raw_rows_by_dataset = {dataset: [{"date": "2026-06-01"}] for dataset in fetch_finmind.DATASETS}

        result = build_metadata(
            "2330",
            "2026-01-01",
            "2026-07-01",
            raw_rows_by_dataset,
            tdcc_holding_distribution_rows=[{"date": "2026-06-01"}],
        )

        self.assertEqual(result["status"], "pass")


class MainOutputResolutionTests(unittest.TestCase):
    def test_main_fails_closed_when_case_resolution_raises(self):
        with patch.object(
            fetch_finmind,
            "case_output_path",
            side_effect=fetch_finmind.CaseResolutionError(
                "expected exactly one companies/2330-*/ directory; found 0: none"
            ),
        ):
            with patch.object(fetch_finmind, "resolve_token", return_value="tok"):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    exit_code = main(["2330"])

        self.assertEqual(exit_code, 1)
        self.assertIn("expected exactly one", stderr.getvalue())

    def test_main_writes_to_resolved_case_output_path_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "market-data.json"
            with patch.object(fetch_finmind, "case_output_path", return_value=target) as mock_resolve:
                with patch.object(fetch_finmind, "resolve_token", return_value="tok"):
                    with patch.object(fetch_finmind, "fetch_all", return_value={"metadata": {"status": "pass"}}):
                        exit_code = main(["2330"])

            mock_resolve.assert_called_once_with(
                "2330", "market-data.json", Path(fetch_finmind.__file__).resolve().parent.parent
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(target.exists())

    def test_main_routes_explicit_output_through_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "explicit.json"
            with patch.object(fetch_finmind, "validate_explicit_output", return_value=target) as mock_validate:
                with patch.object(fetch_finmind, "resolve_token", return_value="tok"):
                    with patch.object(fetch_finmind, "fetch_all", return_value={"metadata": {"status": "pass"}}):
                        exit_code = main(["2330", "--output", str(target)])

            mock_validate.assert_called_once()
            self.assertEqual(exit_code, 0)
            self.assertTrue(target.exists())


class LoadTdccHoldingDistributionResolutionTests(unittest.TestCase):
    def test_degrades_to_warning_when_case_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)
            (repo_root / "companies" / "2330-duplicate-slug").mkdir(parents=True)

            rows, warning = fetch_finmind.load_tdcc_holding_distribution("2330", repo_root=repo_root)

        self.assertEqual(rows, [])
        self.assertIn("tdcc-data.json unavailable", warning)
        self.assertIn("found 2", warning)

    def test_degrades_to_warning_when_case_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()

            rows, warning = fetch_finmind.load_tdcc_holding_distribution("2330", repo_root=repo_root)

        self.assertEqual(rows, [])
        self.assertIn("tdcc-data.json unavailable", warning)


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


class MarketConfirmationMetricsWiringTests(unittest.TestCase):
    def test_computes_days_to_cover_from_latest_short_balance_and_median_volume(self):
        price_rows = [
            {"date": f"2026-06-{day:02d}", "Trading_Volume": 1000 + day}
            for day in range(1, 21)
        ]
        margin_rows = [
            {"date": "2026-06-19", "ShortSaleTodayBalance": 2000},
            {"date": "2026-06-20", "ShortSaleTodayBalance": 3000},
        ]

        result = fetch_finmind.build_market_confirmation_metrics(price_rows, margin_rows)

        self.assertEqual(result["days_to_cover"]["state"], "ready")
        expected_median = sorted(1000 + day for day in range(1, 21))[9:11]
        expected_median_value = sum(expected_median) / 2
        self.assertAlmostEqual(result["days_to_cover"]["value"], 3000 / expected_median_value)

    def test_unavailable_when_no_short_sale_rows(self):
        result = fetch_finmind.build_market_confirmation_metrics(
            [{"date": "2026-06-01", "Trading_Volume": 1000}], []
        )
        self.assertEqual(result["days_to_cover"]["state"], "unavailable")

    def test_emits_explicit_non_values_for_unfetched_market_metric_inputs(self):
        result = fetch_finmind.build_market_confirmation_metrics([], [])

        expected = {
            "normalized_short_pressure",
            "sector_relative_return_63d",
            "sector_relative_return_126d",
            "tdcc_concentration_change_4w",
            "tdcc_concentration_change_13w",
        }
        self.assertTrue(expected.issubset(result))
        self.assertTrue(all(result[key]["state"] == "unavailable" for key in expected))


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
    def test_fetch_all_marks_egg_theory_windows_insufficient_with_less_than_20_price_rows(self):
        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None, session=None):
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
        self.assertIn("Need at least 20 trading rows", egg_read["windows"]["1m"]["warnings"])
        self.assertEqual(egg_read["windows"]["1m"]["signal"], "wait_for_confirmation")
        self.assertEqual(egg_read["windows"]["1m"]["confidence"], "low")

    def test_egg_windows_use_month_scaled_trading_rows(self):
        price_rows = make_price_rows(30)

        result = fetch_finmind.build_egg_theory_read(price_rows)

        self.assertEqual(result["windows"]["1m"]["status"], "ready")
        self.assertIn(
            "Need at least 60 trading rows", result["windows"]["3m"]["warnings"]
        )
        self.assertIn(
            "Need at least 120 trading rows", result["windows"]["6m"]["warnings"]
        )

    def test_fetch_all_stores_extended_chip_datasets(self):
        requested = []

        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None, session=None):
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
        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None, session=None):
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
        def fake_fetch_dataset(dataset, stock_id, start_date, end_date, token=None, session=None):
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
        error_messages = [err["message"] for err in result["metadata"]["errors"]]
        self.assertIn(
            "TaiwanStockHoldingSharesPer unavailable",
            " ".join(error_messages),
        )

    def test_egg_theory_uses_holding_shares_when_available(self):
        price_rows = make_price_rows(180, start_close=200.0, close_step=-0.5, volume=5000)

        result = fetch_finmind.build_egg_theory_read(
            price_rows,
            holding_shares_per_rows=make_holding_rows(),
            shareholding_rows=make_shareholding_rows(),
        )

        six_month = result["windows"]["6m"]

        self.assertEqual(six_month["status"], "ready")
        self.assertEqual(six_month["stage"], "B3")
        self.assertEqual(six_month["signal"], "supply_demand_favorable")
        self.assertEqual(six_month["confidence"], "high")
        self.assertEqual(six_month["turnover_state"], "active")
        self.assertEqual(six_month["holder_count_state"], "decreasing")
        self.assertNotIn("holder_data_missing", six_month["warnings"])

    def test_egg_theory_marks_turnover_unknown_without_issued_shares(self):
        price_rows = make_price_rows(120, start_close=100.0, close_step=1.0, volume=5000)

        result = fetch_finmind.build_egg_theory_read(price_rows)

        six_month = result["windows"]["6m"]

        self.assertEqual(six_month["status"], "ready")
        self.assertIsNone(six_month["average_turnover"])
        self.assertEqual(six_month["turnover_state"], "unknown")
        self.assertEqual(six_month["signal"], "wait_for_confirmation")
        self.assertIn("turnover_data_missing", six_month["warnings"])

    def test_egg_theory_builds_holder_trend_from_accumulated_tdcc_history(self):
        price_rows = make_price_rows(180, start_close=200.0, close_step=-0.5, volume=5000)

        result = fetch_finmind.build_egg_theory_read(
            price_rows,
            shareholding_rows=make_shareholding_rows(),
            tdcc_holding_distribution_rows=make_tdcc_trend_rows(),
        )

        six_month = result["windows"]["6m"]

        self.assertEqual(six_month["status"], "ready")
        self.assertEqual(six_month["stage"], "B3")
        self.assertEqual(six_month["signal"], "supply_demand_favorable")
        self.assertEqual(six_month["confidence"], "medium")
        self.assertEqual(six_month["holder_count_state"], "decreasing")
        self.assertEqual(six_month["holder_change_pct"], -30.0)
        self.assertIn("holder_trend_from_tdcc_weekly", six_month["warnings"])

    def test_load_tdcc_holding_distribution_flattens_history_entries(self):
        payload = {
            "stock_id": "2330",
            "raw": {"holding_distribution": [{"date": "2026-06-20", "people": 700}]},
            "history": [
                {"date": "2026-03-20", "rows": [{"date": "2026-03-20", "people": 1000}]},
                {"date": "2026-06-20", "rows": [{"date": "2026-06-20", "people": 700}]},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            case_dir = repo_root / "companies" / "2330-tsmc"
            case_dir.mkdir(parents=True)
            with open(case_dir / "tdcc-data.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)

            rows, warning = fetch_finmind.load_tdcc_holding_distribution(
                "2330", repo_root=repo_root
            )

        self.assertIsNone(warning)
        self.assertEqual({row["date"] for row in rows}, {"2026-03-20", "2026-06-20"})

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
