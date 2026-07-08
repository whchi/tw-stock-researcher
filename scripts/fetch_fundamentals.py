#!/usr/bin/env python3
"""Fetch FinMind fundamentals: monthly revenue, quarterly statements, and valuation band.

Feeds the financial-analysis / quality-and-valuation layers with official data:
  - TaiwanStockMonthRevenue          -> derived.monthly_revenue_6m
  - TaiwanStockFinancialStatements   -> derived.quarterly_income_8q
  - TaiwanStockBalanceSheet          -> derived.quarterly_balance_key_items
  - TaiwanStockCashFlowsStatement    -> derived.quarterly_cash_flow
  - TaiwanStockPER                   -> derived.valuation_band (P/E, P/B history bands)
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

BASE_URL = "https://api.finmindtrade.com/api/v4/data"

DATASETS = (
    "TaiwanStockMonthRevenue",
    "TaiwanStockFinancialStatements",
    "TaiwanStockBalanceSheet",
    "TaiwanStockCashFlowsStatement",
    "TaiwanStockPER",
)

RAW_DATASET_KEYS = {
    "TaiwanStockMonthRevenue": "month_revenue",
    "TaiwanStockFinancialStatements": "financial_statements",
    "TaiwanStockBalanceSheet": "balance_sheet",
    "TaiwanStockCashFlowsStatement": "cash_flows_statement",
    "TaiwanStockPER": "per",
}

# Statement rows are long format (date, type, value, origin_name) and the type
# list varies by company, so each item tries exact types first and then falls
# back to origin_name keyword matching. A type match must still satisfy
# origin_includes to disambiguate near-duplicate types (e.g. the two operating
# cash-flow rows).
INCOME_ITEMS = {
    "revenue": [{"type": "Revenue", "origin_includes": ["營業收入"]}],
    "gross_profit": [{"type": "GrossProfit", "origin_includes": ["營業毛利"]}],
    "operating_income": [{"type": "OperatingIncome", "origin_includes": ["營業利益"]}],
    "net_income": [
        {"type": "EquityAttributableToOwnersOfParent", "origin_includes": ["母公司業主"]},
        {"type": "IncomeAfterTaxes", "origin_includes": ["本期淨利"]},
        {"type": "TotalConsolidatedProfitForThePeriod", "origin_includes": ["本期綜合損益"]},
    ],
    "eps": [{"type": "EPS", "origin_includes": ["每股盈餘"]}],
}

BALANCE_ITEMS = {
    "cash_and_equivalents": [
        {"type": "CashAndCashEquivalents", "origin_includes": ["現金及約當現金"]}
    ],
    "accounts_receivable": [
        {"type": "AccountsReceivableNet", "origin_includes": ["應收帳款"]}
    ],
    "inventories": [{"type": "Inventories", "origin_includes": ["存貨"]}],
    "accounts_payable": [{"type": "AccountsPayable", "origin_includes": ["應付帳款"]}],
    "current_assets": [{"type": "CurrentAssets", "origin_includes": ["流動資產"]}],
    "current_liabilities": [
        {"type": "CurrentLiabilities", "origin_includes": ["流動負債"]}
    ],
    "total_liabilities": [
        {"type": "Liabilities", "origin_includes": ["負債總額"]},
        {"type": "Liabilities", "origin_includes": ["負債總計"]},
    ],
    "equity": [
        {"type": "Equity", "origin_includes": ["權益總額"]},
        {"type": "Equity", "origin_includes": ["權益總計"]},
    ],
    "total_assets": [
        {"type": "TotalAssets", "origin_includes": ["資產總額"]},
        {"type": "TotalAssets", "origin_includes": ["資產總計"]},
    ],
}

CASH_FLOW_ITEMS = {
    "operating_cash_flow": [
        {"type": "CashFlowsFromOperatingActivities", "origin_includes": ["營業活動"]},
    ],
    "investing_cash_flow": [
        {"type": "CashProvidedByInvestingActivities", "origin_includes": ["投資活動"]},
    ],
    "financing_cash_flow": [
        {"type": "CashFlowsProvidedFromFinancingActivities", "origin_includes": ["籌資活動"]},
        {"type": "CashFlowsProvidedFromFinancingActivities", "origin_includes": ["融資活動"]},
    ],
    "capex": [
        {"type": "PropertyAndPlantAndEquipment", "origin_includes": ["不動產", "設備"]},
    ],
    "depreciation": [{"type": "Depreciation", "origin_includes": ["折舊"]}],
}


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--token")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def default_output_path(stock_id, repo_root=None):
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    companies_dir = root / "companies"
    case_dirs = sorted(p for p in companies_dir.glob(f"{stock_id}-*") if p.is_dir())

    if len(case_dirs) == 1:
        return case_dirs[0] / "fundamentals-data.json"

    return root / f"{stock_id}_fundamentals_data.json"


def resolve_token(args_token=None, env=None):
    env = os.environ if env is None else env
    token = args_token or env.get("FIN_MIND_TOKEN")
    if not token:
        raise RuntimeError(
            'FIN_MIND_TOKEN is required. Export it first: '
            'export FIN_MIND_TOKEN="your_token_here"'
        )
    return token


def fetch_dataset(dataset, stock_id, start_date, end_date, token=None, session=None):
    import requests

    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    client = session if session is not None else requests
    response = client.get(BASE_URL, headers=headers, params=params, timeout=30)

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"FinMind returned non-JSON response for {dataset}: "
            f"HTTP {response.status_code}"
        ) from exc

    if response.status_code == 402:
        msg = payload.get("msg", "quota exceeded")
        raise RuntimeError(
            f"FinMind quota exceeded for {dataset}: HTTP 402, msg={msg}."
        )

    if response.status_code != 200 or payload.get("status") != 200:
        msg = payload.get("msg", "unknown error")
        raise RuntimeError(
            f"FinMind request failed for {dataset}: HTTP {response.status_code}, "
            f"status={payload.get('status')}, msg={msg}"
        )

    return payload.get("data", [])


def to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def round2(value):
    return round(value, 2) if value is not None else None


def pct_change(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous * 100


def margin_pct(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100


# ─── statement pivot & selection ─────────────────────────────


def pivot_statement(rows):
    """Long rows -> {date: {type: {"value": ..., "origin_name": ...}}}."""
    by_date = {}
    for row in rows:
        row_date = row.get("date")
        row_type = row.get("type")
        if not row_date or not row_type:
            continue
        by_date.setdefault(row_date, {})[row_type] = {
            "value": to_float(row.get("value")),
            "origin_name": row.get("origin_name") or "",
        }
    return by_date


def pick_value(items_by_type, candidates):
    for cand in candidates:
        entry = items_by_type.get(cand.get("type"))
        if entry is None or entry["value"] is None:
            continue
        includes = cand.get("origin_includes") or []
        if includes and not all(term in entry["origin_name"] for term in includes):
            continue
        return entry["value"]

    for cand in candidates:
        includes = cand.get("origin_includes") or []
        if not includes:
            continue
        for row_type, entry in items_by_type.items():
            if row_type.endswith("_per"):
                continue
            if entry["value"] is None:
                continue
            if all(term in entry["origin_name"] for term in includes):
                return entry["value"]

    return None


def quarter_label(date_str):
    year, month = date_str[:4], int(date_str[5:7])
    return f"{year}Q{(month - 1) // 3 + 1}"


def prior_year_quarter(label):
    return f"{int(label[:4]) - 1}{label[4:]}"


def build_quarterly_income(by_date, quarters=8):
    rows = []
    for statement_date in sorted(by_date):
        items = by_date[statement_date]
        revenue = pick_value(items, INCOME_ITEMS["revenue"])
        gross_profit = pick_value(items, INCOME_ITEMS["gross_profit"])
        operating_income = pick_value(items, INCOME_ITEMS["operating_income"])
        net_income = pick_value(items, INCOME_ITEMS["net_income"])
        rows.append(
            {
                "quarter": quarter_label(statement_date),
                "date": statement_date,
                "revenue": revenue,
                "gross_profit": gross_profit,
                "operating_income": operating_income,
                "net_income": net_income,
                "eps": pick_value(items, INCOME_ITEMS["eps"]),
                "gross_margin_pct": round2(margin_pct(gross_profit, revenue)),
                "operating_margin_pct": round2(margin_pct(operating_income, revenue)),
                "net_margin_pct": round2(margin_pct(net_income, revenue)),
            }
        )

    by_quarter = {row["quarter"]: row for row in rows}
    for row in rows:
        prior = by_quarter.get(prior_year_quarter(row["quarter"]))
        row["revenue_yoy_pct"] = round2(
            pct_change(row["revenue"], prior["revenue"]) if prior else None
        )
        row["net_income_yoy_pct"] = round2(
            pct_change(row["net_income"], prior["net_income"]) if prior else None
        )

    return rows[-quarters:]


def build_quarterly_key_items(by_date, item_map, quarters=8):
    rows = []
    for statement_date in sorted(by_date):
        items = by_date[statement_date]
        row = {
            "quarter": quarter_label(statement_date),
            "date": statement_date,
        }
        for name, candidates in item_map.items():
            row[name] = pick_value(items, candidates)
        rows.append(row)
    return rows[-quarters:]


def build_quarterly_cash_flow(by_date, quarters=8):
    rows = build_quarterly_key_items(by_date, CASH_FLOW_ITEMS, quarters=quarters)
    for row in rows:
        ocf = row.get("operating_cash_flow")
        capex = row.get("capex")
        # Capex is reported as a negative outflow, so FCF = OCF + capex.
        row["free_cash_flow"] = ocf + capex if (ocf is not None and capex is not None) else None
    return rows


# ─── monthly revenue ─────────────────────────────────────────


def build_monthly_revenue(rows, months=6):
    series = {}
    for row in rows:
        year = row.get("revenue_year")
        month = row.get("revenue_month")
        revenue = to_float(row.get("revenue"))
        if year and month and revenue is not None:
            series[(int(year), int(month))] = revenue

    ordered = sorted(series)
    out = []
    for year, month in ordered:
        revenue = series[(year, month)]
        prev_key = (year, month - 1) if month > 1 else (year - 1, 12)
        current_months = [m for m in range(1, month + 1) if (year, m) in series]
        prior_months = [m for m in range(1, month + 1) if (year - 1, m) in series]
        # Cumulative YoY only when both years cover Jan..month completely,
        # otherwise a partial fetch window would fabricate the comparison.
        complete = len(current_months) == month and len(prior_months) == month
        cumulative = sum(series[(year, m)] for m in current_months) if complete else None
        cumulative_prior = (
            sum(series[(year - 1, m)] for m in prior_months) if complete else None
        )
        out.append(
            {
                "month": f"{year:04d}/{month:02d}",
                "revenue": revenue,
                "mom_pct": round2(pct_change(revenue, series.get(prev_key))),
                "yoy_pct": round2(pct_change(revenue, series.get((year - 1, month)))),
                "cumulative_revenue": cumulative,
                "cumulative_yoy_pct": round2(pct_change(cumulative, cumulative_prior)),
            }
        )

    return out[-months:]


# ─── valuation band ──────────────────────────────────────────


def percentile_rank(sorted_values, current):
    if not sorted_values or current is None:
        return None
    below_or_equal = sum(1 for value in sorted_values if value <= current)
    return below_or_equal / len(sorted_values) * 100


def build_valuation_band(per_rows):
    rows = sorted(
        (row for row in per_rows if row.get("date")), key=lambda row: row["date"]
    )
    if not rows:
        return {"status": "no_data"}

    latest = rows[-1]
    current = {
        "date": latest.get("date"),
        "per": to_float(latest.get("PER")),
        "pbr": to_float(latest.get("PBR")),
        "dividend_yield": to_float(latest.get("dividend_yield")),
    }

    latest_date = date.fromisoformat(latest["date"])

    def field_stats(window_rows, field, current_value):
        # Zero or negative values mean the multiple is undefined (e.g. PER
        # during loss-making periods); they would distort the band.
        values = sorted(
            value
            for value in (to_float(row.get(field)) for row in window_rows)
            if value is not None and value > 0
        )
        if not values:
            return None
        return {
            "min": round2(values[0]),
            "max": round2(values[-1]),
            "median": round2(median(values)),
            "current_percentile": round2(percentile_rank(values, current_value)),
        }

    windows = {}
    for label, days in (("1y", 365), ("3y", 365 * 3), ("5y", 365 * 5)):
        cutoff = (latest_date - timedelta(days=days)).isoformat()
        window_rows = [row for row in rows if row["date"] >= cutoff]
        windows[label] = {
            "trading_days": len(window_rows),
            "per": field_stats(window_rows, "PER", current["per"]),
            "pbr": field_stats(window_rows, "PBR", current["pbr"]),
        }

    return {"status": "ready", "current": current, "windows": windows}


# ─── main flow ───────────────────────────────────────────────


def build_metadata(stock_id, start_date, end_date, raw_rows_by_dataset, warnings):
    source_urls = {
        dataset: (
            f"{BASE_URL}?dataset={dataset}&data_id={stock_id}"
            f"&start_date={start_date}&end_date={end_date}"
        )
        for dataset in DATASETS
    }
    return {
        "fetched_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "source": "FinMind",
        "source_urls": source_urls,
        "datasets": list(DATASETS),
        "date_range": {"start_date": start_date, "end_date": end_date},
        "row_counts": {
            dataset: len(raw_rows_by_dataset.get(dataset, []))
            for dataset in DATASETS
        },
        "warnings": warnings,
    }


def fetch_all(stock_id, start_date, end_date, token=None):
    import requests

    raw_rows_by_dataset = {}
    warnings = []

    def fetch_safely(dataset):
        try:
            return fetch_dataset(
                dataset,
                stock_id,
                start_date,
                end_date,
                token=token,
                session=session,
            ), None
        except RuntimeError as exc:
            return [], f"{dataset} unavailable: {exc}"

    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=len(DATASETS)) as executor:
            futures = {
                dataset: executor.submit(fetch_safely, dataset)
                for dataset in DATASETS
            }
            for dataset in DATASETS:
                rows, warning = futures[dataset].result()
                raw_rows_by_dataset[dataset] = rows
                if warning:
                    warnings.append(warning)

    for dataset, rows in raw_rows_by_dataset.items():
        if not rows:
            warnings.append(f"{dataset} returned no rows")

    income_by_date = pivot_statement(
        raw_rows_by_dataset["TaiwanStockFinancialStatements"]
    )
    balance_by_date = pivot_statement(raw_rows_by_dataset["TaiwanStockBalanceSheet"])
    cash_by_date = pivot_statement(
        raw_rows_by_dataset["TaiwanStockCashFlowsStatement"]
    )

    return {
        "stock_id": stock_id,
        "metadata": build_metadata(
            stock_id, start_date, end_date, raw_rows_by_dataset, warnings
        ),
        "raw": {
            raw_key: raw_rows_by_dataset[dataset]
            for dataset, raw_key in RAW_DATASET_KEYS.items()
        },
        "derived": {
            "monthly_revenue_6m": build_monthly_revenue(
                raw_rows_by_dataset["TaiwanStockMonthRevenue"]
            ),
            "quarterly_income_8q": build_quarterly_income(income_by_date),
            "quarterly_balance_key_items": build_quarterly_key_items(
                balance_by_date, BALANCE_ITEMS
            ),
            "quarterly_cash_flow": build_quarterly_cash_flow(cash_by_date),
            "valuation_band": build_valuation_band(
                raw_rows_by_dataset["TaiwanStockPER"]
            ),
        },
    }


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=args.years * 365)).isoformat()
    token = resolve_token(args.token)
    output_path = (
        Path(args.output) if args.output else default_output_path(args.stock_id)
    )
    data = fetch_all(args.stock_id, start_date, end_date, token=token)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"FinMind fundamentals saved to {output_path}")
    for warning in data["metadata"]["warnings"]:
        print(f"- warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
