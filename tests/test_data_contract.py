import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.data_contract import (
    STATUS_BLOCKED,
    STATUS_DEGRADED,
    STATUS_PASS,
    atomic_write_json,
    classify_status,
    latest_observation_date,
    metadata_envelope,
)


class ClassifyStatusTests(unittest.TestCase):
    def test_required_dataset_empty_is_blocked(self):
        status = classify_status(
            required_counts={"price": 0, "institutional": 5},
            optional_counts={},
            errors=[],
        )
        self.assertEqual(status, STATUS_BLOCKED)

    def test_optional_dataset_empty_with_required_present_is_degraded(self):
        status = classify_status(
            required_counts={"price": 10},
            optional_counts={"margin": 0},
            errors=[],
        )
        self.assertEqual(status, STATUS_DEGRADED)

    def test_all_required_and_optional_present_is_pass(self):
        status = classify_status(
            required_counts={"price": 10},
            optional_counts={"margin": 3},
            errors=[],
        )
        self.assertEqual(status, STATUS_PASS)

    def test_non_fatal_errors_without_empty_counts_still_degrade(self):
        status = classify_status(
            required_counts={"price": 10},
            optional_counts={"margin": 3},
            errors=[{"code": "partial_parse", "dataset": "margin", "message": "some rows skipped"}],
        )
        self.assertEqual(status, STATUS_DEGRADED)

    def test_required_empty_outranks_optional_present(self):
        status = classify_status(
            required_counts={"price": 0},
            optional_counts={"margin": 5},
            errors=[],
        )
        self.assertEqual(status, STATUS_BLOCKED)

    def test_no_datasets_at_all_is_pass(self):
        status = classify_status(required_counts={}, optional_counts={}, errors=[])
        self.assertEqual(status, STATUS_PASS)


class MetadataEnvelopeTests(unittest.TestCase):
    def _base_kwargs(self, **overrides):
        kwargs = dict(
            status=STATUS_PASS,
            fetched_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=timezone.utc),
            source_as_of="2026-07-09",
            expected_source_as_of="2026-07-09",
            requested_range={"start": None, "end": None},
            observed_range={"start": "2026-01-01", "end": "2026-07-09"},
            required_datasets=["price"],
            optional_datasets=["margin"],
            row_counts={"price": 10, "margin": 3},
            source_urls={"price": "https://example.test/price"},
            source_tiers={"price": "official"},
            license_ids={"price": "open-data"},
            warnings=[],
            errors=[],
            parser_version="2",
        )
        kwargs.update(overrides)
        return kwargs

    def test_fetched_at_is_serialized_ending_in_z(self):
        envelope = metadata_envelope(**self._base_kwargs())
        self.assertTrue(envelope["fetched_at"].endswith("Z"))
        self.assertEqual(envelope["fetched_at"], "2026-07-10T00:00:00Z")

    def test_naive_datetime_is_treated_as_utc(self):
        envelope = metadata_envelope(**self._base_kwargs(fetched_at=datetime(2026, 7, 10, 0, 0, 0)))
        self.assertEqual(envelope["fetched_at"], "2026-07-10T00:00:00Z")

    def test_source_as_of_is_passed_through_unchanged_not_derived_from_wall_clock(self):
        with patch("scripts.data_contract.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2099, 1, 1, tzinfo=timezone.utc)
            envelope = metadata_envelope(**self._base_kwargs(source_as_of="2026-07-09"))

        self.assertEqual(envelope["source_as_of"], "2026-07-09")

    def test_envelope_has_the_exact_documented_shape(self):
        envelope = metadata_envelope(**self._base_kwargs())
        self.assertEqual(
            set(envelope.keys()),
            {
                "schema_version",
                "status",
                "fetched_at",
                "source_as_of",
                "expected_source_as_of",
                "requested_range",
                "observed_range",
                "required_datasets",
                "optional_datasets",
                "row_counts",
                "source_urls",
                "source_tiers",
                "license_ids",
                "warnings",
                "errors",
                "parser_version",
            },
        )
        self.assertEqual(envelope["schema_version"], 2)

    def test_warnings_and_errors_must_be_objects_not_strings(self):
        with self.assertRaises(TypeError):
            metadata_envelope(**self._base_kwargs(warnings=["a bare string warning"]))


class AtomicWriteJsonTests(unittest.TestCase):
    def test_writes_sorted_ascii_false_two_space_indent_with_trailing_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.json"
            atomic_write_json(target, {"b": 1, "a": "資料"})

            content = target.read_text(encoding="utf-8")

        self.assertTrue(content.endswith("\n"))
        self.assertLess(content.index('"a"'), content.index('"b"'))
        self.assertIn("資料", content)
        self.assertEqual(json.loads(content), {"b": 1, "a": "資料"})

    def test_failure_leaves_previous_target_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.json"
            atomic_write_json(target, {"version": 1})
            original_content = target.read_text(encoding="utf-8")

            class Unserializable:
                pass

            with self.assertRaises(TypeError):
                atomic_write_json(target, {"version": 2, "bad": Unserializable()})

            self.assertEqual(target.read_text(encoding="utf-8"), original_content)

    def test_cleans_up_temp_file_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.json"

            class Unserializable:
                pass

            with self.assertRaises(TypeError):
                atomic_write_json(target, {"bad": Unserializable()})

            leftovers = [p for p in Path(tmp).iterdir() if p != target]
            self.assertEqual(leftovers, [])


class LatestObservationDateTests(unittest.TestCase):
    def test_returns_the_maximum_date_field(self):
        rows = [{"date": "2026-06-01"}, {"date": "2026-07-09"}, {"date": "2026-01-01"}]
        self.assertEqual(latest_observation_date(rows), "2026-07-09")

    def test_returns_none_for_empty_rows(self):
        self.assertIsNone(latest_observation_date([]))

    def test_ignores_rows_missing_the_field(self):
        rows = [{"date": "2026-06-01"}, {"other": "x"}]
        self.assertEqual(latest_observation_date(rows), "2026-06-01")

    def test_supports_a_custom_field_name(self):
        rows = [{"period": "2025/12"}, {"period": "2026/01"}]
        self.assertEqual(latest_observation_date(rows, field="period"), "2026/01")


if __name__ == "__main__":
    unittest.main()
