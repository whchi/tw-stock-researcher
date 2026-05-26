import tempfile
import unittest
from pathlib import Path

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
