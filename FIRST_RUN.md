

# First Run

Read [DISCLAIMER.md](DISCLAIMER.md)

0. Make sure `python` and `uv` are installed on your system.
1. Clone the repo as your stock research workspace.
2. Initialize a repo-local virtual environment and install scraper dependencies inside it:

```bash
uv venv
source .venv/bin/activate
uv pip install requests beautifulsoup4
```

   `requests` is required by the fetch scripts, and `beautifulsoup4` provides `bs4` for Goodinfo scraping.
3. Pick one stock and create a case.
4. Run the workflow in this order:
   stock-case-init -> yahoo-profile-financials -> company-deep-dive -> financial-analysis -> industry-transmission-analysis -> macro-impact-analysis -> quality-and-valuation-check -> investment-thesis -> market-data-fetch -> market-action-read -> automatic research-html-output
5. Before `market-data-fetch`, set `FIN_MIND_TOKEN` in the environment when FinMind access is required.
6. Use `signal-update` for new events.
7. Use `case-revisit` when you return to an existing case.
8. Use `session-wrap` before ending each research session.

Use public and free sources first. Keep source notes in the case files as you go so later updates stay grounded.
