#!/usr/bin/env python3
"""Fetch shared macro data for macro-impact analysis — Taiwan-focused.

Sources follow templates/shared-macro-view.md and templates/macro-map.md:
  - TWSE Open API    (TAIEX, PE ratio)
  - Yahoo Finance    (USD/TWD, TAIEX, crude oil, copper, gold)
  - Taiwan official   (MOEA / DGBAS — configured via TAIWAN_MACRO_URL)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE_SOURCES = (
    "TWSE Open API",
    "Yahoo Finance / public market data",
    "Taiwan official statistics / MOPS context",
)

YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
TWSE_BASE = "https://openapi.twse.com.tw"

YAHOO_SYMBOLS = (
    {"indicator": "USD/TWD", "symbol": "TWD=X", "unit": "TWD per USD"},
    {"indicator": "TAIEX", "symbol": "^TWII", "unit": "index"},
    {"indicator": "Crude Oil Futures", "symbol": "CL=F", "unit": "USD/bbl"},
    {"indicator": "Copper Futures", "symbol": "HG=F", "unit": "USD/lb"},
    {"indicator": "Gold Futures", "symbol": "GC=F", "unit": "USD/oz"},
)


def default_output_path(repo_root=None):
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    return root / "market" / "shared-macro-data.json"


def request_json(url, method="GET", params=None, payload=None, headers=None):
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("requests is required. Use the repo-local .venv.") from exc

    if method == "POST":
        response = requests.post(
            url, params=params, json=payload, headers=headers, timeout=30
        )
    else:
        response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def request_text(url, params=None, headers=None):
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("requests is required. Use the repo-local .venv.") from exc

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def to_float(value):
    if value in (None, "", "."):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def latest_read(rows):
    valid = [row for row in rows if row.get("date") and row.get("value") is not None]
    valid = sorted(valid, key=lambda row: row["date"])
    if not valid:
        return None

    latest = valid[-1]
    previous = valid[-2] if len(valid) >= 2 else None
    result = {"date": latest["date"], "value": latest["value"]}

    if previous:
        result["previous_date"] = previous["date"]
        result["previous_value"] = previous["value"]
        if previous["value"] not in (None, 0):
            result["change_pct"] = round(
                (latest["value"] - previous["value"]) / previous["value"] * 100, 4
            )

    return result


def build_macro_data(records_by_source, warnings=None):
    sources = {source: records_by_source.get(source, []) for source in TEMPLATE_SOURCES}
    return {
        "metadata": {
            "fetched_at": datetime.now(timezone.utc)
            .astimezone()
            .isoformat(timespec="seconds"),
            "source_scope": list(TEMPLATE_SOURCES),
            "warnings": warnings or [],
        },
        "sources": sources,
    }


def fetch_yahoo_market():
    rows = []
    for item in YAHOO_SYMBOLS:
        url = f"{YAHOO_CHART_BASE}/{item['symbol']}"
        payload = request_json(url, params={"range": "1mo", "interval": "1d"})
        result = (payload.get("chart", {}).get("result") or [{}])[0]
        timestamps = result.get("timestamp") or []
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close") or []
        observations = []
        for ts, close in zip(timestamps, closes):
            observations.append(
                {
                    "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                    "value": to_float(close),
                }
            )
        rows.append(
            {
                "indicator": item["indicator"],
                "symbol": item["symbol"],
                "unit": item["unit"],
                "latest": latest_read(observations),
                "observations": sorted(
                    observations, key=lambda row: row.get("date") or ""
                ),
                "source_url": url,
            }
        )
    return rows


def fetch_twse_market_stats():
    """TWSE 大盤統計：指數、漲跌、成交值"""
    url = f"{TWSE_BASE}/v1/exchangeReport/FMTQIK"
    payload = request_json(url)
    if not payload:
        return []
    latest = payload[0]
    date_str = latest.get("Date", "")
    date_fmt = (
        f"{date_str[:3]}-{date_str[3:5]}-{date_str[5:]}"
        if len(date_str) == 7
        else date_str
    )
    return [
        {
            "indicator": "TAIEX",
            "source": "TWSE FMTQIK (daily market summary)",
            "unit": "index",
            "latest": {
                "date": date_fmt,
                "taiex": to_float(latest.get("TAIEX")),
                "change": to_float(latest.get("Change")),
                "trade_volume_shares": to_float(latest.get("TradeVolume")),
                "trade_value_twd": to_float(latest.get("TradeValue")),
                "transaction_count": to_float(latest.get("Transaction")),
            },
            "source_url": url,
        }
    ]


def fetch_taiwan_official(configured_url=None):
    if not configured_url:
        return [
            {
                "indicator": "Taiwan export orders / industrial production",
                "latest": None,
                "warning": "TAIWAN_MACRO_URL not set — configure a MOEA/DGBAS CSV/JSON endpoint to enable Taiwan export/orders data. See templates/shared-macro-view.md for source list.",
            }
        ]
    text = request_text(configured_url)
    return [
        {
            "indicator": "Taiwan official macro endpoint",
            "latest": None,
            "raw_preview": text[:500],
            "source_url": configured_url,
        }
    ]


def collect_all(args):
    env = os.environ
    records = {}
    warnings = []

    fetchers = (
        ("Yahoo Finance / public market data", fetch_yahoo_market),
        ("TWSE Open API", fetch_twse_market_stats),
        (
            "Taiwan official statistics / MOPS context",
            lambda: fetch_taiwan_official(env.get("TAIWAN_MACRO_URL")),
        ),
    )

    for source, fetcher in fetchers:
        try:
            records[source] = fetcher()
        except Exception as exc:
            records[source] = []
            warnings.append(f"{source}: {exc}")

    return build_macro_data(records, warnings=warnings)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    output_path = Path(args.output) if args.output else default_output_path()
    data = collect_all(args)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Macro data saved to {output_path}")
    if data["metadata"]["warnings"]:
        print("Warnings:")
        for warning in data["metadata"]["warnings"]:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
