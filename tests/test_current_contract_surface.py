import inspect
import unittest
from pathlib import Path

from scripts import fetch_macro


REPO_ROOT = Path(__file__).resolve().parent.parent


class DocumentationContractTests(unittest.TestCase):
    def test_readme_documents_current_html_cli_only(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("scripts/build_research_summary.py --case companies/<ticker-slug>", readme)
        self.assertIn("scripts/render_research_html.py --case companies/<ticker-slug>", readme)
        self.assertNotIn("--data companies/<ticker-slug>/research-summary-data.json", readme)
        self.assertNotIn("--output companies/<ticker-slug>/research-summary.html", readme)

    def test_market_data_skill_documents_tdcc_json_cache(self):
        skill = (REPO_ROOT / ".agents" / "skills" / "market-data-fetch" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("all-market JSON", skill)
        self.assertIn("tdcc-holding-distribution.json", skill)
        self.assertNotIn("all-market CSV", skill)
        self.assertNotIn("tdcc-holding-distribution.csv", skill)

    def test_companies_directory_placeholder_is_preserved(self):
        self.assertTrue((REPO_ROOT / "companies" / ".gitkeep").exists())


class ProductionFetchPolicyTests(unittest.TestCase):
    def test_fetch_macro_has_no_insecure_tls_bypass(self):
        source = inspect.getsource(fetch_macro)

        self.assertNotIn("verify=False", source)
        self.assertNotIn("InsecureRequestWarning", source)
        self.assertNotIn("request_text_with_ssl_fallback", source)


if __name__ == "__main__":
    unittest.main()
