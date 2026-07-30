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

- Missing `metadata.fetched_at` or `metadata.data_availability` fails the current data contract.
- Do not reuse an older artifact to satisfy a current refresh. A requested refresh must produce a current-schema artifact from that run.
- `case-revisit` reports the file date, threshold, `observation_date`, availability status, and confidence impact.
- `market-data-fetch` retains the TDCC provider cache rule (`--max-age-hours`) in addition to the case-artifact threshold above.
- Provider failure is a data limitation, not a negative company signal.
- `partial` requires a visible missing-input note and confidence downgrade.
- `unavailable` blocks every conclusion that depends on that evidence layer.
- A failed refresh leaves any prior file outside the current workflow evidence set; the stage remains incomplete until the source succeeds or the user explicitly removes that evidence layer from scope.
