import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.case_paths import CaseResolutionError, case_output_path, resolve_case_dir
from scripts.data_contract import STATUS_BLOCKED, STATUS_DEGRADED, STATUS_PASS
from scripts.fetch_finmind import build_metadata as build_finmind_metadata
from scripts.fetch_fundamentals import build_metadata as build_fundamentals_metadata
from scripts.fetch_goodinfo import build_metadata as build_goodinfo_metadata
from scripts.fetch_macro import build_customs_trade_rows
from scripts.fetch_official_issuer import fetch_official_issuer
from scripts.fetch_tdcc import (
    CACHE_JSON_NAME,
    build_metadata as build_tdcc_metadata,
    cache_paths,
    parse_holding_distribution,
)
from scripts.fetch_yahoo import build_metadata as build_yahoo_metadata


class CasePathContractTests(unittest.TestCase):
    def test_resolves_exactly_one_real_case_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "companies" / "2330-tsmc"
            case_dir.mkdir(parents=True)

            self.assertEqual(resolve_case_dir("2330", root), case_dir.resolve())
            self.assertEqual(case_output_path("2330", "market-data.json", root), case_dir.resolve() / "market-data.json")

    def test_fails_closed_when_case_directory_is_missing_or_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "companies").mkdir()

            with self.assertRaises(CaseResolutionError):
                resolve_case_dir("2330", root)

            (root / "companies" / "2330-a").mkdir()
            (root / "companies" / "2330-b").mkdir()

            with self.assertRaises(CaseResolutionError):
                resolve_case_dir("2330", root)

    def test_fails_closed_for_non_numeric_stock_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CaseResolutionError):
                resolve_case_dir("../2330", Path(tmp))


class TdccCurrentFormatTests(unittest.TestCase):
    def test_cache_path_uses_native_json_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path, _meta_path = cache_paths(Path(tmp))

            self.assertEqual(cache_path.name, CACHE_JSON_NAME)
            self.assertEqual(cache_path.suffix, ".json")

    def test_parses_native_json_rows_without_csv_conversion(self):
        rows = parse_holding_distribution(
            [
                {
                    "資料日期": "20260710",
                    "證券代號": "2330",
                    "持股分級": "15",
                    "人數": "10",
                    "股數": "123456",
                    "占集保庫存數比例%": "1.23",
                },
                {
                    "資料日期": "20260710",
                    "證券代號": "2317",
                    "持股分級": "15",
                    "人數": "99",
                    "股數": "999",
                    "占集保庫存數比例%": "9.99",
                },
            ],
            "2330",
        )

        self.assertEqual(rows, [
            {
                "date": "2026-07-10",
                "stock_id": "2330",
                "HoldingSharesLevel": "15",
                "people": 10,
                "shares": 123456,
                "percent": 1.23,
                "unit": "股",
            }
        ])

    def test_tdcc_metadata_blocks_when_required_rows_are_missing(self):
        metadata = build_tdcc_metadata([], fetched_at=datetime(2026, 7, 11, tzinfo=timezone.utc))

        self.assertEqual(metadata["status"], STATUS_BLOCKED)
        self.assertEqual(metadata["parser_version"], "3")


class FetcherMetadataContractTests(unittest.TestCase):
    def test_yahoo_profile_is_required_and_supplemental_tables_degrade(self):
        blocked = build_yahoo_metadata("2330", row_counts={"profile": 0})
        degraded = build_yahoo_metadata("2330", row_counts={"profile": 3, "revenue": 0})

        self.assertEqual(blocked["status"], STATUS_BLOCKED)
        self.assertEqual(degraded["status"], STATUS_DEGRADED)

    def test_goodinfo_three_statement_tables_are_required(self):
        passed = build_goodinfo_metadata(
            "2330",
            row_counts={"income_statement": 1, "balance_sheet": 1, "cash_flow": 1},
        )
        blocked = build_goodinfo_metadata(
            "2330",
            row_counts={"income_statement": 1, "balance_sheet": 0, "cash_flow": 1},
        )

        self.assertEqual(passed["status"], STATUS_PASS)
        self.assertEqual(blocked["status"], STATUS_BLOCKED)

    def test_finmind_price_and_institutional_rows_are_required(self):
        raw_counts = {
            "TaiwanStockPrice": 1,
            "TaiwanStockInstitutionalInvestorsBuySell": 1,
            "TaiwanStockMarginPurchaseShortSale": 0,
            "TaiwanStockShareholding": 0,
            "TaiwanStockDayTrading": 0,
            "TaiwanStockHoldingSharesPer": 0,
        }

        degraded = build_finmind_metadata(
            "2330",
            "2026-01-01",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in raw_counts.items()},
            tdcc_holding_distribution_rows=[],
        )
        blocked_counts = dict(raw_counts, TaiwanStockPrice=0)
        blocked = build_finmind_metadata(
            "2330",
            "2026-01-01",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in blocked_counts.items()},
            tdcc_holding_distribution_rows=[],
        )

        self.assertEqual(degraded["status"], STATUS_DEGRADED)
        self.assertEqual(blocked["status"], STATUS_BLOCKED)

    def test_fundamentals_monthly_revenue_and_income_are_required(self):
        raw_counts = {
            "TaiwanStockMonthRevenue": 1,
            "TaiwanStockFinancialStatements": 1,
            "TaiwanStockBalanceSheet": 0,
            "TaiwanStockCashFlowsStatement": 0,
            "TaiwanStockPER": 0,
        }

        degraded = build_fundamentals_metadata(
            "2330",
            "2021-07-11",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in raw_counts.items()},
        )
        blocked_counts = dict(raw_counts, TaiwanStockFinancialStatements=0)
        blocked = build_fundamentals_metadata(
            "2330",
            "2021-07-11",
            "2026-07-11",
            {dataset: [object()] * count for dataset, count in blocked_counts.items()},
        )

        self.assertEqual(degraded["status"], STATUS_DEGRADED)
        self.assertEqual(blocked["status"], STATUS_BLOCKED)


class OfficialIssuerContractTests(unittest.TestCase):
    class FakeResponse:
        def __init__(self, rows):
            self.rows = rows

        def raise_for_status(self):
            return None

        def json(self):
            return self.rows

    class FakeClient:
        def __init__(self, rows_by_dataset):
            self.rows_by_dataset = rows_by_dataset
            self.urls = []

        def get(self, url, timeout):
            self.urls.append(url)
            dataset = url.rsplit("/", 1)[-1]
            return OfficialIssuerContractTests.FakeResponse(self.rows_by_dataset.get(dataset, []))

    def test_official_issuer_uses_allowlisted_twse_datasets_and_blocks_missing_required_rows(self):
        client = self.FakeClient(
            {
                "t187ap03_L": [{"公司代號": "2330"}],
                "t187ap05_L": [{"公司代號": "2330", "資料年月": "11506"}],
                "t187ap06_L_ci": [],
                "t187ap07_L_ci": [{"公司代號": "2330", "年度": "115", "季別": "2"}],
            }
        )

        payload = fetch_official_issuer("2330", "TWSE", "general", client)

        self.assertEqual(payload["metadata"]["status"], STATUS_BLOCKED)
        self.assertTrue(all(url.startswith("https://openapi.twse.com.tw/v1/opendata/") for url in client.urls))
        self.assertEqual(payload["metadata"]["source_tiers"]["income_statement"], "official")


class MacroParserContractTests(unittest.TestCase):
    def test_customs_trade_rows_parse_default_official_csv_shape(self):
        text = (
            "年度,月份,出口總值(新臺幣千元),進口總值(新臺幣千元),出入超(新臺幣千元)\n"
            "114,06,100,80,20\n"
            "115,06,125,90,35\n"
        )

        rows = build_customs_trade_rows(text, "https://example.test/customs.csv")

        self.assertEqual(rows[0]["latest"]["date"], "2026-06")
        self.assertEqual(rows[0]["latest"]["exports_yoy_pct"], 25.0)
        self.assertEqual(rows[0]["observations"][-1]["trade_balance_twd_thousand"], 35.0)


if __name__ == "__main__":
    unittest.main()
