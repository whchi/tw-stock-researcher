import unittest
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from scripts.data_contract import STATUS_BLOCKED, STATUS_PASS
from scripts.fetch_goodinfo import (
    build_metadata,
    build_three_statement_coverage,
    parse_table,
    pick_key,
)


SAMPLE_TABLE_HTML = """
<section>
  <table>
    <tr><th>本業獲利</th><th>2025</th><th>2024</th><th>2023</th></tr>
    <tr><td>金額</td><td>％</td><td>金額</td><td>％</td><td>金額</td><td>％</td></tr>
    <tr><td>營業收入</td><td>8.96</td><td>100</td><td>9.28</td><td>100</td><td>13.33</td><td>100</td></tr>
    <tr><td>稅後淨利</td><td>-0.94</td><td>-10.5</td><td>0.38</td><td>4.1</td><td>4.45</td><td>33.4</td></tr>
  </table>
</section>
"""


class GoodinfoParserTests(unittest.TestCase):
    def test_parse_table_uses_amount_columns_not_percentage_columns(self):
        data, years = parse_table(BeautifulSoup(SAMPLE_TABLE_HTML, "html.parser"))

        self.assertEqual(years, ["2025", "2024", "2023"])
        self.assertEqual(data["營業收入"]["2024"], 9.28)
        self.assertEqual(data["稅後淨利"]["2025"], -0.94)
        self.assertNotEqual(data["營業收入"]["2024"], 100.0)

    def test_pick_key_matches_exact_or_include_terms(self):
        table = {"應收帳款淨額": {}, "其他資產": {}}

        self.assertEqual(pick_key(table, "應收帳款淨額"), "應收帳款淨額")
        self.assertEqual(pick_key(table, "應收帳款", includes=["應收", "帳款"]), "應收帳款淨額")

    def test_coverage_marks_missing_required_items(self):
        result = {
            "income_statement": {"營業收入": {}, "營業利益": {}, "稅後淨利": {}},
            "balance_sheet": {"現金及約當現金": {}, "應收帳款淨額": {}},
            "cash_flow": {"營業活動之淨現金流入(出)": {}},
        }

        coverage = build_three_statement_coverage(result)

        self.assertFalse(coverage["baseline_supported"])
        self.assertIn("inventory", coverage["required_missing"])

    def test_metadata_blocks_without_all_three_required_tables(self):
        blocked = build_metadata(
            "2330",
            row_counts={"income_statement": 1, "balance_sheet": 0, "cash_flow": 1},
            fetched_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        )
        passed = build_metadata(
            "2330",
            row_counts={"income_statement": 1, "balance_sheet": 1, "cash_flow": 1},
        )

        self.assertEqual(blocked["status"], STATUS_BLOCKED)
        self.assertEqual(passed["status"], STATUS_PASS)
        self.assertEqual(blocked["source_tiers"]["income_statement"], "unofficial_scrape")


if __name__ == "__main__":
    unittest.main()
