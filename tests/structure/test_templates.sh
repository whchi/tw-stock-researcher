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

require_line "README.md" "financial-data-fetch"
require_line "README.md" "scripts/build_research_summary.py --case companies/<ticker-slug>"
require_line "README.md" "scripts/render_research_html.py --case companies/<ticker-slug>"
reject_line "README.md" "--data companies/<ticker-slug>/research-summary-data.json"
reject_line "README.md" "--output companies/<ticker-slug>/research-summary.html"

require_line "AGENTS.md" "financial-data-fetch"
require_line "AGENTS.md" "no repo-root fallback"
require_line "AGENTS.md" "market/tdcc-holding-distribution.json"
require_line "AGENTS.md" "templates/research-summary-data.schema.json"

require_line "docs/source-policy.md" "Do not disable TLS certificate verification"
require_line "docs/data-layout.md" "scripts/build_research_summary.py"
require_line "docs/data-layout.md" "scripts/render_research_html.py"
require_line "docs/data-layout.md" "Every manifest entry explicitly declares"

require_line ".agents/skills/market-data-fetch/SKILL.md" "all-market JSON response"
require_line ".agents/skills/market-data-fetch/SKILL.md" "market/tdcc-holding-distribution.json"
reject_line ".agents/skills/market-data-fetch/SKILL.md" "all-market CSV"
reject_line ".agents/skills/market-data-fetch/SKILL.md" "tdcc-holding-distribution.csv"

require_line ".agents/skills/research-html-output/SKILL.md" "scripts/build_research_summary.py --case companies/<ticker-slug>"
require_line ".agents/skills/research-html-output/SKILL.md" "scripts/render_research_html.py --case companies/<ticker-slug>"
require_line ".agents/skills/research-html-output/SKILL.md" "templates/research-summary-data.schema.json"

require_line "templates/research-summary-data.schema.json" '"schema_version": { "const": 2 }'
require_line "templates/research-summary-data.schema.json" '"root"'
require_line "templates/research-html-summary.html" "{{SCHEMA_VERSION}}"
require_line "templates/research-html-summary.html" "{{SOURCE_MANIFEST_ROWS}}"
require_line "templates/research-html-summary.html" "{{DISCLAIMER_LINK}}"

require_line "templates/active-decisions.md" "## Expected Evidence Timeline"
require_line "templates/active-decisions.md" "## Thesis Kill Criteria"
require_line "templates/open-questions.md" "## Active Questions"
require_line "templates/investment-memo.md" "## Expectation Gap Analysis"
require_line "templates/market-action-read.md" "## Egg Theory Read"
require_line "templates/quality-and-valuation-check.md" "## Better Source Checklist"

if grep -R -n -- "verify=False" "$ROOT_DIR/scripts"; then
  printf 'Production script still disables TLS verification.\n' >&2
  exit 1
fi

if grep -R -n --exclude-dir=__pycache__ -- "migrate_case_metadata\|legacy_v0\|version_mismatch" "$ROOT_DIR/scripts" "$ROOT_DIR/templates" "$ROOT_DIR/.agents"; then
  printf 'Backward-compatibility contract residue found.\n' >&2
  exit 1
fi

printf 'All template structure checks passed.\n'
