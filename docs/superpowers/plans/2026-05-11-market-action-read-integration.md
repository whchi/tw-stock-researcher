# Market Action Read Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class market-action layer that summarizes 1D/3D/5D price, volume, and institutional flow evidence without producing trading instructions.

**Architecture:** Keep FinMind raw and derived data in `market-data.json`; add `market-action-read.md` as the human-readable research layer. Extend existing pure functions in `scripts/fetch_finmind.py` so tests cover window calculations without live API calls.

**Tech Stack:** Python standard library, `requests` only for live fetching, `unittest`, markdown templates.

---

## File Structure

- Modify: `scripts/fetch_finmind.py` to add 1D/3D/5D derived windows.
- Modify: `tests/test_fetch_finmind.py` to test 1D/3D/5D price, volume, and institutional flows.
- Create: `templates/market-action-read.md` as the canonical market-action read shape.
- Modify: `templates/stock-meta.json` to include `market_action_read`.
- Modify: `docs/data-layout.md`, `AGENTS.md`, and `README.md` to document the new case file.
- Modify: `tests/structure/test_templates.sh` to verify the new template.
- Create: `companies/6706-whit/market-action-read.md` using existing `market-data.json`.
- Modify: `companies/6706-whit/stock-meta.json` to reference the new case file.

### Task 1: Add Failing Tests For Windowed Market Data

- [ ] Add assertions to `tests/test_fetch_finmind.py` proving `build_market_action_read()` returns `windows["1d"]`, `windows["3d"]`, and `windows["5d"]` with price change, volume change, price-volume labels, and institutional net flow by window.
- [ ] Run `/var/folders/bp/54b6dx9147zb517pxxstwv300000gn/T/opencode/goodinfo-venv/bin/python -m unittest tests/test_fetch_finmind.py -v`.
- [ ] Confirm the new test fails because `windows` is not implemented yet.

### Task 2: Implement Windowed Derivations

- [ ] Add helper functions in `scripts/fetch_finmind.py` to filter institutional rows between comparison date exclusive and latest date inclusive.
- [ ] Add a helper that builds one window for `1d`, `3d`, and `5d` using trading-row offsets.
- [ ] Preserve existing top-level 5D fields for compatibility while adding `derived.market_action_read.windows`.
- [ ] Run `/var/folders/bp/54b6dx9147zb517pxxstwv300000gn/T/opencode/goodinfo-venv/bin/python -m unittest tests/test_fetch_finmind.py -v` and confirm it passes.

### Task 3: Add Architecture Template And Docs

- [ ] Create `templates/market-action-read.md` with disclaimer, current market read, 1D/3D/5D table, institutional flow table, interpretation, watch conditions, and next validation sections.
- [ ] Add `market_action_read` to `templates/stock-meta.json`.
- [ ] Update `docs/data-layout.md`, `AGENTS.md`, and `README.md` to document `market-action-read.md` and `market-data.json`.
- [ ] Update `tests/structure/test_templates.sh` to require core headings in `templates/market-action-read.md` and the new metadata reference.

### Task 4: Add 6706 Market Action Read

- [ ] Read `companies/6706-whit/market-data.json` and calculate 1D/3D/5D comparison values from the existing rows.
- [ ] Create `companies/6706-whit/market-action-read.md` with neutral research language and no buy/sell recommendations.
- [ ] Update `companies/6706-whit/stock-meta.json` with `market_action_read`.

### Task 5: Verify

- [ ] Run `/var/folders/bp/54b6dx9147zb517pxxstwv300000gn/T/opencode/goodinfo-venv/bin/python -m unittest discover -s tests -v`.
- [ ] Run `sh tests/structure/test_templates.sh`.
- [ ] Search new market-action files for prohibited recommendation wording.
- [ ] Review `git diff --stat` and changed file list.
