import unittest
from datetime import datetime, timezone

from scripts.data_contract import STATUS_BLOCKED, STATUS_DEGRADED
from scripts.fetch_yahoo import build_metadata, parse_profile, parse_revenue, parse_statement


PROFILE_HTML = """
<main>
  <h2>公司基本資料</h2>
  <div>公司名稱</div><div>台積電</div>
  <div>英文簡稱</div><div>TSMC</div>
  <div>產業類別</div><div>半導體</div>
  <div>公司網站</div><a href="https://www.tsmc.com">https://www.tsmc.com</a>
  <div>市場別</div><div>上市</div>
  <div>主要經營業務</div><div>積體電路製造與銷售</div>
  <h2>配股資訊</h2>
</main>
"""

REVENUE_HTML = """
<main>
  <div>2026/01</div>
  <div>401,255,128</div><div>19.78%</div><div>293,288,038</div><div>36.81%</div>
  <div>401,255,128</div><div>293,288,038</div><div>36.81%</div>
  <div>2025/12</div>
  <div>335,003,568</div><div>-2.51%</div><div>278,163,107</div><div>20.43%</div>
  <div>3,809,054,272</div><div>2,894,307,699</div><div>31.61%</div>
</main>
"""

INCOME_HTML = """
<main>
  <div>單位 : 仟元</div>
  <div>年度/月份</div>
  <div>2025 Q3</div><div>2025 Q2</div>
  <div>營業收入</div><div>989,918,318</div><div>933,791,869</div>
  <div>營業毛利</div><div>588,542,829</div><div>547,369,238</div>
  <div>稅後淨利</div><div>452,302,326</div><div>398,273,443</div>
</main>
"""


class YahooParserTests(unittest.TestCase):
    def test_parse_profile_extracts_company_fields(self):
        result = parse_profile(PROFILE_HTML)

        self.assertEqual(result["公司名稱"], "台積電")
        self.assertEqual(result["英文簡稱"], "TSMC")
        self.assertEqual(result["產業類別"], "半導體")
        self.assertEqual(result["市場別"], "上市")
        self.assertIn("積體電路", result["主要經營業務"])

    def test_parse_revenue_extracts_monthly_rows(self):
        result = parse_revenue(REVENUE_HTML)

        self.assertEqual(result[0]["period"], "2026/01")
        self.assertEqual(result[0]["monthly_revenue_thousand_twd"], 401255128)
        self.assertEqual(result[0]["monthly_yoy_pct"], 36.81)
        self.assertEqual(result[1]["cumulative_yoy_pct"], 31.61)

    def test_parse_statement_extracts_period_columns_by_line_item(self):
        result = parse_statement(INCOME_HTML, ["營業收入", "營業毛利", "稅後淨利"])

        self.assertEqual(result["unit"], "仟元")
        self.assertEqual(result["periods"], ["2025 Q3", "2025 Q2"])
        self.assertEqual(result["line_items"]["營業收入"]["2025 Q3"], 989918318)
        self.assertEqual(result["line_items"]["營業毛利"]["2025 Q2"], 547369238)

    def test_metadata_uses_current_envelope_and_blocks_missing_profile(self):
        result = build_metadata(
            "2330",
            row_counts={"profile": 0, "revenue": 1, "income_statement": 1, "cash_flow_statement": 1},
            fetched_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        )

        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["status"], STATUS_BLOCKED)
        self.assertEqual(result["source_tiers"]["profile"], "unofficial_secondary")
        self.assertEqual(result["parser_version"], "2")

    def test_metadata_degrades_when_optional_tables_are_missing(self):
        result = build_metadata(
            "2330",
            row_counts={"profile": 3, "revenue": 0, "income_statement": 0, "cash_flow_statement": 0},
        )

        self.assertEqual(result["status"], STATUS_DEGRADED)


if __name__ == "__main__":
    unittest.main()
