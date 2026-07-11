#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

skills="
stock-case-init
yahoo-profile-financials
financial-data-fetch
company-deep-dive
financial-analysis
industry-transmission-analysis
macro-impact-analysis
quality-and-valuation-check
investment-thesis
market-data-fetch
market-action-read
research-html-output
signal-update
case-revisit
session-wrap
"

for skill in $skills; do
  file="$ROOT_DIR/.agents/skills/$skill/SKILL.md"
  if [ ! -f "$file" ]; then
    printf 'Missing skill file: %s\n' ".agents/skills/$skill/SKILL.md" >&2
    exit 1
  fi
  if ! grep -Fq "name: $skill" "$file"; then
    printf 'Skill frontmatter name mismatch: %s\n' ".agents/skills/$skill/SKILL.md" >&2
    exit 1
  fi
  if ! grep -Fq "\`$skill\`" "$ROOT_DIR/README.md"; then
    printf 'README does not list skill: %s\n' "$skill" >&2
    exit 1
  fi
done

printf 'All project skill checks passed.\n'
