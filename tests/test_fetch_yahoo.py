import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.fetch_yahoo as fetch_yahoo
from scripts.fetch_yahoo import (
    build_metadata,
    main,
    parse_profile,
    parse_revenue,
    parse_statement,
)


PROFILE_HTML = """
<main>
  <h2>公司基本資料</h2>
  <div>資料時間：2026/02/18</div>
  <div>公司名稱</div><div>台積電</div>
  <div>英文簡稱</div><div>TSMC</div>
  <div>產業類別</div><div>半導體</div>
  <div>公司網站</div><a href="https://www.tsmc.com">https://www.tsmc.com</a>
  <div>市場別</div><div>上市</div>
  <div>主要經營業務</div>
  <div>依客戶之訂單與其提供之產品設計說明，以從事製造與銷售積體電路。</div>
  <h2>配股資訊</h2>
</main>
"""


REVENUE_HTML = """
<main>
  <h2>營收</h2>
  <div>年度/月份</div>
  <div>單月合併 (單位：仟元)</div>
  <div>當月營收</div><div>月增率%</div><div>去年同月營收</div><div>年增率%</div>
  <div>累計合併 (單位：仟元)</div>
  <div>當月累計營收</div><div>去年累計營收</div><div>年增率%</div>
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
  <h2>損益表</h2>
  <div>單位 : 仟元</div>
  <div>年度/月份</div>
  <div>2025 Q3</div><div>2025 Q2</div>
  <div>營業收入</div>
  <div>989,918,318</div><div>933,791,869</div>
  <div>營業毛利</div>
  <div>588,542,829</div><div>547,369,238</div>
  <div>稅後淨利</div>
  <div>452,302,326</div><div>398,273,443</div>
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
        self.assertEqual(result["公司網站"], "https://www.tsmc.com")

    def test_parse_revenue_extracts_monthly_rows(self):
        result = parse_revenue(REVENUE_HTML)

        self.assertEqual(result[0]["period"], "2026/01")
        self.assertEqual(result[0]["monthly_revenue_thousand_twd"], 401255128)
        self.assertEqual(result[0]["monthly_mom_pct"], 19.78)
        self.assertEqual(result[0]["monthly_yoy_pct"], 36.81)
        self.assertEqual(result[1]["cumulative_yoy_pct"], 31.61)

    def test_parse_statement_extracts_period_columns_by_line_item(self):
        result = parse_statement(INCOME_HTML, ["營業收入", "營業毛利", "稅後淨利"])

        self.assertEqual(result["unit"], "仟元")
        self.assertEqual(result["periods"], ["2025 Q3", "2025 Q2"])
        self.assertEqual(result["line_items"]["營業收入"]["2025 Q3"], 989918318)
        self.assertEqual(result["line_items"]["營業毛利"]["2025 Q2"], 547369238)
        self.assertEqual(result["line_items"]["稅後淨利"]["2025 Q3"], 452302326)

    def test_build_metadata_uses_yahoo_urls(self):
        result = build_metadata("2330")

        self.assertEqual(result["source"], "Yahoo Finance Taiwan")
        self.assertEqual(result["symbol_suffix"], "TW")
        self.assertIn("profile", result["source_urls"])
        self.assertEqual(
            result["source_urls"]["profile"],
            "https://tw.stock.yahoo.com/quote/2330.TW/profile",
        )

    def test_build_metadata_can_use_otc_suffix(self):
        result = build_metadata("8299", suffix="TWO")

        self.assertEqual(
            result["source_urls"]["profile"],
            "https://tw.stock.yahoo.com/quote/8299.TWO/profile",
        )


class MainOutputResolutionTests(unittest.TestCase):
    def test_main_fails_closed_when_case_resolution_raises(self):
        with patch.object(
            fetch_yahoo,
            "case_output_path",
            side_effect=fetch_yahoo.CaseResolutionError("expected exactly one companies/2330-*/ directory; found 0: none"),
        ):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["2330"])

        self.assertEqual(exit_code, 1)
        self.assertIn("expected exactly one", stderr.getvalue())

    def test_main_writes_to_resolved_case_output_path_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "yahoo-data.json"
            with patch.object(fetch_yahoo, "case_output_path", return_value=target) as mock_resolve:
                with patch.object(fetch_yahoo, "fetch_all", return_value={"ok": True}):
                    exit_code = main(["2330"])

            mock_resolve.assert_called_once_with(
                "2330", "yahoo-data.json", Path(fetch_yahoo.__file__).resolve().parent.parent
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(target.exists())

    def test_main_routes_explicit_output_through_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "explicit.json"
            with patch.object(fetch_yahoo, "validate_explicit_output", return_value=target) as mock_validate:
                with patch.object(fetch_yahoo, "fetch_all", return_value={"ok": True}):
                    exit_code = main(["2330", "--output", str(target)])

            mock_validate.assert_called_once()
            self.assertEqual(exit_code, 0)
            self.assertTrue(target.exists())

    def test_main_fails_closed_when_explicit_output_escapes_repo(self):
        with patch.object(
            fetch_yahoo,
            "validate_explicit_output",
            side_effect=fetch_yahoo.CaseResolutionError("explicit output escapes repository"),
        ):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["2330", "--output", "/tmp/escape.json"])

        self.assertEqual(exit_code, 1)
        self.assertIn("escapes repository", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
