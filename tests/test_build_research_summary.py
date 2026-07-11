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

    def test_rejects_malformed_table_shape_in_source_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = self._copy_case(tmp)
            text = (case_dir / "active-decisions.md").read_text(encoding="utf-8")
            text = text.replace(
                "| Number / Signal | Current Read | Why It Matters | Next Check |",
                "| Number / Signal | Current Read | Why It Matters |",
            )
            (case_dir / "active-decisions.md").write_text(text, encoding="utf-8")

            with self.assertRaises(Exception):
                build_summary(case_dir)


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
