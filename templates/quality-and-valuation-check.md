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

| Metric | Current Read | Trend | Why It Matters | Source |
| --- | --- | --- | --- | --- |
| Owner Earnings |  |  | Cash available after maintenance reinvestment |  |
| Operating cash flow / net income |  |  | Earnings quality |  |
| Free cash flow / net income |  |  | Cash conversion |  |
| Capex / revenue |  |  | Capital intensity |  |

## Working Capital Quality Judgment

| Metric | Current Read | Trend | Risk Signal | Source |
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

The reverse read is conditional, not a unique measure of market belief. Current price divided by its trailing P/E merely reproduces trailing EPS. State fixed assumptions, solved variable, valuation date, target period, units and accounting basis; show multiple plausible combinations and sensitivity or mark the calculation blocked.

| Input | Current / Assumed Value | Source Or Method | Note |
| --- | --- | --- | --- |
| Current price |  |  |  |
| Shares outstanding |  |  |  |
| Market cap |  |  |  |
| Net cash / debt |  |  |  |
| Historical EPS used in trailing P/E (not a future implication) |  |  |  |
| Revenue growth implied by base margin |  |  |  |
| Margin implied by base revenue |  |  |  |

### Valuation Band Anchor

Use `fundamentals-data.json` → `derived.valuation_band` as historical context, not as a rule that selects the scenario multiple. Explain method, comparability and why any assumption is suitable. If the required current band is unavailable, block dependent estimates rather than reuse an old one.

| Multiple | Current | 1y Min / Median / Max | 3y Min / Median / Max | 5y Min / Median / Max | Current Percentile |
| --- | --- | --- | --- | --- | --- |
| P/E |  |  |  |  |  |
| P/B |  |  |  |  |  |

## Operating Assumptions Bridge

| Driver | Starting period / source | Scenario assumption and rationale | Link to next step | Missing input |
| --- | --- | --- | --- | --- |
| Revenue: volume / price / mix |  |  |  |  |
| Margin / operating costs |  |  |  |  |
| Tax, dilution and EPS basis |  |  |  |  |
| Working capital, capex and cash flow |  |  |  |  |

## Reverse Valuation And Sensitivity

- Valuation method and suitability:
- Valuation date, target period, units and accounting basis:
- Fixed assumptions and sources (multiple, discount rate, timing and shares where applicable):
- Solved variable and calculation:
- Alternative combinations and sensitivity of at least two material assumptions, or reason blocked:
- What is inferred versus independently sourced market expectation:
- Scenario calculations in this file are the single source for memo ranges; do not fabricate missing inputs.

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
