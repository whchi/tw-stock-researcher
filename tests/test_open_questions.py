import tempfile
import unittest
from pathlib import Path

from scripts.open_questions import _load_contract, resolve_question, upsert_question, validate_ledger

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "open-questions"

CONTRACT = {
    "consumable_statuses": ["pass", "degraded"],
    "stages": [
        {"id": "stock-case-init", "depends_on": [], "question_namespace": "CASE"},
        {"id": "financial-data-fetch", "depends_on": ["stock-case-init"], "question_namespace": "FIN-DATA"},
        {"id": "financial-analysis", "depends_on": ["financial-data-fetch"], "question_namespace": "FIN"},
        {"id": "session-wrap", "depends_on": ["financial-analysis"], "question_namespace": "WRAP"},
    ],
}

ACTIVE_HEADER = "| ID | Origin Stage | Priority | Status | Blocking Stage | Question | Why It Matters | Resolve When | Evidence Refs | Next Check | Last Checked |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
RESOLVED_HEADER = "| ID | Resolution | Evidence Refs | Evidence As Of | Resolved By Stage | Closed On | Reopen Trigger |\n| --- | --- | --- | --- | --- | --- | --- |\n"


def base_doc(active_rows="", resolved_rows=""):
    return (
        "# Open Questions\n\n"
        "## Critical Unresolved Question\n\n"
        "Critical ID: _(none yet)_\n\n"
        "## Active Questions\n\n"
        f"{ACTIVE_HEADER}{active_rows}\n"
        "## Resolved Questions\n\n"
        f"{RESOLVED_HEADER}{resolved_rows}"
    )


class ValidateLedgerTests(unittest.TestCase):
    def test_valid_document_has_no_issues(self):
        active = "| FIN-DATA-VALUATION | financial-data-fetch | high | open |  | Is the band complete? | matters | ready | | fetch.py | 2026-07-09 |\n"
        text = base_doc(active_rows=active)

        issues = validate_ledger(text, CONTRACT)

        self.assertEqual(issues, [])

    def test_rejects_duplicate_ids(self):
        active = (
            "| FIN-DATA-VALUATION | financial-data-fetch | high | open |  | Q1 | why | ready | | fetch.py | 2026-07-09 |\n"
            "| FIN-DATA-VALUATION | financial-data-fetch | high | open |  | Q2 | why | ready | | fetch.py | 2026-07-09 |\n"
        )
        issues = validate_ledger(base_doc(active_rows=active), CONTRACT)
        self.assertTrue(any("duplicate id" in issue for issue in issues))

    def test_rejects_unknown_namespace(self):
        active = "| ZZZ-1 | financial-data-fetch | high | open |  | Q | why | ready | | fetch.py | 2026-07-09 |\n"
        issues = validate_ledger(base_doc(active_rows=active), CONTRACT)
        self.assertTrue(any("namespace" in issue for issue in issues))

    def test_rejects_unknown_status(self):
        active = "| FIN-DATA-VALUATION | financial-data-fetch | high | not-a-status |  | Q | why | ready | | fetch.py | 2026-07-09 |\n"
        issues = validate_ledger(base_doc(active_rows=active), CONTRACT)
        self.assertTrue(any("status" in issue for issue in issues))

    def test_rejects_missing_resolution_evidence(self):
        resolved = "| FIN-DATA-VALUATION | done |  | 2026-07-09 | financial-data-fetch | 2026-07-09 | trigger |\n"
        issues = validate_ledger(base_doc(resolved_rows=resolved), CONTRACT)
        self.assertTrue(any("evidence" in issue.lower() for issue in issues))

    def test_rejects_missing_source_as_of(self):
        resolved = "| FIN-DATA-VALUATION | done | ref |  | financial-data-fetch | 2026-07-09 | trigger |\n"
        issues = validate_ledger(base_doc(resolved_rows=resolved), CONTRACT)
        self.assertTrue(any("as-of" in issue.lower() or "as of" in issue.lower() for issue in issues))

    def test_rejects_missing_reopen_trigger(self):
        resolved = "| FIN-DATA-VALUATION | done | ref | 2026-07-09 | financial-data-fetch | 2026-07-09 |  |\n"
        issues = validate_ledger(base_doc(resolved_rows=resolved), CONTRACT)
        self.assertTrue(any("reopen" in issue.lower() for issue in issues))

    def test_rejects_session_wrap_as_resolver(self):
        resolved = "| WRAP-1 | done | ref | 2026-07-09 | session-wrap | 2026-07-09 | trigger |\n"
        issues = validate_ledger(base_doc(resolved_rows=resolved), CONTRACT)
        self.assertTrue(any("session-wrap" in issue for issue in issues))

    def test_rejects_unknown_origin_stage(self):
        active = "| FIN-DATA-VALUATION | not-a-real-stage | high | open |  | Q | why | ready | | fetch.py | 2026-07-09 |\n"
        issues = validate_ledger(base_doc(active_rows=active), CONTRACT)
        self.assertTrue(any("origin stage" in issue.lower() for issue in issues))


class UpsertQuestionTests(unittest.TestCase):
    def _init_case(self, tmp):
        (Path(tmp) / "open-questions.md").write_text(base_doc(), encoding="utf-8")

    def test_creates_a_new_question_in_the_active_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)

            upsert_question(
                tmp,
                contract=CONTRACT,
                question_id="FIN-DATA-VALUATION",
                stage="financial-data-fetch",
                priority="high",
                question="Is the valuation band complete?",
                why_it_matters="Needed for pricing thesis",
                resolve_when="valuation_band.status == ready",
                next_check="fetch_fundamentals.py",
                as_of="2026-07-09",
            )

            text = (Path(tmp) / "open-questions.md").read_text(encoding="utf-8")
            self.assertIn("FIN-DATA-VALUATION", text)
            self.assertIn("Is the valuation band complete?", text)

    def test_rejects_stage_outside_its_own_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)

            with self.assertRaises(ValueError):
                upsert_question(
                    tmp,
                    contract=CONTRACT,
                    question_id="FIN-DATA-VALUATION",
                    stage="financial-analysis",
                    priority="high",
                    question="Q",
                    why_it_matters="why",
                    resolve_when="ready",
                    next_check="check",
                    as_of="2026-07-09",
                )

    def test_rejects_changing_origin_stage_of_an_existing_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)
            upsert_question(
                tmp, contract=CONTRACT, question_id="FIN-DATA-VALUATION", stage="financial-data-fetch",
                priority="high", question="Q", why_it_matters="why", resolve_when="ready",
                next_check="check", as_of="2026-07-09",
            )

            with self.assertRaises(ValueError):
                upsert_question(
                    tmp, contract=CONTRACT, question_id="FIN-DATA-VALUATION", stage="stock-case-init",
                    priority="high", question="Q2", why_it_matters="why", resolve_when="ready",
                    next_check="check", as_of="2026-07-10",
                )

    def test_upsert_updates_existing_question_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_case(tmp)
            upsert_question(
                tmp, contract=CONTRACT, question_id="FIN-DATA-VALUATION", stage="financial-data-fetch",
                priority="high", question="Q1", why_it_matters="why", resolve_when="ready",
                next_check="check", as_of="2026-07-09",
            )
            upsert_question(
                tmp, contract=CONTRACT, question_id="FIN-DATA-VALUATION", stage="financial-data-fetch",
                priority="medium", question="Q1 updated", why_it_matters="why", resolve_when="ready",
                next_check="check2", as_of="2026-07-10",
            )

            text = (Path(tmp) / "open-questions.md").read_text(encoding="utf-8")
            self.assertIn("Q1 updated", text)
            self.assertNotIn("| Q1 |", text)


class ResolveQuestionTests(unittest.TestCase):
    def _case_with_open_question(self, tmp):
        (Path(tmp) / "open-questions.md").write_text(base_doc(), encoding="utf-8")
        upsert_question(
            tmp, contract=CONTRACT, question_id="FIN-DATA-VALUATION", stage="financial-data-fetch",
            priority="high", question="Is the band complete?", why_it_matters="why",
            resolve_when="ready", next_check="check", as_of="2026-07-09",
        )

    def test_moves_question_from_active_to_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._case_with_open_question(tmp)

            resolve_question(
                tmp,
                contract=CONTRACT,
                question_id="FIN-DATA-VALUATION",
                stage="financial-data-fetch",
                evidence="fundamentals-data.json#/derived/valuation_band",
                as_of="2026-07-09",
                resolution="Official valuation-band inputs are present.",
                reopen_trigger="source period or filing id changes",
            )

            text = (Path(tmp) / "open-questions.md").read_text(encoding="utf-8")
            issues = validate_ledger(text, CONTRACT)
            self.assertEqual(issues, [])
            headers, active_rows = _active_rows(text)
            self.assertEqual(active_rows, [])
            _, resolved_rows = _resolved_rows(text)
            self.assertEqual(len(resolved_rows), 1)
            self.assertEqual(resolved_rows[0]["ID"], "FIN-DATA-VALUATION")

    def test_rejects_resolving_unknown_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "open-questions.md").write_text(base_doc(), encoding="utf-8")

            with self.assertRaises(ValueError):
                resolve_question(
                    tmp, contract=CONTRACT, question_id="FIN-DATA-NOPE", stage="financial-data-fetch",
                    evidence="ref", as_of="2026-07-09", resolution="r", reopen_trigger="trigger",
                )

    def test_rejects_stage_outside_its_own_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._case_with_open_question(tmp)

            with self.assertRaises(ValueError):
                resolve_question(
                    tmp, contract=CONTRACT, question_id="FIN-DATA-VALUATION", stage="financial-analysis",
                    evidence="ref", as_of="2026-07-09", resolution="r", reopen_trigger="trigger",
                )

    def test_rejects_session_wrap_as_resolver(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "open-questions.md").write_text(base_doc(), encoding="utf-8")
            upsert_question(
                tmp, contract=CONTRACT, question_id="WRAP-1", stage="session-wrap",
                priority="low", question="Q", why_it_matters="why", resolve_when="ready",
                next_check="check", as_of="2026-07-09",
            )

            with self.assertRaises(ValueError):
                resolve_question(
                    tmp, contract=CONTRACT, question_id="WRAP-1", stage="session-wrap",
                    evidence="ref", as_of="2026-07-09", resolution="r", reopen_trigger="trigger",
                )


def _active_rows(text):
    from scripts.markdown_contract import extract_table_under_heading
    return extract_table_under_heading(text, "Active Questions")


def _resolved_rows(text):
    from scripts.markdown_contract import extract_table_under_heading
    return extract_table_under_heading(text, "Resolved Questions")


class FixtureValidationTests(unittest.TestCase):
    """Exercises the committed fixtures against the real repo contract."""

    def test_valid_fixture_has_no_issues(self):
        contract = _load_contract()
        text = (FIXTURES_DIR / "valid.md").read_text(encoding="utf-8")

        self.assertEqual(validate_ledger(text, contract), [])

    def test_invalid_closure_fixture_reports_all_missing_closure_fields(self):
        contract = _load_contract()
        text = (FIXTURES_DIR / "invalid-closure.md").read_text(encoding="utf-8")

        issues = validate_ledger(text, contract)

        self.assertTrue(any("evidence" in issue.lower() for issue in issues))
        self.assertTrue(any("reopen" in issue.lower() for issue in issues))
        self.assertTrue(any("session-wrap" in issue for issue in issues))


class DeterministicResolverTests(unittest.TestCase):
    def test_three_statement_coverage_ready_when_nothing_missing(self):
        from scripts.open_questions import resolve_three_statement_coverage

        result = resolve_three_statement_coverage({"three_statement_coverage": {"required_missing": []}})
        self.assertTrue(result["ready"])

    def test_three_statement_coverage_not_ready_when_fields_missing(self):
        from scripts.open_questions import resolve_three_statement_coverage

        result = resolve_three_statement_coverage(
            {"three_statement_coverage": {"required_missing": ["現金及約當現金"]}}
        )
        self.assertFalse(result["ready"])
        self.assertIn("現金及約當現金", result["reason"])

    def test_monthly_revenue_period_ready_with_enough_rows(self):
        from scripts.open_questions import resolve_monthly_revenue_period

        data = {"derived": {"monthly_revenue_6m": [{"period": "2026-05"}, {"period": "2026-06"}]}}
        result = resolve_monthly_revenue_period(data, min_rows=1)
        self.assertTrue(result["ready"])
        self.assertIn("2026-06", result["reason"])

    def test_monthly_revenue_period_not_ready_when_empty(self):
        from scripts.open_questions import resolve_monthly_revenue_period

        result = resolve_monthly_revenue_period({"derived": {"monthly_revenue_6m": []}}, min_rows=1)
        self.assertFalse(result["ready"])

    def test_valuation_band_ready_when_status_ready(self):
        from scripts.open_questions import resolve_valuation_band_readiness

        result = resolve_valuation_band_readiness({"derived": {"valuation_band": {"status": "ready"}}})
        self.assertTrue(result["ready"])

    def test_valuation_band_not_ready_when_no_data(self):
        from scripts.open_questions import resolve_valuation_band_readiness

        result = resolve_valuation_band_readiness({"derived": {"valuation_band": {"status": "no_data"}}})
        self.assertFalse(result["ready"])

    def test_market_price_5d_window_ready_with_five_rows(self):
        from scripts.open_questions import resolve_market_price_5d_window

        result = resolve_market_price_5d_window({"raw": {"price": [{}] * 5}})
        self.assertTrue(result["ready"])

    def test_market_price_5d_window_not_ready_with_four_rows(self):
        from scripts.open_questions import resolve_market_price_5d_window

        result = resolve_market_price_5d_window({"raw": {"price": [{}] * 4}})
        self.assertFalse(result["ready"])

    def test_market_history_6m_window_requires_120_rows(self):
        from scripts.open_questions import resolve_market_history_6m_window

        self.assertFalse(resolve_market_history_6m_window({"raw": {"price": [{}] * 119}})["ready"])
        self.assertTrue(resolve_market_history_6m_window({"raw": {"price": [{}] * 120}})["ready"])

    def test_tdcc_history_length_ready_with_one_snapshot(self):
        from scripts.open_questions import resolve_tdcc_history_length

        result = resolve_tdcc_history_length({"history": [{"date": "2026-07-04"}]})
        self.assertTrue(result["ready"])

    def test_tdcc_history_length_not_ready_when_empty(self):
        from scripts.open_questions import resolve_tdcc_history_length

        result = resolve_tdcc_history_length({"history": []})
        self.assertFalse(result["ready"])

    def test_macro_variable_readiness_ready_when_latest_populated(self):
        from scripts.open_questions import resolve_macro_variable_readiness

        data = {"sources": {"TWSE Open API": [{"indicator": "TAIEX", "latest": {"date": "2026-07-09"}}]}}
        result = resolve_macro_variable_readiness(data, "TWSE Open API")
        self.assertTrue(result["ready"])

    def test_macro_variable_readiness_not_ready_when_empty(self):
        from scripts.open_questions import resolve_macro_variable_readiness

        data = {"sources": {"TWSE Open API": []}}
        result = resolve_macro_variable_readiness(data, "TWSE Open API")
        self.assertFalse(result["ready"])


if __name__ == "__main__":
    unittest.main()
