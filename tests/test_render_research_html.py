import json
import tempfile
import unittest
from pathlib import Path

from scripts.render_research_html import render_html


class RenderResearchHtmlTests(unittest.TestCase):
    def test_render_html_replaces_placeholders_with_payload_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template.html"
            output = root / "output.html"
            template.write_text(
                "<html><title>{{TITLE}}</title><body>{{BODY_HTML}}</body></html>",
                encoding="utf-8",
            )
            payload = {"TITLE": "6741 91APP", "BODY_HTML": "<strong>quality view</strong>"}

            render_html(template, output, payload)

            html = output.read_text(encoding="utf-8")
            self.assertIn("<title>6741 91APP</title>", html)
            self.assertIn("<strong>quality view</strong>", html)
            self.assertNotIn("{{TITLE}}", html)
            self.assertNotIn("{{BODY_HTML}}", html)

    def test_render_html_fails_when_payload_misses_template_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template.html"
            output = root / "output.html"
            template.write_text("{{TITLE}} {{MISSING}}", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "Missing template values: MISSING"):
                render_html(template, output, {"TITLE": "6706 惠特"})

    def test_render_html_cli_accepts_json_payload_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload_path = root / "payload.json"
            payload_path.write_text(
                json.dumps({"TITLE": "6706 惠特", "BODY_HTML": "preview"}),
                encoding="utf-8",
            )
            template = root / "template.html"
            output = root / "output.html"
            template.write_text("{{TITLE}}: {{BODY_HTML}}", encoding="utf-8")

            from scripts.render_research_html import main

            exit_code = main(
                [
                    "--template",
                    str(template),
                    "--data",
                    str(payload_path),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "6706 惠特: preview")

    def test_render_html_cli_writes_output_inside_company_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "companies" / "6741-91app"
            case_dir.mkdir(parents=True)
            payload_path = case_dir / "research-summary-data.json"
            payload_path.write_text(
                json.dumps({"TITLE": "6741 91APP", "BODY_HTML": "case preview"}),
                encoding="utf-8",
            )
            template = root / "template.html"
            output = case_dir / "research-summary.html"
            template.write_text("{{TITLE}}: {{BODY_HTML}}", encoding="utf-8")

            from scripts.render_research_html import main

            exit_code = main(
                [
                    "--template",
                    str(template),
                    "--data",
                    str(payload_path),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertEqual(output.read_text(encoding="utf-8"), "6741 91APP: case preview")


if __name__ == "__main__":
    unittest.main()
