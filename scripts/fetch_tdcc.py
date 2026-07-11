#!/usr/bin/env python3
"""Fetch TDCC ownership distribution data for chip-structure analysis."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from case_paths import CaseResolutionError, case_output_path, validate_explicit_output  # noqa: E402
from data_contract import (  # noqa: E402
    atomic_write_json,
    classify_status,
    latest_observation_date,
    metadata_envelope,
)

PARSER_VERSION = "3"

# TDCC official OpenAPI, verified live 2026-07-11 under strict TLS
# certificate verification -- see docs/source-policy.md.
TDCC_HOLDING_DISTRIBUTION_URL = "https://openapi.tdcc.com.tw/v1/opendata/1-5"

# The endpoint returns the all-market table (~2.3MB); TDCC refreshes it weekly,
# so a shared cache avoids re-downloading it for every stock case.
CACHE_JSON_NAME = "tdcc-holding-distribution.json"
CACHE_META_NAME = "tdcc-cache-meta.json"
DEFAULT_CACHE_MAX_AGE_HOURS = 72


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id")
    parser.add_argument("--output")
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=DEFAULT_CACHE_MAX_AGE_HOURS,
        help="Reuse the shared all-market JSON cache when younger than this.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore the cache and re-download the all-market JSON response.",
    )
    return parser.parse_args(argv)


def cache_paths(repo_root=None):
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    market_dir = root / "market"
    return market_dir / CACHE_JSON_NAME, market_dir / CACHE_META_NAME


def load_cached_rows(repo_root=None, max_age_hours=DEFAULT_CACHE_MAX_AGE_HOURS):
    """Return (rows, meta) when a fresh current-format cache exists."""
    json_path, meta_path = cache_paths(repo_root=repo_root)
    if not json_path.exists() or not meta_path.exists():
        return None, None

    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        with open(json_path, encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            return None, None
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None, None

    age = datetime.now(timezone.utc) - fetched_at.astimezone(timezone.utc)
    if age > timedelta(hours=max_age_hours):
        return None, None

    return rows, meta


def save_cached_rows(rows, repo_root=None):
    json_path, meta_path = cache_paths(repo_root=repo_root)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(json_path, rows)

    meta = {
        "fetched_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "source_url": TDCC_HOLDING_DISTRIBUTION_URL,
    }
    atomic_write_json(meta_path, meta)
    return meta


def tdcc_date(value):
    if not value or len(value) != 8:
        return value
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def to_float(value):
    if value is None or value == "":
        return None
    return float(value)


def parse_holding_distribution(source_rows, stock_id):
    rows = []
    for row in source_rows:
        row_stock_id = (row.get("證券代號") or "").strip()
        if row_stock_id != stock_id:
            continue

        rows.append(
            {
                "date": tdcc_date(row.get("﻿資料日期") or row.get("資料日期")),
                "stock_id": row_stock_id,
                "HoldingSharesLevel": (row.get("持股分級") or "").strip(),
                "people": int(row.get("人數") or 0),
                "shares": int(row.get("股數") or 0),
                "percent": to_float(row.get("占集保庫存數比例%")) or 0.0,
                "unit": "股",
            }
        )

    return rows


def fetch_holding_distribution_rows():
    """Fetch the all-market ownership-distribution dataset from TDCC's
    official OpenAPI. A TLS or HTTP failure here is a source failure; it is
    never retried with verify=False or a curl subprocess."""
    import requests

    response = requests.get(TDCC_HOLDING_DISTRIBUTION_URL, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            "TDCCStockHoldingDistribution request failed: "
            f"HTTP {response.status_code}"
        )

    rows = response.json()
    if not isinstance(rows, list):
        raise RuntimeError("TDCCStockHoldingDistribution response was not a JSON array")

    return rows


def merge_history(previous_payload, snapshot_rows):
    """Append the new snapshot to the per-date history, deduplicated by date."""
    history = list((previous_payload or {}).get("history") or [])

    known_dates = {entry.get("date") for entry in history}
    snapshot_dates = sorted({row.get("date") for row in snapshot_rows if row.get("date")})
    for snapshot_date in snapshot_dates:
        if snapshot_date in known_dates:
            continue
        history.append(
            {
                "date": snapshot_date,
                "rows": [row for row in snapshot_rows if row.get("date") == snapshot_date],
            }
        )

    history.sort(key=lambda entry: entry.get("date") or "")
    return history


def build_metadata(rows, history=None, fetched_at=None):
    row_counts = {
        "TDCCStockHoldingDistribution": len(rows),
        "TDCCHoldingDistributionHistoryDates": len(history or []),
    }
    status = classify_status(
        required_counts={"TDCCStockHoldingDistribution": row_counts["TDCCStockHoldingDistribution"]},
        optional_counts={},
        errors=[],
    )
    warnings = (
        []
        if rows
        else [{"code": "no_rows", "dataset": "TDCCStockHoldingDistribution", "message": "TDCCStockHoldingDistribution returned no rows"}]
    )
    return metadata_envelope(
        status=status,
        fetched_at=fetched_at or datetime.now(timezone.utc),
        source_as_of=latest_observation_date(rows),
        expected_source_as_of=None,
        requested_range={"start": None, "end": None},
        observed_range={"start": None, "end": None},
        required_datasets=["TDCCStockHoldingDistribution"],
        optional_datasets=[],
        row_counts=row_counts,
        source_urls={"TDCCStockHoldingDistribution": TDCC_HOLDING_DISTRIBUTION_URL},
        source_tiers={"TDCCStockHoldingDistribution": "official"},
        license_ids={},
        warnings=warnings,
        errors=[],
        parser_version=PARSER_VERSION,
    )


def fetch_all(
    stock_id,
    repo_root=None,
    max_age_hours=DEFAULT_CACHE_MAX_AGE_HOURS,
    refresh=False,
    previous_payload=None,
):
    source_rows, cache_meta = (None, None)
    if not refresh:
        source_rows, cache_meta = load_cached_rows(
            repo_root=repo_root, max_age_hours=max_age_hours
        )
    cache_hit = source_rows is not None

    if not cache_hit:
        source_rows = fetch_holding_distribution_rows()
        cache_meta = save_cached_rows(source_rows, repo_root=repo_root)

    rows = parse_holding_distribution(source_rows, stock_id)
    history = merge_history(previous_payload, rows)
    return {
        "stock_id": stock_id,
        "metadata": build_metadata(rows, history=history),
        "cache": {
            "hit": cache_hit,
            "path": f"market/{CACHE_JSON_NAME}",
            "cache_fetched_at": (cache_meta or {}).get("fetched_at"),
        },
        "raw": {
            "holding_distribution": rows,
        },
        "history": history,
    }


def load_previous_payload(output_path):
    if not output_path.exists():
        return None
    try:
        with open(output_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(__file__).resolve().parent.parent
    try:
        if args.output:
            output_path = validate_explicit_output(Path(args.output), repo_root)
        else:
            output_path = case_output_path(args.stock_id, "tdcc-data.json", repo_root)
    except CaseResolutionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = fetch_all(
        args.stock_id,
        max_age_hours=args.max_age_hours,
        refresh=args.refresh,
        previous_payload=load_previous_payload(output_path),
    )

    atomic_write_json(output_path, data)

    print(f"TDCC data saved to {output_path}")
    return 2 if data["metadata"]["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
