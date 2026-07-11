import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_research_summary import audit_case


class AuditCaseTests(unittest.TestCase):
    def test_payload_without_current_schema_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp)
            (case_dir / "research-summary-data.json").write_text(json.dumps({}), encoding="utf-8")

            report = audit_case(case_dir)

            self.assertEqual(report["status"], "invalid_payload")

    def test_non_current_version_is_invalid_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp)
            payload = {"schema_version": 0, "template_version": 0}
            (case_dir / "research-summary-data.json").write_text(json.dumps(payload), encoding="utf-8")

            report = audit_case(case_dir)

            self.assertEqual(report["status"], "invalid_payload")


if __name__ == "__main__":
    unittest.main()
