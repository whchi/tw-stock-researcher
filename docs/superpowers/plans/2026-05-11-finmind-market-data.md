# FinMind Market Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/fetch_finmind.py` so it fetches FinMind price and institutional investor data and writes `market-data.json` for market-action analysis.

**Architecture:** Keep this as a focused standalone script, mirroring `scripts/fetch_goodinfo.py` for case-directory auto-detection and JSON output. Separate pure derivation functions from network I/O so tests can cover market-read logic without calling FinMind.

**Tech Stack:** Python standard library, `requests`, `unittest`.

---

## File Structure

- Create: `tests/test_fetch_finmind.py` for unit tests covering output path, derived market metrics, institutional net flow, and insufficient-data behavior.
- Modify: `scripts/fetch_finmind.py` for CLI parsing, FinMind API fetching, output path selection, metadata, raw data persistence, and derived metrics.
- No commits should be made unless the user explicitly requests them, even though this plan is task-based.

### Task 1: Add Unit Tests For Pure Behavior

**Files:**
- Create: `tests/test_fetch_finmind.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fetch_finmind.py`:

```python
import tempfile
import unittest
from pathlib import Path

from scripts.fetch_finmind import (
    build_market_action_read,
    default_output_path,
    summarize_institutional_flows,
)


PRICE_ROWS = [
    {"date": "2026-04-27", "stock_id": "2330", "Trading_Volume": 1000, "close": 100.0},
    {"date": "2026-04-28", "stock_id": "2330", "Trading_Volume": 1100, "close": 101.0},
    {"date": "2026-04-29", "stock_id": "2330", "Trading_Volume": 1200, "close": 102.0},
    {"date": "2026-04-30", "stock_id": "2330", "Trading_Volume": 1300, "close": 103.0},
    {"date": "2026-05-04", "stock_id": "2330", "Trading_Volume": 1400, "close": 104.0},
    {"date": "2026-05-05", "stock_id": "2330", "Trading_Volume": 2000, "close": 110.0},
]


INSTITUTIONAL_ROWS = [
    {"date": "2026-05-05", "stock_id": "2330", "name": "Foreign_Investor", "buy": 5000, "sell": 3000},
    {"date": "2026-05-05", "stock_id": "2330", "name": "Investment_Trust", "buy": 1000, "sell": 1200},
    {"date": "2026-05-05", "stock_id": "2330", "name": "Dealer", "buy": 700, "sell": 400},
]


class OutputPathTests(unittest.TestCase):
    def test_default_output_path_uses_unique_case_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies" / "2330-tsmc").mkdir(parents=True)

            output_path = default_output_path("2330", repo_root=repo_root)

            self.assertEqual(output_path, repo_root / "companies" / "2330-tsmc" / "market-data.json")

    def test_default_output_path_falls_back_to_repo_root_without_unique_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "companies").mkdir()

            output_path = default_output_path("2330", repo_root=repo_root)

            self.assertEqual(output_path, repo_root / "2330_market_data.json")


class MarketActionReadTests(unittest.TestCase):
    def test_build_market_action_read_calculates_5d_price_volume_and_state(self):
        result = build_market_action_read(PRICE_ROWS, INSTITUTIONAL_ROWS)

        self.assertEqual(result["latest_date"], "2026-05-05")
        self.assertEqual(result["comparison_date"], "2026-04-27")
        self.assertAlmostEqual(result["price_5d_change_pct"], 10.0)
        self.assertAlmostEqual(result["volume_5d_change_pct"], 100.0)
        self.assertEqual(result["price_volume_read"], "price_up_volume_up")
        self.assertEqual(result["market_state"], "overheated")
        self.assertEqual(result["institutional_total_net_buy_sell"], 2100.0)

    def test_build_market_action_read_marks_insufficient_price_data(self):
        result = build_market_action_read(PRICE_ROWS[:2], INSTITUTIONAL_ROWS)

        self.assertEqual(result["market_state"], "insufficient_data")
        self.assertIn("Need at least 6 trading rows", result["warnings"])

    def test_summarize_institutional_flows_groups_by_name(self):
        result = summarize_institutional_flows(INSTITUTIONAL_ROWS)

        self.assertEqual(result["by_name"]["Foreign_Investor"]["net_buy_sell"], 2000.0)
        self.assertEqual(result["by_name"]["Investment_Trust"]["net_buy_sell"], -200.0)
        self.assertEqual(result["total_net_buy_sell"], 2100.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests/test_fetch_finmind.py -v`

Expected: FAIL or ERROR because `build_market_action_read`, `default_output_path`, and `summarize_institutional_flows` are not implemented in `scripts/fetch_finmind.py`.

### Task 2: Implement Fetcher And Derived Market Read

**Files:**
- Modify: `scripts/fetch_finmind.py`

- [ ] **Step 1: Replace the placeholder script with implementation**

Implement these concrete units in `scripts/fetch_finmind.py`:

```python
#!/usr/bin/env python3
"""Fetch FinMind price and institutional investor data for market-action analysis."""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

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
    parser.add_argument("--days", type=int, default=30)
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


def fetch_dataset(dataset, stock_id, start_date, end_date, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
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
        raise RuntimeError(f"FinMind returned non-JSON response for {dataset}: HTTP {response.status_code}") from exc
    if response.status_code != 200 or payload.get("status") != 200:
        msg = payload.get("msg", "unknown error")
        raise RuntimeError(f"FinMind request failed for {dataset}: HTTP {response.status_code}, status={payload.get('status')}, msg={msg}")
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
        entry = by_name.setdefault(name, {"buy": 0.0, "sell": 0.0, "net_buy_sell": 0.0})
        entry["buy"] += buy
        entry["sell"] += sell
        entry["net_buy_sell"] += buy - sell
        total += buy - sell
    return {"by_name": by_name, "total_net_buy_sell": total}


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


def build_market_action_read(price_rows, institutional_rows):
    warnings = []
    sorted_price = sorted(price_rows, key=lambda row: row.get("date", ""))
    institutional_summary = summarize_institutional_flows(institutional_rows)
    if len(sorted_price) < 6:
        warnings.append("Need at least 6 trading rows to compute a 5D market-action read")
        return {
            "latest_date": sorted_price[-1].get("date") if sorted_price else None,
            "comparison_date": None,
            "market_state": "insufficient_data",
            "price_volume_read": "insufficient_data",
            "warnings": warnings,
            "institutional_flows_by_name": institutional_summary["by_name"],
            "institutional_total_net_buy_sell": institutional_summary["total_net_buy_sell"],
        }

    latest = sorted_price[-1]
    comparison = sorted_price[-6]
    latest_close = to_float(latest.get("close"))
    comparison_close = to_float(comparison.get("close"))
    latest_volume = to_float(latest.get("Trading_Volume"))
    comparison_volume = to_float(comparison.get("Trading_Volume"))
    price_change = pct_change(latest_close, comparison_close)
    volume_change = pct_change(latest_volume, comparison_volume)
    price_dir = direction(price_change)
    volume_dir = direction(volume_change, threshold=10.0)
    state = classify_market_state(price_change, volume_change)

    return {
        "latest_date": latest.get("date"),
        "comparison_date": comparison.get("date"),
        "latest_close": latest_close,
        "comparison_close": comparison_close,
        "latest_volume": latest_volume,
        "comparison_volume": comparison_volume,
        "price_5d_change_pct": round(price_change, 2) if price_change is not None else None,
        "volume_5d_change_pct": round(volume_change, 2) if volume_change is not None else None,
        "price_volume_read": f"price_{price_dir}_volume_{volume_dir}",
        "market_state": state,
        "warnings": warnings,
        "institutional_flows_by_name": institutional_summary["by_name"],
        "institutional_total_net_buy_sell": institutional_summary["total_net_buy_sell"],
    }


def build_metadata(stock_id, start_date, end_date, price_rows, institutional_rows, warnings):
    return {
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": "FinMind",
        "source_urls": {
            dataset: f"{BASE_URL}?dataset={dataset}&data_id={stock_id}&start_date={start_date}&end_date={end_date}"
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
    price_rows = fetch_dataset("TaiwanStockPrice", stock_id, start_date, end_date, token=token)
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
        "metadata": build_metadata(stock_id, start_date, end_date, price_rows, institutional_rows, warnings),
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
    token = args.token or os.environ.get("FINMIND_TOKEN")
    output_path = Path(args.output) if args.output else default_output_path(args.stock_id)
    data = fetch_all(args.stock_id, start_date, end_date, token=token)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"FinMind market data saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m unittest tests/test_fetch_finmind.py -v`

Expected: PASS for all tests.

### Task 3: Verify CLI Behavior Without Live API Dependency

**Files:**
- Modify if needed: `scripts/fetch_finmind.py`

- [ ] **Step 1: Run import and CLI help checks**

Run: `python -m py_compile scripts/fetch_finmind.py tests/test_fetch_finmind.py`

Expected: no output and exit code 0.

Run: `python scripts/fetch_finmind.py --help`

Expected: usage text includes `stock_id`, `--start-date`, `--end-date`, `--days`, `--token`, and `--output`.

- [ ] **Step 2: Run the existing fetch_goodinfo tests**

Run: `python -m unittest tests/test_fetch_goodinfo.py -v`

Expected: PASS, confirming the new script did not break existing tested behavior.

- [ ] **Step 3: Check git diff manually**

Run: `git diff -- scripts/fetch_finmind.py tests/test_fetch_finmind.py docs/superpowers/specs/2026-05-11-finmind-market-data-design.md docs/superpowers/plans/2026-05-11-finmind-market-data.md`

Expected: diff only contains the FinMind fetcher, tests, spec, and plan changes.
