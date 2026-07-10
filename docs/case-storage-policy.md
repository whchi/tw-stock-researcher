# Case Storage Policy

## Case Artifacts Are Local, Private Session Data — Not Source Code

Everything under `companies/<ticker>-<slug>/` is git-ignored by design
(`.gitignore`: `companies/**/*.md`, `companies/**/*.json`). This policy
document explains that boundary; it does not change it. Do not remove
those ignore rules as part of implementing this policy.

- The repository (scripts, templates, docs, tests) is the versioned
  system of record for *how* research is conducted.
- A case folder is the versioned-nowhere record of *one specific research
  session's findings* for one stock: scraped data, derived metrics, the
  analyst's (or agent's) written facts/inference/open questions, and any
  personal position context the user has shared.
- This split exists so that: (a) case data — which may include a user's
  actual holdings — never becomes part of the repository's git history or
  any future public sharing of the codebase, and (b) upgrading the
  workflow contract, templates, or fetchers never requires editing or
  regenerating dozens of case folders in lockstep.

## Backup, Export, And Retention

Because case data lives only on the local filesystem, the user is
responsible for its durability. This project does not provide an
automated backup mechanism. Recommended practice:

- **Backup**: if a case folder matters beyond the current machine, copy
  `companies/<ticker>-<slug>/` to encrypted local storage or an
  encrypted archive before wiping a machine or losing disk access.
  Because these files may include a user's actual position size or cost
  basis (see below), do not sync case folders to shared or non-encrypted
  cloud storage.
- **Export**: `companies/<ticker>-<slug>/research-summary.html` (built by
  `scripts/render_research_html.py`) is the one artifact designed to be
  shared as a self-contained snapshot. `scripts/build_research_summary.py`
  only reads from a fixed, reviewed source map — it never includes
  `yahoo-data.json` or anything tagged `distribution: restricted` in a
  `shareable` payload (see `docs/source-policy.md` and
  `scripts/research_summary_contract.py`). Prefer exporting that HTML
  file over copying raw case JSON/Markdown if the goal is to share
  findings with someone else.
- **Retention**: there is no enforced expiry. A case is stale evidence,
  not wrong evidence — `scripts/workflow_state.py`'s `stage_records`
  already marks a stage `stale` when an upstream input changes, and
  `open-questions.md` tracks `Next Check` dates per open question. Delete
  a case folder only by explicit user request (see Red Lines below); this
  project does not auto-delete old cases.

## User-Provided Position Context

When a user shares their own actual position (shares held, cost basis,
entry rationale), that text is **user-provided position context**, not a
model-generated recommendation, and must be labeled as such wherever it
is recorded (`active-decisions.md` per `AGENTS.md`'s Disclaimer
Discipline). This is a data-handling rule, not just a wording rule:

- Store it only inside the case's own git-ignored files; never promote it
  into a repo-tracked file (template, doc, or test fixture).
- Never let position context leak into a `shareable` research-summary
  payload as if it were a scenario or a target price — `validate_summary`
  in `scripts/research_summary_contract.py` rejects scenario/valuation
  fields that look like fabricated targets, but it cannot detect prose
  smuggled into a free-text field, so this remains a writing-discipline
  rule for whichever stage writes `active-decisions.md`.

## Read-Only Migration Auditing

`scripts/migrate_case_metadata.py --all --dry-run` (or `--case CASE_DIR
--dry-run`) reports drift between an existing case and the current
`stock-meta.json` / `open-questions.md` / `research-summary-data.json`
contracts: missing or unknown metadata keys, mixed or dangling
`file_references` paths, absent `stage_records` (a pre-workflow-state
case), legacy open-question table shapes, and legacy or version-mismatched
HTML render payloads.

- This command never writes to a case. There is intentionally no
  `--apply` in this release.
- A future change may add a per-case `--apply`, but only after the user
  has reviewed the dry-run report for that specific case and explicitly
  approved the exact migration targets — the same approval discipline
  `AGENTS.md`'s Red Lines already require for any destructive or
  irreversible operation.
- CI (`.github/workflows/verify.yml`) never runs this command and never
  reads `companies/**`; it only runs the repository's own structure and
  unit tests, which use fixtures under `tests/fixtures/`, not real case
  data.

## Do Not

- Do not remove or narrow the `companies/**` `.gitignore` rules as part
  of implementing this policy.
- Do not commit a case folder's contents to git, even temporarily, to
  "share progress" — use the exported HTML instead.
- Do not add an automated `--apply` migration path without a per-case,
  explicit user approval step.
- Do not let CI depend on `FIN_MIND_TOKEN`, live network access, or the
  contents of any real `companies/**` case.
