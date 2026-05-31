# TW Stock Researcher

> **New here?** Read [`FIRST_RUN.md`](FIRST_RUN.md) first for the quick-start checklist.

## What This Is

This repository is a markdown-first workspace template for researching one stock thesis at a time. It is designed to keep a case persistent across sessions so facts, inference, open questions, signals, and active decisions stay separate and reviewable.

## Core Principles

- Work one stock case at a time.
- Preserve reusable files instead of one-off chat summaries.
- Separate facts, inferences, open questions, and thesis changes.
- Prefer public and free sources unless the user explicitly provides something else.
- Update the case incrementally when new signals arrive.

## Standard Workflow

1. Start a case with `stock-case-init`.
2. Fetch Yahoo profile + financials with `scripts/fetch_yahoo.py`.
3. Build the company view with `company-deep-dive`.
4. Run financial analysis with Goodinfo via `scripts/fetch_goodinfo.py`, then write `financial-analysis.md`.
5. Map industry drivers with `industry-transmission-analysis`.
6. Filter macro variables with `macro-impact-analysis`.
7. Add the value-investor quality layer with `quality-and-valuation-check`.
8. Write the current thesis with `investment-thesis`.
9. Add the market-state layer with `market-action-read` after fetching FinMind market data.
10. Record expected evidence, thesis kill criteria, and tracking triggers in `active-decisions.md`.
11. Use `signal-update` for new filings, revenue releases, or news.
12. Use `case-revisit` when returning to the case later.
13. Use `session-wrap` before ending a session.

## Data Layout

The workspace keeps shared market context under `market/`, reusable templates under `templates/`, and per-stock cases under `companies/`. Create shared market files in `market/` by copying the corresponding templates from `templates/` when needed. See `docs/data-layout.md` for the full layout and file ownership rules.

## HTML Summary Output

Markdown and JSON files remain the source of truth. When the user explicitly asks for a comprehensive research result as HTML, use the `research-html-output` skill and render a derived preview from `templates/research-html-summary.html`.

The HTML output is produced by string replacement, not by changing the canonical case files:

```bash
.venv/bin/python scripts/render_research_html.py \
  --data companies/<ticker-slug>/research-summary-data.json \
  --output companies/<ticker-slug>/research-summary.html
```

Build the JSON payload from the case files in the same company folder, then let `scripts/render_research_html.py` replace the template placeholders. The HTML output should stay in that company folder as `companies/<ticker-slug>/research-summary.html`. The 6706 惠特 and 6741 91APP preview layouts are represented by the shared template structure: research snapshot, expectation gap, expected evidence timeline, thesis kill criteria, scenario summary, watch items, source quality, and sources.

## The Skills

- `stock-case-init`: create case metadata, core questions, and initial open questions.
- `company-deep-dive`: analyze business model, products, customers, and revenue structure.
- `industry-transmission-analysis`: map the industry chain and leading indicators.
- `macro-impact-analysis`: keep only macro variables that materially transmit into the case.
- `quality-and-valuation-check`: assess ROIC, owner earnings, working-capital quality, capital allocation, implied expectations, and margin of safety.
- `investment-thesis`: produce the current memo with assumptions and disconfirming evidence.
- `market-action-read`: summarize 1D/3D/5D price-volume action and institutional flow without trading instructions.
- `research-html-output`: render an explicit HTML summary request from `templates/research-html-summary.html` using `scripts/render_research_html.py`.
- `signal-update`: append new events and decide whether the thesis changed.
- `case-revisit`: re-enter an existing case with a file-grounded summary.
- `session-wrap`: preserve unresolved questions, expected evidence, thesis kill criteria, decisions, and next follow-ups.

## Getting Started

1. Read `FIRST_RUN.md`.
2. Start a new case with `stock-case-init` so metadata, research questions, and open questions are created in the right order.
3. Use the files in `templates/` as the canonical shapes for the artifacts each skill should create or update.
4. Create shared market context files in `market/` by copying the corresponding templates from `templates/` when needed.
5. Run the structure and skill checks in `tests/` after changing the workspace.

## Usage Examples

### Example 1: Researching a new stock

**User:** "幫我分析 3037 欣興"

**What happens:**
1. `stock-case-init` creates `companies/3105-awsc/` directory
2. Runs `scripts/fetch_yahoo.py 3105` → saves `yahoo-data.json` in the case directory
3. Fetches Yahoo profile + financials (revenue, margins, cash flow) for the company deep-dive input
4. Runs `scripts/fetch_goodinfo.py 3105` → saves `raw-data.json` in the case directory
5. Uses Goodinfo data with MOPS cross-check links for financial-analysis primary evidence
6. Writes `company-analysis.md` with business model, product mix, margin analysis
7. Writes `financial-analysis.md` with 3D analysis (經營/獲利/財務健全度) using Goodinfo data
8. Writes `industry-transmission.md` mapping the industry chain
9. Writes `macro-map.md` filtering relevant macro variables
10. Writes `quality-and-valuation-check.md` with business quality, implied expectations, and margin-of-safety evidence
11. Writes `investment-memo.md` with Bull/Base/Bear scenarios using the `investment-reasoning-framework.md` pricing framework
12. Runs `scripts/fetch_finmind.py 3105` with `FIN_MIND_TOKEN` → saves `market-data.json` in the case directory
13. Writes `market-action-read.md` with 1D/3D/5D price-volume and institutional flow evidence
14. Records expected evidence timeline and thesis kill criteria in `active-decisions.md`
15. Updates `stock-meta.json` with all file references

**Files created:**
```
companies/3105-awsc/
├── stock-meta.json          # Case index
├── yahoo-data.json          # Yahoo profile, revenue, margins, and cash-flow summary
├── raw-data.json            # Goodinfo raw financial data
├── research-questions.md    # Core questions & unknowns
├── open-questions.md        # Active open questions
├── active-decisions.md      # Current position & entry targets
├── company-analysis.md      # Business model deep-dive
├── financial-analysis.md    # 3D financial analysis
├── industry-transmission.md # Industry chain & leading indicators
├── macro-map.md            # Macro variables
├── quality-and-valuation-check.md # Quality, implied expectations, margin of safety
├── investment-memo.md      # Investment thesis (dual framework)
├── market-data.json        # FinMind price/volume and institutional raw data
├── market-action-read.md   # Neutral market-state read
└── signal-log.md           # Decision history
```

### Example 2: Updating a case with new data

**User:** "更新 2344 華邦電最新財報"

**What happens:**
1. `signal-update` re-runs `scripts/fetch_goodinfo.py 2344`
2. Reads existing case files to understand prior thesis
3. Appends new financial data to `financial-analysis.md`
4. Updates `investment-memo.md` if thesis changes
5. Logs the update in `signal-log.md`

### Example 3: Revisiting a case

**User:** "我上次研究的 6789 采鈺現在怎麼樣了？"

**What happens:**
1. `case-revisit` reads `stock-meta.json` to find the case
2. Summarizes current active decisions from `active-decisions.md`
3. Lists open questions from `open-questions.md`
4. Suggests next follow-ups

### Example 4: Comparing peers

**User:** "幫我比較 2330 台積電和 2454 聯發科"

**What happens:**
1. Initializes both cases if not existing
2. Fetches financial data for both
3. Creates side-by-side comparison in `financial-analysis.md`
4. Highlights key differences (business model, margins, valuation)

### Key Conventions

- **Raw data:** Always saved as `companies/{ticker-slug}/raw-data.json`, never in repo root
- **Yahoo data:** Always saved as `companies/{ticker-slug}/yahoo-data.json`, never in repo root
- **Market data:** Always saved as `companies/{ticker-slug}/market-data.json`, never in repo root
- **Financial data:** Primary source is Goodinfo.tw; always include MOPS links for cross-checking
- **Macro data:** Taiwan-focused. Run `scripts/fetch_macro.py` to refresh `market/shared-macro-data.json` (TWSE Open API, Yahoo Finance, Taiwan official statistics); include only variables with a concrete company-level transmission path
- **Quality and valuation:** Keep business-quality judgment and implied market expectations in `quality-and-valuation-check.md`; the investment memo should consume its conclusion, not duplicate its tables
- **Expectation gap:** Use `investment-memo.md` to separate market belief, verified evidence, narrative-only claims, and the evidence needed to close or invalidate the gap
- **Market action:** `market-action-read.md` summarizes evidence only; it must not output trade instructions
- **Tracking discipline:** Use `active-decisions.md` for expected evidence timelines, thesis kill criteria, and review triggers so a case can be downgraded when evidence stops compounding
- **Thesis format:** Dual framework (Business Thesis + Pricing Thesis per `investment-reasoning-framework.md`)
- **Pricing stages:** Stage 1 (narrative expansion) → Stage 2 (fundamentals catch up) → Stage 3 (growth slows)
- **No unsupported targets:** Never generate price targets without scenario analysis

## What This Is Not

- Not a trading bot.
- Not a valuation engine.
- Not a scheduler or watchlist product.
- Not a source of guaranteed returns, price targets, or trade orders.
