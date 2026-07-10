import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.workflow_state import (
    gate_stage,
    hash_file,
    invalidate_downstream,
    load_contract,
    record_stage,
    status as workflow_status,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "cases"

CONTRACT = {
    "schema_version": 1,
    "terminal_stage": "session-wrap",
    "stage_statuses": ["pending", "running", "pass", "degraded", "blocked", "stale", "failed"],
    "consumable_statuses": ["pass", "degraded"],
    "stages": [
        {"id": "stock-case-init", "depends_on": [], "required_inputs": [], "optional_inputs": [], "outputs": ["research-questions.md"], "question_namespace": "CASE"},
        {"id": "yahoo-profile-financials", "depends_on": ["stock-case-init"], "required_inputs": ["stock-meta.json"], "optional_inputs": [], "outputs": ["yahoo-data.json"], "question_namespace": "PROFILE"},
        {"id": "company-deep-dive", "depends_on": ["yahoo-profile-financials"], "required_inputs": ["yahoo-data.json"], "optional_inputs": ["official-issuer-data.json"], "outputs": ["company-analysis.md"], "question_namespace": "COMPANY"},
        {"id": "financial-analysis", "depends_on": ["company-deep-dive"], "required_inputs": ["company-analysis.md"], "optional_inputs": [], "outputs": ["financial-analysis.md"], "question_namespace": "FIN"},
        {"id": "investment-thesis", "depends_on": ["financial-analysis"], "required_inputs": ["financial-analysis.md"], "optional_inputs": [], "outputs": ["investment-memo.md"], "question_namespace": "THESIS"},
        {"id": "session-wrap", "depends_on": ["investment-thesis"], "required_inputs": ["investment-memo.md"], "optional_inputs": [], "outputs": ["active-decisions.md"], "question_namespace": "WRAP"},
        {"id": "research-html-output", "depends_on": ["session-wrap"], "required_inputs": ["active-decisions.md"], "optional_inputs": [], "outputs": ["research-summary.html"], "question_namespace": "HTML"},
    ],
}


def write(case_dir, filename, content):
    path = Path(case_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_json(case_dir, filename, payload):
    write(case_dir, filename, json.dumps(payload))


class HashFileTests(unittest.TestCase):
    def test_hash_is_deterministic_for_same_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.txt", "hello")
            self.assertEqual(hash_file(path), hash_file(path))

    def test_hash_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.txt", "hello")
            first = hash_file(path)
            write(tmp, "a.txt", "hello world")
            self.assertNotEqual(first, hash_file(path))

    def test_missing_file_hashes_to_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(hash_file(Path(tmp) / "missing.txt"))


class RecordStageTests(unittest.TestCase):
    def _init_case(self, tmp):
        write_json(tmp, "stock-meta.json", {"file_references": {}, "stage_records": {}})
        write(tmp, "research-questions.md", "# Research Questions")

    def test_record_stores_relative_filenames_not_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)
            record = record_stage(tmp, "stock-case-init", CONTRACT)

            for filename in record["output_hashes"]:
                self.assertNotIn(str(tmp), filename)
                self.assertFalse(Path(filename).is_absolute())

    def test_record_status_is_blocked_when_a_required_output_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(tmp, "stock-meta.json", {"file_references": {}, "stage_records": {}})
            # research-questions.md deliberately not written

            record = record_stage(tmp, "stock-case-init", CONTRACT)

            self.assertEqual(record["status"], "blocked")
            self.assertTrue(any("research-questions.md" in issue for issue in record["issues"]))

    def test_record_status_is_blocked_when_a_required_input_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)
            record_stage(tmp, "stock-case-init", CONTRACT)
            # yahoo-profile-financials requires stock-meta.json (present) -> should pass
            record = record_stage(tmp, "yahoo-profile-financials", CONTRACT)
            self.assertEqual(record["status"], "blocked")  # yahoo-data.json output not written yet
            self.assertTrue(any("yahoo-data.json" in issue for issue in record["issues"]))

    def test_record_status_pass_when_all_outputs_and_inputs_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)
            record_stage(tmp, "stock-case-init", CONTRACT)
            write_json(tmp, "yahoo-data.json", {"metadata": {"status": "pass"}})

            record = record_stage(tmp, "yahoo-profile-financials", CONTRACT)

            self.assertEqual(record["status"], "pass")
            self.assertEqual(record["issues"], [])

    def test_record_status_reflects_degraded_embedded_json_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)
            record_stage(tmp, "stock-case-init", CONTRACT)
            write_json(tmp, "yahoo-data.json", {"metadata": {"status": "degraded"}})

            record = record_stage(tmp, "yahoo-profile-financials", CONTRACT)

            self.assertEqual(record["status"], "degraded")

    def test_record_writes_stage_record_into_stock_meta_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)
            record_stage(tmp, "stock-case-init", CONTRACT)

            with open(Path(tmp) / "stock-meta.json", encoding="utf-8") as handle:
                meta = json.load(handle)

            self.assertIn("stock-case-init", meta["stage_records"])
            self.assertEqual(meta["stage_records"]["stock-case-init"]["status"], "pass")


class InvalidateDownstreamTests(unittest.TestCase):
    def _recorded_meta(self):
        return {
            "stage_records": {
                "stock-case-init": {"status": "pass", "output_hashes": {}},
                "yahoo-profile-financials": {"status": "pass", "output_hashes": {"yahoo-data.json": "h1"}},
                "company-deep-dive": {"status": "pass", "output_hashes": {"company-analysis.md": "h2"}},
                "financial-analysis": {"status": "pass", "output_hashes": {"financial-analysis.md": "h3"}},
                "investment-thesis": {"status": "pass", "output_hashes": {"investment-memo.md": "h4"}},
                "session-wrap": {"status": "pass", "output_hashes": {"active-decisions.md": "h5"}},
            }
        }

    def test_marks_every_transitive_consumer_stale(self):
        meta = self._recorded_meta()

        invalidated = invalidate_downstream(meta, "yahoo-profile-financials", CONTRACT)

        self.assertEqual(
            set(invalidated),
            {"company-deep-dive", "financial-analysis", "investment-thesis", "session-wrap"},
        )
        for stage_id in invalidated:
            self.assertEqual(meta["stage_records"][stage_id]["status"], "stale")

    def test_does_not_touch_stages_without_a_record(self):
        meta = self._recorded_meta()
        del meta["stage_records"]["session-wrap"]

        invalidated = invalidate_downstream(meta, "yahoo-profile-financials", CONTRACT)

        self.assertNotIn("session-wrap", invalidated)
        self.assertNotIn("session-wrap", meta["stage_records"])

    def test_record_stage_cascades_invalidation_when_output_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(tmp, "stock-meta.json", {"file_references": {}, "stage_records": {}})
            write(tmp, "research-questions.md", "# Research Questions")
            record_stage(tmp, "stock-case-init", CONTRACT)
            write_json(tmp, "yahoo-data.json", {"metadata": {"status": "pass"}, "version": 1})
            record_stage(tmp, "yahoo-profile-financials", CONTRACT)
            write(tmp, "company-analysis.md", "# Company Analysis")
            record_stage(tmp, "company-deep-dive", CONTRACT)

            # Refresh yahoo-data.json with different content and re-record.
            write_json(tmp, "yahoo-data.json", {"metadata": {"status": "pass"}, "version": 2})
            record_stage(tmp, "yahoo-profile-financials", CONTRACT)

            with open(Path(tmp) / "stock-meta.json", encoding="utf-8") as handle:
                meta = json.load(handle)

            self.assertEqual(meta["stage_records"]["company-deep-dive"]["status"], "stale")


class GateStageTests(unittest.TestCase):
    def test_rejects_when_required_upstream_stage_not_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(tmp, "stock-meta.json", {"file_references": {}, "stage_records": {}})

            result = gate_stage(tmp, "yahoo-profile-financials", CONTRACT, date(2026, 7, 10))

            self.assertFalse(result["ready"])
            self.assertTrue(any("stock-case-init" in reason for reason in result["blocking_reasons"]))

    def test_rejects_when_required_upstream_stage_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(
                tmp,
                "stock-meta.json",
                {"file_references": {}, "stage_records": {"stock-case-init": {"status": "stale"}}},
            )

            result = gate_stage(tmp, "yahoo-profile-financials", CONTRACT, date(2026, 7, 10))

            self.assertFalse(result["ready"])

    def test_rejects_when_required_upstream_stage_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(
                tmp,
                "stock-meta.json",
                {"file_references": {}, "stage_records": {"stock-case-init": {"status": "blocked"}}},
            )

            result = gate_stage(tmp, "yahoo-profile-financials", CONTRACT, date(2026, 7, 10))

            self.assertFalse(result["ready"])

    def test_accepts_when_required_upstream_stage_is_degraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(
                tmp,
                "stock-meta.json",
                {"file_references": {}, "stage_records": {"stock-case-init": {"status": "degraded"}}},
            )

            result = gate_stage(tmp, "yahoo-profile-financials", CONTRACT, date(2026, 7, 10))

            self.assertTrue(result["ready"])

    def test_optional_input_missing_does_not_block_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(
                tmp,
                "stock-meta.json",
                {"file_references": {}, "stage_records": {"yahoo-profile-financials": {"status": "pass"}}},
            )
            write_json(tmp, "yahoo-data.json", {"metadata": {"status": "pass"}})
            # official-issuer-data.json (optional input) deliberately absent

            result = gate_stage(tmp, "company-deep-dive", CONTRACT, date(2026, 7, 10))

            self.assertTrue(result["ready"])

    def test_no_readiness_for_research_html_output_without_session_wrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(tmp, "stock-meta.json", {"file_references": {}, "stage_records": {}})

            result = gate_stage(tmp, "research-html-output", CONTRACT, date(2026, 7, 10))

            self.assertFalse(result["ready"])
            self.assertTrue(any("session-wrap" in reason for reason in result["blocking_reasons"]))

    def test_readiness_for_research_html_output_once_session_wrap_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(
                tmp,
                "stock-meta.json",
                {"file_references": {}, "stage_records": {"session-wrap": {"status": "pass"}}},
            )
            write(tmp, "active-decisions.md", "# Active Decisions")

            result = gate_stage(tmp, "research-html-output", CONTRACT, date(2026, 7, 10))

            self.assertTrue(result["ready"])


class LoadContractTests(unittest.TestCase):
    def test_loads_the_real_repo_contract_by_default(self):
        contract = load_contract()
        self.assertEqual(contract["terminal_stage"], "session-wrap")


class FixtureCaseTests(unittest.TestCase):
    """Exercises the committed golden fixtures against the real repo contract."""

    def test_workflow_valid_fixture_is_complete_through_session_wrap(self):
        contract = load_contract()
        result = workflow_status(FIXTURES_DIR / "workflow-valid", contract)

        self.assertTrue(result["complete"])
        for stage_id, record in result["stage_records"].items():
            self.assertEqual(record["status"], "pass", stage_id)

    def test_workflow_stale_fixture_cascades_invalidation_on_re_record(self):
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "workflow-stale"
            shutil.copytree(FIXTURES_DIR / "workflow-stale", case_dir)

            before = workflow_status(case_dir, contract)
            self.assertTrue(before["complete"])

            record_stage(case_dir, "yahoo-profile-financials", contract)
            after = workflow_status(case_dir, contract)

            self.assertFalse(after["complete"])
            self.assertEqual(after["stage_records"]["session-wrap"]["status"], "stale")
            self.assertEqual(after["stage_records"]["company-deep-dive"]["status"], "stale")
            self.assertEqual(after["stage_records"]["market-data-fetch"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
