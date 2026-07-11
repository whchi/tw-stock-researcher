import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_tdcc as fetch_tdcc

JSON_ROWS = [
    {"﻿資料日期": "20260605", "證券代號": "6451  ", "持股分級": "1", "人數": "11983", "股數": "1394229", "占集保庫存數比例%": "1.22"},
    {"﻿資料日期": "20260605", "證券代號": "6451  ", "持股分級": "17", "人數": "19022", "股數": "113593460", "占集保庫存數比例%": "100.00"},
    {"﻿資料日期": "20260605", "證券代號": "6706  ", "持股分級": "17", "人數": "46918", "股數": "78549433", "占集保庫存數比例%": "100.00"},
]


class TdccHoldingDistributionTests(unittest.TestCase):
    def test_cache_uses_current_json_transport_shape(self):
        self.assertEqual(
            getattr(fetch_tdcc, "CACHE_JSON_NAME", None),
            "tdcc-holding-distribution.json",
        )

    def test_parse_holding_distribution_filters_requested_stock(self):
        result = fetch_tdcc.parse_holding_distribution(JSON_ROWS, "6451")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["date"], "2026-06-05")
        self.assertEqual(result[0]["stock_id"], "6451")
        self.assertEqual(result[0]["HoldingSharesLevel"], "1")
        self.assertEqual(result[0]["people"], 11983)
        self.assertEqual(result[0]["shares"], 1394229)
        self.assertEqual(result[0]["percent"], 1.22)
        self.assertEqual(result[0]["unit"], "股")
        self.assertEqual(result[1]["HoldingSharesLevel"], "17")

    def test_fetch_all_returns_only_requested_stock_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_tdcc, "fetch_holding_distribution_rows", return_value=JSON_ROWS):
                result = fetch_tdcc.fetch_all("6451", repo_root=Path(tmp))

        self.assertEqual(result["stock_id"], "6451")
        self.assertEqual(result["raw"]["holding_distribution"][0]["stock_id"], "6451")
        self.assertEqual(result["metadata"]["row_counts"]["TDCCStockHoldingDistribution"], 2)

    def test_fetch_all_saves_cache_and_reuses_it_within_max_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            with patch.object(
                fetch_tdcc, "fetch_holding_distribution_rows", return_value=JSON_ROWS
            ) as fetcher:
                first = fetch_tdcc.fetch_all("6451", repo_root=repo_root)
                second = fetch_tdcc.fetch_all("6451", repo_root=repo_root)

            self.assertEqual(fetcher.call_count, 1)
            self.assertFalse(first["cache"]["hit"])
            self.assertTrue(second["cache"]["hit"])
            self.assertTrue((repo_root / "market" / fetch_tdcc.CACHE_JSON_NAME).exists())
            self.assertEqual(
                second["raw"]["holding_distribution"][0]["stock_id"], "6451"
            )

    def test_fetch_all_refetches_when_cache_expired_or_refresh_forced(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            with patch.object(
                fetch_tdcc, "fetch_holding_distribution_rows", return_value=JSON_ROWS
            ) as fetcher:
                fetch_tdcc.fetch_all("6451", repo_root=repo_root)
                fetch_tdcc.fetch_all("6451", repo_root=repo_root, max_age_hours=0)
                fetch_tdcc.fetch_all("6451", repo_root=repo_root, refresh=True)

            self.assertEqual(fetcher.call_count, 3)

    def test_parse_args_defaults_cache_options(self):
        args = fetch_tdcc.parse_args(["6451"])

        self.assertEqual(args.max_age_hours, fetch_tdcc.DEFAULT_CACHE_MAX_AGE_HOURS)
        self.assertFalse(args.refresh)

    def test_merge_history_appends_new_dates_and_dedupes(self):
        previous = {
            "history": [
                {
                    "date": "2026-05-29",
                    "rows": [{"date": "2026-05-29", "HoldingSharesLevel": "17", "people": 900}],
                }
            ]
        }
        snapshot = [{"date": "2026-06-05", "HoldingSharesLevel": "17", "people": 1000}]

        history = fetch_tdcc.merge_history(previous, snapshot)
        self.assertEqual([entry["date"] for entry in history], ["2026-05-29", "2026-06-05"])

        deduped = fetch_tdcc.merge_history({"history": history}, snapshot)
        self.assertEqual(len(deduped), 2)

    def test_fetch_all_accumulates_history_and_keeps_latest_snapshot_in_raw(self):
        previous = {
            "history": [
                {
                    "date": "2026-05-29",
                    "rows": [{"date": "2026-05-29", "HoldingSharesLevel": "17", "people": 18800}],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_tdcc, "fetch_holding_distribution_rows", return_value=JSON_ROWS):
                result = fetch_tdcc.fetch_all(
                    "6451", repo_root=Path(tmp), previous_payload=previous
                )

        self.assertEqual(
            [entry["date"] for entry in result["history"]],
            ["2026-05-29", "2026-06-05"],
        )
        self.assertEqual(
            {row["date"] for row in result["raw"]["holding_distribution"]},
            {"2026-06-05"},
        )
        self.assertEqual(
            result["metadata"]["row_counts"]["TDCCHoldingDistributionHistoryDates"], 2
        )
        
    def test_fetch_holding_distribution_returns_official_json_rows(self):
        json_rows = [
            {
                "證券代號": "6451  ",
                "﻿資料日期": "20260605",
                "持股分級": "17",
                "人數": "19022",
                "股數": "113593460",
                "占集保庫存數比例%": "100.00",
            }
        ]

        class Response:
            status_code = 200

            def json(self):
                return json_rows

        with patch("requests.get", return_value=Response()) as get:
            rows = fetch_tdcc.fetch_holding_distribution_rows()

        self.assertEqual(get.call_args.args[0], fetch_tdcc.TDCC_HOLDING_DISTRIBUTION_URL)
        self.assertEqual(get.call_args.kwargs["timeout"], 30)
        self.assertIn("openapi.tdcc.com.tw", fetch_tdcc.TDCC_HOLDING_DISTRIBUTION_URL)

        parsed = fetch_tdcc.parse_holding_distribution(rows, "6451")
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["date"], "2026-06-05")
        self.assertEqual(parsed[0]["people"], 19022)

    def test_fetch_holding_distribution_does_not_retry_without_verification_on_tls_failure(self):
        import requests

        with patch("requests.get", side_effect=requests.exceptions.SSLError("bad cert")) as get:
            with self.assertRaises(requests.exceptions.SSLError):
                fetch_tdcc.fetch_holding_distribution_rows()

        self.assertEqual(get.call_count, 1)
        for call in get.call_args_list:
            self.assertNotIn("verify", call.kwargs)

    def test_fetch_holding_distribution_raises_on_non_200_status(self):
        class Response:
            status_code = 500

        with patch("requests.get", return_value=Response()):
            with self.assertRaises(RuntimeError):
                fetch_tdcc.fetch_holding_distribution_rows()

    def test_fetch_holding_distribution_raises_when_response_is_not_a_json_array(self):
        class Response:
            status_code = 200

            def json(self):
                return {"not": "a list"}

        with patch("requests.get", return_value=Response()):
            with self.assertRaises(RuntimeError):
                fetch_tdcc.fetch_holding_distribution_rows()


class BuildMetadataTests(unittest.TestCase):
    def test_blocked_when_requested_stock_snapshot_is_empty(self):
        result = fetch_tdcc.build_metadata([])

        self.assertEqual(result["status"], "blocked")

    def test_pass_when_requested_stock_snapshot_has_rows(self):
        result = fetch_tdcc.build_metadata([{"date": "2026-06-05", "stock_id": "6451"}])

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["source_as_of"], "2026-06-05")


class MainOutputResolutionTests(unittest.TestCase):
    def test_main_fails_closed_when_case_resolution_raises(self):
        with patch.object(
            fetch_tdcc,
            "case_output_path",
            side_effect=fetch_tdcc.CaseResolutionError(
                "expected exactly one companies/6451-*/ directory; found 0: none"
            ),
        ):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = fetch_tdcc.main(["6451"])

        self.assertEqual(exit_code, 1)
        self.assertIn("expected exactly one", stderr.getvalue())

    def test_main_writes_to_resolved_case_output_path_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "tdcc-data.json"
            with patch.object(fetch_tdcc, "case_output_path", return_value=target) as mock_resolve:
                with patch.object(fetch_tdcc, "fetch_all", return_value={"metadata": {"status": "pass"}}):
                    exit_code = fetch_tdcc.main(["6451"])

            mock_resolve.assert_called_once_with(
                "6451", "tdcc-data.json", Path(fetch_tdcc.__file__).resolve().parent.parent
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(target.exists())

    def test_main_routes_explicit_output_through_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "explicit.json"
            with patch.object(fetch_tdcc, "validate_explicit_output", return_value=target) as mock_validate:
                with patch.object(fetch_tdcc, "fetch_all", return_value={"metadata": {"status": "pass"}}):
                    exit_code = fetch_tdcc.main(["6451", "--output", str(target)])

            mock_validate.assert_called_once()
            self.assertEqual(exit_code, 0)
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
