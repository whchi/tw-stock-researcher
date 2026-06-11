#!/usr/bin/env python3
"""Fetch TDCC ownership distribution data for chip-structure analysis."""

import argparse
import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TDCC_HOLDING_DISTRIBUTION_URL = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def default_output_path(stock_id, repo_root=None):
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    companies_dir = root / "companies"
    case_dirs = sorted(p for p in companies_dir.glob(f"{stock_id}-*") if p.is_dir())

    if len(case_dirs) == 1:
        return case_dirs[0] / "tdcc-data.json"

    return root / f"{stock_id}_tdcc_data.json"


def tdcc_date(value):
    if not value or len(value) != 8:
        return value
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def to_float(value):
    if value is None or value == "":
        return None
    return float(value)


def parse_holding_distribution(csv_text, stock_id):
    rows = []
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))

    for row in reader:
        row_stock_id = (row.get("證券代號") or "").strip()
        if row_stock_id != stock_id:
            continue

        rows.append(
            {
                "date": tdcc_date(row.get("資料日期")),
                "stock_id": row_stock_id,
                "HoldingSharesLevel": (row.get("持股分級") or "").strip(),
                "people": int(row.get("人數") or 0),
                "shares": int(row.get("股數") or 0),
                "percent": to_float(row.get("占集保庫存數比例%")) or 0.0,
                "unit": "股",
            }
        )

    return rows


def fetch_holding_distribution_csv():
    import requests
    import urllib3

    try:
        response = requests.get(TDCC_HOLDING_DISTRIBUTION_URL, timeout=30)
    except requests.exceptions.SSLError:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            response = requests.get(
                TDCC_HOLDING_DISTRIBUTION_URL,
                timeout=30,
                verify=False,
            )
        except requests.exceptions.RequestException:
            return fetch_holding_distribution_csv_with_curl()
    except requests.exceptions.RequestException:
        return fetch_holding_distribution_csv_with_curl()

    if response.status_code != 200:
        raise RuntimeError(
            "TDCCStockHoldingDistribution request failed: "
            f"HTTP {response.status_code}"
        )
    return response.text


def fetch_holding_distribution_csv_with_curl():
    completed = subprocess.run(
        [
            "curl",
            "-L",
            "--max-time",
            "90",
            TDCC_HOLDING_DISTRIBUTION_URL,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def build_metadata(rows):
    return {
        "fetched_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "source": "TDCC",
        "source_urls": {
            "TDCCStockHoldingDistribution": TDCC_HOLDING_DISTRIBUTION_URL,
        },
        "datasets": ["TDCCStockHoldingDistribution"],
        "row_counts": {
            "TDCCStockHoldingDistribution": len(rows),
        },
        "warnings": []
        if rows
        else ["TDCCStockHoldingDistribution returned no rows"],
    }


def fetch_all(stock_id):
    csv_text = fetch_holding_distribution_csv()
    rows = parse_holding_distribution(csv_text, stock_id)
    return {
        "stock_id": stock_id,
        "metadata": build_metadata(rows),
        "raw": {
            "holding_distribution": rows,
        },
    }


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    output_path = Path(args.output) if args.output else default_output_path(args.stock_id)
    data = fetch_all(args.stock_id)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"TDCC data saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
