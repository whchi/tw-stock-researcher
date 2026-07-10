import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.migrate_case_metadata import analyze_case, main, parse_args

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "migrate-case-metadata"


def _hash_tree(directory):
    digests = {}
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file():
            digests[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


class DryRunImmutabilityTests(unittest.TestCase):
    def _assert_immutable(self, fixture_name):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp_dir:
            case_dir = Path(tmp_dir) / "case"
            shutil.copytree(FIXTURES_DIR / fixture_name, case_dir)
            before = _hash_tree(case_dir)

            analyze_case(case_dir)

            after = _hash_tree(case_dir)
            self.assertEqual(before, after)

    def test_current_template_is_untouched(self):
        self._assert_immutable("current-template")

    def test_old_template_is_untouched(self):
        self._assert_immutable("old-template")

    def test_malformed_is_untouched(self):
        self._assert_immutable("malformed")


class AnalyzeCaseTests(unittest.TestCase):
    def test_current_template_is_clean(self):
        report = analyze_case(FIXTURES_DIR / "current-template")
        self.assertTrue(report["clean"], report["findings"])
        self.assertEqual(report["findings"], [])

    def test_old_template_reports_key_drift(self):
        report = analyze_case(FIXTURES_DIR / "old-template")
        self.assertFalse(report["clean"])

        def find(check, status):
            matches = [f for f in report["findings"] if f["check"] == check and f["status"] == status]
            self.assertEqual(len(matches), 1, f"expected exactly one {check}/{status} finding, got {matches}")
            return matches[0]

        missing_top_level = find("stock_meta_keys", "missing_keys")
        self.assertIn("stage_records", missing_top_level["detail"])
        self.assertIn("workflow_contract_version", missing_top_level["detail"])

        unknown_top_level = find("stock_meta_keys", "unknown_keys")
        self.assertIn("notes", unknown_top_level["detail"])

        self.assertEqual(find("stage_state", "absent")["status"], "absent")

        self.assertEqual(find("file_references_keys", "missing_keys")["status"], "missing_keys")

        mixed_convention = find("file_references_convention", "mixed")
        self.assertEqual(mixed_convention["detail"], ["case_relative", "repo_relative"])

        dangling = find("file_references_dangling", "dangling")
        dangling_keys = {entry["key"] for entry in dangling["detail"]}
        self.assertEqual(dangling_keys, {"yahoo_data", "financial_analysis"})

        self.assertEqual(find("open_questions", "legacy_table_shape")["status"], "legacy_table_shape")
        self.assertEqual(find("research_summary_data", "legacy_v0")["status"], "legacy_v0")

    def test_malformed_case_reports_parse_failures_without_crashing(self):
        report = analyze_case(FIXTURES_DIR / "malformed")
        self.assertFalse(report["clean"])
        checks = {finding["check"]: finding for finding in report["findings"]}

        self.assertEqual(checks["stock_meta_presence"]["status"], "invalid_json")
        self.assertEqual(checks["open_questions"]["status"], "missing")
        self.assertEqual(checks["research_summary_data"]["status"], "invalid_json")


class CliTests(unittest.TestCase):
    def test_dry_run_flag_is_required(self):
        with self.assertRaises(SystemExit):
            parse_args(["--case", str(FIXTURES_DIR / "current-template")])

    def test_all_and_case_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            parse_args(["--all", "--case", str(FIXTURES_DIR / "current-template"), "--dry-run"])

    def test_neither_all_nor_case_is_rejected(self):
        with self.assertRaises(SystemExit):
            parse_args(["--dry-run"])

    def test_main_case_json_reports_clean(self):
        args = ["--case", str(FIXTURES_DIR / "current-template"), "--dry-run", "--json"]

        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(args)

        self.assertEqual(exit_code, 0)
        reports = json.loads(buffer.getvalue())
        self.assertEqual(len(reports), 1)
        self.assertTrue(reports[0]["clean"])

    def test_main_all_scans_every_case_under_companies_dir(self):
        import io
        from contextlib import redirect_stdout

        import scripts.migrate_case_metadata as migrate_module

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp_dir:
            companies_dir = Path(tmp_dir) / "companies"
            companies_dir.mkdir()
            shutil.copytree(FIXTURES_DIR / "current-template", companies_dir / "current-template")
            shutil.copytree(FIXTURES_DIR / "old-template", companies_dir / "old-template")

            original_companies_dir = migrate_module.COMPANIES_DIR
            migrate_module.COMPANIES_DIR = companies_dir
            try:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = main(["--all", "--dry-run", "--json"])
            finally:
                migrate_module.COMPANIES_DIR = original_companies_dir

        self.assertEqual(exit_code, 0)
        reports = json.loads(buffer.getvalue())
        cases = {report["case"]: report for report in reports}
        self.assertTrue(cases["current-template"]["clean"])
        self.assertFalse(cases["old-template"]["clean"])


if __name__ == "__main__":
    unittest.main()
