import unittest
from unittest.mock import patch

import scripts.fetch_macro as fetch_macro
from scripts.data_contract import STATUS_BLOCKED, STATUS_DEGRADED


CUSTOMS_CSV = (
    "年度,月份,出口總值(新臺幣千元),進口總值(新臺幣千元),出入超(新臺幣千元)\n"
    "114,04,1000,800,200\n"
    "115,03,1100,880,220\n"
    "115,04,1200,900,300\n"
)


class MacroFetchTests(unittest.TestCase):
    def test_template_sources_match_macro_templates_only(self):
        self.assertEqual(
            fetch_macro.TEMPLATE_SOURCES,
            (
                "TWSE Open API",
                "Yahoo Finance / public market data",
                "Taiwan official statistics / MOPS context",
            ),
        )

    def test_parse_customs_trade_csv_converts_roc_dates_and_sorts(self):
        rows = fetch_macro.parse_customs_trade_csv(CUSTOMS_CSV)

        self.assertEqual([row["date"] for row in rows], ["2025-04", "2026-03", "2026-04"])
        self.assertEqual(rows[-1]["trade_balance_twd_thousand"], 300.0)

    def test_build_customs_trade_rows_computes_exports_yoy(self):
        result = fetch_macro.build_customs_trade_rows(CUSTOMS_CSV, "https://example.test/customs.csv")

        self.assertEqual(result[0]["latest"]["date"], "2026-04")
        self.assertEqual(result[0]["latest"]["exports_yoy_pct"], 20.0)

    def test_fetch_taiwan_official_uses_strict_request_text(self):
        with patch.object(fetch_macro, "request_text", return_value=CUSTOMS_CSV) as request_text:
            rows = fetch_macro.fetch_taiwan_official(None)

        self.assertEqual(request_text.call_args.kwargs["encoding"], "utf-8-sig")
        self.assertEqual(request_text.call_args.args[0], fetch_macro.DEFAULT_TAIWAN_MACRO_URL)
        self.assertEqual(rows[0]["latest"]["date"], "2026-04")

    def test_build_macro_data_blocks_when_every_source_is_empty(self):
        data = fetch_macro.build_macro_data({})

        self.assertEqual(data["metadata"]["status"], STATUS_BLOCKED)

    def test_build_macro_data_degrades_when_one_optional_source_is_empty(self):
        data = fetch_macro.build_macro_data({"TWSE Open API": [{"latest": {"date": "2026-07-10"}}]})

        self.assertEqual(data["metadata"]["status"], STATUS_DEGRADED)


if __name__ == "__main__":
    unittest.main()
