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
        def files(path, heading):
            lines = (ROOT / path).read_text().splitlines()
            section_start = lines.index(heading) + 1
            section = []
            for line in lines[section_start:]:
                if line.startswith("## "):
                    break
                section.append(line)
            return {
                line.split("`")[1]
                for line in section
                if line.startswith("| `")
            }

        agents = files("AGENTS.md", "## File Structure & Ownership")
        layout = files("docs/data-layout.md", "## File Ownership")
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

    def test_investment_thesis_preserves_conflicts_and_runs_adversarial_review(self):
        skill = (ROOT / ".agents/skills/investment-thesis/SKILL.md").read_text()
        template = (ROOT / "templates/investment-memo.md").read_text()

        self.assertIn("cross-layer conflict map", skill)
        self.assertIn("before assigning Bull/Base/Bear probabilities", skill)
        for reviewer in ("Bull Researcher", "Bear Researcher", "Risk Reviewer"):
            self.assertIn(reviewer, skill)
            self.assertIn(f"| {reviewer} |", template)

        conflict_step = skill.index("Build a cross-layer conflict map")
        review_step = skill.index("Run the adversarial review")
        scenario_step = skill.index("Include Bull/Base/Bear scenarios")
        self.assertLess(conflict_step, review_step)
        self.assertLess(review_step, scenario_step)
        self.assertIn("same evidence cutoff", skill)

        self.assertIn("## Cross-Layer Conflict Map", template)
        for column in (
            "Evidence Layer",
            "Current Signal",
            "Time Horizon",
            "Conflicts With",
            "Reconciliation",
            "Resolution Evidence",
            "Confidence Impact",
        ):
            self.assertIn(column, template)
        self.assertIn("## Adversarial Review", template)

    def test_research_updates_use_evidence_thesis_impact_next_verification(self):
        contract = "Evidence → Thesis Impact → Next Verification"
        for path in (
            ".agents/skills/investment-thesis/SKILL.md",
            ".agents/skills/signal-update/SKILL.md",
            ".agents/skills/session-wrap/SKILL.md",
            "templates/investment-memo.md",
            "templates/signal-log.md",
            "templates/active-decisions.md",
        ):
            content = (ROOT / path).read_text()
            self.assertIn(contract, content, path)
            self.assertIn("Next Verification", content, path)

        signal_skill = (ROOT / ".agents/skills/signal-update/SKILL.md").read_text()
        signal_template = (ROOT / "templates/signal-log.md").read_text()
        self.assertNotIn("Next Action", signal_skill)
        self.assertNotIn("Next Action", signal_template)
        expected_headers = {
            "templates/investment-memo.md": (
                "| Evidence | Source / Observation Date | "
                "Thesis Impact (Business / Pricing / Both) | "
                "Next Verification | Failure Signal |"
            ),
            "templates/active-decisions.md": (
                "| Evidence | Source / Observation Date | "
                "Thesis Impact (Business / Pricing / Both) | "
                "Next Verification | Failure Signal |"
            ),
            "templates/signal-log.md": (
                "| Date | Signal Layer | Signal Type | Claim Type | "
                "Classification | Source / Observation Date | Evidence | "
                "Price Reaction | Revenue/Earnings Validation | "
                "Thesis Impact (Business / Pricing / Both) | Next Verification |"
            ),
        }
        for path, header in expected_headers.items():
            self.assertIn(header, (ROOT / path).read_text(), path)

    def test_html_requires_all_current_research_contract_blocks(self):
        skill = (ROOT / ".agents/skills/research-html-output/SKILL.md").read_text()
        template = (ROOT / "templates/research-html-summary.html").read_text()

        for placeholder in (
            "CROSS_LAYER_CONFLICT_ROWS",
            "ADVERSARIAL_REVIEW_ROWS",
            "EVIDENCE_THESIS_VERIFICATION_ROWS",
            "DATA_AVAILABILITY_ROWS",
        ):
            self.assertIn(placeholder, skill)
            self.assertIn(f"{{{{{placeholder}}}}}", template)
        self.assertNotIn("backward-compatible", skill)
        self.assertNotIn("older payload", skill)

    def test_html_pricing_stage_gate_has_the_same_five_columns_as_the_memo(self):
        template = (ROOT / "templates/research-html-summary.html").read_text()
        section = template.split('id="pricing-stage-verification"', 1)[1].split(
            "</section>", 1
        )[0]
        headers = (
            "Criterion",
            "Verification Rule",
            "Current Evidence",
            "Result",
            "Missing Evidence / Next Check",
        )

        self.assertEqual(section.count("<th>"), len(headers))
        positions = [section.index(f"<th>{header}</th>") for header in headers]
        self.assertEqual(positions, sorted(positions))

    def test_data_availability_contract_is_current_only_and_blocks_unavailable_layers(self):
        agents = (ROOT / "AGENTS.md").read_text()
        layout = (ROOT / "docs/data-layout.md").read_text()
        freshness = (ROOT / "docs/data-freshness.md").read_text()

        self.assertIn("Data Availability Contract", agents)
        self.assertIn("metadata.data_availability", layout)
        for field in (
            "status",
            "observation_date",
            "source",
            "missing_inputs",
            "failure_reasons",
            "confidence_impact",
        ):
            self.assertIn(f"`{field}`", layout)

        self.assertIn(
            "Provider failure is a data limitation, not a negative company signal",
            freshness,
        )
        self.assertIn(
            "Do not reuse an older artifact to satisfy a current refresh",
            freshness,
        )
        self.assertIn(
            "`unavailable` blocks every conclusion that depends on that evidence layer",
            freshness,
        )
        for legacy_rule in (
            "intentionally reused",
            "reason for reuse",
            "keep the last successful artifact",
        ):
            self.assertNotIn(legacy_rule, freshness)

        for path in (
            ".agents/skills/yahoo-profile-financials/SKILL.md",
            ".agents/skills/financial-analysis/SKILL.md",
            ".agents/skills/macro-impact-analysis/SKILL.md",
            ".agents/skills/market-data-fetch/SKILL.md",
            ".agents/skills/case-revisit/SKILL.md",
        ):
            skill = (ROOT / path).read_text()
            self.assertIn("metadata.data_availability", skill, path)
            self.assertIn("unavailable", skill, path)

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
