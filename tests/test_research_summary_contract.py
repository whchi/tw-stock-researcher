import json
import unittest

from scripts.research_summary_contract import canonical_json, validate_summary

SCHEMA_VERSION = 1
TEMPLATE_VERSION = 1


def valid_payload(**overrides):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "template_version": TEMPLATE_VERSION,
        "case_id": "fixture-listed",
        "locale": "zh-Hant-TW",
        "timezone": "Asia/Taipei",
        "as_of": "2026-07-09",
        "distribution": "local",
        "identity": {"ticker": "9999", "company_name": "Fixture Co", "market": "TWSE", "currency": "TWD"},
        "current_view": {
            "headline": "Headline text",
            "summary": "Summary text",
            "stance": "Base Case Constructive",
            "disclaimer": "研究參考用途",
        },
        "kpis": [
            {
                "label": "Revenue YoY",
                "fact": {"value": "12.3%", "unit": "", "period": "2026-06", "state": "ready", "source_ref": "fundamentals-data.json"},
                "read": "accelerating",
            }
        ],
        "expectation_gaps": [
            {"market_belief": "belief", "evidence_status": "confirmed", "gap": "none", "verification_source": "financial-analysis.md"}
        ],
        "pricing_stage": {
            "label": "Stage 1",
            "read": "narrative expansion",
            "rows": [
                {"stage": "Stage 1 (narrative expansion)", "status": "current", "evidence": "e", "transition_trigger": "t"},
            ],
        },
        "egg_theory": [
            {"window": "6m", "stage": "B3", "signal": "supply_demand_favorable", "confidence": "high", "read": "read"}
        ],
        "evidence_timeline": [
            {"evidence": "monthly revenue", "expected_timing": "monthly", "what_confirms": "beat", "what_disconfirms": "miss", "source": "fundamentals-data.json"}
        ],
        "kill_criteria": [
            {"kill_condition": "condition", "evidence_needed": "evidence", "source": "source", "tracking_impact": "impact"}
        ],
        "scenarios": [
            {
                "name": "Bull",
                "probability": {"value": 30, "unit": "%", "period": "", "state": "ready", "source_ref": "investment-memo.md"},
                "eps_driver_assumption": "a",
                "multiple_assumption": "m",
                "scenario_derived_range": "r",
                "validation_trigger": "v",
                "break_condition": "b",
            },
            {
                "name": "Base",
                "probability": {"value": 50, "unit": "%", "period": "", "state": "ready", "source_ref": "investment-memo.md"},
                "eps_driver_assumption": "a",
                "multiple_assumption": "m",
                "scenario_derived_range": "r",
                "validation_trigger": "v",
                "break_condition": "b",
            },
            {
                "name": "Bear",
                "probability": {"value": 20, "unit": "%", "period": "", "state": "ready", "source_ref": "investment-memo.md"},
                "eps_driver_assumption": "a",
                "multiple_assumption": "m",
                "scenario_derived_range": "r",
                "validation_trigger": "v",
                "break_condition": "b",
            },
        ],
        "watch_items": [{"trigger": "monthly revenue release", "why_it_matters": "validates thesis"}],
        "open_questions": [{"id": "FIN-DATA-VALUATION", "priority": "high", "question": "q", "status": "open"}],
        "sources": [{"name": "FinMind", "tier": "secondary_aggregator", "url": "https://finmind.github.io", "restricted": False}],
        "source_manifest": [{"path": "active-decisions.md", "sha256": "a" * 64}],
    }
    payload.update(overrides)
    return payload


class ValidateSummaryTests(unittest.TestCase):
    def test_valid_payload_has_no_issues(self):
        self.assertEqual(validate_summary(valid_payload()), [])

    def test_rejects_unknown_top_level_field(self):
        payload = valid_payload()
        payload["unexpected_field"] = "x"
        issues = validate_summary(payload)
        self.assertTrue(any("unexpected_field" in issue.message for issue in issues))

    def test_rejects_missing_required_field(self):
        payload = valid_payload()
        del payload["identity"]
        issues = validate_summary(payload)
        self.assertTrue(any("identity" in issue.message for issue in issues))

    def test_rejects_none_in_scalar_position(self):
        payload = valid_payload()
        payload["current_view"]["headline"] = None
        issues = validate_summary(payload)
        self.assertTrue(any("headline" in issue.path for issue in issues))

    def test_rejects_dict_in_scalar_position(self):
        payload = valid_payload()
        payload["current_view"]["stance"] = {"nested": "dict"}
        issues = validate_summary(payload)
        self.assertTrue(any("stance" in issue.path for issue in issues))

    def test_rejects_duplicate_open_question_ids(self):
        payload = valid_payload()
        payload["open_questions"] = [
            {"id": "FIN-DATA-X", "priority": "high", "question": "q1", "status": "open"},
            {"id": "FIN-DATA-X", "priority": "low", "question": "q2", "status": "open"},
        ]
        issues = validate_summary(payload)
        self.assertTrue(any("duplicate" in issue.message.lower() for issue in issues))

    def test_rejects_invalid_distribution_enum(self):
        payload = valid_payload(distribution="public")
        issues = validate_summary(payload)
        self.assertTrue(any("distribution" in issue.path for issue in issues))

    def test_rejects_invalid_fact_state_enum(self):
        payload = valid_payload()
        payload["kpis"][0]["fact"]["state"] = "maybe"
        issues = validate_summary(payload)
        self.assertTrue(any("state" in issue.path for issue in issues))

    def test_rejects_unavailable_fact_without_reason(self):
        payload = valid_payload()
        payload["kpis"][0]["fact"] = {"state": "unavailable"}
        issues = validate_summary(payload)
        self.assertTrue(any("reason" in issue.message.lower() for issue in issues))

    def test_accepts_unavailable_fact_with_reason(self):
        payload = valid_payload()
        payload["kpis"][0]["fact"] = {"state": "unavailable", "reason": "required source field absent"}
        self.assertEqual(validate_summary(payload), [])

    def test_rejects_scenario_probabilities_not_summing_to_100(self):
        payload = valid_payload()
        payload["scenarios"][0]["probability"]["value"] = 10
        issues = validate_summary(payload)
        self.assertTrue(any("100" in issue.message for issue in issues))

    def test_allows_scenario_probability_sum_check_to_be_skipped_when_a_probability_is_unavailable(self):
        payload = valid_payload()
        payload["scenarios"][0]["probability"] = {"state": "unavailable", "reason": "not modeled"}
        self.assertEqual(validate_summary(payload), [])

    def test_rejects_restricted_source_in_shareable_distribution(self):
        payload = valid_payload(distribution="shareable")
        payload["sources"][0]["restricted"] = True
        issues = validate_summary(payload)
        self.assertTrue(any("restricted" in issue.message.lower() for issue in issues))

    def test_allows_restricted_source_in_local_distribution(self):
        payload = valid_payload(distribution="local")
        payload["sources"][0]["restricted"] = True
        self.assertEqual(validate_summary(payload), [])

    def test_rejects_wrong_schema_version(self):
        payload = valid_payload(schema_version=2)
        issues = validate_summary(payload)
        self.assertTrue(any("schema_version" in issue.path for issue in issues))


class CanonicalJsonTests(unittest.TestCase):
    def test_sorts_keys_and_ends_with_trailing_newline(self):
        text = canonical_json({"b": 1, "a": 2})
        self.assertTrue(text.endswith("\n"))
        self.assertLess(text.index('"a"'), text.index('"b"'))

    def test_two_calls_on_equal_payloads_are_byte_identical(self):
        payload = valid_payload()
        self.assertEqual(canonical_json(payload), canonical_json(json.loads(json.dumps(payload))))

    def test_uses_two_space_indent(self):
        text = canonical_json({"a": {"b": 1}})
        self.assertIn('  "a"', text)

    def test_preserves_non_ascii_characters(self):
        text = canonical_json({"a": "研究參考"})
        self.assertIn("研究參考", text)


if __name__ == "__main__":
    unittest.main()
