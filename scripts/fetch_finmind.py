#!/usr/bin/env python3
"""Fetch FinMind price and institutional investor data for market-action analysis."""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE_URL = "https://api.finmindtrade.com/api/v4/data"
DATASETS = (
    "TaiwanStockPrice",
    "TaiwanStockInstitutionalInvestorsBuySell",
    "TaiwanStockMarginPurchaseShortSale",
    "TaiwanStockShareholding",
    "TaiwanStockDayTrading",
    "TaiwanStockHoldingSharesPer",
)

RAW_DATASET_KEYS = {
    "TaiwanStockPrice": "price",
    "TaiwanStockInstitutionalInvestorsBuySell": "institutional_investors",
    "TaiwanStockMarginPurchaseShortSale": "margin_purchase_short_sale",
    "TaiwanStockShareholding": "shareholding",
    "TaiwanStockDayTrading": "day_trading",
    "TaiwanStockHoldingSharesPer": "holding_shares_per",
}
OPTIONAL_DATASETS = {
    "TaiwanStockMarginPurchaseShortSale",
    "TaiwanStockShareholding",
    "TaiwanStockDayTrading",
    "TaiwanStockHoldingSharesPer",
}


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--days", type=int, default=400)
    parser.add_argument("--token")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def default_date_range(days, end_date=None):
    end = date.fromisoformat(end_date) if end_date else date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def default_output_path(stock_id, repo_root=None):
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    companies_dir = root / "companies"
    case_dirs = sorted(p for p in companies_dir.glob(f"{stock_id}-*") if p.is_dir())

    if len(case_dirs) == 1:
        return case_dirs[0] / "market-data.json"

    return root / f"{stock_id}_market_data.json"


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
            f"FinMind quota exceeded for {dataset}: HTTP 402, msg={msg}. "
            "Check https://api.web.finmindtrade.com/v2/user_info or wait "
            "for your request limit to reset."
        )

    if response.status_code != 200 or payload.get("status") != 200:
        msg = payload.get("msg", "unknown error")
        raise RuntimeError(
            f"FinMind request failed for {dataset}: HTTP {response.status_code}, "
            f"status={payload.get('status')}, msg={msg}"
        )

    return payload.get("data", [])


def fetch_dataset_safely(dataset, stock_id, start_date, end_date, token=None, session=None):
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
        if dataset not in OPTIONAL_DATASETS:
            raise
        return [], f"{dataset} unavailable: {exc}"


def to_float(value):
    if value is None or value == "":
        return None
    return float(value)


def pct_change(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous * 100


def direction(value, threshold=2.0):
    if value is None:
        return "unknown"
    if value > threshold:
        return "up"
    if value < -threshold:
        return "down"
    return "flat"


def summarize_institutional_flows(rows):
    by_name = {}
    total = 0.0

    for row in rows:
        name = row.get("name") or "Unknown"
        buy = to_float(row.get("buy")) or 0.0
        sell = to_float(row.get("sell")) or 0.0
        entry = by_name.setdefault(
            name,
            {"buy": 0.0, "sell": 0.0, "net_buy_sell": 0.0},
        )
        entry["buy"] += buy
        entry["sell"] += sell
        entry["net_buy_sell"] += buy - sell
        total += buy - sell

    return {"by_name": by_name, "total_net_buy_sell": total}


def institutional_rows_between(rows, comparison_date, latest_date):
    return [
        row
        for row in rows
        if comparison_date < row.get("date", "") <= latest_date
    ]


def classify_market_state(price_change_pct, volume_change_pct):
    if price_change_pct is None or volume_change_pct is None:
        return "insufficient_data"
    if price_change_pct >= 8 and volume_change_pct >= 50:
        return "overheated"
    if price_change_pct >= 3 and volume_change_pct >= 10:
        return "bullish"
    if price_change_pct <= -3 and volume_change_pct >= 10:
        return "bearish"
    if price_change_pct <= -3 and volume_change_pct <= -10:
        return "pullback"
    if price_change_pct < 0 and volume_change_pct > 30:
        return "failed_breakout"
    return "neutral"


def build_window_read(label, sorted_price, institutional_rows):
    offset = int(label[:-1])
    if len(sorted_price) < offset + 1:
        return {
            "window": label,
            "market_state": "insufficient_data",
            "price_volume_read": "insufficient_data",
            "warnings": [f"Need at least {offset + 1} trading rows for {label}"],
        }

    latest = sorted_price[-1]
    comparison = sorted_price[-(offset + 1)]
    latest_date = latest.get("date")
    comparison_date = comparison.get("date")
    latest_close = to_float(latest.get("close"))
    comparison_close = to_float(comparison.get("close"))
    latest_volume = to_float(latest.get("Trading_Volume"))
    comparison_volume = to_float(comparison.get("Trading_Volume"))
    price_change = None
    volume_change = None

    if latest_close is not None and comparison_close is not None:
        price_change = latest_close - comparison_close
    if latest_volume is not None and comparison_volume is not None:
        volume_change = latest_volume - comparison_volume

    price_change_pct = pct_change(latest_close, comparison_close)
    volume_change_pct = pct_change(latest_volume, comparison_volume)
    institutional_summary = summarize_institutional_flows(
        institutional_rows_between(institutional_rows, comparison_date, latest_date)
    )
    price_dir = direction(price_change_pct)
    volume_dir = direction(volume_change_pct, threshold=10.0)

    return {
        "window": label,
        "latest_date": latest_date,
        "comparison_date": comparison_date,
        "latest_close": latest_close,
        "comparison_close": comparison_close,
        "price_change": round(price_change, 2) if price_change is not None else None,
        "price_change_pct": round(price_change_pct, 2)
        if price_change_pct is not None
        else None,
        "latest_volume": latest_volume,
        "comparison_volume": comparison_volume,
        "volume_change": round(volume_change, 2)
        if volume_change is not None
        else None,
        "volume_change_pct": round(volume_change_pct, 2)
        if volume_change_pct is not None
        else None,
        "price_volume_read": f"price_{price_dir}_volume_{volume_dir}",
        "market_state": classify_market_state(price_change_pct, volume_change_pct),
        "institutional_flows_by_name": institutional_summary["by_name"],
        "institutional_total_net_buy_sell": institutional_summary["total_net_buy_sell"],
        "warnings": [],
    }


def build_market_action_read(price_rows, institutional_rows):
    warnings = []
    sorted_price = sorted(price_rows, key=lambda row: row.get("date", ""))
    institutional_summary = summarize_institutional_flows(institutional_rows)
    windows = {
        label: build_window_read(label, sorted_price, institutional_rows)
        for label in ("1d", "3d", "5d")
    }

    if len(sorted_price) < 6:
        warnings.append("Need at least 6 trading rows")
        return {
            "latest_date": sorted_price[-1].get("date") if sorted_price else None,
            "comparison_date": None,
            "market_state": "insufficient_data",
            "price_volume_read": "insufficient_data",
            "windows": windows,
            "warnings": warnings,
            "institutional_flows_by_name": institutional_summary["by_name"],
            "institutional_total_net_buy_sell": institutional_summary[
                "total_net_buy_sell"
            ],
        }

    five_day = windows["5d"]

    return {
        "latest_date": five_day.get("latest_date"),
        "comparison_date": five_day.get("comparison_date"),
        "latest_close": five_day.get("latest_close"),
        "comparison_close": five_day.get("comparison_close"),
        "latest_volume": five_day.get("latest_volume"),
        "comparison_volume": five_day.get("comparison_volume"),
        "price_5d_change_pct": five_day.get("price_change_pct"),
        "volume_5d_change_pct": five_day.get("volume_change_pct"),
        "price_volume_read": five_day.get("price_volume_read"),
        "market_state": five_day.get("market_state"),
        "windows": windows,
        "warnings": warnings,
        "institutional_flows_by_name": five_day.get("institutional_flows_by_name"),
        "institutional_total_net_buy_sell": five_day.get(
            "institutional_total_net_buy_sell"
        ),
    }


# Trading rows per window: ~20 trading days per calendar month.
EGG_WINDOWS = {
    "1m": 20,
    "3m": 60,
    "6m": 120,
}


def average(values):
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


def latest_issued_shares(shareholding_rows):
    dated_rows = [
        row
        for row in shareholding_rows
        if row.get("date") and to_float(row.get("NumberOfSharesIssued"))
    ]
    if not dated_rows:
        return None
    latest = sorted(dated_rows, key=lambda row: row.get("date", ""))[-1]
    return to_float(latest.get("NumberOfSharesIssued"))


def turnover_pct(row, issued_shares=None):
    volume = to_float(row.get("Trading_Volume"))
    if volume is not None and issued_shares not in (None, 0):
        return volume / issued_shares * 100
    # Trading_turnover is a transaction count, not a percentage; without issued
    # shares there is no valid turnover ratio.
    return None


def classify_turnover(avg_turnover):
    if avg_turnover is None:
        return "unknown"
    if avg_turnover >= 0.8:
        return "active"
    if avg_turnover <= 0.3:
        return "low"
    return "normal"


def default_tdcc_data_path(stock_id, repo_root=None):
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    companies_dir = root / "companies"
    case_dirs = sorted(p for p in companies_dir.glob(f"{stock_id}-*") if p.is_dir())

    if len(case_dirs) == 1:
        return case_dirs[0] / "tdcc-data.json"

    return root / f"{stock_id}_tdcc_data.json"


def load_tdcc_holding_distribution(stock_id, repo_root=None):
    path = default_tdcc_data_path(stock_id, repo_root=repo_root)
    if not path.exists():
        return [], f"{path.name} not found; run scripts/fetch_tdcc.py {stock_id}"

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    # Newer tdcc-data.json accumulates weekly snapshots under history; flatten
    # them so multi-date holder trends become possible. Older files only have
    # the single latest snapshot.
    history = payload.get("history") or []
    rows = [row for entry in history for row in entry.get("rows", [])]
    if rows:
        return rows, None

    rows = payload.get("raw", {}).get("holding_distribution", [])
    return rows, None


def holding_totals_by_date(rows):
    totals = {}
    for row in rows:
        row_date = row.get("date")
        if not row_date:
            continue
        totals[row_date] = totals.get(row_date, 0.0) + (to_float(row.get("people")) or 0.0)
    return totals


def holder_state_for_window(holding_shares_per_rows, start_date, end_date):
    rows = [
        row
        for row in holding_shares_per_rows
        if start_date <= row.get("date", "") <= end_date
    ]
    totals = holding_totals_by_date(rows)
    dates = sorted(date_key for date_key, total in totals.items() if total > 0)

    if len(dates) < 2:
        return {
            "holder_count_state": "unknown",
            "holder_change_pct": None,
            "has_holder_data": False,
        }

    first_total = totals[dates[0]]
    latest_total = totals[dates[-1]]
    holder_change_pct = pct_change(latest_total, first_total)

    if holder_change_pct is None:
        holder_count_state = "unknown"
    elif holder_change_pct <= -5:
        holder_count_state = "decreasing"
    elif holder_change_pct >= 5:
        holder_count_state = "increasing"
    else:
        holder_count_state = "flat"

    return {
        "holder_count_state": holder_count_state,
        "holder_change_pct": round(holder_change_pct, 2)
        if holder_change_pct is not None
        else None,
        "has_holder_data": True,
    }


def tdcc_holder_snapshot(rows):
    if not rows:
        return {
            "holder_count_state": "unknown",
            "holder_total_count": None,
            "large_holder_percent": None,
            "retail_holder_percent": None,
            "has_holder_snapshot": False,
        }

    latest_date = max(row.get("date", "") for row in rows)
    latest_rows = [row for row in rows if row.get("date") == latest_date]
    total_row = next(
        (row for row in latest_rows if str(row.get("HoldingSharesLevel")) == "17"),
        None,
    )
    large_holder_percent = sum(
        to_float(row.get("percent")) or 0.0
        for row in latest_rows
        if str(row.get("HoldingSharesLevel")) in {"12", "13", "14", "15"}
    )
    retail_holder_percent = sum(
        to_float(row.get("percent")) or 0.0
        for row in latest_rows
        if str(row.get("HoldingSharesLevel")) in {"1", "2", "3"}
    )

    return {
        "holder_count_state": "snapshot_only",
        "holder_total_count": int(total_row.get("people"))
        if total_row and total_row.get("people") is not None
        else None,
        "large_holder_percent": round(large_holder_percent, 2),
        "retail_holder_percent": round(retail_holder_percent, 2),
        "has_holder_snapshot": True,
    }


def classify_egg_stage(price_change_pct, turnover_state, holder_count_state):
    price_structure = "A" if (price_change_pct or 0) >= 0 else "B"

    if price_structure == "A":
        if turnover_state == "low" and holder_count_state == "decreasing":
            return "A1", "supply_demand_favorable"
        if turnover_state == "active" and holder_count_state == "increasing":
            return "A3", "supply_demand_risk"
        return "A2", "wait_for_confirmation"

    if turnover_state == "low" and holder_count_state == "decreasing":
        return "B1", "supply_demand_risk"
    if turnover_state == "active" and holder_count_state == "decreasing":
        return "B3", "supply_demand_favorable"
    return "B2", "wait_for_confirmation"


def build_egg_window_read(
    label,
    sorted_price,
    holding_shares_per_rows=None,
    shareholding_rows=None,
    tdcc_holding_distribution_rows=None,
):
    required_rows = EGG_WINDOWS[label]
    if len(sorted_price) < required_rows:
        return {
            "window": label,
            "status": "insufficient_data",
            "stage": None,
            "signal": "wait_for_confirmation",
            "confidence": "low",
            "warnings": [f"Need at least {required_rows} trading rows"],
        }

    window_price = sorted_price[-required_rows:]
    latest = window_price[-1]
    comparison = window_price[0]
    latest_close = to_float(latest.get("close"))
    comparison_close = to_float(comparison.get("close"))
    price_change_pct = pct_change(latest_close, comparison_close)
    issued_shares = latest_issued_shares(shareholding_rows or [])
    avg_turnover = average(turnover_pct(row, issued_shares) for row in window_price)
    turnover_state = classify_turnover(avg_turnover)
    holder_read = holder_state_for_window(
        holding_shares_per_rows or [],
        comparison.get("date", ""),
        latest.get("date", ""),
    )
    holder_snapshot = tdcc_holder_snapshot(tdcc_holding_distribution_rows or [])
    # Level "17" is the TDCC all-holders total row, so per-date level-17 people
    # counts form a weekly holder-count series when snapshots are accumulated.
    tdcc_level17_rows = [
        row
        for row in (tdcc_holding_distribution_rows or [])
        if str(row.get("HoldingSharesLevel")) == "17"
    ]
    warnings = []

    if avg_turnover is None:
        warnings.append("turnover_data_missing")

    if holder_read["has_holder_data"]:
        confidence = "high"
    else:
        tdcc_trend = holder_state_for_window(
            tdcc_level17_rows,
            comparison.get("date", ""),
            latest.get("date", ""),
        )
        if tdcc_trend["has_holder_data"]:
            confidence = "medium"
            holder_read = tdcc_trend
            warnings.append("holder_trend_from_tdcc_weekly")
        elif holder_snapshot["has_holder_snapshot"]:
            confidence = "medium"
            holder_read = {
                "holder_count_state": holder_snapshot["holder_count_state"],
                "holder_change_pct": None,
                "has_holder_data": False,
            }
            warnings.append("holder_trend_insufficient")
        else:
            confidence = "medium"
            warnings.append("holder_data_missing")

    stage, signal = classify_egg_stage(
        price_change_pct,
        turnover_state,
        holder_read["holder_count_state"],
    )

    return {
        "window": label,
        "status": "ready",
        "stage": stage,
        "signal": signal,
        "confidence": confidence,
        "latest_date": latest.get("date"),
        "comparison_date": comparison.get("date"),
        "price_change_pct": round(price_change_pct, 2)
        if price_change_pct is not None
        else None,
        "average_turnover": round(avg_turnover, 4)
        if avg_turnover is not None
        else None,
        "turnover_state": turnover_state,
        "holder_count_state": holder_read["holder_count_state"],
        "holder_change_pct": holder_read["holder_change_pct"],
        "holder_total_count": holder_snapshot["holder_total_count"],
        "large_holder_percent": holder_snapshot["large_holder_percent"],
        "retail_holder_percent": holder_snapshot["retail_holder_percent"],
        "warnings": warnings,
    }


def build_egg_theory_read(
    price_rows,
    holding_shares_per_rows=None,
    shareholding_rows=None,
    tdcc_holding_distribution_rows=None,
):
    sorted_price = sorted(price_rows, key=lambda row: row.get("date", ""))
    return {
        "method": "egg_theory_v1",
        "windows": {
            label: build_egg_window_read(
                label,
                sorted_price,
                holding_shares_per_rows=holding_shares_per_rows,
                shareholding_rows=shareholding_rows,
                tdcc_holding_distribution_rows=tdcc_holding_distribution_rows,
            )
            for label in ("1m", "3m", "6m")
        },
    }


def build_metadata(
    stock_id,
    start_date,
    end_date,
    raw_rows_by_dataset,
    warnings,
    tdcc_holding_distribution_rows=None,
):
    source_urls = {
        dataset: (
            f"{BASE_URL}?dataset={dataset}&data_id={stock_id}"
            f"&start_date={start_date}&end_date={end_date}"
        )
        for dataset in DATASETS
    }
    row_counts = {
        dataset: len(raw_rows_by_dataset.get(dataset, []))
        for dataset in DATASETS
    }
    row_counts["TDCCHoldingDistributionSnapshot"] = len(
        tdcc_holding_distribution_rows or []
    )

    return {
        "fetched_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "source": "FinMind",
        "source_urls": source_urls,
        "datasets": list(DATASETS),
        "date_range": {"start_date": start_date, "end_date": end_date},
        "row_counts": row_counts,
        "warnings": warnings,
    }


def fetch_all(stock_id, start_date, end_date, token=None):
    import requests

    raw_rows_by_dataset = {}
    warnings = []

    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=len(DATASETS)) as executor:
            futures = {
                dataset: executor.submit(
                    fetch_dataset_safely,
                    dataset,
                    stock_id,
                    start_date,
                    end_date,
                    token=token,
                    session=session,
                )
                for dataset in DATASETS
            }
            for dataset in DATASETS:
                rows, warning = futures[dataset].result()
                raw_rows_by_dataset[dataset] = rows
                if warning:
                    warnings.append(warning)

    price_rows = raw_rows_by_dataset["TaiwanStockPrice"]
    institutional_rows = raw_rows_by_dataset[
        "TaiwanStockInstitutionalInvestorsBuySell"
    ]

    for dataset, rows in raw_rows_by_dataset.items():
        if not rows:
            warnings.append(f"{dataset} returned no rows")

    tdcc_holding_distribution_rows, tdcc_warning = load_tdcc_holding_distribution(
        stock_id
    )
    if tdcc_warning:
        warnings.append(tdcc_warning)

    market_action_read = build_market_action_read(price_rows, institutional_rows)
    egg_theory_read = build_egg_theory_read(
        price_rows,
        holding_shares_per_rows=raw_rows_by_dataset["TaiwanStockHoldingSharesPer"],
        shareholding_rows=raw_rows_by_dataset["TaiwanStockShareholding"],
        tdcc_holding_distribution_rows=tdcc_holding_distribution_rows,
    )
    warnings.extend(market_action_read.get("warnings", []))

    return {
        "stock_id": stock_id,
        "metadata": build_metadata(
            stock_id,
            start_date,
            end_date,
            raw_rows_by_dataset,
            warnings,
            tdcc_holding_distribution_rows=tdcc_holding_distribution_rows,
        ),
        "raw": {
            **{
                raw_key: raw_rows_by_dataset[dataset]
                for dataset, raw_key in RAW_DATASET_KEYS.items()
            },
            "tdcc_holding_distribution": tdcc_holding_distribution_rows,
        },
        "derived": {
            "market_action_read": market_action_read,
            "egg_theory_read": egg_theory_read,
        },
    }


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    end_date = args.end_date
    start_date = args.start_date

    if not start_date:
        start_date, computed_end = default_date_range(args.days, end_date=end_date)
        end_date = end_date or computed_end
    elif not end_date:
        end_date = date.today().isoformat()

    token = resolve_token(args.token)
    output_path = (
        Path(args.output) if args.output else default_output_path(args.stock_id)
    )
    data = fetch_all(args.stock_id, start_date, end_date, token=token)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"FinMind market data saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
