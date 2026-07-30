import unittest
from inspect import signature


class DataAvailabilityTests(unittest.TestCase):
    def test_complete_current_observation_is_available(self):
        try:
            from scripts.data_availability import build_data_availability
        except ModuleNotFoundError:
            self.fail("scripts.data_availability contract is missing")

        availability = build_data_availability(
            observation_date="2026-07-30",
            source="FinMind",
        )

        self.assertEqual(
            availability,
            {
                "status": "available",
                "observation_date": "2026-07-30",
                "source": "FinMind",
                "missing_inputs": [],
                "failure_reasons": [],
                "confidence_impact": "none",
            },
        )
        self.assertNotIn("fallback_used", availability)
        self.assertNotIn("stale_reused", availability)

    def test_missing_inputs_or_failures_make_current_observation_partial(self):
        from scripts.data_availability import build_data_availability

        availability = build_data_availability(
            observation_date="2026-07-30",
            source="FinMind",
            missing_inputs=["TaiwanStockHoldingSharesPer"],
            failure_reasons=["provider_plan_restriction"],
        )

        self.assertEqual(availability["status"], "partial")
        self.assertEqual(availability["confidence_impact"], "downgrade")
        self.assertEqual(
            availability["missing_inputs"], ["TaiwanStockHoldingSharesPer"]
        )
        self.assertEqual(
            availability["failure_reasons"], ["provider_plan_restriction"]
        )

    def test_missing_current_observation_is_unavailable(self):
        from scripts.data_availability import build_data_availability

        availability = build_data_availability(
            observation_date=None,
            source="TWSE OpenAPI",
            failure_reasons=["no_current_observation"],
        )

        self.assertEqual(availability["status"], "unavailable")
        self.assertEqual(availability["confidence_impact"], "block")

    def test_latest_observation_date_reads_nested_current_periods(self):
        from scripts import data_availability

        self.assertTrue(
            hasattr(data_availability, "latest_observation_date"),
            "latest_observation_date is missing",
        )

        latest = data_availability.latest_observation_date(
            [{"date": "2026-07-28"}],
            {"periods": ["2025Q4", "2026Q1"]},
            [{"revenue_year": 2026, "revenue_month": 6}],
        )

        self.assertEqual(latest, "2026-07-28")

    def test_latest_observation_date_ignores_non_date_values_and_invalid_dates(self):
        from scripts.data_availability import latest_observation_date

        latest = latest_observation_date(
            {
                "stock_id": "2026",
                "value": 2027,
                "rows": [{"date": "2026-99-99"}],
            }
        )

        self.assertIsNone(latest)

    def test_contract_has_one_source_and_no_fallback_provenance_fields(self):
        from scripts.data_availability import build_data_availability

        parameters = signature(build_data_availability).parameters
        self.assertIn("source", parameters)
        self.assertNotIn("primary_source", parameters)
        self.assertNotIn("actual_source", parameters)

    def test_latest_observation_date_normalizes_spaced_quarter_periods(self):
        from scripts.data_availability import latest_observation_date

        self.assertEqual(
            latest_observation_date({"periods": ["2025 Q4", "2026 Q1"]}),
            "2026Q1",
        )


if __name__ == "__main__":
    unittest.main()
