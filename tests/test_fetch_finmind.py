import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from scripts.data_contract import STATUS_BLOCKED, STATUS_DEGRADED
from scripts.fetch_finmind import (
    build_market_action_read,
    build_metadata,
    load_tdcc_holding_distribution,
    resolve_token,
    summarize_institutional_flows,
)


def make_price_rows(count, start_close=100.0, close_step=1.0, volume=1000):
    start = date(2026, 1, 1)
    return [
        {
            "date": (start + timedelta(days=index)).isoformat(),
            "stock_id": "2330",
            "Trading_Volume": volume + index * 100,
            "close": start_close + index * close_step,
        }
        for index in range(count)
    ]


class FinmindDerivedTests(unittest.TestCase):
    def test_resolve_token_requires_token(self):
        with self.assertRaisesRegex(RuntimeError, "FIN_MIND_TOKEN is required"):
            resolve_token(args_token=None, env={})

    def test_summarize_institutional_flows_groups_by_investor(self):
        rows = [
            {"name": "Foreign_Investor", "buy": 100, "sell": 40},
            {"name": "Foreign_Investor", "buy": 50, "sell": 20},
            {"name": "Dealer", "buy": 10, "sell": 30},
        ]

        result = summarize_institutional_flows(rows)

        self.assertEqual(result["by_name"]["Foreign_Investor"]["net_buy_sell"], 90)
        self.assertEqual(result["total_net_buy_sell"], 70)

    def test_market_action_read_derives_5d_window(self):
        institutional = [
            {"date": "2026-01-03", "name": "Foreign_Investor", "buy": 100, "sell": 10},
            {"date": "2026-01-06", "name": "Dealer", "buy": 10, "sell": 40},
        ]

        result = build_market_action_read(make_price_rows(6), institutional)

        self.assertEqual(result["market_state"], "bullish")
        self.assertEqual(result["price_5d_change_pct"], 5.0)
        self.assertEqual(result["institutional_total_net_buy_sell"], 60)

    def test_load_tdcc_holding_distribution_requires_single_current_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root / "companies" / "2330-tsmc"
            case.mkdir(parents=True)
            (case / "tdcc-data.json").write_text(
                json.dumps({"history": [{"rows": [{"date": "2026-07-10", "HoldingSharesLevel": "17", "people": 10}]}]}),
                encoding="utf-8",
            )

            rows, warning = load_tdcc_holding_distribution("2330", repo_root=root)

        self.assertIsNone(warning)
        self.assertEqual(rows[0]["people"], 10)

    def test_metadata_blocks_missing_price_and_degrades_missing_optional(self):
        counts = {
            "TaiwanStockPrice": 1,
            "TaiwanStockInstitutionalInvestorsBuySell": 1,
            "TaiwanStockMarginPurchaseShortSale": 0,
            "TaiwanStockShareholding": 0,
            "TaiwanStockDayTrading": 0,
            "TaiwanStockHoldingSharesPer": 0,
        }

        degraded = build_metadata(
            "2330",
            "2026-01-01",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in counts.items()},
            tdcc_holding_distribution_rows=[],
        )
        blocked_counts = dict(counts, TaiwanStockPrice=0)
        blocked = build_metadata(
            "2330",
            "2026-01-01",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in blocked_counts.items()},
            tdcc_holding_distribution_rows=[],
        )

        self.assertEqual(degraded["status"], STATUS_DEGRADED)
        self.assertEqual(blocked["status"], STATUS_BLOCKED)


if __name__ == "__main__":
    unittest.main()
