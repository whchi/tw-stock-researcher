# FinMind Market Data Fetcher Design

## Goal

Implement `scripts/fetch_finmind.py` to fetch FinMind market data for one Taiwan stock and persist it as a reusable market-action dataset for later volume/price relationship analysis.

## Scope

- Fetch `TaiwanStockPrice` for daily OHLCV data.
- Fetch `TaiwanStockInstitutionalInvestorsBuySell` for institutional buy/sell data.
- Write output to `companies/<stock_id>-*/market-data.json` when exactly one matching case directory exists.
- Fall back to `<stock_id>_market_data.json` in the repo root when no unique case directory exists.
- Include raw API rows plus conservative derived metrics for market-action reading.
- Avoid any buy/sell recommendation, target price, stop-loss, or position-sizing language.

## Command Interface

```bash
python scripts/fetch_finmind.py <stock_id> [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--days N] [--token TOKEN] [--output PATH]
```

Defaults:

- `stock_id`: required positional argument.
- `--days`: 30 calendar days when no explicit `--start-date` is supplied.
- `--end-date`: today in local date when omitted.
- `--token`: optional; if omitted, use `FINMIND_TOKEN` from the environment when present.

## Output Shape

`market-data.json` will contain:

- `stock_id`
- `metadata`: source, fetched timestamp, date range, dataset names, FinMind URLs, and warning messages.
- `raw.price`: rows from `TaiwanStockPrice`.
- `raw.institutional_investors`: rows from `TaiwanStockInstitutionalInvestorsBuySell`.
- `derived.market_action_read`: 5-trading-day price/volume state, rule-based price-volume read, institutional net buy/sell summaries, and watch-condition style flags.

## Derived Metrics

The script will compute from the latest available trading rows:

- 5-trading-day close price change percentage.
- 5-trading-day trading volume change percentage.
- Latest close, latest volume, prior comparison close, and prior comparison volume.
- Price-volume label: price up/down/flat and volume up/down/flat.
- Market state labels: bullish, neutral, bearish, overheated, failed breakout, pullback, or insufficient data.
- Institutional net flow by investor `name`: `buy - sell`, plus aggregate net flow.

The labels are descriptive research signals only. They do not produce trading instructions.

## Error Handling

- Raise a clear error when FinMind returns a non-200 HTTP status or non-success payload.
- Preserve API messages in errors where available.
- Continue writing output when one dataset is empty, but include warnings in metadata and mark derived metrics as insufficient where needed.
- Validate required columns before deriving metrics.

## Testing

- Add unit tests for derived metric calculation and default output path behavior.
- Use local fixture-like rows rather than live FinMind API calls.
- Keep network fetching small and dependency-light by using `requests` only.
