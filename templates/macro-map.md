# Macro Map

## Market Regime

## Market Regime Link

- Current regime:
- Why the regime matters for this company:
- Transmission into revenue / margin / cash flow / valuation multiple:
- What would make the regime irrelevant to this case:

## Candidate Variables

Use public/free macro sources first. Record the source, latest observed value or trend, transmission path, and whether the variable is included or excluded.

| Variable | Source | Latest Read / Trend | Transmission Path To This Company | Include? | Reason |
| --- | --- | --- | --- | --- | --- |
| TAIEX / market PE ratio | TWSE Open API / Yahoo Finance |  | Market valuation backdrop, liquidity regime |  |  |
| USD/TWD exchange rate | Yahoo Finance / CBC |  | Export revenue translation, import cost, foreign-investor flow |  |  |
| Crude oil / commodity prices | Yahoo Finance / market data |  | Manufacturing input cost, logistics cost, end-demand proxy |  |  |
| Taiwan export orders | MOEA / Taiwan official statistics |  | Sector demand, backlog, order visibility |  |  |
| Taiwan industrial production | MOEA / DGBAS |  | Capacity utilization, factory activity, foundry loading |  |  |
| Taiwan GDP / CPI | DGBAS |  | Domestic demand, inflation pass-through, policy rate direction |  |  |
| Taiwan interest rates / money supply | CBC |  | Financing cost, liquidity, valuation multiple |  |  |

## Included Variables

Only include variables with a concrete and material transmission path into revenue, margin, cash flow, valuation multiple, or market narrative.

| Variable | Why It Matters | Directional Impact | Evidence | Monitoring Cadence | Thesis Link |
| --- | --- | --- | --- | --- | --- |

## Excluded Variables

Exclude broad macro variables that sound relevant but do not materially transmit into this specific case. State why they are excluded so future sessions do not re-add them by habit.

| Variable | Why Excluded | Reconsider If |
| --- | --- | --- |

## Macro Data Source Checklist

- TWSE Open API: TAIEX, PE ratio, market turnover. https://openapi.twse.com.tw/
- Yahoo Finance: USD/TWD, TAIEX (^TWII), crude oil (CL=F), copper (HG=F), gold (GC=F).
- MOEA (經濟部統計處): export orders (外銷訂單), industrial production (工業生產指數). Set TAIWAN_MACRO_URL to a known stable CSV/JSON endpoint.
- DGBAS (主計總處): GDP, CPI, national accounts. https://www.dgbas.gov.tw/
- MOF (財政部): trade statistics. https://portal.sw.nat.gov.tw/
- CBC (中央銀行): interest rates, money supply, FX reserves. https://www.cbc.gov.tw/
- MOPS context: company-level filings and industry-specific context from public filing platform.

## Monitoring Cadence

| Variable | Frequency | Update Trigger | Source Link |
| --- | --- | --- | --- |

## Facts

## Inferences

## Open Questions

## Sources
