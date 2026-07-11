import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.render_research_html import RenderError, main, render_summary

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = REPO_ROOT / "templates" / "research-html-summary.html"
FIXTURE_CASE = REPO_ROOT / "tests" / "fixtures" / "research-summary-v1" / "case"
EXPECTED_DATA = REPO_ROOT / "tests" / "fixtures" / "research-summary-v1" / "expected-data.json"
EXPECTED_HTML = REPO_ROOT / "tests" / "fixtures" / "research-summary-v1" / "expected.html"


def load_expected_payload():
    return json.loads(EXPECTED_DATA.read_text(encoding="utf-8"))


class RenderSummaryGoldenTests(unittest.TestCase):
    def test_matches_the_golden_expected_html(self):
        payload = load_expected_payload()
        template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")

        html = render_summary(payload, template)

        self.assertEqual(html, EXPECTED_HTML.read_text(encoding="utf-8"))

    def test_two_renders_of_the_same_payload_are_byte_identical(self):
        payload = load_expected_payload()
        template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")

        first = render_summary(payload, template)
        second = render_summary(payload, template)

        self.assertEqual(first, second)

    def test_no_placeholder_tokens_remain(self):
        payload = load_expected_payload()
        template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")

        html = render_summary(payload, template)

        self.assertNotIn("{{", html)
        self.assertNotIn("}}", html)


class RenderSummarySecurityTests(unittest.TestCase):
    def test_escapes_script_tags_in_headline(self):
        payload = load_expected_payload()
        payload["current_view"]["headline"] = "<script>alert(1)</script>"

        html = render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_escapes_closing_title_tag(self):
        payload = load_expected_payload()
        payload["identity"]["company_name"] = "</title><script>x</script>"

        html = render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

        self.assertNotIn("</title><script>", html)

    def test_escapes_ampersand_and_quotes(self):
        payload = load_expected_payload()
        payload["current_view"]["stance"] = 'A & B "quoted"'

        html = render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn("&amp;", html)
        self.assertIn("&quot;", html)

    def test_preserves_literal_double_brace_text_in_payload_values(self):
        payload = load_expected_payload()
        payload["current_view"]["summary"] = "Contains a literal {{TOKEN}} in the text"

        html = render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn("{{TOKEN}}", html)

    def test_source_manifest_hash_is_truncated_with_full_hash_in_title(self):
        payload = load_expected_payload()
        full_hash = "a" * 64
        payload["source_manifest"] = [{"root": "repo", "path": "DISCLAIMER.md", "sha256": full_hash}]

        html = render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn(f'title="{full_hash}"', html)
        self.assertNotIn(f">{full_hash}<", html)
        self.assertIn(f">{full_hash[:12]}…<", html)

    def test_disclaimer_banner_links_to_disclaimer_file(self):
        payload = load_expected_payload()

        html = render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn('href="../../DISCLAIMER.md"', html)

    def test_rejects_non_http_source_url(self):
        payload = load_expected_payload()
        payload["sources"] = payload["sources"] + [
            {"name": "evil", "tier": "unknown", "url": "javascript:alert(1)", "restricted": False}
        ]

        with self.assertRaises(RenderError):
            render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))


class RenderSummaryValidationTests(unittest.TestCase):
    def test_rejects_invalid_payload_before_rendering(self):
        payload = load_expected_payload()
        payload["unexpected_field"] = "x"

        with self.assertRaises(RenderError):
            render_summary(payload, DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

    def test_rejects_template_placeholder_with_no_payload_mapping(self):
        payload = load_expected_payload()
        template = "{{TITLE}} {{SOME_UNKNOWN_PLACEHOLDER}}"

        with self.assertRaises(RenderError):
            render_summary(payload, template)


class MainCliTests(unittest.TestCase):
    def _prepare_case(self, tmp):
        case_dir = Path(tmp) / "case"
        shutil.copytree(FIXTURE_CASE, case_dir)
        (case_dir / "research-summary-data.json").write_text(
            json.dumps(load_expected_payload()), encoding="utf-8"
        )
        return case_dir

    def test_check_mode_does_not_write_output(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            case_dir = self._prepare_case(tmp)
            output_path = case_dir / "research-summary.html"

            exit_code = main(["--case", str(case_dir), "--check"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(output_path.exists())

    def test_writes_html_into_the_case_folder(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            case_dir = self._prepare_case(tmp)
            output_path = case_dir / "research-summary.html"

            exit_code = main(["--case", str(case_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())

    def test_rejects_case_dir_escaping_the_repository(self):
        exit_code = main(["--case", "/etc"])
        self.assertEqual(exit_code, 1)

    def test_fails_closed_when_payload_file_missing(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            case_dir = Path(tmp) / "case"
            shutil.copytree(FIXTURE_CASE, case_dir)

            exit_code = main(["--case", str(case_dir)])

            self.assertEqual(exit_code, 1)

    def test_atomic_write_failure_leaves_previous_output_unchanged(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            case_dir = self._prepare_case(tmp)
            main(["--case", str(case_dir)])
            output_path = case_dir / "research-summary.html"
            original = output_path.read_text(encoding="utf-8")

            bad_payload = load_expected_payload()
            bad_payload["unexpected_field"] = "x"
            (case_dir / "research-summary-data.json").write_text(json.dumps(bad_payload), encoding="utf-8")

            exit_code = main(["--case", str(case_dir)])

            self.assertEqual(exit_code, 1)
            self.assertEqual(output_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
