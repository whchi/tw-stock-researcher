#!/usr/bin/env python3
"""Fetch Yahoo Finance Taiwan profile and financial summary data."""

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from case_paths import CaseResolutionError, case_output_path, validate_explicit_output  # noqa: E402
from data_contract import (  # noqa: E402
    atomic_write_json,
    classify_status,
    latest_observation_date,
    metadata_envelope,
)

PARSER_VERSION = "2"

BASE_URL = "https://tw.stock.yahoo.com/quote"
PAGE_PATHS = {
    "profile": "profile",
    "revenue": "revenue",
    "income_statement": "income-statement",
    "cash_flow_statement": "cash-flow-statement",
}

PROFILE_FIELDS = (
    "公司名稱",
    "發言人",
    "英文簡稱",
    "代理發言人",
    "成立時間",
    "總機電話",
    "掛牌日期",
    "傳真號碼",
    "產業類別",
    "公司網站",
    "董事長",
    "電子郵件",
    "總經理",
    "股務代理",
    "股本",
    "簽證會計師",
    "已發行普通股數",
    "公司地址",
    "市值 (百萬)",
    "市場別",
    "董監持股比例(%)",
    "所屬集團",
    "主要經營業務",
)

INCOME_ITEMS = ("營業收入", "營業毛利", "營業費用", "營業利益", "稅後淨利")
CASH_FLOW_ITEMS = (
    "營業現金流",
    "投資現金流",
    "融資現金流",
    "自由現金流",
)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)


def html_lines(html):
    parser = TextExtractor()
    parser.feed(html)
    return [part.strip() for part in parser.parts if part.strip()]


def normalize_number(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in ("", "-", "--"):
        return None
    multiplier = -1 if text.startswith("(") and text.endswith(")") else 1
    text = text.strip("()")
    if text.endswith("%"):
        text = text[:-1]
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number) * multiplier
    return number * multiplier


def yahoo_url(stock_id, page_key, suffix="TW"):
    return f"{BASE_URL}/{stock_id}.{suffix}/{PAGE_PATHS[page_key]}"


def build_metadata(
    stock_id,
    suffix="TW",
    row_counts=None,
    warnings=None,
    errors=None,
    fetched_at=None,
    source_as_of=None,
):
    # Tier "unofficial_secondary" per docs/source-policy.md: local profile /
    # discovery fallback, excluded from shareable research-summary payloads.
    row_counts = row_counts or {}
    required_datasets = ["profile"]
    optional_datasets = ["revenue", "income_statement", "cash_flow_statement"]
    status = classify_status(
        required_counts={key: row_counts.get(key, 0) for key in required_datasets},
        optional_counts={key: row_counts.get(key, 0) for key in optional_datasets},
        errors=errors or [],
    )
    return metadata_envelope(
        status=status,
        fetched_at=fetched_at or datetime.now(timezone.utc),
        source_as_of=source_as_of,
        expected_source_as_of=None,
        requested_range={"start": None, "end": None},
        observed_range={"start": None, "end": None},
        required_datasets=required_datasets,
        optional_datasets=optional_datasets,
        row_counts=row_counts,
        source_urls={
            key: yahoo_url(stock_id, key, suffix=suffix)
            for key in ("profile", "revenue", "income_statement", "cash_flow_statement")
        },
        source_tiers={key: "unofficial_secondary" for key in ("profile", "revenue", "income_statement", "cash_flow_statement")},
        license_ids={},
        warnings=warnings or [],
        errors=errors or [],
        parser_version=PARSER_VERSION,
    )


def text_between(lines, start_marker, end_markers):
    try:
        start = lines.index(start_marker) + 1
    except ValueError:
        return []

    end = len(lines)
    for marker in end_markers:
        try:
            marker_index = lines.index(marker, start)
        except ValueError:
            continue
        end = min(end, marker_index)
    return lines[start:end]


def parse_profile(html):
    lines = text_between(
        html_lines(html),
        "公司基本資料",
        ("配股資訊", "財務資訊", "重要行事曆"),
    )
    fields = {}
    labels = set(PROFILE_FIELDS)

    i = 0
    while i < len(lines):
        label = lines[i]
        if label not in labels:
            i += 1
            continue

        value_parts = []
        i += 1
        while i < len(lines) and lines[i] not in labels:
            value_parts.append(lines[i])
            i += 1

        value = " ".join(value_parts).strip()
        if value:
            fields[label] = value

    return fields


def parse_revenue(html):
    lines = html_lines(html)
    rows = []
    period_pattern = re.compile(r"^\d{4}/\d{2}$")
    value_pattern = re.compile(r"^-?[\d,]+(?:\.\d+)?%?$")

    for i, line in enumerate(lines):
        if not period_pattern.match(line):
            continue

        values = []
        j = i + 1
        while j < len(lines) and len(values) < 7:
            if value_pattern.match(lines[j]):
                values.append(lines[j])
            elif period_pattern.match(lines[j]):
                break
            j += 1

        if len(values) < 7:
            continue

        rows.append(
            {
                "period": line,
                "monthly_revenue_thousand_twd": normalize_number(values[0]),
                "monthly_mom_pct": normalize_number(values[1]),
                "monthly_last_year_revenue_thousand_twd": normalize_number(values[2]),
                "monthly_yoy_pct": normalize_number(values[3]),
                "cumulative_revenue_thousand_twd": normalize_number(values[4]),
                "cumulative_last_year_revenue_thousand_twd": normalize_number(values[5]),
                "cumulative_yoy_pct": normalize_number(values[6]),
            }
        )

    return rows


def parse_statement(html, line_items):
    lines = html_lines(html)
    unit = None
    periods = []
    labels = set(line_items)
    line_data = {}

    for i, line in enumerate(lines):
        if line.startswith("單位"):
            unit = line.split(":", 1)[-1].strip()
        if line == "年度/月份":
            j = i + 1
            while j < len(lines) and re.match(r"^\d{4} Q[1-4]$", lines[j]):
                periods.append(lines[j])
                j += 1
            break

    if not periods:
        return {"unit": unit, "periods": [], "line_items": {}}

    value_pattern = re.compile(r"^-?[\d,]+(?:\.\d+)?$")
    for i, line in enumerate(lines):
        if line not in labels:
            continue
        values = []
        j = i + 1
        while j < len(lines) and len(values) < len(periods):
            if lines[j] in labels:
                break
            if value_pattern.match(lines[j]):
                values.append(lines[j])
            j += 1
        if values:
            line_data[line] = {
                period: normalize_number(value)
                for period, value in zip(periods, values)
            }

    return {"unit": unit, "periods": periods, "line_items": line_data}


def build_summary(profile, revenue, income_statement, cash_flow_statement):
    income_items = income_statement.get("line_items", {})
    periods = income_statement.get("periods", [])
    latest_period = periods[0] if periods else None
    latest_revenue = None
    latest_gross_profit = None
    latest_net_income = None

    if latest_period:
        latest_revenue = income_items.get("營業收入", {}).get(latest_period)
        latest_gross_profit = income_items.get("營業毛利", {}).get(latest_period)
        latest_net_income = income_items.get("稅後淨利", {}).get(latest_period)

    def margin(numerator, denominator):
        if numerator is None or not denominator:
            return None
        return round(numerator / denominator * 100, 2)

    return {
        "company_name": profile.get("公司名稱"),
        "industry": profile.get("產業類別"),
        "market": profile.get("市場別"),
        "business_scope": profile.get("主要經營業務"),
        "latest_monthly_revenue": revenue[0] if revenue else None,
        "latest_income_period": latest_period,
        "latest_gross_margin_pct": margin(latest_gross_profit, latest_revenue),
        "latest_net_margin_pct": margin(latest_net_income, latest_revenue),
        "cash_flow_periods": cash_flow_statement.get("periods", []),
    }


def fetch_page(url, session=None):
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "requests is required to fetch Yahoo data. Use the external venv "
            "described in AGENTS.md before running scripts/fetch_yahoo.py."
        ) from exc

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }
    client = session if session is not None else requests
    try:
        response = client.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Yahoo request failed for {url}: {exc}") from exc
    return response.text


def fetch_all(stock_id, suffix="TW"):
    page_keys = ("profile", "revenue", "income_statement", "cash_flow_statement")
    session = None
    try:
        import requests
    except ModuleNotFoundError:
        pass  # fetch_page raises the descriptive error
    else:
        session = requests.Session()

    try:
        with ThreadPoolExecutor(max_workers=len(page_keys)) as executor:
            futures = {
                key: executor.submit(
                    fetch_page, yahoo_url(stock_id, key, suffix=suffix), session
                )
                for key in page_keys
            }
            pages = {key: future.result() for key, future in futures.items()}
    finally:
        if session is not None:
            session.close()
    profile = parse_profile(pages["profile"])
    revenue = parse_revenue(pages["revenue"])
    income_statement = parse_statement(pages["income_statement"], INCOME_ITEMS)
    cash_flow_statement = parse_statement(
        pages["cash_flow_statement"],
        CASH_FLOW_ITEMS,
    )
    row_counts = {
        "profile": len(profile),
        "revenue": len(revenue),
        "income_statement": len(income_statement.get("line_items") or {}),
        "cash_flow_statement": len(cash_flow_statement.get("line_items") or {}),
    }
    errors = []
    warnings = []

    if not profile:
        errors.append({"code": "no_rows", "dataset": "profile", "message": "Yahoo profile returned no parsed fields"})
    if not revenue:
        warnings.append({"code": "no_rows", "dataset": "revenue", "message": "Yahoo revenue returned no parsed rows"})
    if not income_statement.get("line_items"):
        warnings.append({"code": "no_rows", "dataset": "income_statement", "message": "Yahoo income statement returned no parsed line items"})
    if not cash_flow_statement.get("line_items"):
        warnings.append({"code": "no_rows", "dataset": "cash_flow_statement", "message": "Yahoo cash flow statement returned no parsed line items"})

    source_as_of = latest_observation_date(revenue, field="period")

    return {
        "stock_id": stock_id,
        "symbol_suffix": suffix,
        "metadata": build_metadata(
            stock_id,
            suffix=suffix,
            row_counts=row_counts,
            warnings=warnings,
            errors=errors,
            source_as_of=source_as_of,
        ),
        "profile": profile,
        "revenue": revenue,
        "income_statement": income_statement,
        "cash_flow_statement": cash_flow_statement,
        "summary": build_summary(profile, revenue, income_statement, cash_flow_statement),
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id")
    parser.add_argument("--suffix", default="TW", choices=("TW", "TWO"))
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(__file__).resolve().parent.parent
    try:
        if args.output:
            output_path = validate_explicit_output(Path(args.output), repo_root)
        else:
            output_path = case_output_path(args.stock_id, "yahoo-data.json", repo_root)
    except CaseResolutionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = fetch_all(args.stock_id, suffix=args.suffix)

    atomic_write_json(output_path, data)

    print(f"Yahoo Finance Taiwan data saved to {output_path}")
    return 2 if data["metadata"]["status"] == "blocked" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
