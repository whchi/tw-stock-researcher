# Shared Macro View

## Included Indicators

Use this file only for reusable cross-case macro context. Keep company-specific transmission analysis in each case's `macro-map.md`.

| Indicator | Primary Source | What It Captures | Reusable For |
| --- | --- | --- | --- |
| TAIEX / market PE ratio | TWSE Open API / Yahoo Finance | Market valuation regime and sentiment | All Taiwan listed stocks |
| USD/TWD exchange rate | Yahoo Finance / CBC | Export competitiveness and translation effect | Exporters, import-cost-sensitive companies |
| Crude oil / commodity prices | Yahoo Finance / market data | Input, logistics and energy-cost pressure | Manufacturing, transport, chemicals |
| Taiwan export orders | MOEA / Taiwan official statistics | External-demand cycle for Taiwan exports | Export-driven, electronics supply-chain |
| Taiwan industrial production | MOEA / DGBAS | Domestic production cycle | Manufacturers, foundry-dependent companies |
| Taiwan trade statistics | MOF / MOPS context | Trade balance, import trends | Exporters, raw-material importers |

## Current Read

| Indicator | Latest Read / Trend | Source Link | Confidence | Notes |
| --- | --- | --- | --- | --- |

## Watch Items

| Indicator | Watch Trigger | Why It Matters | Affected Case Types |
| --- | --- | --- | --- |

## Sources

- TWSE Open API: TAIEX, PE ratio, market turnover. https://openapi.twse.com.tw/
- Yahoo Finance: USD/TWD, TAIEX (^TWII), crude oil (CL=F), copper (HG=F), gold (GC=F).
- MOEA (經濟部統計處): export orders (外銷訂單), industrial production (工業生產指數). Set TAIWAN_MACRO_URL to a known stable CSV/JSON endpoint.
- DGBAS (主計總處): GDP, CPI, national accounts. https://www.dgbas.gov.tw/
- MOF (財政部): trade statistics. https://portal.sw.nat.gov.tw/ — verified open-data CSV (monthly customs exports/imports, data.gov.tw dataset 6053, `fetch_macro.py` default): https://opendata.customs.gov.tw/data/6053/csv.csv
- CBC (中央銀行): interest rates, money supply, FX reserves. https://www.cbc.gov.tw/
- MOPS context: company-level filings and industry-specific context from public filing platform.
