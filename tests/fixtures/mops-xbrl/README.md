# MOPS XBRL Fixtures — Not Present

This directory intentionally contains no sample XBRL instance documents.

See `docs/adr/0001-mops-xbrl-ingestion.md` for the full decision. Summary:
TWSE's terms of use prohibit automated retrieval of MOPS content without
consent, the only sanctioned automated channel is a paid subscription
(`套裝五 XBRL`, NT$40,000/month) that is disproportionate to this project's
one-stock-at-a-time scope, and this project does not scrape around that
gate. The current decision is `manual_only` — no production XBRL fetcher
exists in `scripts/`, and none should be added while that ADR stands.

## If a future ADR reopens this decision

A local parser feasibility spike (one general issuer, one financial
issuer, one mixed-industry issuer, eight quarters each) needs real sample
instance documents. To add them here without violating TWSE's terms:

1. A human manually downloads individual filings through the MOPS web UI
   (`https://mops.twse.com.tw`), the same way a person doing manual
   research already would — not through any automated tool or script.
2. Alternatively, acquire the paid `套裝五 XBRL` feed
   (`https://eshop.twse.com.tw/zh/mops/list`) and export sample filings
   from that contractual channel.
3. Record each sample's source filing id, company, period, consolidation
   scope (individual / entity / consolidated), and taxonomy version
   alongside the file.
4. Re-run the technical feasibility checks from
   `docs/adr/0001-mops-xbrl-ingestion.md` Step 2 (instant/duration
   context, consolidated vs. individual scope, cumulative vs.
   single-quarter conversion, taxonomy version/extensions, duplicate
   facts, units, restatements) against the real samples before writing a
   new ADR.

Do not add sample files obtained by scripted or scraped retrieval from
`mops.twse.com.tw`.
