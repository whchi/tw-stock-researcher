import tempfile
import unittest
from pathlib import Path

from scripts.case_paths import (
    CaseResolutionError,
    case_output_path,
    resolve_case_dir,
    validate_explicit_output,
)


class ResolveCaseDirTests(unittest.TestCase):
    def test_resolves_the_single_matching_case_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)

            result = resolve_case_dir("2330", repo_root)

            self.assertEqual(result, (repo_root / "companies" / "2330-tsmc").resolve())

    def test_raises_when_zero_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()

            with self.assertRaises(CaseResolutionError) as ctx:
                resolve_case_dir("2330", repo_root)

            self.assertIn("found 0", str(ctx.exception))
            self.assertIn("none", str(ctx.exception))

    def test_raises_when_two_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)
            (repo_root / "companies" / "2330-legacy-slug").mkdir(parents=True)

            with self.assertRaises(CaseResolutionError) as ctx:
                resolve_case_dir("2330", repo_root)

            self.assertIn("found 2", str(ctx.exception))

    def test_ignores_non_directory_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()
            (repo_root / "companies" / "2330-stray-file").write_text("not a case dir")

            with self.assertRaises(CaseResolutionError):
                resolve_case_dir("2330", repo_root)

    def test_rejects_non_numeric_stock_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()

            with self.assertRaises(CaseResolutionError):
                resolve_case_dir("../etc", repo_root)


class CaseOutputPathTests(unittest.TestCase):
    def test_joins_filename_onto_resolved_case_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)

            result = case_output_path("2330", "yahoo-data.json", repo_root)

            self.assertEqual(
                result,
                (repo_root / "companies" / "2330-tsmc" / "yahoo-data.json").resolve(),
            )

    def test_rejects_filename_containing_a_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)

            with self.assertRaises(CaseResolutionError):
                case_output_path("2330", "../escape.json", repo_root)

    def test_propagates_ambiguous_case_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()

            with self.assertRaises(CaseResolutionError):
                case_output_path("2330", "yahoo-data.json", repo_root)


class ValidateExplicitOutputTests(unittest.TestCase):
    def test_allows_output_inside_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            target = repo_root / "companies" / "2330-tsmc" / "yahoo-data.json"

            result = validate_explicit_output(target, repo_root)

            self.assertEqual(result, target.resolve())

    def test_allows_output_at_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            target = repo_root

            result = validate_explicit_output(target, repo_root)

            self.assertEqual(result, repo_root.resolve())

    def test_rejects_output_escaping_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            escaped = Path(tmp) / "outside.json"

            with self.assertRaises(CaseResolutionError):
                validate_explicit_output(escaped, repo_root)


if __name__ == "__main__":
    unittest.main()
