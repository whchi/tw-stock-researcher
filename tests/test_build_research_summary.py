import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build_research_summary import DISCLAIMER_SUMMARY, BuildError, build_summary, write_summary

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_CASE = REPO_ROOT / "tests" / "fixtures" / "research-summary-v1" / "case"
EXPECTED_DATA = REPO_ROOT / "tests" / "fixtures" / "research-summary-v1" / "expected-data.json"


class BuildSummaryGoldenTests(unittest.TestCase):
    def test_matches_the_golden_expected_payload(self):
        payload = build_summary(FIXTURE_CASE)
        expected = json.loads(EXPECTED_DATA.read_text(encoding="utf-8"))
        self.assertEqual(payload, expected)

    def test_two_consecutive_builds_are_identical(self):
        first = build_summary(FIXTURE_CASE)
        second = build_summary(FIXTURE_CASE)
        self.assertEqual(first, second)

    def test_source_manifest_hashes_are_stable_sha256_of_actual_file_bytes(self):
        import hashlib

        payload = build_summary(FIXTURE_CASE)
        for entry in payload["source_manifest"]:
            root = REPO_ROOT if entry["root"] == "repo" else FIXTURE_CASE
            actual = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
            self.assertEqual(entry["sha256"], actual)

    def test_source_manifest_includes_repo_disclaimer_used_by_payload(self):
        payload = build_summary(FIXTURE_CASE)

        disclaimers = [
            entry for entry in payload["source_manifest"]
            if entry["root"] == "repo" and entry["path"] == "DISCLAIMER.md"
        ]
        self.assertEqual(len(disclaimers), 1)
        self.assertEqual(len(disclaimers[0]["sha256"]), 64)

    def test_current_view_disclaimer_is_the_short_summary_not_the_raw_file(self):
        payload = build_summary(FIXTURE_CASE)

        self.assertEqual(payload["current_view"]["disclaimer"], DISCLAIMER_SUMMARY)
        self.assertNotIn("Limitation of Liability", payload["current_view"]["disclaimer"])

    def test_scenario_probabilities_sum_to_100_in_the_fixture(self):
        payload = build_summary(FIXTURE_CASE)
        total = sum(s["probability"]["value"] for s in payload["scenarios"])
        self.assertEqual(total, 100)


class BuildSummaryRejectionTests(unittest.TestCase):
    def _copy_case(self, tmp):
        target = Path(tmp) / "case"
        shutil.copytree(FIXTURE_CASE, target)
        return target

    def test_rejects_when_a_required_markdown_source_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = self._copy_case(tmp)
            (case_dir / "investment-memo.md").unlink()

            with self.assertRaises(BuildError):
                build_summary(case_dir)

    def test_missing_section_renders_empty_instead_of_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = self._copy_case(tmp)
            text = (case_dir / "active-decisions.md").read_text(encoding="utf-8")
            text = text.replace("## Expected Evidence Timeline", "## Removed Section")
            (case_dir / "active-decisions.md").write_text(text, encoding="utf-8")

            payload = build_summary(case_dir)

            self.assertEqual(payload["evidence_timeline"], [])

    def test_template_style_heading_and_column_variants_still_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = self._copy_case(tmp)
            text = (case_dir / "active-decisions.md").read_text(encoding="utf-8")
            text = text.replace("## Expected Evidence Timeline", "## Evidence Timeline")
            text = text.replace(
                "| Evidence | Expected Timing | What Confirms | What Disconfirms | Source |",
                "| Event | When | Key Watch | What Disconfirms | Source |",
            )
            (case_dir / "active-decisions.md").write_text(text, encoding="utf-8")

            payload = build_summary(case_dir)

            self.assertEqual(len(payload["evidence_timeline"]), 1)
            self.assertEqual(payload["evidence_timeline"][0]["evidence"], "Monthly revenue")
            self.assertEqual(payload["evidence_timeline"][0]["expected_timing"], "Monthly, ~10th")

    def test_transposed_scenario_table_renders_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = self._copy_case(tmp)
            memo = (case_dir / "investment-memo.md").read_text(encoding="utf-8")
            for heading in ("## Bull Case", "## Base Case", "## Bear Case"):
                start = memo.index(heading)
                end = memo.index("## ", start + 3)
                memo = memo[:start] + memo[end:]
            memo += (
                "\n## Scenarios\n\n"
                "| | Bull (30%) | Base (50%) | Bear (20%) |\n"
                "|---|---|---|---|\n"
                "| Assumptions | fast growth | steady | stall |\n"
                "| P/B | 3x | 2x | 1x |\n"
                "| Range | 120-140 | 95-115 | 70-90 |\n"
            )
            (case_dir / "investment-memo.md").write_text(memo, encoding="utf-8")

            payload = build_summary(case_dir)

            names = [s["name"] for s in payload["scenarios"]]
            self.assertEqual(names, ["Bull", "Base", "Bear"])
            self.assertEqual(sum(s["probability"]["value"] for s in payload["scenarios"]), 100)
            self.assertEqual(payload["scenarios"][0]["scenario_derived_range"], "120-140")
            self.assertEqual(payload["scenarios"][1]["multiple_assumption"], "2x")


class WriteSummaryTests(unittest.TestCase):
    def test_check_mode_does_not_write_the_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            shutil.copytree(FIXTURE_CASE, case_dir)
            output_path = case_dir / "research-summary-data.json"

            write_summary(case_dir, check=True)

            self.assertFalse(output_path.exists())

    def test_writes_canonical_json_matching_build_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            shutil.copytree(FIXTURE_CASE, case_dir)

            output_path = write_summary(case_dir)

            self.assertTrue(output_path.exists())
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written, build_summary(case_dir))
            self.assertTrue(output_path.read_text(encoding="utf-8").endswith("\n"))

    def test_restricted_sources_rejected_in_shareable_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            shutil.copytree(FIXTURE_CASE, case_dir)

            with self.assertRaises(BuildError):
                write_summary(case_dir, distribution="shareable")


if __name__ == "__main__":
    unittest.main()
