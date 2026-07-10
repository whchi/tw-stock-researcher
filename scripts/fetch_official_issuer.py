#!/usr/bin/env python3
"""TWSE/TPEx official issuer adapter: company master, monthly revenue, and
quarterly income summary.

See docs/source-policy.md for verified endpoint findings: TWSE's OpenAPI
succeeds under strict TLS verification with `requests`' bundled CA store;
TPEx's certificate genuinely fails verification today (confirmed live,
2026-07-11) and is therefore treated as a source failure (status=blocked),
never bypassed with verify=False. The same TWSE dataset code covers both
"general" and "financial" industry issuers; financial issuers simply
report certain fields as the literal sentinel "--".
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from case_paths import CaseResolutionError, case_output_path, validate_explicit_output  # noqa: E402
from data_contract import atomic_write_json, classify_status, metadata_envelope  # noqa: E402

PARSER_VERSION = "1"

# Explicit endpoint allowlist -- never string-build a host from untrusted input.
ENDPOINT_TEMPLATES = {
    "TWSE": "https://openapi.twse.com.tw/v1/opendata/{dataset}",
    "TPEx": "https://www.tpex.org.tw/openapi/v1/{dataset}",
}
MARKET_SUFFIX = {"TWSE": "L", "TPEx": "O"}
DATASET_CODES = {
    "basic_info": "t187ap03_{suffix}",
    "monthly_revenue": "t187ap05_{suffix}",
    "quarterly_income": "t187ap14_{suffix}",
}
ISSUER_TYPES = ("general", "financial")


class OfficialIssuerError(RuntimeError):
    pass


def _dataset_url(market, dataset_key):
    if market not in ENDPOINT_TEMPLATES:
        raise OfficialIssuerError(f"unknown market: {market!r}")
    suffix = MARKET_SUFFIX[market]
    dataset_code = DATASET_CODES[dataset_key].format(suffix=suffix)
    return ENDPOINT_TEMPLATES[market].format(dataset=dataset_code), dataset_code


def normalize_period(value):
    """Return (period_type, period_key, source_as_of) for a raw TWSE/TPEx row."""
    if "資料年月" in value:
        raw = value["資料年月"]
        roc_year, month = int(raw[:-2]), int(raw[-2:])
        period_key = f"{roc_year + 1911:04d}-{month:02d}"
        return "monthly", period_key, period_key
    if "年度" in value and "季別" in value:
        roc_year, quarter = int(value["年度"]), int(value["季別"])
        period_key = f"{roc_year + 1911:04d}Q{quarter}"
        return "quarterly", period_key, period_key
    raise OfficialIssuerError(f"cannot normalize period from row: {value!r}")


def fetch_official_issuer(stock_id, market, issuer_type, client):
    if issuer_type not in ISSUER_TYPES:
        raise OfficialIssuerError(f"unknown issuer_type: {issuer_type!r}")
    if market not in ENDPOINT_TEMPLATES:
        raise OfficialIssuerError(f"unknown market: {market!r}")

    raw = {}
    errors = []
    source_urls = {}
    for dataset_key in DATASET_CODES:
        url, dataset_code = _dataset_url(market, dataset_key)
        source_urls[dataset_key] = url
        try:
            response = client.get(url, timeout=30)
            response.raise_for_status()
            rows = response.json()
        except Exception as exc:
            errors.append({"code": "fetch_failed", "dataset": dataset_code, "message": str(exc)})
            raw[dataset_key] = []
            continue
        if not isinstance(rows, list):
            errors.append({"code": "unexpected_shape", "dataset": dataset_code, "message": "expected a JSON array"})
            raw[dataset_key] = []
            continue
        raw[dataset_key] = [row for row in rows if row.get("公司代號") == stock_id]

    row_counts = {key: len(rows) for key, rows in raw.items()}
    required_datasets = ["basic_info"]
    optional_datasets = ["monthly_revenue", "quarterly_income"]
    status = classify_status(
        required_counts={key: row_counts[key] for key in required_datasets},
        optional_counts={key: row_counts[key] for key in optional_datasets},
        errors=errors,
    )

    source_as_of = None
    for row in raw.get("monthly_revenue") or []:
        try:
            _, _, source_as_of = normalize_period(row)
            break
        except OfficialIssuerError:
            continue

    metadata = metadata_envelope(
        status=status,
        fetched_at=datetime.now(timezone.utc),
        source_as_of=source_as_of,
        expected_source_as_of=None,
        requested_range={"start": None, "end": None},
        observed_range={"start": None, "end": None},
        required_datasets=required_datasets,
        optional_datasets=optional_datasets,
        row_counts=row_counts,
        source_urls=source_urls,
        source_tiers={key: "official" for key in DATASET_CODES},
        license_ids={},
        warnings=[],
        errors=errors,
        parser_version=PARSER_VERSION,
    )

    return {
        "stock_id": stock_id,
        "market": market,
        "issuer_type": issuer_type,
        "raw": raw,
        "metadata": metadata,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id")
    parser.add_argument("--market", required=True, choices=tuple(ENDPOINT_TEMPLATES))
    parser.add_argument("--issuer-type", default="general", choices=ISSUER_TYPES)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    import requests

    repo_root = Path(__file__).resolve().parent.parent
    try:
        if args.output:
            output_path = validate_explicit_output(Path(args.output), repo_root)
        else:
            output_path = case_output_path(args.stock_id, "official-issuer-data.json", repo_root)
    except CaseResolutionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = fetch_official_issuer(args.stock_id, args.market, args.issuer_type, requests)
    atomic_write_json(output_path, data)
    print(f"Official issuer data saved to {output_path}")
    return 2 if data["metadata"]["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
