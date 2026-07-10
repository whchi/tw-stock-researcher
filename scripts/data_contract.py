"""Shared fetch status classification, provenance envelope, and atomic JSON writes."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATUS_PASS = "pass"
STATUS_DEGRADED = "degraded"
STATUS_BLOCKED = "blocked"


def classify_status(required_counts, optional_counts, errors):
    if any(count == 0 for count in required_counts.values()):
        return STATUS_BLOCKED
    if errors or any(count == 0 for count in optional_counts.values()):
        return STATUS_DEGRADED
    return STATUS_PASS


def _iso_utc(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_objects(items, label):
    for item in items:
        if not isinstance(item, dict):
            raise TypeError(f"{label} must be a list of objects with code/dataset/message, not {item!r}")
    return list(items)


def metadata_envelope(
    *,
    status,
    fetched_at,
    source_as_of,
    expected_source_as_of,
    requested_range,
    observed_range,
    required_datasets,
    optional_datasets,
    row_counts,
    source_urls,
    source_tiers,
    license_ids,
    warnings,
    errors,
    parser_version,
):
    return {
        "schema_version": 2,
        "status": status,
        "fetched_at": _iso_utc(fetched_at),
        "source_as_of": source_as_of,
        "expected_source_as_of": expected_source_as_of,
        "requested_range": dict(requested_range),
        "observed_range": dict(observed_range),
        "required_datasets": list(required_datasets),
        "optional_datasets": list(optional_datasets),
        "row_counts": dict(row_counts),
        "source_urls": dict(source_urls),
        "source_tiers": dict(source_tiers),
        "license_ids": dict(license_ids),
        "warnings": _require_objects(warnings, "warnings"),
        "errors": _require_objects(errors, "errors"),
        "parser_version": parser_version,
    }


def atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def latest_observation_date(rows, field="date"):
    dates = [row[field] for row in rows if row.get(field)]
    return max(dates) if dates else None
