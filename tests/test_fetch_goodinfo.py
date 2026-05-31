import contextlib
import io
import unittest

from bs4 import BeautifulSoup

import scripts.fetch_goodinfo as goodinfo
from scripts.fetch_goodinfo import parse_table, pick_key


SAMPLE_AJAX_HTML = """
<section class='box_style'>
  <table>
    <tr>
      <th>本業獲利 (金額:億元)</th>
      <th>2025</th>
      <th>2024</th>
      <th>2023</th>
    </tr>
    <tr>
      <td>金額</td>
      <td>％</td>
      <td>金額</td>
      <td>％</td>
      <td>金額</td>
      <td>％</td>
    </tr>
    <tr>
      <td>銷貨收入淨額</td>
      <td>8.49</td>
      <td>94.7</td>
      <td>8.98</td>
      <td>96.8</td>
      <td>13.07</td>
      <td>98.0</td>
    </tr>
    <tr>
      <td>營業收入</td>
      <td>8.96</td>
      <td>100</td>
      <td>9.28</td>
      <td>100</td>
      <td>13.33</td>
      <td>100</td>
    </tr>
    <tr>
      <td>稅後淨利</td>
      <td>-0.94</td>
      <td>-10.5</td>
      <td>0.38</td>
      <td>4.1</td>
      <td>4.45</td>
      <td>33.4</td>
    </tr>
    <tr>
      <td>每股稅後盈餘(元)</td>
      <td>-1.18</td>
      <td></td>
      <td>0.48</td>
      <td></td>
      <td>5.58</td>
      <td></td>
    </tr>
  </table>
</section>
"""

SAMPLE_AJAX_PAIR_HTML = """
<section class='box_style'>
  <table>
    <tr>
      <th>本業獲利 (金額:億元)</th>
      <th>2025</th>
      <th>2024</th>
      <th>2023</th>
    </tr>
    <tr>
      <td>金額</td>
      <td>％</td>
      <td>金額</td>
      <td>％</td>
      <td>金額</td>
      <td>％</td>
    </tr>
    <tr>
      <td>營業收入</td>
      <td>8.96</td>
      <td>100</td>
      <td>9.28</td>
      <td>100</td>
      <td>13.34</td>
      <td>100</td>
    </tr>
    <tr>
      <td>營業毛利</td>
      <td>1.37</td>
      <td>15.2</td>
      <td>0.82</td>
      <td>8.79</td>
      <td>1.01</td>
      <td>7.6</td>
    </tr>
  </table>
</section>
"""


class ParseTableTests(unittest.TestCase):
    def test_parse_table_supports_ajax_single_table_layout(self):
        soup = BeautifulSoup(SAMPLE_AJAX_HTML, "html.parser")

        data, years = parse_table(soup)

        self.assertEqual(years, ["2025", "2024", "2023"])
        self.assertEqual(data["銷貨收入淨額"]["2025"], 8.49)
        self.assertEqual(data["營業收入"]["2024"], 9.28)
        self.assertEqual(data["稅後淨利"]["2023"], 4.45)
        self.assertEqual(data["每股稅後盈餘(元)"]["2025"], -1.18)
        self.assertNotEqual(data["營業收入"]["2024"], 100.0)

    def test_parse_table_uses_amount_columns_when_ajax_rows_include_percentages(self):
        soup = BeautifulSoup(SAMPLE_AJAX_PAIR_HTML, "html.parser")

        data, years = parse_table(soup)

        self.assertEqual(years, ["2025", "2024", "2023"])
        self.assertEqual(data["營業收入"]["2025"], 8.96)
        self.assertEqual(data["營業收入"]["2024"], 9.28)
        self.assertEqual(data["營業毛利"]["2023"], 1.01)


class PickKeyTests(unittest.TestCase):
    def test_pick_key_prefers_exact_match_over_partial_match(self):
        keys = ["其他營業收入", "營業收入", "合併稅後淨利", "稅後淨利"]

        self.assertEqual(pick_key(keys, "營業收入"), "營業收入")
        self.assertEqual(pick_key(keys, "稅後淨利"), "稅後淨利")


class ThreeStatementCoverageTests(unittest.TestCase):
    def test_coverage_confirms_baseline_fields_for_three_statement_pattern_read(self):
        result = {
            "income_statement": {
                "營業收入": {"2025": 100.0},
                "營業利益": {"2025": 20.0},
                "稅後淨利": {"2025": 15.0},
                "每股稅後盈餘(元)": {"2025": 3.0},
            },
            "balance_sheet": {
                "現金及約當現金": {"2025": 30.0},
                "應收帳款淨額": {"2025": 40.0},
                "存貨": {"2025": 25.0},
                "流動資產合計": {"2025": 120.0},
                "流動負債合計": {"2025": 60.0},
                "應付帳款": {"2025": 22.0},
                "負債總額": {"2025": 90.0},
                "股東權益總額": {"2025": 150.0},
                "資產總額": {"2025": 240.0},
            },
            "cash_flow": {
                "營業活動之淨現金流入(出)": {"2025": 18.0},
                "投資活動之淨現金流入(出)": {"2025": -10.0},
                "融資活動之淨現金流入(出)": {"2025": -5.0},
                "固定資產(增加)減少": {"2025": -8.0},
                "發放現金股利": {"2025": -4.0},
            },
        }

        self.assertTrue(hasattr(goodinfo, "build_three_statement_coverage"))
        coverage = goodinfo.build_three_statement_coverage(result)

        self.assertTrue(coverage["baseline_supported"])
        self.assertEqual(coverage["required_missing"], [])
        self.assertEqual(
            coverage["required"]["accounts_receivable"]["matched_key"],
            "應收帳款淨額",
        )
        self.assertEqual(
            coverage["required"]["operating_cash_flow"]["statement"],
            "cash_flow",
        )

    def test_coverage_reports_missing_fields_that_need_mops_or_notes(self):
        result = {
            "income_statement": {"營業收入": {"2025": 100.0}},
            "balance_sheet": {"資產總額": {"2025": 240.0}},
            "cash_flow": {},
        }

        self.assertTrue(hasattr(goodinfo, "build_three_statement_coverage"))
        coverage = goodinfo.build_three_statement_coverage(result)

        self.assertFalse(coverage["baseline_supported"])
        self.assertIn("accounts_receivable", coverage["required_missing"])
        self.assertIn("operating_cash_flow", coverage["required_missing"])
        self.assertIn("debt_maturity_schedule", coverage["supplemental_missing"])


class VerificationTests(unittest.TestCase):
    def test_run_verification_fails_when_goodinfo_tables_are_empty(self):
        result = {
            "years": [],
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "metadata": {"mops_url": "https://mops.example.test"},
        }

        with contextlib.redirect_stdout(io.StringIO()):
            verified = goodinfo.run_verification(result, {})

        self.assertFalse(verified["verification"]["sanity_pass"])
        fields = [warning["field"] for warning in verified["verification"]["sanity"]]
        self.assertIn("Goodinfo 財報年度", fields)
        self.assertIn("Goodinfo 損益表", fields)


if __name__ == "__main__":
    unittest.main()
