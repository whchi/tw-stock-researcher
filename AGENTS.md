# AGENTS.md

## Core Goal
- Research one stock at a time, persist facts / inference / open questions / active decisions across sessions.
- Never auto-generate trade orders, direct buy/sell instructions, or guaranteed returns.

## Workflow Order (Mandatory)
```
stock-case-init
  → yahoo-profile-financials    # Uses fetch_yahoo.py / yahoo-data.json
  → company-deep-dive
  → financial-analysis          # Must run fetch_goodinfo.py FIRST
  → industry-transmission-analysis
  → macro-impact-analysis       # Must run fetch_macro.py FIRST when macro data is stale/missing
  → quality-and-valuation-check # Business quality, implied expectations, margin of safety
  → investment-thesis
  → market-action-read          # Uses fetch_finmind.py / market-data.json
```
- **Return visit:** `case-revisit` → `session-wrap`
- **New event:** `signal-update` (appends to `signal-log.md`, may update `thesis-updates.md`)

## File Structure & Ownership

Create one directory per stock under `companies/<ticker>-<slug>/`.

| File | Owner | Purpose |
|------|-------|---------|
| `stock-meta.json` | `stock-case-init` | Case index + status. All `file_references` values are `null` or repo-relative paths rooted in the case dir. |
| `yahoo-data.json` | `fetch_yahoo.py` | Yahoo Finance Taiwan company profile, revenue, income statement, cash flow, and derived summary. |
| `raw-data.json` | `fetch_goodinfo.py` | Goodinfo scraped data (auto-detected by script). |
| `research-questions.md` | `stock-case-init` | Core questions, facts to establish, disconfirming evidence to seek. |
| `open-questions.md` | `case-revisit` / `session-wrap` | Unresolved items to carry forward; closed questions logged here. |
| `active-decisions.md` | `session-wrap` | Current research stance, expected evidence timeline, thesis kill criteria, user-provided position context, observation ranges, structure-break conditions, next review triggers. |
| `company-analysis.md` | `company-deep-dive` | Business model, product mix, revenue structure, margin analysis. |
| `financial-analysis.md` | `financial-analysis` | 3D analysis: 經營分析 / 獲利分析 / 財務健全度. |
| `industry-transmission.md` | `industry-transmission-analysis` | Industry chain, leading indicators, noise vs signal. |
| `macro-map.md` | `macro-impact-analysis` | Included / excluded macro variables with transmission paths. |
| `quality-and-valuation-check.md` | `quality-and-valuation-check` | Business quality, owner earnings, capital allocation, implied expectations, margin of safety. |
| `investment-memo.md` | `investment-thesis` | Bull / Base / Bear scenarios. Must integrate `investment-reasoning-framework.md` dual framework (Business Thesis + Pricing Thesis). |
| `market-data.json` | `fetch_finmind.py` | FinMind price, volume, and institutional investor raw data plus 1D / 3D / 5D derived windows. |
| `market-action-read.md` | `market-action-read` | Neutral market-state view: price/volume, institutional flow, market confirmation, watch conditions. No trade instructions. |
| `signal-log.md` | `signal-update` | Append-only event log with data points and thesis changes. |

## Critical Toolchain & Commands

### 1. Fetching Yahoo Profile + Financials
```bash
# Requires requests. Use the repo-local venv:
.venv/bin/python scripts/fetch_yahoo.py <stock_id>
```
- **Auto-detection:** The script looks for exactly one `companies/<stock_id>-*/` directory. If found, writes `yahoo-data.json` there. If zero or multiple matches, falls back to repo root (`<stock_id>_yahoo_data.json`) — **avoid this.**
- **Market suffix:** Listed stocks default to `.TW`; use `--suffix TWO` for OTC stocks when Yahoo uses the `.TWO` symbol.
- **Purpose:** `yahoo-data.json` feeds `company-deep-dive` with company profile, industry, market, business scope, revenue trend, margin snapshot, and cash-flow context.
- **Role:** Yahoo is a profile and supplemental financial source. Goodinfo + MOPS remain the primary financial-analysis source.

### 2. Fetching Financial Data
```bash
# Requires requests + beautifulsoup4. Use the repo-local venv:

# Run the scraper. It auto-detects the case directory and writes raw-data.json there:
.venv/bin/python scripts/fetch_goodinfo.py <stock_id>
```
- **Auto-detection:** The script looks for exactly one `companies/<stock_id>-*/` directory. If found, writes `raw-data.json` there. If zero or multiple matches, falls back to repo root (`<stock_id>_raw_data.json`) — **avoid this.**
- **Provenance:** `raw-data.json` includes `metadata` with `fetched_at`, Goodinfo URLs, and MOPS links.
- **Sanity checks:** The script flags gross margin >100%, current ratio <0, debt ratio >100%, ROE >100%, and adjacent-year net margin swings >30pp.
- **Cross-check:** Always include the MOPS official filing URL in `financial-analysis.md`.

### 3. Writing Files
- **Always use `write` or `edit` tools** for markdown/JSON files. Do NOT use bash `echo`, `cat`, or `mv` for file creation.
- **Do NOT create HTML dashboards.** Output all financial analysis as markdown (`financial-analysis.md`).
- **Never leave `*_raw_data.json` in repo root.** Move to `companies/<ticker>-<slug>/raw-data.json` if the script fails auto-detection.
- **Never leave `*_yahoo_data.json` in repo root.** Move to `companies/<ticker>-<slug>/yahoo-data.json` if the Yahoo script fails auto-detection.
- **Never leave `*_market_data.json` in repo root.** Move to `companies/<ticker>-<slug>/market-data.json` if the FinMind script fails auto-detection.

### 4. Fetching Market Data
```bash
# Uses the same repo-local venv:
.venv/bin/python scripts/fetch_finmind.py <stock_id>
```
- **Datasets:** `TaiwanStockPrice`, `TaiwanStockInstitutionalInvestorsBuySell`.
- **Auto-detection:** The script looks for exactly one `companies/<stock_id>-*/` directory. If found, writes `market-data.json` there. If zero or multiple matches, falls back to repo root (`<stock_id>_market_data.json`) — **avoid this.**
- **Derived windows:** `market-data.json` includes 1D / 3D / 5D price change, volume change, price-volume read, and institutional net buy/sell by investor type.

### 5. Fetching Shared Macro Data
```bash
# Uses the same repo-local venv:
.venv/bin/python scripts/fetch_macro.py
```
- **Output:** writes `market/shared-macro-data.json` by default.
- **Scope discipline:** fetch only sources explicitly listed in `templates/shared-macro-view.md` and `templates/macro-map.md`: TWSE Open API, Yahoo Finance / public market data, and Taiwan official statistics / MOPS context.
- **Taiwan official endpoint:** set `TAIWAN_MACRO_URL` when using a stable official CSV/JSON endpoint for Taiwan exports/orders (MOEA/DGBAS). If unset, the endpoint is recorded as a warning — the script still writes TWSE + Yahoo data.

### 6. .gitignore Trap
```
companies/**/*.md
companies/**/*.json
```
**All case files are git-ignored by default.** This is intentional — case files are session artifacts, not repo source code. Only root-level docs, scripts, templates, and market context are version controlled.

### 7. HTML Summary Output
When the user explicitly asks for a comprehensive research result as HTML, use the `research-html-output` skill from `.agents/skills/research-html-output/SKILL.md` or `.claude/skills/research-html-output/SKILL.md`.

- Keep markdown / JSON case files as the source of truth.
- Use `templates/research-html-summary.html` as the shared template.
- Build a JSON payload from the case files in the same company folder and render via string replacement:
```bash
.venv/bin/python scripts/render_research_html.py \
  --data companies/<ticker-slug>/research-summary-data.json \
  --output companies/<ticker-slug>/research-summary.html
```
- The output HTML must live in the company folder as `companies/<ticker-slug>/research-summary.html`.
- HTML is a derived preview, not a replacement for `investment-memo.md`, `active-decisions.md`, or other case artifacts.
- Preserve disclaimer discipline and never introduce buy/sell, entry/exit, stop-loss, or target-price language.

## Financial Analysis Conventions

### Data Source
- **Primary:** Goodinfo.tw (`IS_YEAR`, `BS_YEAR`, `CF_YEAR`)
- **Scraper:** `scripts/fetch_goodinfo.py`
- **Cross-check:** MOPS (https://mops.twse.com.tw)

### Key Fields
| Statement | Critical Fields |
|-----------|----------------|
| Income | 營業收入, 營業毛利(淨額), 推銷費用, 管理費用, 研究發展費用, 營業利益, 稅後淨利, 每股稅後盈餘(元) |
| Balance | 現金及約當現金, 存貨, 流動資產合計, 流動負債合計, 負債總額, 股東權益總額, 資產總額 |
| Cash Flow | 營業活動之淨現金流入(出), 投資活動之淨現金流入(出), 融資活動之淨現金流入(出), 固定資產(增加)減少, 發放現金股利 |

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

### Output Format
- Write `financial-analysis.md` as markdown, not HTML.
- Include data tables with YoY changes and a "trend assessment" column (▲ up / ▼ down / ■ neutral).
- Cover three dimensions: Operating Analysis, Profitability Analysis, Financial Health.

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

## Repo Layout Reference
```
companies/           # Per-stock cases (git-ignored contents)
market/              # Shared macro/industry context
templates/           # Canonical file shapes for each skill
scripts/             # fetch_yahoo.py, fetch_goodinfo.py, and fetch_finmind.py (use .venv at repo root)
docs/data-layout.md  # Full layout rules
investment-reasoning-framework.md         # Pricing framework (dual thesis)
```
