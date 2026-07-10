# Market Action Read

> 免責聲明：本文件僅供研究參考，不構成投資建議、買賣推薦或任何形式之邀約。本文只整理市場定價、量價、法人籌碼與後續驗證條件，不產生交易指令。

## Current Market Read

- Confirmation: Confirming / Diverging / Overextended / Insufficient data
- Confidence: Low / Medium / High
- Reason:
- Latest data date:

## Price / Volume Windows

| Window | Comparison Date | Close Change | Close Change % | Volume Change | Volume Change % | Price-Volume Read |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1D |  |  |  |  |  |  |
| 3D |  |  |  |  |  |  |
| 5D |  |  |  |  |  |  |

## Institutional Flow Windows

| Window | Foreign Investor | Investment Trust | Dealer Self | Dealer Hedging | Total Net Buy/Sell | Read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1D |  |  |  |  |  |  |
| 3D |  |  |  |  |  |  |
| 5D |  |  |  |  |  |  |

## Derived Market Confirmation Metrics

Read directly from `market-data.json` → `derived.market_confirmation_metrics`; do not recompute days-to-cover from raw price/margin rows here. Each metric carries its own `state` (`ready` / `unavailable` / `not_meaningful`) — show the caveat when it is not `ready` instead of a blank or fabricated value.

| Metric | Current Read | State / Caveat |
| --- | --- | --- |
| Days to cover (short balance / median 20D volume) |  |  |

## Holder Distribution Snapshot

| Source Date | Total Holders | Retail Holder % | Large Holder % | Holder Data State | Read |
| --- | ---: | ---: | ---: | --- | --- |
|  |  |  |  | snapshot_only / trend_available / missing |  |

## Egg Theory Read

| Horizon | Stage | Research Label | Confidence | Holder Data Caveat | Read |
| --- | --- | --- | --- | --- | --- |
| 1M | A1 / A2 / A3 / B1 / B2 / B3 / insufficient data | supply_demand_favorable / wait_for_confirmation / supply_demand_risk / holder_data_missing | low / medium / high |  |  |
| 3M | A1 / A2 / A3 / B1 / B2 / B3 / insufficient data | supply_demand_favorable / wait_for_confirmation / supply_demand_risk / holder_data_missing | low / medium / high |  |  |
| 6M | A1 / A2 / A3 / B1 / B2 / B3 / insufficient data | supply_demand_favorable / wait_for_confirmation / supply_demand_risk / holder_data_missing | low / medium / high |  |  |

## Market Interpretation

- Is the market confirming the thesis:
- Is the move stock-specific or theme-driven:
- Is the move early, middle, late, or exhausted:
- Price-in / overextension risk:

## Watch Conditions

- What would strengthen the thesis:
- What would weaken the thesis:
- What would suggest overpricing:
- What would suggest the setup failed:

## Next Validation

- Next event:
- Next monthly revenue:
- Next earnings report:
- Next price-volume check:

## Sources

- `market-data.json`
- `tdcc-data.json` when present
- FinMind datasets: `TaiwanStockPrice`, `TaiwanStockInstitutionalInvestorsBuySell`, `TaiwanStockMarginPurchaseShortSale`, `TaiwanStockShareholding`, `TaiwanStockDayTrading`, `TaiwanStockHoldingSharesPer` when available
- TDCC OpenData dataset `id=1-5` when `tdcc-data.json` is present
