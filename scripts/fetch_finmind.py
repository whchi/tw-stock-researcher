#!/usr/bin/env python3
"""Fetch FinMind price and institutional investor data for market-action analysis."""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE_URL = "https://api.finmindtrade.com/api/v4/data"
DATASETS = (
    "TaiwanStockPrice",
    "TaiwanStockInstitutionalInvestorsBuySell",
)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--days", type=int, default=7)
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


def fetch_dataset(dataset, stock_id, start_date, end_date, token=None):
    import requests

    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    response = requests.get(BASE_URL, headers=headers, params=params, timeout=30)

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


def build_metadata(
    stock_id, start_date, end_date, price_rows, institutional_rows, warnings
):
    return {
        "fetched_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "source": "FinMind",
        "source_urls": {
            dataset: (
                f"{BASE_URL}?dataset={dataset}&data_id={stock_id}"
                f"&start_date={start_date}&end_date={end_date}"
            )
            for dataset in DATASETS
        },
        "datasets": list(DATASETS),
        "date_range": {"start_date": start_date, "end_date": end_date},
        "row_counts": {
            "TaiwanStockPrice": len(price_rows),
            "TaiwanStockInstitutionalInvestorsBuySell": len(institutional_rows),
        },
        "warnings": warnings,
    }


def fetch_all(stock_id, start_date, end_date, token=None):
    price_rows = fetch_dataset(
        "TaiwanStockPrice",
        stock_id,
        start_date,
        end_date,
        token=token,
    )
    institutional_rows = fetch_dataset(
        "TaiwanStockInstitutionalInvestorsBuySell",
        stock_id,
        start_date,
        end_date,
        token=token,
    )
    warnings = []

    if not price_rows:
        warnings.append("TaiwanStockPrice returned no rows")
    if not institutional_rows:
        warnings.append("TaiwanStockInstitutionalInvestorsBuySell returned no rows")

    derived = build_market_action_read(price_rows, institutional_rows)
    warnings.extend(derived.get("warnings", []))

    return {
        "stock_id": stock_id,
        "metadata": build_metadata(
            stock_id,
            start_date,
            end_date,
            price_rows,
            institutional_rows,
            warnings,
        ),
        "raw": {
            "price": price_rows,
            "institutional_investors": institutional_rows,
        },
        "derived": {"market_action_read": derived},
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
