import json
import unittest
from pathlib import Path

from scripts.fetch_official_issuer import (
    OfficialIssuerError,
    fetch_official_issuer,
    normalize_period,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "official-sources"


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeClient:
    """Routes fixture rows by dataset code found in the requested URL, so no
    real network call ever happens in these tests."""

    def __init__(self, dataset_rows, fail_datasets=()):
        self.dataset_rows = dataset_rows
        self.fail_datasets = set(fail_datasets)
        self.requested_urls = []

    def get(self, url, timeout=None):
        self.requested_urls.append(url)
        for dataset_key, rows in self.dataset_rows.items():
            if dataset_key in url:
                if dataset_key in self.fail_datasets:
                    raise RuntimeError("simulated TLS failure")
                return FakeResponse(rows)
        return FakeResponse([])


def load_fixture(name):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class NormalizePeriodTests(unittest.TestCase):
    def test_normalizes_monthly_revenue_row(self):
        period_type, period_key, source_as_of = normalize_period({"資料年月": "11505"})
        self.assertEqual(period_type, "monthly")
        self.assertEqual(period_key, "2026-05")
        self.assertEqual(source_as_of, "2026-05")

    def test_normalizes_quarterly_row(self):
        period_type, period_key, source_as_of = normalize_period({"年度": "115", "季別": "1"})
        self.assertEqual(period_type, "quarterly")
        self.assertEqual(period_key, "2026Q1")
        self.assertEqual(source_as_of, "2026Q1")

    def test_raises_when_period_fields_absent(self):
        with self.assertRaises(OfficialIssuerError):
            normalize_period({"unrelated": "field"})


class FetchOfficialIssuerTests(unittest.TestCase):
    def test_general_issuer_returns_pass_with_matched_rows(self):
        fixture = load_fixture("twse-listed-general.json")
        client = FakeClient(
            {
                "t187ap03_L": fixture["basic_info"],
                "t187ap05_L": fixture["monthly_revenue"],
                "t187ap06_L_ci": fixture["quarterly_income"],
                "t187ap07_L_ci": [{"公司代號": "2330", "年度": "115", "季別": "1", "資產總額": "100"}],
            }
        )

        result = fetch_official_issuer("2330", "TWSE", "general", client)

        self.assertEqual(result["metadata"]["status"], "pass")
        self.assertEqual(len(result["raw"]["basic_info"]), 1)
        self.assertEqual(result["raw"]["basic_info"][0]["公司代號"], "2330")
        self.assertEqual(result["metadata"]["source_as_of"], "2026-05")
        self.assertEqual(len(result["raw"]["income_statement"]), 1)
        self.assertEqual(len(result["raw"]["balance_sheet"]), 1)
        self.assertTrue(
            {
                "material_events",
                "major_shareholders",
                "director_holdings",
                "director_pledges",
                "insider_transfers",
                "dividends",
            }.issubset(result["raw"])
        )

    def test_financial_issuer_tolerates_not_applicable_sentinel_fields(self):
        fixture = load_fixture("twse-listed-financial.json")
        client = FakeClient(
            {
                "t187ap03_L": fixture["basic_info"],
                "t187ap05_L": fixture["monthly_revenue"],
                "t187ap06_L_fh": fixture["quarterly_income"],
                "t187ap07_L_fh": [{"公司代號": "2891", "年度": "115", "季別": "1", "資產總額": "100"}],
            }
        )

        result = fetch_official_issuer("2891", "TWSE", "financial", client)

        self.assertEqual(result["metadata"]["status"], "degraded")  # monthly_revenue optional dataset is empty
        self.assertEqual(result["metadata"]["source_as_of"], "2026Q1")
        income_row = result["raw"]["income_statement"][0]
        self.assertEqual(income_row["基本每股盈餘（元）"], "1.18")

    def test_sibling_variant_failure_is_not_erased_by_a_later_matching_variant(self):
        fixture = load_fixture("twse-listed-financial.json")
        client = FakeClient(
            {
                "t187ap03_L": fixture["basic_info"],
                "t187ap05_L": fixture["monthly_revenue"],
                "t187ap06_L_basi": [],
                "t187ap06_L_fh": fixture["quarterly_income"],
                "t187ap07_L_fh": [{"公司代號": "2891", "年度": "115", "季別": "1", "資產總額": "100"}],
            },
            fail_datasets={"t187ap06_L_basi"},
        )

        result = fetch_official_issuer("2891", "TWSE", "financial", client)

        # basi (tried before fh) genuinely failed; fh matched afterwards.
        # The genuine basi failure must survive in errors/status even though
        # the search overall found the company's income-statement row.
        self.assertEqual(result["metadata"]["status"], "degraded")
        self.assertTrue(
            any(
                error["dataset"] == "t187ap06_L_basi" and error["code"] == "fetch_failed"
                for error in result["metadata"]["errors"]
            )
        )
        self.assertEqual(len(result["raw"]["income_statement"]), 1)

    def test_tpex_endpoint_failure_is_blocked_not_bypassed(self):
        fixture = load_fixture("tpex-otc-general.json")
        client = FakeClient(
            {
                "t187ap03_O": fixture["basic_info"],
                "t187ap05_O": fixture["monthly_revenue"],
                "t187ap06_O_ci": fixture["quarterly_income"],
                "t187ap07_O_ci": [{"公司代號": "6488", "年度": "115", "季別": "1"}],
            },
            fail_datasets={"t187ap03_O", "t187ap05_O", "t187ap06_O_ci", "t187ap07_O_ci"},
        )

        result = fetch_official_issuer("6488", "TPEx", "general", client)

        self.assertEqual(result["metadata"]["status"], "blocked")
        self.assertTrue(result["metadata"]["errors"])
        self.assertEqual(result["raw"]["basic_info"], [])

    def test_uses_explicit_endpoint_allowlist_per_market(self):
        fixture = load_fixture("twse-listed-general.json")
        client = FakeClient(
            {
                "t187ap03_L": fixture["basic_info"],
                "t187ap05_L": fixture["monthly_revenue"],
                "t187ap06_L_ci": fixture["quarterly_income"],
                "t187ap07_L_ci": [{"公司代號": "2330", "年度": "115", "季別": "1"}],
            }
        )

        fetch_official_issuer("2330", "TWSE", "general", client)

        self.assertTrue(all(url.startswith("https://openapi.twse.com.tw/") for url in client.requested_urls))

    def test_rejects_unknown_market(self):
        with self.assertRaises(Exception):
            fetch_official_issuer("2330", "NYSE", "general", FakeClient({}))

    def test_rejects_unknown_issuer_type(self):
        with self.assertRaises(Exception):
            fetch_official_issuer("2330", "TWSE", "bank", FakeClient({}))


if __name__ == "__main__":
    unittest.main()
