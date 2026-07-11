# AGENTS.md

## Core Goal
- Research one stock at a time, persist facts / inference / open questions / active decisions across sessions.
- Never auto-generate trade orders, direct buy/sell instructions, or guaranteed returns.

## Workflow Order (Mandatory)

Canonical order — the DAG in `workflow-contract.json` is the source of truth; this line must match it (`tests/test_workflow_contract.py` checks this document against the contract):

```
stock-case-init -> yahoo-profile-financials -> financial-data-fetch -> market-data-fetch -> company-deep-dive -> financial-analysis -> industry-transmission-analysis -> macro-impact-analysis -> market-action-read -> quality-and-valuation-check -> investment-thesis -> session-wrap -> research-html-output
```

The three fetch stages (`yahoo-profile-financials`, `financial-data-fetch`, `market-data-fetch`) may run concurrently once `stock-case-init` completes; the line above is one valid linearization, not a claim that each stage must wait for the previous one specifically.

| Stage | Notes |
| --- | --- |
| `stock-case-init` | Creates the case shell: `stock-meta.json`, `research-questions.md`, `open-questions.md`. |
| `yahoo-profile-financials` | Uses `fetch_yahoo.py` / `yahoo-data.json`. |
| `financial-data-fetch` | Runs `fetch_fundamentals.py` (official monthly/quarterly layer) and `fetch_goodinfo.py` (annual fallback); owns all network fetching for this layer. |
| `market-data-fetch` | Runs `fetch_tdcc.py` then `fetch_finmind.py` (`FIN_MIND_TOKEN` required). |
| `company-deep-dive` | Depends on `yahoo-profile-financials`. |
| `financial-analysis` | Depends on `company-deep-dive` and `financial-data-fetch`; consumes already-fetched artifacts, does not fetch data itself. |
| `industry-transmission-analysis` | Depends on `company-deep-dive`. |
| `macro-impact-analysis` | Depends on `company-deep-dive`; run `fetch_macro.py` first when macro data is stale or missing. |
| `market-action-read` | Depends on `market-data-fetch`; reads `market-data.json` / `tdcc-data.json`; never edits `investment-memo.md`. |
| `quality-and-valuation-check` | Depends on `financial-analysis` and `market-data-fetch`; business quality, implied expectations, margin of safety. |
| `investment-thesis` | Depends on `company-deep-dive`, `financial-analysis`, `industry-transmission-analysis`, `macro-impact-analysis`, `quality-and-valuation-check`, and `market-action-read`; writes the whole memo once. |
| `session-wrap` | Terminal gate for both first visits and return visits; depends on `investment-thesis`. |
| `research-html-output` | Optional, explicit-request-only; requires a passing `session-wrap` gate. |

- **Return visit:** `case-revisit` -> affected stages -> their invalidated downstream stages (per `scripts/workflow_state.py` staleness cascade) -> `session-wrap`
- **New event:** `signal-update` (appends to `signal-log.md`, may update `thesis-updates.md`)
- Every stage above follows `preflight (gate) -> work -> record -> question transition` using `scripts/workflow_state.py` and `scripts/open_questions.py`; see each skill's `SKILL.md` for exact commands.

## File Structure & Ownership

Create one directory per stock under `companies/<ticker>-<slug>/`.

| File | Owner | Purpose |
|------|-------|---------|
| `stock-meta.json` | `stock-case-init` | Case index + status. All `file_references` values are `null` or repo-relative paths rooted in the case dir. |
| `yahoo-data.json` | `fetch_yahoo.py` | Yahoo Finance Taiwan company profile, revenue, income statement, cash flow, and derived summary. |
| `raw-data.json` | `fetch_goodinfo.py` | Goodinfo scraped data plus three-statement coverage check (auto-detected by script). |
| `fundamentals-data.json` | `fetch_fundamentals.py` | FinMind official monthly revenue, quarterly IS / BS / CF, and P/E / P/B valuation band with derived 6M / 8Q reads. |
| `research-questions.md` | `stock-case-init` | Core questions, facts to establish, disconfirming evidence to seek. |
| `open-questions.md` | `stock-case-init` (creation); each stage upserts/resolves only its own `question_namespace` via `scripts/open_questions.py` | Evidence-backed Active/Resolved question ledger. `case-revisit` and `session-wrap` report on it but never write to it. |
| `active-decisions.md` | `session-wrap` | Current research stance, expected evidence timeline, thesis kill criteria, user-provided position context, observation ranges, structure-break conditions, next review triggers. |
| `company-analysis.md` | `company-deep-dive` | Business model, product mix, revenue structure, margin analysis. |
| `financial-analysis.md` | `financial-analysis` | 3D analysis: 經營分析 / 獲利分析 / 財務健全度. |
| `industry-transmission.md` | `industry-transmission-analysis` | Industry chain, leading indicators, noise vs signal. |
| `macro-map.md` | `macro-impact-analysis` | Included / excluded macro variables with transmission paths. |
| `quality-and-valuation-check.md` | `quality-and-valuation-check` | Business quality, owner earnings, capital allocation, implied expectations, margin of safety. |
| `investment-memo.md` | `investment-thesis` | Bull / Base / Bear scenarios. Must integrate `investment-reasoning-framework.md` dual framework (Business Thesis + Pricing Thesis). |
| `market-data.json` | `fetch_finmind.py` | FinMind price, volume, institutional, margin, shareholding, and day-trading raw data plus derived 1D / 3D / 5D windows and 1m / 3m / 6m egg-theory reads. |
| `tdcc-data.json` | `fetch_tdcc.py` | TDCC ownership distribution snapshot: holding level, people, shares, and concentration by stock_id. |
| `market-action-read.md` | `market-action-read` | Neutral market-state view: price/volume, institutional flow, market confirmation, watch conditions. No trade instructions. |
| `signal-log.md` | `signal-update` | Append-only event log with data points and thesis changes. |
| `thesis-updates.md` | `signal-update` | Explicit thesis changes when a signal shifts the research stance. |

## Critical Toolchain & Commands

### 1. Fetching Yahoo Profile + Financials
```bash
# Requires requests. Use the repo-local venv:
.venv/bin/python scripts/fetch_yahoo.py <stock_id>
```
- **Auto-detection:** The script requires exactly one real (non-symlink) `companies/<stock_id>-*/` directory and writes `yahoo-data.json` there. Zero, multiple, or escaping/symlink matches fail closed; there is no repo-root fallback.
- **Market suffix:** Listed stocks default to `.TW`; use `--suffix TWO` for OTC stocks when Yahoo uses the `.TWO` symbol.
- **Purpose:** `yahoo-data.json` feeds `company-deep-dive` with company profile, industry, market, business scope, revenue trend, margin snapshot, and cash-flow context.
- **Role:** Yahoo is a profile and supplemental financial source. Goodinfo + MOPS remain the primary financial-analysis source.

### 1a. Fetching Official Issuer Data (TWSE/TPEx)
```bash
# Requires requests. Use the repo-local venv:
.venv/bin/python scripts/fetch_official_issuer.py <stock_id> --market TWSE --issuer-type general
```
- **Endpoint allowlist:** `https://openapi.twse.com.tw/v1/opendata/{dataset}` for `--market TWSE`, `https://www.tpex.org.tw/openapi/v1/{dataset}` for `--market TPEx`. Never string-build a host from untrusted input.
- **Datasets:** company basic info (`t187ap03_{L,O}`), monthly revenue (`t187ap05_{L,O}`), required industry-specific income statement / balance sheet summaries (`t187ap06/07_{L,O}_{ci,basi,bd,fh,ins}`), plus contextual material events, >10% shareholders, director holdings/pledges, insider transfer declarations, and dividends (`t187ap04/02/11/09/12/45_{L,O}`). General issuers use `ci`; financial issuers are matched across `basi`, `bd`, `fh`, and `ins` without guessing a subtype.
- **Verified TLS status (2026-07-11, see `docs/source-policy.md`):** TWSE succeeds under strict certificate verification. TPEx's certificate currently fails verification (`Missing Subject Key Identifier`) even with `requests`' bundled CA store — this is treated as a source failure (`status: blocked`), never bypassed with `verify=False`.
- **Role:** tier `official`; canonical for company identity, monthly revenue, and quarterly income/balance-sheet fields when it succeeds.

### 2. Fetching Financial Data
```bash
# Requires requests + beautifulsoup4. Use the repo-local venv:

# Run the scraper. It auto-detects the case directory and writes raw-data.json there:
.venv/bin/python scripts/fetch_goodinfo.py <stock_id>
```
- **Auto-detection:** requires exactly one real `companies/<stock_id>-*/` directory; zero, multiple, symlink, or escaping matches fail closed with no repo-root fallback.
- **Provenance:** `raw-data.json` includes `metadata` with `fetched_at`, Goodinfo URLs, and MOPS links.
- **Coverage checks:** `raw-data.json` includes `three_statement_coverage` to show whether Goodinfo annual IS / BS / CF fields are sufficient for balance-sheet demand validation and three-statement pattern reads.
- **Sanity checks:** The script flags gross margin >100%, current ratio <0, debt ratio >100%, ROE >100%, and adjacent-year net margin swings >30pp.
- **Cross-check:** Always include the MOPS official filing URL in `financial-analysis.md`.
- **Role:** tier `unofficial_scrape` — temporary annual fallback/cross-check once official (`fetch_official_issuer.py`) or FinMind (`fetch_fundamentals.py`) coverage exists for a metric.

### 2a. Fetching Fundamentals (FinMind)
```bash
# Uses the same repo-local venv. FIN_MIND_TOKEN must be set in the environment:
.venv/bin/python scripts/fetch_fundamentals.py <stock_id>
```
- **Datasets:** `TaiwanStockMonthRevenue`, `TaiwanStockFinancialStatements`, `TaiwanStockBalanceSheet`, `TaiwanStockCashFlowsStatement`, `TaiwanStockPER` (5-year window; any dataset failure degrades to a warning).
- **Auto-detection:** same fail-closed single real case-folder rule; there is no repo-root fallback.
- **Derived reads:** `derived.monthly_revenue_6m` (official 6M revenue path with MoM / YoY / cumulative YoY), `derived.quarterly_income_8q` (8 quarters with margins and YoY), `derived.quarterly_balance_key_items`, `derived.quarterly_cash_flow` (CFO / capex / FCF), and `derived.valuation_band` (current P/E / P/B vs 1y / 3y / 5y min / median / max with percentile).
- **Role:** tier `secondary_aggregator` per `docs/source-policy.md` — a normalized monthly + quarterly layer, reconciled against `official-issuer-data.json` (`scripts/reconcile_sources.py:reconcile_metric`) where both cover the same metric and period rather than trusted outright. Goodinfo stays the annual baseline, MOPS stays the official cross-check, and `valuation_band` is the required anchor for implied-expectation and pricing-thesis multiples.

### 3. Writing Files
- **Always use `write` or `edit` tools** for markdown/JSON files. Do NOT use bash `echo`, `cat`, or `mv` for file creation.
- **Do NOT create HTML dashboards.** Output all financial analysis as markdown (`financial-analysis.md`).
- **Never leave `*_raw_data.json` in repo root.** Move to `companies/<ticker>-<slug>/raw-data.json` if the script fails auto-detection.
- **Never leave `*_yahoo_data.json` in repo root.** Move to `companies/<ticker>-<slug>/yahoo-data.json` if the Yahoo script fails auto-detection.
- **Never leave `*_market_data.json` in repo root.** Move to `companies/<ticker>-<slug>/market-data.json` if the FinMind script fails auto-detection.
- **Never leave `*_fundamentals_data.json` in repo root.** Move to `companies/<ticker>-<slug>/fundamentals-data.json` if the fundamentals script fails auto-detection.

### 4. Fetching Market Data
```bash
# Uses the same repo-local venv. FIN_MIND_TOKEN must be set in the environment:
.venv/bin/python scripts/fetch_finmind.py <stock_id>
```
- **Token:** `FIN_MIND_TOKEN` is required — the script exits with an error without it. Never write the token into repo files.
- **Datasets:** `TaiwanStockPrice`, `TaiwanStockInstitutionalInvestorsBuySell`, `TaiwanStockMarginPurchaseShortSale`, `TaiwanStockShareholding`, `TaiwanStockDayTrading`, `TaiwanStockHoldingSharesPer`. Optional datasets (margin, shareholding, day trading, holding-shares-per) degrade to warnings instead of failing the run.
- **Auto-detection:** requires exactly one real `companies/<stock_id>-*/` directory; zero, multiple, symlink, or escaping matches fail closed with no repo-root fallback.
- **Derived windows:** `market-data.json` includes 1D / 3D / 5D price change, volume change, price-volume read, institutional net buy/sell by investor type, and 1m / 3m / 6m egg-theory reads.

### 4a. Fetching TDCC Ownership Distribution
```bash
# Uses the same repo-local venv:
.venv/bin/python scripts/fetch_tdcc.py <stock_id>
```
- **Source:** TDCC's official OpenAPI dataset `id=1-5` (`https://openapi.tdcc.com.tw/v1/opendata/1-5`) is the all-market ownership distribution table, not a stock id, and succeeds under strict TLS verification — see `docs/source-policy.md`.
- **Auto-detection:** requires exactly one real `companies/<stock_id>-*/` directory; zero, multiple, symlink, or escaping matches fail closed with no repo-root fallback.
- **Purpose:** `tdcc-data.json` stores the requested stock's holding levels (`持股分級`), people count, shares, and TDCC custody percentage. `fetch_finmind.py` reads this local file for egg-theory holder reads; it does not fetch TDCC directly.
- **Cache:** the all-market JSON response is cached without format conversion at `market/tdcc-holding-distribution.json` and reused for 72h by default (`--max-age-hours`, `--refresh` to force a re-download).
- **Trend accumulation:** the endpoint serves only the latest weekly snapshot, but each new snapshot date is appended to `tdcc-data.json` under `history`. After a few weekly runs, `fetch_finmind.py` derives holder-count trends from this history (`holder_trend_from_tdcc_weekly`, confidence capped at medium) when FinMind `TaiwanStockHoldingSharesPer` is not accessible.

### 5. Fetching Shared Macro Data
```bash
# Uses the same repo-local venv:
.venv/bin/python scripts/fetch_macro.py
```
- **Output:** writes `market/shared-macro-data.json` by default.
- **Scope discipline:** fetch only sources explicitly listed in `templates/shared-macro-view.md` and `templates/macro-map.md`: TWSE Open API, Yahoo Finance / public market data, and Taiwan official statistics / MOPS context.
- **Taiwan official endpoint:** defaults to the MOF Customs monthly trade statistics CSV (data.gov.tw dataset 6053, `https://opendata.customs.gov.tw/data/6053/csv.csv`) with parsed exports / imports / trade balance and exports YoY. Set `TAIWAN_MACRO_URL` to override with another stable official CSV/JSON endpoint; custom endpoints are stored as a raw preview.

### 6. .gitignore Trap
```
companies/**/*.md
companies/**/*.json
```
**All case files are git-ignored by default.** This is intentional — case files are session artifacts, not repo source code. Only root-level docs, scripts, templates, and market context are version controlled.

### 7. HTML Summary Output
When the user explicitly asks for a comprehensive research result as HTML, use the `research-html-output` skill from `.agents/skills/research-html-output/SKILL.md`.

- Keep markdown / JSON case files as the source of truth.
- Use `templates/research-html-summary.html` as the shared template and `templates/research-summary-data.schema.json` as the payload shape (enforced by `scripts/research_summary_contract.py`).
- Build the typed payload deterministically from fixed source files, then render it:
```bash
.venv/bin/python scripts/build_research_summary.py --case companies/<ticker-slug>
.venv/bin/python scripts/render_research_html.py --case companies/<ticker-slug>
```
- Both commands accept `--check` to validate without writing. `build_research_summary.py` fails closed (non-zero exit) when a required source is missing, a source table is malformed, the built payload fails validation, or `research-html-output`'s workflow gate is not ready (most commonly because `session-wrap` has not passed).
- Never hand-write `research-summary-data.json` and never consult an existing `research-summary-data.json` or `research-summary.html` as a builder input — every field is re-derived from the canonical markdown/JSON case files each time.
- The output HTML must live in the company folder as `companies/<ticker-slug>/research-summary.html`.
- HTML is a derived preview, not a replacement for `investment-memo.md`, `active-decisions.md`, or other case artifacts.
- Preserve disclaimer discipline and never introduce buy/sell, entry/exit, stop-loss, or target-price language.
- Run `scripts/validate_research_summary.py --all` to audit current-format `research-summary-data.json` files for invalid payloads or stale manifests. It is read-only and never rewrites a case.

## Financial Analysis Conventions

### Data Source
- **Primary (annual):** Goodinfo.tw (`IS_YEAR`, `BS_YEAR`, `CF_YEAR`) via `scripts/fetch_goodinfo.py`
- **Primary (monthly / quarterly):** FinMind via `scripts/fetch_fundamentals.py` (`fundamentals-data.json`: official monthly revenue, quarterly IS / BS / CF, valuation band)
- **Cross-check:** MOPS (https://mops.twse.com.tw)

### Key Fields
| Statement | Critical Fields |
|-----------|----------------|
| Income | 營業收入, 營業毛利(淨額), 推銷費用, 管理費用, 研究發展費用, 營業利益, 利息費用, 稅後淨利, 每股稅後盈餘(元) |
| Balance | 現金及約當現金, 應收帳款, 存貨, 應付帳款, 預付款項, 合約負債 / 遞延收入 / 預收款項（若有）, 流動資產合計, 流動負債合計, 短期借款, 長期借款, 負債總額, 商譽 / 無形資產（若有）, 股東權益總額, 資產總額 |
| Cash Flow | 營業活動之淨現金流入(出), 投資活動之淨現金流入(出), 融資活動之淨現金流入(出), 固定資產(增加)減少, 折舊及攤銷, 發放現金股利 |

### Derived Metrics
- Gross margin = 營業毛利 / 營業收入
- Operating margin = 營業利益 / 營業收入
- Net margin = 稅後淨利 / 營業收入
- Current ratio = 流動資產 / 流動負債
- Debt ratio = 負債總額 / 資產總額
- ROE = 稅後淨利 / 股東權益
- ROA = 稅後淨利 / 資產總額
- FCF = 營業現金流 + 固定資產增減 (capex is negative)
- ROIC = after-tax operating profit / invested capital
- Owner earnings = operating cash flow - maintenance capex estimate
- Cash conversion = free cash flow / net income
- Working capital quality = receivable days, inventory days, payable days, and cash conversion cycle trend
- Three-statement demand validation = revenue growth, receivables growth, inventory growth, and CFO / FCF direction read together
- Capex productivity = capex / revenue, fixed assets, depreciation / revenue, and ROIC trend read together

### Data Sufficiency For Three-Statement Pattern Reads
- `fetch_goodinfo.py` writes `three_statement_coverage.baseline_supported=true` only when the annual Goodinfo income statement, balance sheet, and cash-flow statement include the required raw fields for a baseline three-statement read.
- Goodinfo annual data is generally sufficient for baseline checks: cash collection vs revenue, receivables / inventory build, CFO / FCF conversion, liquidity, leverage, capex intensity, and shareholder equity growth.
- Goodinfo annual data is not sufficient by itself for full NVDA-style depth when the thesis depends on quarter timing, debt maturity schedules, allowance for doubtful accounts, customer prepayments / contract liabilities detail, dilution notes, customer concentration, or management guidance. Use MOPS filings, quarterly reports, company reports, or official notes for those items.
- If `required_missing` is not empty, do not force a conclusion. Put the missing fields in `financial-analysis.md` → `Open Verification Items`.
- If only `supplemental_missing` is non-empty, the baseline annual read may proceed, but any conclusion depending on missing supplemental items must be labeled as lower-confidence.

### Output Format
- Write `financial-analysis.md` as markdown, not HTML.
- Include data tables with YoY changes and a "trend assessment" column (▲ up / ▼ down / ■ neutral).
- Cover three dimensions: Operating Analysis, Profitability Analysis, Financial Health.
- Include a balance-sheet demand validation table that connects revenue, receivables, inventory, payables, CFO, capex, and liquidity instead of judging each line item in isolation.

### Flow Boundary
- `financial-analysis.md` is the financial fact layer: statements, calculated metrics, source checks, and red flags.
- `quality-and-valuation-check.md` is the judgment layer: business quality, capital allocation, implied expectations, and margin of safety based on the financial facts.
- `investment-memo.md` should summarize how evidence changes Bull / Base / Bear probabilities; do not duplicate raw financial, macro, quality, or market-action tables there.

## Macro Impact Analysis Conventions

- `macro-impact-analysis` writes `macro-map.md`; shared reusable context may go in `market/shared-macro-view.md` using `templates/shared-macro-view.md`.
- Run `.venv/bin/python scripts/fetch_macro.py` before writing `macro-map.md` when `market/shared-macro-data.json` is missing or stale.
- Start from public/free sources: TWSE Open API, Yahoo Finance / public market data, Taiwan official statistics, and MOPS context.
- Do not include macro variables just because they are popular. Include only variables with a concrete transmission path into revenue, margin, cash flow, valuation multiple, or market narrative for the specific company.
- For every included variable, document: source, latest read or trend, directional impact, transmission path, monitoring cadence, and thesis link.
- For excluded variables, state why the transmission path is weak or immaterial and what evidence would make the variable worth reconsidering.
- Prefer neutral labels such as `macro backdrop`, `transmission path`, `monitoring trigger`, and `assumption failure signal`; do not turn macro reads into trade instructions.
- Keep investment themes out of `macro-map.md`; themes belong in `investment-memo.md`. Macro only records market regime and variables with concrete transmission paths.

## Investment Memo Conventions

- **Dual Framework:** Every memo must have **Business Thesis** (fundamentals / validation / cash) and **Pricing Thesis** (market re-rating / narrative expansion per `investment-reasoning-framework.md`).
- **Quality Input:** Read `quality-and-valuation-check.md` before writing scenarios. Use it to separate good-business evidence from already-priced expectations.
- **Evidence Summary Only:** Do not copy raw 6M revenue, market-action, macro, or quality tables into the memo. Summarize which evidence supports or weakens each scenario.
- **Expectation Gap:** Separate market belief from verified evidence, narrative-only claims, and the evidence needed to close or invalidate the gap.
- **Pricing Stages:** Stage 1 (narrative expansion) → Stage 2 (fundamentals catch up) → Stage 3 (growth slows / valuation contraction).
- **Scenarios:** Always include Bull / Base / Bear with probability weights, EPS assumptions, and scenario-derived price ranges.
- **No unsupported price targets.** Every price range must derive from an explicit scenario.

## Market Action Read Conventions

- `market-action-read.md` is an evidence layer, not a trading decision layer.
- Cover 1D / 3D / 5D price-volume changes and three-major-institution flow.
- Use neutral labels such as `market confirmation`, `price-in risk`, `thesis validation trigger`, and `assumption failure signal`.
- Do **not** include entry, exit, stop-loss, position sizing, or target-price language.
- Use confirmation labels such as `Confirming`, `Diverging`, `Overextended`, and `Insufficient data`; avoid action-like labels such as `Avoid`.

## Disclaimer Discipline

- Follow `DISCLAIMER.md` whenever writing any stock-specific analysis, memo, or decision log.
- All outputs are for educational, research, and reference purposes only. They **must not** be written as investment advice, purchase recommendations, price targets, or solicitations to buy or sell.
- Express valuation only as **scenario analysis** or **observation frameworks** tied to assumptions (for example: Base Case price range, validation trigger, structure-break condition).
- Do **not** write imperative recommendation language such as `建議買進`, `建議進場`, `目標價`, `停損價`, `應該買`, `應該賣`, `take profit`, or `stop-loss`, unless explicitly quoting or preserving the user's own words as user context.
- Prefer neutral research language such as `scenario price range`, `observation range`, `thesis validation trigger`, `assumption failure signal`, and `structure-break condition`.
- When recording an existing personal position from the user, label it clearly as **user-provided position context**, not as a model-generated recommendation.
- `investment-memo.md` and `active-decisions.md` should include a short disclaimer note near the top linking to the project disclaimer when practical.
- `active-decisions.md` should state expected evidence timelines and thesis kill criteria in neutral tracking language, not trade instructions.

## Red Lines
- No fabricated data.
- No unsupported price targets.
- No language that constitutes investment advice, purchase recommendation, target price, or solicitation to buy or sell.
- No paid-source claims without actual access.
- No destructive overwrites without confirmation.
- Never leave `venv*/` or `.venv/` in repo root (already in `.gitignore`).
- Never leave `*_raw_data.json` in repo root.
- Never leave `*_market_data.json` in repo root.
- Never leave `*_fundamentals_data.json` in repo root.
- Never leave `*_official_issuer_data.json` in repo root.
- Never disable TLS certificate verification (`verify=False`) in any production fetch path; a TLS failure is a source failure, not something to bypass.
- Never average conflicting source values; classify the conflict per `docs/source-policy.md` instead.

## Repo Layout Reference
```
companies/           # Per-stock cases (git-ignored contents)
market/              # Shared macro/industry context
templates/           # Canonical file shapes for each skill
scripts/             # fetch_yahoo.py, fetch_official_issuer.py, fetch_goodinfo.py, fetch_fundamentals.py, fetch_finmind.py, fetch_tdcc.py, fetch_macro.py, reconcile_sources.py (use .venv at repo root)
docs/data-layout.md  # Full layout rules
investment-reasoning-framework.md         # Pricing framework (dual thesis)
```
