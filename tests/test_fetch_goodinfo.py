import unittest

from bs4 import BeautifulSoup

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


if __name__ == "__main__":
    unittest.main()
