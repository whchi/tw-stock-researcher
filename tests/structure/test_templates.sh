#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

require_line() {
  file=$1
  pattern=$2
  if ! grep -Fq -- "$pattern" "$ROOT_DIR/$file"; then
    printf 'Missing pattern in %s: %s\n' "$file" "$pattern" >&2
    return 1
  fi
}

reject_line() {
  file=$1
  pattern=$2
  if grep -Fq -- "$pattern" "$ROOT_DIR/$file"; then
    printf 'Unexpected pattern in %s: %s\n' "$file" "$pattern" >&2
    return 1
  fi
}

require_line "README.md" "Fetch Yahoo profile + financials"
require_line "README.md" "Run financial analysis with Goodinfo"
require_line "README.md" "HTML Summary Output"
require_line "README.md" "scripts/render_research_html.py"
require_line "README.md" "templates/research-html-summary.html"
require_line "README.md" "companies/<ticker-slug>/research-summary.html"
require_line "DISCLAIMER.md" "Yahoo Finance Taiwan"
require_line "DISCLAIMER.zh-tw.md" "Yahoo 股市"

require_line "templates/company-analysis.md" "## Technical Bottleneck And Why It Matters"
require_line "templates/company-analysis.md" "## Customer Dependency And Switching Cost"
require_line "templates/company-analysis.md" "## Monetization Path"

require_line "templates/financial-analysis.md" "## Expense Structure"
require_line "templates/financial-analysis.md" "## Asset Efficiency"
require_line "templates/financial-analysis.md" "## Cash Flow And Capital Intensity"
require_line "templates/financial-analysis.md" "## Debt And Liquidity"
require_line "templates/financial-analysis.md" "## Balance Sheet Demand Validation"
require_line "templates/financial-analysis.md" "Revenue growth + receivables growth + inventory growth + CFO direction"
require_line "templates/financial-analysis.md" "## Data Sources And MOPS Cross-Check"
require_line "templates/financial-analysis.md" "- MOPS official filing URL:"
require_line "templates/financial-analysis.md" "## Break-Even And Verification"

require_line "templates/quality-and-valuation-check.md" "## Business Quality"
require_line "templates/quality-and-valuation-check.md" "ROIC"
require_line "templates/quality-and-valuation-check.md" "Owner Earnings"
require_line "templates/quality-and-valuation-check.md" "## Working Capital Quality"
require_line "templates/quality-and-valuation-check.md" "## Capital Allocation"
require_line "templates/quality-and-valuation-check.md" "## Three-Statement Pattern Read"
require_line "templates/quality-and-valuation-check.md" "Demand validated / stuffing risk / capex productivity / liquidity pressure / shareholder value accrual"
require_line "templates/quality-and-valuation-check.md" "## Current Price Implied Expectations"
require_line "templates/quality-and-valuation-check.md" "## Margin Of Safety"
require_line "templates/quality-and-valuation-check.md" "## Better Source Checklist"

require_line "templates/investment-memo.md" "> 免責聲明：本文件僅供研究參考"
require_line "templates/investment-memo.md" "scenario-derived price range"
require_line "templates/investment-memo.md" "## Business Thesis"
require_line "templates/investment-memo.md" "## Pricing Thesis"
require_line "templates/investment-memo.md" "## Technical Bottleneck -> Customer Dependency -> Monetization -> Pricing"
require_line "templates/investment-memo.md" "## Evidence Support Summary"
require_line "templates/investment-memo.md" "## Quality And Valuation Inputs"
require_line "templates/investment-memo.md" "## Expectation Gap Analysis"
require_line "templates/investment-memo.md" "| Market Belief | Evidence Status | Gap / Mispricing Risk | Verification Source |"
require_line "templates/investment-memo.md" "## Theme Stack Position"
require_line "templates/investment-memo.md" "## Critical Unresolved Question"
require_line "templates/investment-memo.md" "## Non-Portable Content Filter"
reject_line "templates/investment-memo.md" "## Recent 6M Snapshot"
reject_line "templates/investment-memo.md" "## Price / Revenue Divergence"
reject_line "templates/investment-memo.md" "## Valuation Method Split"

require_line "templates/market-action-read.md" "> 免責聲明：本文件僅供研究參考"
require_line "templates/market-action-read.md" "## Current Market Read"
require_line "templates/market-action-read.md" "Confirmation: Confirming / Diverging / Overextended / Insufficient data"
require_line "templates/market-action-read.md" "## Price / Volume Windows"
require_line "templates/market-action-read.md" "## Institutional Flow Windows"
require_line "templates/market-action-read.md" "## Market Interpretation"
require_line "templates/market-action-read.md" "## Watch Conditions"
require_line "templates/market-action-read.md" "## Next Validation"
reject_line "templates/market-action-read.md" "Bias:"
reject_line "templates/market-action-read.md" "Avoid"
require_line "templates/stock-meta.json" '"yahoo_data": null'
require_line "templates/stock-meta.json" '"quality_and_valuation_check": null'
require_line "templates/stock-meta.json" '"market_action_read": null'
require_line "templates/research-html-summary.html" "{{TITLE}}"
require_line "templates/research-html-summary.html" "{{EXPECTATION_GAP_ROWS}}"
require_line "templates/research-html-summary.html" "{{EGG_THEORY_ROWS}}"
require_line "templates/research-html-summary.html" "{{EVIDENCE_TIMELINE_ROWS}}"
require_line "templates/research-html-summary.html" "{{KILL_CRITERIA_ROWS}}"

require_line "AGENTS.md" "→ quality-and-valuation-check"
require_line "AGENTS.md" "research-html-output"
require_line "AGENTS.md" "scripts/render_research_html.py"
require_line "AGENTS.md" "companies/<ticker-slug>/research-summary.html"
require_line "README.md" "quality-and-valuation-check"
require_line "docs/data-layout.md" "quality-and-valuation-check"

require_line "templates/research-questions.md" "## Claim Hygiene Register"
require_line "templates/research-questions.md" "| Claim | Type | Why It Matters | Next Check |"
require_line "templates/research-questions.md" "| Verified Fact |"
require_line "templates/research-questions.md" "| Management Claim |"
require_line "templates/research-questions.md" "| Market Inference |"
require_line "templates/research-questions.md" "| Speculation To Verify |"
require_line "templates/research-questions.md" "| Action Language To Ignore |"

require_line "templates/active-decisions.md" "> 免責聲明：本文件僅供研究參考"
require_line "templates/active-decisions.md" "非實際交易指令"
require_line "templates/active-decisions.md" "## Three Numbers To Watch"
require_line "templates/active-decisions.md" "## Leading Signals"
require_line "templates/active-decisions.md" "## Validation Signals"
require_line "templates/active-decisions.md" "## Lagging Signals"
require_line "templates/active-decisions.md" "## Expected Evidence Timeline"
require_line "templates/active-decisions.md" "| Evidence | Expected Timing | What Confirms | What Disconfirms | Source |"
require_line "templates/active-decisions.md" "## Thesis Kill Criteria"
require_line "templates/active-decisions.md" "| Kill Condition | Evidence Needed | Source | Tracking Impact |"
require_line "templates/active-decisions.md" "## Next Review Triggers"
reject_line "templates/active-decisions.md" "## Recent 6M Tracking"
reject_line "templates/active-decisions.md" "## Validation Window"

require_line "templates/open-questions.md" "## Critical Unresolved Question"
require_line "templates/open-questions.md" "| Question | Why It Matters | What Evidence Would Resolve It | Next Check |"

require_line "templates/signal-log.md" "| Date | Signal Layer | Signal Type | Claim Type | Classification | Source | Summary | Price Reaction | Revenue/Earnings Validation | Thesis Impact | Next Action |"

require_line "templates/macro-map.md" "## Market Regime Link"
reject_line "templates/macro-map.md" "## Theme Stack Position"
reject_line "templates/macro-map.md" "Primary theme:"

if git check-ignore -q "$ROOT_DIR/docs/superpowers/plans/2026-05-11-template-framework-upgrade.md"; then
  printf 'Plan path is still ignored: %s\n' "docs/superpowers/plans/2026-05-11-template-framework-upgrade.md" >&2
  exit 1
fi

if git check-ignore -q "$ROOT_DIR/.claude/skills/research-html-output/SKILL.md"; then
  printf 'Claude skill path is ignored: %s\n' ".claude/skills/research-html-output/SKILL.md" >&2
  exit 1
fi

require_line ".agents/skills/research-html-output/SKILL.md" "name: research-html-output"
require_line ".agents/skills/research-html-output/SKILL.md" "companies/<ticker-slug>/research-summary.html"

printf 'All template structure checks passed.\n'
