# Market Action Read Integration Design

## Goal

Make FinMind market data a first-class research layer by adding a neutral `market-action-read.md` view and expanding `market-data.json` derived metrics to compare 1D, 3D, and 5D price, volume, and institutional investor flows.

## Scope

- Add `market-action-read.md` to the case-file architecture.
- Add a reusable template for market-action reads.
- Add `market_action_read` to `stock-meta.json` file references.
- Update data-layout documentation and structure tests.
- Enhance `scripts/fetch_finmind.py` derived output with 1D, 3D, and 5D windows.
- Create `companies/6706-whit/market-action-read.md` from the already-fetched `market-data.json`.
- Update `companies/6706-whit/stock-meta.json` to reference the new file.

## Output Semantics

`market-action-read.md` is a research view, not a trading-decision view. It should describe current market state, price-volume confirmation or divergence, institutional flow, watch conditions, and next validation events.

The file must not include buy/sell recommendations, target prices, stop-loss instructions, or position-sizing guidance.

## Derived JSON Shape

`derived.market_action_read.windows` will include `1d`, `3d`, and `5d`. Each window will contain:

- `latest_date`
- `comparison_date`
- `latest_close`
- `comparison_close`
- `price_change`
- `price_change_pct`
- `latest_volume`
- `comparison_volume`
- `volume_change`
- `volume_change_pct`
- `price_volume_read`
- `institutional_total_net_buy_sell`
- `institutional_flows_by_name`

The existing top-level 5D fields will remain for compatibility where reasonable, but new analysis should prefer `windows`.

## 6706 Case Read

The 6706 read will use the existing `companies/6706-whit/market-data.json`. It will summarize the latest available trading date, compare 1D/3D/5D changes, list institutional flows by type, and state what would strengthen or weaken the thesis in neutral research language.

## Verification

- Add unit tests for 1D/3D/5D window calculations and institutional flow by window.
- Run all Python unit tests.
- Run template structure checks.
- Verify the 6706 markdown uses no recommendation language.
