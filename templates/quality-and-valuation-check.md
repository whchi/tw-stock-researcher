# Quality And Valuation Check

> 免責聲明：本文件僅供研究參考，不構成投資建議、買賣推薦或任何形式之邀約。所有估值內容均為情境推估與市場預期反推，不得視為目標價或交易指令。

## Current Quality View

## Business Quality

| Metric | Current Read | Multi-Year Trend | What It Says | Evidence Quality |
| --- | --- | --- | --- | --- |
| ROIC |  |  | Capital efficiency and moat quality |  |
| Incremental ROIC |  |  | Whether new capital creates value |  |
| Gross margin stability |  |  | Pricing power and product mix resilience |  |
| Operating margin stability |  |  | Cost control and operating leverage |  |

## Owner Earnings And Cash Conversion

Owner Earnings and Cash Conversion values must come from `fundamentals-data.json` → `derived.financial_quality_metrics` (also shown in `financial-analysis.md` → Derived Financial Quality Metrics); do not recompute here. Carry the metric's `state` forward — if `unavailable` or `not_meaningful`, write the caveat instead of a number.

| Metric | Current Read | Trend | Why It Matters | State / Caveat |
| --- | --- | --- | --- | --- |
| Owner Earnings |  |  | Cash available after maintenance reinvestment |  |
| Cash Conversion (FCF / net income) |  |  | Cash conversion |  |
| Capex / revenue |  |  | Capital intensity |  |

## Working Capital Quality Judgment

DSO / DIO / DPO / Cash Conversion Cycle values must come from `fundamentals-data.json` → `derived.financial_quality_metrics`; do not recompute here. Carry the metric's `state` forward — if `unavailable` or `not_meaningful`, write the caveat instead of a number.

| Metric | Current Read | Trend | Risk Signal | State / Caveat |
| --- | --- | --- | --- | --- |
| Days sales outstanding |  |  | Receivables rising faster than sales |  |
| Inventory days |  |  | Inventory build without revenue validation |  |
| Days payable outstanding |  |  | Supplier financing dependence |  |
| Cash conversion cycle |  |  | Cash tied up in operations |  |

## Capital Allocation

| Item | Current Read | Value-Creation Read | Evidence Needed |
| --- | --- | --- | --- |
| Dividends |  |  |  |
| Share buybacks / treasury shares |  |  |  |
| Cash capital increase / dilution |  |  |  |
| Major capex |  |  |  |
| M&A / investments |  |  |  |

## Governance And Ownership

| Item | Current Read | Why It Matters | Source |
| --- | --- | --- | --- |
| Directors and supervisors shareholding |  | Alignment with shareholders |  |
| Pledged share ratio |  | Forced-selling or governance risk |  |
| Insider transfers |  | Signal quality and alignment |  |
| TDCC ownership distribution |  | Concentration / dispersion change |  |

## Current Price Implied Expectations

| Input | Current / Assumed Value | Source Or Method | Note |
| --- | --- | --- | --- |
| Current price |  |  |  |
| Shares outstanding |  |  |  |
| Market cap |  |  |  |
| Net cash / debt |  |  |  |
| EPS implied by current P/E |  |  |  |
| Revenue growth implied by base margin |  |  |  |
| Margin implied by base revenue |  |  |  |

### Valuation Band Anchor

Multiples must come from `fundamentals-data.json` → `derived.valuation_band`, not from memory.

| Multiple | Current | 1y Min / Median / Max | 3y Min / Median / Max | 5y Min / Median / Max | Current Percentile |
| --- | --- | --- | --- | --- | --- |
| P/E |  |  |  |  |  |
| P/B |  |  |  |  |  |

## Margin Of Safety

| Case | Scenario-Derived Value Range | Current Price Gap | What Must Be True | What Would Break It |
| --- | --- | --- | --- | --- |
| Bull |  |  |  |  |
| Base |  |  |  |  |
| Bear |  |  |  |  |

## Accounting Quality Red Flags

- CFO and net income divergence:
- One-time gains / losses:
- Receivables or inventory rising faster than revenue:
- Related-party transactions:
- Capitalized expenses or unusual accounting items:

## Three-Statement Pattern Read

| Pattern | Evidence Combination | Current Read | Scenario Impact | Missing / Better Source |
| --- | --- | --- | --- | --- |
| Demand validated | Revenue growth + CFO / FCF improvement + receivables and inventory not outpacing sales |  |  |  |
| Stuffing risk | Revenue growth + receivables growth + inventory growth + CFO deterioration |  |  |  |
| Capex productivity | Capex / revenue + fixed assets + depreciation / revenue + ROIC trend |  |  |  |
| Liquidity pressure | Cash + current liabilities + interest coverage + FCF vs debt maturity |  |  |  |
| Shareholder value accrual | Equity growth + ROIC + dilution / buyback / dividend record |  |  |  |

- Demand validated / stuffing risk / capex productivity / liquidity pressure / shareholder value accrual:
- Which pattern has the strongest evidence:
- Which pattern is still only a hypothesis:
- What data would change the pattern read:

## Better Source Checklist

| Evidence Need | Preferred Source | Fallback Source | Status |
| --- | --- | --- | --- |
| Official financial statements | MOPS | Goodinfo / FinMind |  |
| Monthly revenue | MOPS / TWSE OpenAPI / TPEx | FinMind |  |
| PER / PBR / dividend yield | TWSE OpenAPI / TPEx | FinMind |  |
| Dividends and capital changes | MOPS / TWSE / TPEx | FinMind |  |
| Directors shareholding / pledging | MOPS / TWSE OpenAPI | Yahoo / Goodinfo |  |
| Ownership distribution | TDCC | FinMind shareholding dataset |  |

## Inputs To Investment Memo

- Business quality conclusion:
- Current price implied expectation:
- Margin of safety read:
- Evidence that should change Bull / Base / Bear probabilities:
- Critical unresolved question:

## Sources
