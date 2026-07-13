import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def test_stock_meta_template_covers_all_case_artifacts(self):
        refs = json.loads((ROOT / "templates/stock-meta.json").read_text())["file_references"]
        expected = {
            "yahoo_data",
            "raw_data",
            "fundamentals_data",
            "research_questions",
            "company_analysis",
            "financial_analysis",
            "industry_transmission",
            "macro_map",
            "quality_and_valuation_check",
            "investment_memo",
            "market_data",
            "tdcc_data",
            "market_action_read",
            "signal_log",
            "thesis_updates",
            "open_questions",
            "active_decisions",
            "research_summary_data",
            "research_summary_html",
        }
        self.assertTrue(expected.issubset(refs.keys()))

    def test_ownership_docs_cover_the_same_case_file_set(self):
        def files(path):
            return {
                line.split("`")[1]
                for line in (ROOT / path).read_text().splitlines()
                if line.startswith("| `")
            }

        agents = files("AGENTS.md")
        layout = files("docs/data-layout.md")
        self.assertEqual(agents, layout)
        self.assertIn("research-summary.html", agents)

    def test_framework_contains_no_position_or_trade_tactics(self):
        framework = (ROOT / "investment-reasoning-framework.md").read_text()
        for phrase in ("邊漲邊賣", "三段式減碼", "建立什麼規模的觀察部位"):
            self.assertNotIn(phrase, framework)

    def test_first_run_uses_valid_uv_install_and_declares_token(self):
        first_run = (ROOT / "FIRST_RUN.md").read_text()
        self.assertIn("uv pip install requests beautifulsoup4", first_run)
        self.assertIn("FIN_MIND_TOKEN", first_run)
        self.assertIn("session-wrap", first_run)
        self.assertIn("before ending", first_run)

    def test_html_skill_has_standard_source_and_output_sections(self):
        skill = (ROOT / ".agents/skills/research-html-output/SKILL.md").read_text()
        self.assertIn("## Source Of Truth", skill)
        self.assertIn("## Output", skill)

    def test_readme_does_not_put_peer_comparison_in_case_financial_analysis(self):
        readme = (ROOT / "README.md").read_text()
        self.assertNotIn("side-by-side comparison in `financial-analysis.md`", readme)

    def test_goodinfo_help_is_side_effect_free(self):
        fallback = ROOT / "--help_raw_data.json"
        fallback.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/fetch_goodinfo.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout.lower())
        self.assertFalse(fallback.exists())


if __name__ == "__main__":
    unittest.main()
