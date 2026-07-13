# Data Freshness Defaults

These are research-workflow defaults, not claims about a data provider's update guarantee. A material filing, revenue release, market event, or explicit user request overrides the age threshold.

## Default thresholds

| Artifact | Stale after | Refresh trigger |
| --- | ---: | --- |
| `yahoo-data.json` | 90 days | New company event or profile change |
| `raw-data.json` | 120 days | New annual filing or financial-analysis refresh |
| `fundamentals-data.json` | 45 days | New monthly revenue, quarterly statement, or valuation-band update |
| `market-data.json` | 7 calendar days | Any market-action read or new market event |
| `tdcc-data.json` | 10 calendar days | Weekly ownership snapshot or holder-structure question |
| `market/shared-macro-data.json` | 35 days | New macro release or macro-map refresh |

## Rules

- Missing `metadata.fetched_at` is stale unless the file explicitly records an unavailable or intentionally reused source.
- A refresh is not required merely because a file is old when the workflow records why the existing evidence remains fit for the current question.
- `case-revisit` reports the file date, threshold, and reason for reuse or refresh.
- `market-data-fetch` retains the TDCC provider cache rule (`--max-age-hours`) in addition to the case-artifact threshold above.
- When a source fails, keep the last successful artifact, record the failure and timestamp, and label conclusions that depend on it as lower confidence.
