import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_tdcc as fetch_tdcc
from scripts.data_contract import STATUS_BLOCKED


SOURCE_ROWS = [
    {
        "資料日期": "20260710",
        "證券代號": "6451",
        "持股分級": "17",
        "人數": "19022",
        "股數": "113593460",
        "占集保庫存數比例%": "100.00",
    },
    {
        "資料日期": "20260710",
        "證券代號": "6706",
        "持股分級": "17",
        "人數": "46918",
        "股數": "78549433",
        "占集保庫存數比例%": "100.00",
    },
]


class TdccJsonContractTests(unittest.TestCase):
    def test_parse_holding_distribution_filters_requested_stock_from_json_rows(self):
        result = fetch_tdcc.parse_holding_distribution(SOURCE_ROWS, "6451")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["date"], "2026-07-10")
        self.assertEqual(result[0]["stock_id"], "6451")
        self.assertEqual(result[0]["people"], 19022)
        self.assertEqual(result[0]["percent"], 100.0)

    def test_fetch_all_saves_json_cache_and_reuses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(fetch_tdcc, "fetch_holding_distribution_rows", return_value=SOURCE_ROWS) as fetcher:
                first = fetch_tdcc.fetch_all("6451", repo_root=root)
                second = fetch_tdcc.fetch_all("6451", repo_root=root)

        self.assertEqual(fetcher.call_count, 1)
        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(first["cache"]["path"], "market/tdcc-holding-distribution.json")
        self.assertEqual(second["raw"]["holding_distribution"][0]["stock_id"], "6451")

    def test_fetch_all_refetches_when_cache_expired_or_refresh_forced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(fetch_tdcc, "fetch_holding_distribution_rows", return_value=SOURCE_ROWS) as fetcher:
                fetch_tdcc.fetch_all("6451", repo_root=root)
                fetch_tdcc.fetch_all("6451", repo_root=root, max_age_hours=0)
                fetch_tdcc.fetch_all("6451", repo_root=root, refresh=True)

        self.assertEqual(fetcher.call_count, 3)

    def test_merge_history_appends_new_dates_and_dedupes(self):
        previous = {"history": [{"date": "2026-07-03", "rows": [{"date": "2026-07-03"}]}]}
        snapshot = [{"date": "2026-07-10", "HoldingSharesLevel": "17", "people": 1000}]

        history = fetch_tdcc.merge_history(previous, snapshot)
        deduped = fetch_tdcc.merge_history({"history": history}, snapshot)

        self.assertEqual([entry["date"] for entry in history], ["2026-07-03", "2026-07-10"])
        self.assertEqual(len(deduped), 2)

    def test_metadata_blocks_when_no_requested_stock_rows_exist(self):
        metadata = fetch_tdcc.build_metadata([])

        self.assertEqual(metadata["status"], STATUS_BLOCKED)
        self.assertEqual(metadata["parser_version"], "3")


if __name__ == "__main__":
    unittest.main()
