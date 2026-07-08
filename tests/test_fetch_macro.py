import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_macro as fetch_macro
from scripts.fetch_macro import (
    TEMPLATE_SOURCES,
    build_macro_data,
    default_output_path,
    latest_read,
)


class OutputPathTests(unittest.TestCase):
    def test_default_output_path_uses_shared_market_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            output_path = default_output_path(repo_root=repo_root)

            self.assertEqual(output_path, repo_root / "market" / "shared-macro-data.json")


class SourceScopeTests(unittest.TestCase):
    def test_template_sources_match_macro_templates_only(self):
        self.assertEqual(
            TEMPLATE_SOURCES,
            (
                "TWSE Open API",
                "Yahoo Finance / public market data",
                "Taiwan official statistics / MOPS context",
            ),
        )


class TwseMarketStatsTests(unittest.TestCase):
    def test_fetch_twse_market_stats_uses_last_ascending_row_and_iso_date(self):
        payload = [
            {
                "Date": "1150701",
                "TAIEX": "22000.00",
                "Change": "10.0",
                "TradeVolume": "1000",
                "TradeValue": "2000",
                "Transaction": "300",
            },
            {
                "Date": "1150707",
                "TAIEX": "23111.55",
                "Change": "-5.0",
                "TradeVolume": "4000",
                "TradeValue": "5000",
                "Transaction": "600",
            },
        ]

        with patch.object(fetch_macro, "request_json", return_value=payload):
            rows = fetch_macro.fetch_twse_market_stats()

        self.assertEqual(rows[0]["latest"]["date"], "2026-07-07")
        self.assertEqual(rows[0]["latest"]["taiex"], 23111.55)
        self.assertEqual(rows[0]["latest"]["change"], -5.0)


CUSTOMS_CSV = (
    '﻿"年度","月份","出口總值(新臺幣千元)","進口總值(新臺幣千元)","出入超(新臺幣千元)"\n'
    '"115","4","1200","900","300"\n'
    '"115","3","1100","880","220"\n'
    '"114","4","1000","800","200"\n'
)


class TaiwanOfficialTests(unittest.TestCase):
    def test_parse_customs_trade_csv_converts_roc_dates_and_sorts_ascending(self):
        rows = fetch_macro.parse_customs_trade_csv(CUSTOMS_CSV)

        self.assertEqual([row["date"] for row in rows], ["2025-04", "2026-03", "2026-04"])
        self.assertEqual(rows[-1]["exports_total_twd_thousand"], 1200.0)
        self.assertEqual(rows[-1]["trade_balance_twd_thousand"], 300.0)

    def test_build_customs_trade_rows_computes_exports_yoy(self):
        result = fetch_macro.build_customs_trade_rows(CUSTOMS_CSV, "https://example.gov/csv")

        latest = result[0]["latest"]
        self.assertEqual(latest["date"], "2026-04")
        self.assertEqual(latest["exports_yoy_pct"], 20.0)
        self.assertEqual(result[0]["unit"], "TWD thousand")

    def test_fetch_taiwan_official_uses_customs_default(self):
        with patch.object(
            fetch_macro, "request_text_with_ssl_fallback", return_value=CUSTOMS_CSV
        ) as fetcher:
            rows = fetch_macro.fetch_taiwan_official(None)

        self.assertEqual(fetcher.call_args.args[0], fetch_macro.DEFAULT_TAIWAN_MACRO_URL)
        self.assertEqual(rows[0]["latest"]["date"], "2026-04")

    def test_fetch_taiwan_official_previews_custom_endpoints(self):
        with patch.object(
            fetch_macro, "request_text_with_ssl_fallback", return_value="col1,col2"
        ):
            rows = fetch_macro.fetch_taiwan_official("https://example.com/custom.csv")

        self.assertEqual(rows[0]["raw_preview"], "col1,col2")
        self.assertIsNone(rows[0]["latest"])


class LatestReadTests(unittest.TestCase):
    def test_latest_read_uses_latest_valid_observation_and_previous_change(self):
        rows = [
            {"date": "2026-01-01", "value": 100.0},
            {"date": "2026-02-01", "value": None},
            {"date": "2026-03-01", "value": 106.0},
        ]

        result = latest_read(rows)

        self.assertEqual(result["date"], "2026-03-01")
        self.assertEqual(result["value"], 106.0)
        self.assertEqual(result["previous_date"], "2026-01-01")
        self.assertEqual(result["previous_value"], 100.0)
        self.assertAlmostEqual(result["change_pct"], 6.0)

    def test_build_macro_data_groups_records_by_template_source(self):
        records = {
            "TWSE Open API": [{"indicator": "TAIEX", "latest": {"value": 22000}}],
            "Yahoo Finance / public market data": [],
        }

        result = build_macro_data(records, warnings=["TAIWAN_MACRO_URL not set"])

        self.assertEqual(result["sources"]["TWSE Open API"][0]["indicator"], "TAIEX")
        self.assertEqual(result["sources"]["Yahoo Finance / public market data"], [])
        self.assertIn("TAIWAN_MACRO_URL not set", result["metadata"]["warnings"])


if __name__ == "__main__":
    unittest.main()
