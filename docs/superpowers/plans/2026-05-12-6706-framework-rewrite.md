# 6706 Framework Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the `6706-whit` case files into full compliance with `investment-reasoning-framework.md` without expanding scope beyond this case.

**Architecture:** Keep the change file-local and evidence-driven. Rewrite `investment-memo.md` around the framework's decision order, then sync only the dependent files that carry live stance or unresolved-question state. Do a final language and consistency sweep before reporting completion.

**Tech Stack:** Markdown case files, JSON-backed research artifacts, FinMind and MOPS sourced evidence, `apply_patch`, `grep`

---

### Task 1: Persist Design Artifacts

**Files:**
- Create: `docs/superpowers/specs/2026-05-12-6706-framework-rewrite-design.md`
- Create: `docs/superpowers/plans/2026-05-12-6706-framework-rewrite.md`

- [ ] **Step 1: Add the design doc**

Create a spec that records scope, evidence base, recommended approach, planned document structure, risks, and success criteria for the `6706` rewrite.

- [ ] **Step 2: Add the implementation plan**

Create this plan file so later sessions can see the exact intended workflow and touched files.

### Task 2: Rewrite The Memo Around The Framework

**Files:**
- Modify: `companies/6706-whit/investment-memo.md`
- Read for alignment: `investment-reasoning-framework.md`
- Read for evidence: `companies/6706-whit/financial-analysis.md`
- Read for evidence: `companies/6706-whit/market-action-read.md`

- [ ] **Step 1: Replace the memo structure**

Reorder the memo to follow the framework:

```markdown
## Current View
## Dual Framework
### Business Thesis
### Pricing Thesis
## Recent 6M Evidence Layer
## Stage Judgment
## Market Regime Link
## Checklist Read
## Scenario Analysis
## Monitoring Signals
## Critical Unresolved Question
## Sources
```

- [ ] **Step 2: Insert explicit 6M evidence**

Use these exact numbers in the memo:

```text
2025-11-03 close 69.2
2025-11-04 close 66.1
2026-05-05 close 183.0
2026-05-11 close 168.5
6M change +143.50%
rebound from low to last +154.92%
drawdown from high to last -7.92%
latest PBR 3.45
6M PBR band 1.36x to 3.75x
```

- [ ] **Step 3: Make the event layer evidence-safe**

State directly that the repo currently lacks captured broker target-price records for `6706`, so the usable evidence is limited to public product/showcase activity plus the visible price-volume expansion in early May 2026.

- [ ] **Step 4: Expand scenario sections**

For each of `Bull`, `Base`, and `Bear`, include:

```markdown
- Probability weight:
- Assumptions:
- Why the recent 6M evidence does or does not support it:
- Validation triggers:
- Structure-break condition:
- Scenario-derived price range:
```

### Task 3: Sync The Live Stance Files

**Files:**
- Modify: `companies/6706-whit/active-decisions.md`
- Modify: `companies/6706-whit/open-questions.md`
- Modify: `companies/6706-whit/signal-log.md`

- [ ] **Step 1: Update active decisions**

Reflect the refined stance:

```text
late Stage 1 / not yet Stage 2
valuation still near top of 6M P/B band
watch for revenue and margin confirmation, not just narrative continuity
```

- [ ] **Step 2: Update open questions**

Ensure at least one question asks whether `3x+` book-value valuation can persist if EPS and operating cash flow remain unverified.

- [ ] **Step 3: Append signal-log entry**

Add a dated note that the framework rewrite reclassified the stock from generic turnaround watch to explicit late-Stage-1 pricing with elevated `price-in risk`.

### Task 4: Verify Compliance

**Files:**
- Verify: `companies/6706-whit/investment-memo.md`
- Verify: `companies/6706-whit/active-decisions.md`
- Verify: `companies/6706-whit/open-questions.md`
- Verify: `companies/6706-whit/signal-log.md`

- [ ] **Step 1: Search for prohibited language**

Run a repo-local content search for banned recommendation terms in the changed `6706` files.

- [ ] **Step 2: Check framework coverage**

Read back the changed files and confirm the memo contains:

```text
Dual Framework
Recent 6M Evidence Layer
Stage Judgment
Market Regime Link
Checklist Read
Bull/Base/Bear with validation trigger and structure-break condition
```

- [ ] **Step 3: Summarize remaining risks**

If any evidence remains unavailable, document that as a residual gap rather than implying certainty.
