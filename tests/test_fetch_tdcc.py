import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_tdcc as fetch_tdcc


class TdccHoldingDistributionTests(unittest.TestCase):
    def test_parse_holding_distribution_filters_requested_stock(self):
        csv_text = "\ufeff資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n"
        csv_text += "20260605,6451  ,1,11983,1394229,1.22\n"
        csv_text += "20260605,6451  ,17,19022,113593460,100.00\n"
        csv_text += "20260605,6706  ,17,46918,78549433,100.00\n"

        result = fetch_tdcc.parse_holding_distribution(csv_text, "6451")

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
        csv_text = "\ufeff資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n"
        csv_text += "20260605,6451  ,17,19022,113593460,100.00\n"
        csv_text += "20260605,6706  ,17,46918,78549433,100.00\n"

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_tdcc, "fetch_holding_distribution_csv", return_value=csv_text):
                result = fetch_tdcc.fetch_all("6451", repo_root=Path(tmp))

        self.assertEqual(result["stock_id"], "6451")
        self.assertEqual(result["raw"]["holding_distribution"][0]["stock_id"], "6451")
        self.assertEqual(result["metadata"]["row_counts"]["TDCCStockHoldingDistribution"], 1)

    def test_fetch_all_saves_cache_and_reuses_it_within_max_age(self):
        csv_text = "﻿資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n"
        csv_text += "20260605,6451  ,17,19022,113593460,100.00\n"

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            with patch.object(
                fetch_tdcc, "fetch_holding_distribution_csv", return_value=csv_text
            ) as fetcher:
                first = fetch_tdcc.fetch_all("6451", repo_root=repo_root)
                second = fetch_tdcc.fetch_all("6451", repo_root=repo_root)

            self.assertEqual(fetcher.call_count, 1)
            self.assertFalse(first["cache"]["hit"])
            self.assertTrue(second["cache"]["hit"])
            self.assertTrue((repo_root / "market" / fetch_tdcc.CACHE_CSV_NAME).exists())
            self.assertEqual(
                second["raw"]["holding_distribution"][0]["stock_id"], "6451"
            )

    def test_fetch_all_refetches_when_cache_expired_or_refresh_forced(self):
        csv_text = "﻿資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n"
        csv_text += "20260605,6451  ,17,19022,113593460,100.00\n"

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            with patch.object(
                fetch_tdcc, "fetch_holding_distribution_csv", return_value=csv_text
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
        csv_text = "﻿資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n"
        csv_text += "20260605,6451  ,17,19022,113593460,100.00\n"
        previous = {
            "history": [
                {
                    "date": "2026-05-29",
                    "rows": [{"date": "2026-05-29", "HoldingSharesLevel": "17", "people": 18800}],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_tdcc, "fetch_holding_distribution_csv", return_value=csv_text):
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
        
    def test_fetch_holding_distribution_retries_without_ssl_verification_for_tdcc_cert_issue(self):
        import requests

        class Response:
            status_code = 200
            text = "csv"

        with patch(
            "requests.get",
            side_effect=[requests.exceptions.SSLError("bad cert"), Response()],
        ) as get:
            result = fetch_tdcc.fetch_holding_distribution_csv()

        self.assertEqual(result, "csv")
        self.assertEqual(get.call_args_list[0].kwargs["timeout"], 30)
        self.assertFalse(get.call_args_list[1].kwargs["verify"])

    def test_fetch_holding_distribution_falls_back_to_curl_when_requests_redirects_loop(self):
        import requests

        completed = type("Completed", (), {"stdout": "csv-from-curl"})()

        with patch("requests.get", side_effect=requests.exceptions.TooManyRedirects()):
            with patch("subprocess.run", return_value=completed) as run:
                result = fetch_tdcc.fetch_holding_distribution_csv()

        self.assertEqual(result, "csv-from-curl")
        self.assertEqual(run.call_args.args[0][0], "curl")
        self.assertIn("90", run.call_args.args[0])
        self.assertIn(fetch_tdcc.TDCC_HOLDING_DISTRIBUTION_URL, run.call_args.args[0])


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
