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

    def test_financial_analysis_requires_four_three_statement_contradiction_checks(self):
        skill = (ROOT / ".agents/skills/financial-analysis/SKILL.md").read_text()
        template = (ROOT / "templates/financial-analysis.md").read_text()

        self.assertIn("four three-statement contradiction checks", skill)
        self.assertIn("## Three-Statement Contradiction Checks", template)
        for check in (
            "Revenue vs cash conversion",
            "Operating profit vs revenue",
            "Capex follow-through",
            "Inventory-to-CFO lead",
        ):
            self.assertIn(check, template)
        self.assertIn("Confirming / Diverging / Watch / Insufficient data", template)

    def test_pricing_thesis_requires_a_stage_one_to_two_verification_gate(self):
        framework = (ROOT / "investment-reasoning-framework.md").read_text()
        skill = (ROOT / ".agents/skills/investment-thesis/SKILL.md").read_text()
        template = (ROOT / "templates/investment-memo.md").read_text()

        self.assertIn("Stage 1 → Stage 2 驗證門檻", framework)
        self.assertIn("至少 5 個百分點", framework)
        self.assertIn("Revenue vs cash conversion 為 Diverging", framework)
        self.assertIn("至少 3 項有來源的當期成果陳述", framework)
        self.assertIn("Stage 1 → Stage 2 verification gate", skill)
        self.assertIn("## Pricing Stage Verification", template)
        for criterion in ("Structure", "Quality", "Narrative"):
            self.assertIn(f"| {criterion} |", template)

    def test_period_comparisons_keep_the_current_period_as_the_subject(self):
        for path in (
            ".agents/skills/financial-analysis/SKILL.md",
            ".agents/skills/case-revisit/SKILL.md",
        ):
            content = (ROOT / path).read_text()
            self.assertIn(
                "the current period is the subject and prior periods are comparison baselines",
                content,
                path,
            )

    def test_session_wrap_persists_a_six_dimension_completeness_gate(self):
        skill = (ROOT / ".agents/skills/session-wrap/SKILL.md").read_text()
        template = (ROOT / "templates/active-decisions.md").read_text()

        self.assertIn("six-dimension research completeness gate", skill)
        self.assertIn("## Research Completeness Gate", template)
        for dimension in (
            "Business",
            "Risk",
            "Financial",
            "Quality Signal",
            "Forward-Looking",
            "Internal Consistency",
        ):
            self.assertIn(f"| {dimension} |", template)
        self.assertIn("## Critical Gaps And Remedy", template)

    def test_investment_thesis_exposes_information_edge_and_confidence_downgrades(self):
        skill = (ROOT / ".agents/skills/investment-thesis/SKILL.md").read_text()
        template = (ROOT / "templates/investment-memo.md").read_text()

        self.assertIn("information edge", skill)
        self.assertIn("automatically lower overall memo confidence", skill)
        self.assertIn("## Information Edge", template)
        self.assertIn("No defensible information edge identified", template)
        self.assertIn("## Confidence Calibration", template)
        self.assertIn("Low-confidence evidence layers", template)

    def test_company_analysis_tracks_management_claims_without_inventing_outcomes(self):
        skill = (ROOT / ".agents/skills/company-deep-dive/SKILL.md").read_text()
        template = (ROOT / "templates/company-analysis.md").read_text()

        self.assertIn("management narrative tracking", skill)
        self.assertIn("Insufficient data", skill)
        self.assertIn("## Management Narrative Tracking", template)
        self.assertIn("Prior Commitment", template)
        self.assertIn("Current-Period Outcome Evidence", template)
        self.assertIn("Plan / Outcome / Silence", template)
        self.assertIn("Silence is an open question, not evidence of abandonment", template)

    def test_financial_analysis_treats_accounting_anomalies_as_verification_candidates(self):
        skill = (ROOT / ".agents/skills/financial-analysis/SKILL.md").read_text()
        template = (ROOT / "templates/financial-analysis.md").read_text()

        self.assertIn("accounting anomaly verification", skill)
        self.assertIn("MOPS financial-statement notes", skill)
        self.assertIn("Low confidence", skill)
        self.assertIn("## Accounting Anomaly Verification", template)
        for candidate in (
            "Related-party transactions",
            "Off-balance-sheet commitments",
            "Revenue-recognition policy changes",
            "One-period line-item discontinuities",
            "Non-operating gains / losses",
            "Investment structure",
            "Asset revaluation",
        ):
            self.assertIn(candidate, template)

    def test_company_analysis_classifies_segment_transitions_only_with_comparable_data(self):
        skill = (ROOT / ".agents/skills/company-deep-dive/SKILL.md").read_text()
        template = (ROOT / "templates/company-analysis.md").read_text()

        self.assertIn("segment transition analysis", skill)
        self.assertIn("15 percentage points", skill)
        self.assertIn("upgrading / downgrading / stable / diversifying", skill)
        self.assertIn("## Segment Transition", template)
        self.assertIn("Comparable / Changed definition / Insufficient data", template)
        self.assertIn("Do not substitute company-wide gross margin for segment margin", template)

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
