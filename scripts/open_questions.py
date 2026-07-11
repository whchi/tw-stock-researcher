#!/usr/bin/env python3
"""Evidence-backed open-question ledger.

Validates, upserts, and resolves rows in a case's open-questions.md against
the canonical stage/question-namespace contract in workflow-contract.json.
A stage may only create, update, or resolve questions in its own namespace;
session-wrap may never resolve a question. Closing a question requires
evidence, a source as-of date, and a reopen trigger — an agent writing a
resolution sentence is not, by itself, a closure.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomic_io import atomic_write_text  # noqa: E402
from markdown_contract import (  # noqa: E402
    MarkdownContractError,
    extract_table_under_heading,
    normalize_text,
    render_pipe_table,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "workflow-contract.json"

STATUSES = ("open", "waiting_external", "blocked", "resolved", "superseded")
ACTIVE_HEADING = "Active Questions"
RESOLVED_HEADING = "Resolved Questions"
ACTIVE_HEADERS = [
    "ID", "Origin Stage", "Priority", "Status", "Blocking Stage", "Question",
    "Why It Matters", "Resolve When", "Evidence Refs", "Next Check", "Last Checked",
]
RESOLVED_HEADERS = [
    "ID", "Resolution", "Evidence Refs", "Evidence As Of", "Resolved By Stage",
    "Closed On", "Reopen Trigger",
]
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _load_contract():
    with open(CONTRACT_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def _stages_by_id(contract):
    return {stage["id"]: stage for stage in contract["stages"]}


def _namespaces(contract):
    return {
        stage["question_namespace"]: stage["id"]
        for stage in contract["stages"]
        if stage.get("question_namespace")
    }


def _namespace_of(question_id, namespaces):
    for namespace in sorted(namespaces, key=len, reverse=True):
        if question_id == namespace or question_id.startswith(namespace + "-"):
            return namespace
    return None


def _own_namespace(stage, namespaces):
    for namespace, owning_stage in namespaces.items():
        if owning_stage == stage:
            return namespace
    return None


def _sort_key(row):
    priority = row.get("Priority", "").strip().lower()
    return (PRIORITY_RANK.get(priority, 99), row.get("ID", ""))


def validate_ledger(text, contract):
    text = normalize_text(text)
    issues = []
    stage_ids = set(_stages_by_id(contract))
    namespaces = _namespaces(contract)

    try:
        active_headers, active_rows = extract_table_under_heading(text, ACTIVE_HEADING)
    except MarkdownContractError as exc:
        issues.append(str(exc))
        active_rows = []
    else:
        if active_headers != ACTIVE_HEADERS:
            issues.append(f"active table headers do not match the canonical shape: {active_headers}")

    try:
        resolved_headers, resolved_rows = extract_table_under_heading(text, RESOLVED_HEADING)
    except MarkdownContractError as exc:
        issues.append(str(exc))
        resolved_rows = []
    else:
        if resolved_headers != RESOLVED_HEADERS:
            issues.append(f"resolved table headers do not match the canonical shape: {resolved_headers}")

    seen_ids = set()

    for row in active_rows:
        qid = row.get("ID", "").strip()
        if not qid:
            issues.append("active row missing ID")
            continue
        if qid in seen_ids:
            issues.append(f"duplicate id: {qid}")
        seen_ids.add(qid)
        if _namespace_of(qid, namespaces) is None:
            issues.append(f"unknown namespace for id: {qid}")
        origin = row.get("Origin Stage", "").strip()
        if origin not in stage_ids:
            issues.append(f"unknown origin stage for {qid}: {origin!r}")
        status_value = row.get("Status", "").strip()
        if status_value not in STATUSES:
            issues.append(f"unknown status for {qid}: {status_value!r}")
        blocking = row.get("Blocking Stage", "").strip()
        if blocking and blocking not in stage_ids:
            issues.append(f"unknown blocking stage for {qid}: {blocking!r}")

    for row in resolved_rows:
        qid = row.get("ID", "").strip()
        if not qid:
            issues.append("resolved row missing ID")
            continue
        if qid in seen_ids:
            issues.append(f"duplicate id: {qid}")
        seen_ids.add(qid)
        if _namespace_of(qid, namespaces) is None:
            issues.append(f"unknown namespace for id: {qid}")
        if not row.get("Evidence Refs", "").strip():
            issues.append(f"missing resolution evidence for {qid}")
        if not row.get("Evidence As Of", "").strip():
            issues.append(f"missing evidence as-of for {qid}")
        if not row.get("Reopen Trigger", "").strip():
            issues.append(f"missing reopen trigger for {qid}")
        resolver = row.get("Resolved By Stage", "").strip()
        if resolver == "session-wrap":
            issues.append(f"session-wrap may not resolve questions: {qid}")
        elif resolver not in stage_ids:
            issues.append(f"unknown resolver stage for {qid}: {resolver!r}")

    return issues


def _replace_table(text, heading, headers, rows, level=2):
    marker = "#" * level + " " + heading
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.rstrip("\n") == marker:
            start = i + 1
            break
    if start is None:
        raise MarkdownContractError(f"heading not found: {marker!r}")

    heading_re = re.compile(r"^#{1,%d}\s" % level)
    section_end = len(lines)
    for i in range(start, len(lines)):
        if heading_re.match(lines[i]):
            section_end = i
            break

    table_start = None
    for i in range(start, section_end):
        if lines[i].lstrip().startswith("|"):
            table_start = i
            break
    if table_start is None:
        raise MarkdownContractError(f"no table found under heading: {marker!r}")

    table_end = section_end
    for i in range(table_start, section_end):
        if not lines[i].lstrip().startswith("|"):
            table_end = i
            break

    new_table_text = render_pipe_table(headers, rows)
    new_lines = lines[:table_start] + [new_table_text] + lines[table_end:]
    return "".join(new_lines)


def upsert_question(
    case_dir,
    *,
    contract,
    question_id,
    stage,
    priority,
    question,
    resolve_when,
    next_check,
    why_it_matters="",
    blocking_stage="",
    evidence_refs="",
    as_of=None,
):
    case_dir = Path(case_dir)
    path = case_dir / "open-questions.md"
    text = normalize_text(path.read_text(encoding="utf-8"))

    namespaces = _namespaces(contract)
    own_namespace = _own_namespace(stage, namespaces)
    if own_namespace is None:
        raise ValueError(f"unknown stage: {stage!r}")
    if _namespace_of(question_id, namespaces) != own_namespace:
        raise ValueError(
            f"stage {stage!r} may only upsert questions in its own namespace "
            f"{own_namespace!r}, got id {question_id!r}"
        )

    _, active_rows = extract_table_under_heading(text, ACTIVE_HEADING)
    _, resolved_rows = extract_table_under_heading(text, RESOLVED_HEADING)

    if any(row["ID"] == question_id for row in resolved_rows):
        raise ValueError(f"question {question_id!r} is already resolved")

    existing = next((row for row in active_rows if row["ID"] == question_id), None)
    if existing is not None and existing["Origin Stage"] != stage:
        raise ValueError(
            f"question {question_id!r} was created by {existing['Origin Stage']!r}; "
            f"{stage!r} may not change its origin stage"
        )

    as_of = as_of or date.today().isoformat()
    new_row = {
        "ID": question_id,
        "Origin Stage": stage,
        "Priority": priority,
        "Status": existing["Status"] if existing else "open",
        "Blocking Stage": blocking_stage or (existing.get("Blocking Stage", "") if existing else ""),
        "Question": question,
        "Why It Matters": why_it_matters or (existing.get("Why It Matters", "") if existing else ""),
        "Resolve When": resolve_when,
        "Evidence Refs": evidence_refs or (existing.get("Evidence Refs", "") if existing else ""),
        "Next Check": next_check,
        "Last Checked": as_of,
    }

    active_rows = [row for row in active_rows if row["ID"] != question_id]
    active_rows.append(new_row)
    active_rows.sort(key=_sort_key)

    new_text = _replace_table(text, ACTIVE_HEADING, ACTIVE_HEADERS, active_rows)

    issues = validate_ledger(new_text, contract)
    if issues:
        raise ValueError(f"upsert would produce an invalid ledger: {issues}")

    atomic_write_text(path, new_text)
    return new_row


def resolve_question(
    case_dir,
    *,
    contract,
    question_id,
    stage,
    evidence,
    as_of,
    resolution,
    reopen_trigger,
):
    if stage == "session-wrap":
        raise ValueError("session-wrap may not resolve questions")

    case_dir = Path(case_dir)
    path = case_dir / "open-questions.md"
    text = normalize_text(path.read_text(encoding="utf-8"))

    namespaces = _namespaces(contract)
    own_namespace = _own_namespace(stage, namespaces)
    if own_namespace is None:
        raise ValueError(f"unknown stage: {stage!r}")
    if _namespace_of(question_id, namespaces) != own_namespace:
        raise ValueError(
            f"stage {stage!r} may only resolve questions in its own namespace {own_namespace!r}"
        )

    _, active_rows = extract_table_under_heading(text, ACTIVE_HEADING)
    _, resolved_rows = extract_table_under_heading(text, RESOLVED_HEADING)

    if not any(row["ID"] == question_id for row in active_rows):
        raise ValueError(f"unknown active question id: {question_id!r}")

    remaining_active = [row for row in active_rows if row["ID"] != question_id]

    new_resolved_row = {
        "ID": question_id,
        "Resolution": resolution,
        "Evidence Refs": evidence,
        "Evidence As Of": as_of,
        "Resolved By Stage": stage,
        "Closed On": date.today().isoformat(),
        "Reopen Trigger": reopen_trigger,
    }
    resolved_rows = resolved_rows + [new_resolved_row]
    resolved_rows.sort(key=lambda row: row["ID"])

    new_text = _replace_table(text, ACTIVE_HEADING, ACTIVE_HEADERS, remaining_active)
    new_text = _replace_table(new_text, RESOLVED_HEADING, RESOLVED_HEADERS, resolved_rows)

    issues = validate_ledger(new_text, contract)
    if issues:
        raise ValueError(f"resolve would produce an invalid ledger: {issues}")

    atomic_write_text(path, new_text)
    return new_resolved_row


# Deterministic resolver hooks: pure predicates over already-fetched JSON
# evidence. Each returns {"ready": bool, "evidence_ref": str, "reason": str}
# so a caller can decide whether to call resolve_question with that same
# evidence_ref, rather than an agent inventing a resolution by prose alone.
# Every resolver here closes only its own namespace (FIN-DATA, MKT-DATA, or
# MAC) and only when the stated predicate is actually true.


def resolve_three_statement_coverage(raw_data):
    """FIN-DATA: closes when Goodinfo's annual three-statement baseline has no required fields missing."""
    coverage = raw_data.get("three_statement_coverage") or {}
    required_missing = coverage.get("required_missing") or []
    ready = not required_missing
    reason = "no required fields missing" if ready else f"missing: {required_missing}"
    return {"ready": ready, "evidence_ref": "raw-data.json#/three_statement_coverage", "reason": reason}


def resolve_monthly_revenue_period(fundamentals_data, min_rows=1):
    """FIN-DATA: closes when the official monthly-revenue window has at least min_rows periods."""
    monthly = ((fundamentals_data.get("derived") or {}).get("monthly_revenue_6m")) or []
    ready = len(monthly) >= min_rows
    latest_period = monthly[-1].get("period") if monthly else None
    return {
        "ready": ready,
        "evidence_ref": "fundamentals-data.json#/derived/monthly_revenue_6m",
        "reason": f"{len(monthly)} monthly revenue rows (need >= {min_rows}), latest period {latest_period!r}",
    }


def resolve_valuation_band_readiness(fundamentals_data):
    """FIN-DATA: closes when derived.valuation_band.status == 'ready'."""
    band = (fundamentals_data.get("derived") or {}).get("valuation_band") or {}
    status_value = band.get("status")
    ready = status_value == "ready"
    return {
        "ready": ready,
        "evidence_ref": "fundamentals-data.json#/derived/valuation_band",
        "reason": f"status={status_value!r}",
    }


def resolve_market_price_window(market_data, min_rows):
    """MKT-DATA: closes when raw.price has at least min_rows rows for the requested window."""
    rows = (market_data.get("raw") or {}).get("price") or []
    ready = len(rows) >= min_rows
    return {
        "ready": ready,
        "evidence_ref": "market-data.json#/raw/price",
        "reason": f"{len(rows)} price rows (need >= {min_rows})",
    }


def resolve_market_price_5d_window(market_data):
    """MKT-DATA: closes when there are enough price rows for a 5-day window read."""
    return resolve_market_price_window(market_data, min_rows=5)


def resolve_market_history_6m_window(market_data):
    """MKT-DATA: closes when there are enough price rows (~120 trading days) for a 6-month read."""
    return resolve_market_price_window(market_data, min_rows=120)


def resolve_tdcc_history_length(tdcc_data, min_entries=1):
    """MKT-DATA: closes when the accumulated weekly TDCC history has at least min_entries snapshots."""
    history = tdcc_data.get("history") or []
    ready = len(history) >= min_entries
    return {
        "ready": ready,
        "evidence_ref": "tdcc-data.json#/history",
        "reason": f"{len(history)} history snapshots (need >= {min_entries})",
    }


def resolve_macro_variable_readiness(macro_data, source_name):
    """MAC: closes when the named macro source has at least one record with a populated latest read."""
    records = (macro_data.get("sources") or {}).get(source_name) or []
    ready = any(record.get("latest") for record in records)
    return {
        "ready": ready,
        "evidence_ref": f"shared-macro-data.json#/sources/{source_name}",
        "reason": f"{len(records)} records for {source_name!r}, ready={ready}",
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("path")

    upsert_parser = subparsers.add_parser("upsert")
    upsert_parser.add_argument("case_dir")
    upsert_parser.add_argument("--id", dest="question_id", required=True)
    upsert_parser.add_argument("--stage", required=True)
    upsert_parser.add_argument("--priority", required=True)
    upsert_parser.add_argument("--question", required=True)
    upsert_parser.add_argument("--why-it-matters", default="")
    upsert_parser.add_argument("--resolve-when", required=True)
    upsert_parser.add_argument("--next-check", required=True)
    upsert_parser.add_argument("--blocking-stage", default="")
    upsert_parser.add_argument("--evidence-refs", default="")
    upsert_parser.add_argument("--as-of")

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("case_dir")
    resolve_parser.add_argument("--id", dest="question_id", required=True)
    resolve_parser.add_argument("--stage", required=True)
    resolve_parser.add_argument("--evidence", required=True)
    resolve_parser.add_argument("--as-of", required=True)
    resolve_parser.add_argument("--resolution", required=True)
    resolve_parser.add_argument("--reopen-trigger", required=True)

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    contract = _load_contract()

    if args.command == "validate":
        text = normalize_text(Path(args.path).read_text(encoding="utf-8"))
        issues = validate_ledger(text, contract)
        if issues:
            for issue in issues:
                print(f"- {issue}", file=sys.stderr)
            return 1
        print("valid")
        return 0

    if args.command == "upsert":
        try:
            row = upsert_question(
                args.case_dir,
                contract=contract,
                question_id=args.question_id,
                stage=args.stage,
                priority=args.priority,
                question=args.question,
                why_it_matters=args.why_it_matters,
                resolve_when=args.resolve_when,
                next_check=args.next_check,
                blocking_stage=args.blocking_stage,
                evidence_refs=args.evidence_refs,
                as_of=args.as_of,
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(row, ensure_ascii=False))
        return 0

    if args.command == "resolve":
        try:
            row = resolve_question(
                args.case_dir,
                contract=contract,
                question_id=args.question_id,
                stage=args.stage,
                evidence=args.evidence,
                as_of=args.as_of,
                resolution=args.resolution,
                reopen_trigger=args.reopen_trigger,
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(row, ensure_ascii=False))
        return 0

    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
