

# First Run

Read [DISCLAIMER.md](DISCLAIMER.md)

0. Make sure `python` and `uv` are installed on your system.
1. Clone the repo as your stock research workspace.
2. Initialize a repo-local virtual environment and install scraper dependencies inside it:

```bash
uv venv
source .venv/bin/activate
uv pip add requests beautifulsoup4
```

   `requests` is required by the fetch scripts, and `beautifulsoup4` provides `bs4` for Goodinfo scraping.
3. Pick one stock and create a case.
4. Run the workflow in this order (matches `workflow-contract.json`; checked by `tests/test_workflow_contract.py`):
   stock-case-init -> yahoo-profile-financials -> financial-data-fetch -> market-data-fetch -> company-deep-dive -> financial-analysis -> industry-transmission-analysis -> macro-impact-analysis -> market-action-read -> quality-and-valuation-check -> investment-thesis -> session-wrap -> research-html-output
5. Use signal-update for new events.
6. Use case-revisit when you return later, then session-wrap to close the session — session-wrap is the terminal gate before HTML output.

Use public and free sources first. Keep source notes in the case files as you go so later updates stay grounded.
