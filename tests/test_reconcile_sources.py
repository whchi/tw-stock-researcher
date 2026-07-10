import json
import unittest
from decimal import Decimal
from pathlib import Path

from scripts.reconcile_sources import (
    CLASSIFICATION_CONSOLIDATION_MISMATCH,
    CLASSIFICATION_MATCH,
    CLASSIFICATION_PERIOD_MISMATCH,
    CLASSIFICATION_RESTATEMENT,
    CLASSIFICATION_ROUNDING,
    CLASSIFICATION_TRUE_CONFLICT,
    CLASSIFICATION_UNIT_MISMATCH,
    reconcile_metric,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "official-sources" / "finmind-secondary.json"


def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class ReconcileMetricTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture()
        self.canonical = self.fixture["canonical_official"]

    def test_identical_values_match(self):
        result = reconcile_metric(self.canonical, self.fixture["candidate_matching"], Decimal("0.001"))
        self.assertEqual(result["classification"], CLASSIFICATION_MATCH)
        self.assertTrue(result["comparable"])

    def test_small_difference_within_tolerance_is_rounding(self):
        result = reconcile_metric(self.canonical, self.fixture["candidate_rounding"], Decimal("0.001"))
        self.assertEqual(result["classification"], CLASSIFICATION_ROUNDING)
        self.assertTrue(result["comparable"])

    def test_large_difference_beyond_tolerance_is_true_conflict(self):
        result = reconcile_metric(self.canonical, self.fixture["candidate_true_conflict"], Decimal("0.001"))
        self.assertEqual(result["classification"], CLASSIFICATION_TRUE_CONFLICT)
        self.assertTrue(result["comparable"])

    def test_period_mismatch_is_not_comparable(self):
        result = reconcile_metric(self.canonical, self.fixture["candidate_period_mismatch"], Decimal("0.001"))
        self.assertEqual(result["classification"], CLASSIFICATION_PERIOD_MISMATCH)
        self.assertFalse(result["comparable"])

    def test_consolidation_mismatch_is_not_comparable(self):
        result = reconcile_metric(self.canonical, self.fixture["candidate_consolidation_mismatch"], Decimal("0.001"))
        self.assertEqual(result["classification"], CLASSIFICATION_CONSOLIDATION_MISMATCH)
        self.assertFalse(result["comparable"])

    def test_restatement_is_not_comparable(self):
        result = reconcile_metric(self.canonical, self.fixture["candidate_restatement"], Decimal("0.001"))
        self.assertEqual(result["classification"], CLASSIFICATION_RESTATEMENT)
        self.assertFalse(result["comparable"])

    def test_unit_mismatch_is_not_comparable(self):
        candidate = dict(self.fixture["candidate_matching"])
        candidate["unit"] = "TWD_million"
        result = reconcile_metric(self.canonical, candidate, Decimal("0.001"))
        self.assertEqual(result["classification"], CLASSIFICATION_UNIT_MISMATCH)
        self.assertFalse(result["comparable"])

    def test_never_averages_a_true_conflict(self):
        result = reconcile_metric(self.canonical, self.fixture["candidate_true_conflict"], Decimal("0.001"))
        self.assertNotIn("averaged_value", result)
        self.assertNotIn("value", result)

    def test_result_never_mutates_input_dicts(self):
        canonical_copy = dict(self.canonical)
        candidate_copy = dict(self.fixture["candidate_rounding"])
        reconcile_metric(self.canonical, self.fixture["candidate_rounding"], Decimal("0.001"))
        self.assertEqual(self.canonical, canonical_copy)
        self.assertEqual(self.fixture["candidate_rounding"], candidate_copy)


if __name__ == "__main__":
    unittest.main()
