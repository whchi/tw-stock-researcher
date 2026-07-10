#!/usr/bin/env python3
"""Fetch shared macro data for macro-impact analysis — Taiwan-focused.

Sources follow templates/shared-macro-view.md and templates/macro-map.md:
  - TWSE Open API    (TAIEX, PE ratio)
  - Yahoo Finance    (USD/TWD, TAIEX, crude oil, copper, gold)
  - Taiwan official  (MOF Customs monthly trade statistics by default;
                      override with TAIWAN_MACRO_URL)
"""

import argparse
import csv
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_contract import (  # noqa: E402
    STATUS_BLOCKED,
    atomic_write_json,
    classify_status,
    latest_observation_date,
    metadata_envelope,
)

PARSER_VERSION = "2"

TEMPLATE_SOURCES = (
    "TWSE Open API",
    "Yahoo Finance / public market data",
    "Taiwan official statistics / MOPS context",
)

YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
TWSE_BASE = "https://openapi.twse.com.tw"

# MOF Customs monthly import/export totals — data.gov.tw dataset 6053,
# official, free, updated monthly. Override with TAIWAN_MACRO_URL.
DEFAULT_TAIWAN_MACRO_URL = "https://opendata.customs.gov.tw/data/6053/csv.csv"

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


def make_session():
    try:
        import requests
    except ModuleNotFoundError:
        return None
    return requests.Session()


def request_json(url, method="GET", params=None, payload=None, headers=None, session=None):
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("requests is required. Use the repo-local .venv.") from exc

    client = session if session is not None else requests
    if method == "POST":
        response = client.post(
            url, params=params, json=payload, headers=headers, timeout=30
        )
    else:
        response = client.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def request_text(url, params=None, headers=None, session=None, encoding=None):
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("requests is required. Use the repo-local .venv.") from exc

    client = session if session is not None else requests
    response = client.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    if encoding:
        # Taiwan government hosts often omit the charset header, which makes
        # requests fall back to ISO-8859-1 and garble UTF-8 CSV headers.
        response.encoding = encoding
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


def build_macro_data(records_by_source, warnings=None, errors=None, fetched_at=None):
    sources = {source: records_by_source.get(source, []) for source in TEMPLATE_SOURCES}
    row_counts = {source: len(records) for source, records in sources.items()}

    if all(count == 0 for count in row_counts.values()):
        status = STATUS_BLOCKED
    else:
        status = classify_status(required_counts={}, optional_counts=row_counts, errors=errors or [])

    observation_dates = [
        {"date": record["latest"]["date"]}
        for records in sources.values()
        for record in records
        if record.get("latest") and record["latest"].get("date")
    ]

    metadata = metadata_envelope(
        status=status,
        fetched_at=fetched_at or datetime.now(timezone.utc),
        source_as_of=latest_observation_date(observation_dates),
        expected_source_as_of=None,
        requested_range={"start": None, "end": None},
        observed_range={"start": None, "end": None},
        required_datasets=[],
        optional_datasets=list(TEMPLATE_SOURCES),
        row_counts=row_counts,
        source_urls={},
        source_tiers={
            "TWSE Open API": "official",
            "Yahoo Finance / public market data": "unofficial_secondary",
            "Taiwan official statistics / MOPS context": "official",
        },
        license_ids={},
        warnings=warnings or [],
        errors=errors or [],
        parser_version=PARSER_VERSION,
    )
    return {
        "metadata": metadata,
        "sources": sources,
    }


def fetch_yahoo_market(session=None):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }

    def fetch_symbol(item):
        url = f"{YAHOO_CHART_BASE}/{item['symbol']}"
        payload = request_json(
            url,
            params={"range": "1mo", "interval": "1d"},
            headers=headers,
            session=session,
        )
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
        return {
            "indicator": item["indicator"],
            "symbol": item["symbol"],
            "unit": item["unit"],
            "latest": latest_read(observations),
            "observations": sorted(
                observations, key=lambda row: row.get("date") or ""
            ),
            "source_url": url,
        }

    # The chart API rate-limits concurrent bursts (429), so symbols stay
    # sequential; the shared session still reuses the connection.
    return [fetch_symbol(item) for item in YAHOO_SYMBOLS]


def fetch_twse_market_stats(session=None):
    """TWSE 大盤統計：指數、漲跌、成交值"""
    url = f"{TWSE_BASE}/v1/exchangeReport/FMTQIK"
    payload = request_json(url, session=session)
    if not payload:
        return []
    # FMTQIK rows are ascending (oldest first); the last row is the latest trading day.
    latest = payload[-1]
    date_str = latest.get("Date", "")
    date_fmt = (
        f"{int(date_str[:3]) + 1911}-{date_str[3:5]}-{date_str[5:]}"
        if len(date_str) == 7 and date_str.isdigit()
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


def request_text_with_ssl_fallback(url, session=None, encoding="utf-8-sig"):
    """Some Taiwan government hosts serve certificate chains that fail strict
    verification (same issue as TDCC OpenData); retry unverified for these
    public statistical downloads."""
    import requests

    try:
        return request_text(url, session=session, encoding=encoding)
    except requests.exceptions.SSLError:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(url, timeout=30, verify=False)
        response.raise_for_status()
        if encoding:
            response.encoding = encoding
        return response.text


def parse_customs_trade_csv(text):
    """Parse data.gov.tw dataset 6053 (海關進出口貿易統計, ROC year rows)."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    observations = []
    for row in reader:
        roc_year = to_float((row.get("年度") or "").strip())
        month = to_float((row.get("月份") or "").strip())
        if roc_year is None or month is None:
            continue
        observations.append(
            {
                "date": f"{int(roc_year) + 1911:04d}-{int(month):02d}",
                "exports_total_twd_thousand": to_float(row.get("出口總值(新臺幣千元)")),
                "imports_total_twd_thousand": to_float(row.get("進口總值(新臺幣千元)")),
                "trade_balance_twd_thousand": to_float(row.get("出入超(新臺幣千元)")),
            }
        )
    observations.sort(key=lambda row: row["date"])
    return observations


def build_customs_trade_rows(text, source_url):
    observations = parse_customs_trade_csv(text)
    if not observations:
        return [
            {
                "indicator": "Taiwan customs trade (monthly)",
                "latest": None,
                "warning": "customs trade CSV returned no parsable rows",
                "source_url": source_url,
            }
        ]

    latest = observations[-1]
    year, month = latest["date"].split("-")
    prior_date = f"{int(year) - 1:04d}-{month}"
    prior = next((row for row in observations if row["date"] == prior_date), None)
    exports_yoy_pct = None
    if prior and prior["exports_total_twd_thousand"] not in (None, 0):
        exports_yoy_pct = round(
            (latest["exports_total_twd_thousand"] - prior["exports_total_twd_thousand"])
            / prior["exports_total_twd_thousand"]
            * 100,
            2,
        )

    return [
        {
            "indicator": "Taiwan customs exports / imports (monthly)",
            "source": "MOF Customs open data (data.gov.tw dataset 6053)",
            "unit": "TWD thousand",
            "latest": {
                "date": latest["date"],
                "exports_total_twd_thousand": latest["exports_total_twd_thousand"],
                "imports_total_twd_thousand": latest["imports_total_twd_thousand"],
                "trade_balance_twd_thousand": latest["trade_balance_twd_thousand"],
                "exports_yoy_pct": exports_yoy_pct,
            },
            "observations": observations[-24:],
            "source_url": source_url,
        }
    ]


def fetch_taiwan_official(configured_url=None, session=None):
    url = configured_url or DEFAULT_TAIWAN_MACRO_URL
    text = request_text_with_ssl_fallback(url, session=session)

    if url == DEFAULT_TAIWAN_MACRO_URL:
        return build_customs_trade_rows(text, url)

    return [
        {
            "indicator": "Taiwan official macro endpoint",
            "latest": None,
            "raw_preview": text[:500],
            "source_url": url,
        }
    ]


def collect_all(args):
    env = os.environ
    records = {}
    errors = []
    session = make_session()

    fetchers = (
        (
            "Yahoo Finance / public market data",
            lambda: fetch_yahoo_market(session=session),
        ),
        ("TWSE Open API", lambda: fetch_twse_market_stats(session=session)),
        (
            "Taiwan official statistics / MOPS context",
            lambda: fetch_taiwan_official(env.get("TAIWAN_MACRO_URL"), session=session),
        ),
    )

    try:
        with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
            futures = [
                (source, executor.submit(fetcher)) for source, fetcher in fetchers
            ]
            for source, future in futures:
                try:
                    records[source] = future.result()
                except Exception as exc:
                    records[source] = []
                    errors.append({"code": "fetch_failed", "dataset": source, "message": f"{source}: {exc}"})
    finally:
        if session is not None:
            session.close()

    return build_macro_data(records, errors=errors)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    output_path = Path(args.output) if args.output else default_output_path()
    data = collect_all(args)

    atomic_write_json(output_path, data)

    print(f"Macro data saved to {output_path}")
    if data["metadata"]["errors"]:
        print("Errors:")
        for error in data["metadata"]["errors"]:
            print(f"- {error['message']}")
    return 2 if data["metadata"]["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
