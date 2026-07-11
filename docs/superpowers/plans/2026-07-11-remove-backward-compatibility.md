# Remove Backward Compatibility Implementation Plan

> **For agentic workers:** Execute inline with TDD; do not preserve legacy case formats.

**Goal:** Make every runtime and validation path accept only the current workflow, stage-record, question-ledger, and research-summary contracts.

**Architecture:** Delete the read-only legacy migration subsystem. Tighten the remaining validators so missing current fields are invalid instead of receiving defaults or legacy classifications. Keep source degradation and provenance versions because they are current operational contracts, not backward compatibility.

**Tech Stack:** Python 3, `unittest`, Markdown/JSON contracts.

## Global Constraints

- Preserve all unrelated and previously approved uncommitted changes.
- Do not remove `schema_version`, `template_version`, or `parser_version`.
- Do not remove source fallbacks, optional-source degradation, or upstream field normalization.
- Delete only the migration files explicitly approved by the user.
- Write behavior tests before tightening production code.

### Task 1: Require the current research-summary manifest shape

**Files:**
- Modify: `tests/test_research_summary_contract.py`
- Modify: `tests/test_build_research_summary.py`
- Modify: `scripts/research_summary_contract.py`
- Modify: `scripts/build_research_summary.py`
- Modify: `scripts/validate_research_summary.py`
- Modify: `templates/research-summary-data.schema.json`
- Modify: `tests/fixtures/research-summary-v1/expected-data.json`

- [ ] Add tests proving a manifest entry without `root` is invalid.
- [ ] Run the focused tests and confirm the old default makes them fail.
- [ ] Require `root` on every manifest entry and remove `entry.get("root", "case")`.
- [ ] Run summary builder, contract, renderer, and validator tests.

### Task 2: Require the current workflow stage-record shape

**Files:**
- Modify: `tests/test_workflow_state.py`
- Modify: `scripts/workflow_state.py`
- Modify current workflow fixtures only if their records lack required fields.

- [ ] Add tests proving dependency records without `input_hashes` or `output_hashes` fail closed.
- [ ] Run the focused tests and confirm legacy records are currently accepted.
- [ ] Validate the current stage-record keys before reading hashes.
- [ ] Run all workflow-state tests.

### Task 3: Delete the migration subsystem

**Files:**
- Delete: `scripts/migrate_case_metadata.py`
- Delete: `tests/test_migrate_case_metadata.py`
- Delete: `tests/fixtures/migrate-case-metadata/current-template/open-questions.md`
- Delete: `tests/fixtures/migrate-case-metadata/current-template/stock-meta.json`
- Delete: `tests/fixtures/migrate-case-metadata/malformed/research-summary-data.json`
- Delete: `tests/fixtures/migrate-case-metadata/malformed/stock-meta.json`
- Delete: `tests/fixtures/migrate-case-metadata/old-template/open-questions.md`
- Delete: `tests/fixtures/migrate-case-metadata/old-template/research-summary-data.json`
- Delete: `tests/fixtures/migrate-case-metadata/old-template/stock-meta.json`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/case-storage-policy.md`
- Modify: `docs/data-layout.md`
- Modify: `scripts/validate_research_summary.py`

- [ ] Delete the approved migration files and fixtures.
- [ ] Remove migration/legacy audit documentation and special `legacy_v0` classification.
- [ ] Keep current-schema rejection and stale-manifest validation.
- [ ] Search the repository for dangling migration and legacy references.

### Task 4: Verify the strict current-only contract

- [ ] Run `git diff --check`.
- [ ] Run `.venv/bin/python -m compileall -q scripts tests`.
- [ ] Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`.
- [ ] Run current CLI help and read-only summary audit commands.
- [ ] Review the final diff for unrelated deletions and compatibility defaults.
