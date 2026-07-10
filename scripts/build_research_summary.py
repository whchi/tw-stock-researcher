#!/usr/bin/env python3
"""Deterministic case-files-to-payload builder for research-summary-data.json.

Reads only the fixed set of canonical source files documented in
docs/data-layout.md; never consults an existing research-summary-data.json
or research-summary.html as an input. Requires the research-html-output
stage's gate to be ready (session-wrap passed/degraded and its required
inputs present) before building.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from markdown_contract import extract_table_under_heading, extract_text_under_heading, normalize_text  # noqa: E402
from open_questions import ACTIVE_HEADING, validate_ledger  # noqa: E402
from research_summary_contract import SCHEMA_VERSION, TEMPLATE_VERSION, canonical_json, validate_summary  # noqa: E402
from workflow_state import gate_stage, hash_file, load_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


class BuildError(RuntimeError):
    pass


def _read_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path):
    if not path.exists():
        return None
    return normalize_text(path.read_text(encoding="utf-8"))


def _ready_fact(value, source_ref):
    value = (value or "").strip()
    if not value:
        return {"state": "unavailable", "reason": "required source field absent"}
    return {"value": value, "unit": "", "period": "", "state": "ready", "source_ref": source_ref}


def _build_identity(meta):
    return {
        "ticker": meta.get("ticker", ""),
        "company_name": meta.get("company_name", ""),
        "market": meta.get("market", ""),
        "currency": meta.get("currency", ""),
    }


def _build_current_view(active_text, disclaimer_text):
    return {
        "headline": extract_text_under_heading(active_text, "Headline"),
        "summary": extract_text_under_heading(active_text, "Summary"),
        "stance": extract_text_under_heading(active_text, "Stance"),
        "disclaimer": disclaimer_text,
    }


def _build_kpis(active_text):
    _, rows = extract_table_under_heading(active_text, "Three Numbers To Watch")
    return [
        {
            "label": row.get("Number / Signal", ""),
            "fact": _ready_fact(row.get("Current Read"), "active-decisions.md"),
            "read": row.get("Why It Matters", ""),
        }
        for row in rows
    ]


def _build_evidence_timeline(active_text):
    _, rows = extract_table_under_heading(active_text, "Expected Evidence Timeline")
    return [
        {
            "evidence": row.get("Evidence", ""),
            "expected_timing": row.get("Expected Timing", ""),
            "what_confirms": row.get("What Confirms", ""),
            "what_disconfirms": row.get("What Disconfirms", ""),
            "source": row.get("Source", ""),
        }
        for row in rows
    ]


def _build_kill_criteria(active_text):
    _, rows = extract_table_under_heading(active_text, "Thesis Kill Criteria")
    return [
        {
            "kill_condition": row.get("Kill Condition", ""),
            "evidence_needed": row.get("Evidence Needed", ""),
            "source": row.get("Source", ""),
            "tracking_impact": row.get("Tracking Impact", ""),
        }
        for row in rows
    ]


def _build_watch_items(active_text):
    _, rows = extract_table_under_heading(active_text, "Next Review Triggers")
    return [
        {"trigger": row.get("Trigger", ""), "why_it_matters": row.get("Why It Matters", "")}
        for row in rows
    ]


def _build_expectation_gaps(memo_text):
    _, rows = extract_table_under_heading(memo_text, "Expectation Gap Analysis")
    return [
        {
            "market_belief": row.get("Market Belief", ""),
            "evidence_status": row.get("Evidence Status", ""),
            "gap": row.get("Gap / Mispricing Risk", ""),
            "verification_source": row.get("Verification Source", ""),
        }
        for row in rows
    ]


def _build_pricing_stage(memo_text):
    _, rows = extract_table_under_heading(memo_text, "Pricing Stage Assessment")
    stage_rows = [
        {
            "stage": row.get("Stage", ""),
            "status": row.get("Status", ""),
            "evidence": row.get("Evidence", ""),
            "transition_trigger": row.get("Transition Trigger", ""),
        }
        for row in rows
    ]
    current = next((row for row in stage_rows if row["status"].strip().lower() == "current"), None)
    label = current["stage"] if current else "Not yet assessed"
    read = current["evidence"] if current else ""
    return {"label": label, "read": read, "rows": stage_rows}


SCENARIO_HEADINGS = ("Bull Case", "Base Case", "Bear Case")


def _build_scenarios(memo_text):
    scenarios = []
    for heading in SCENARIO_HEADINGS:
        _, rows = extract_table_under_heading(memo_text, heading)
        if not rows:
            continue
        row = rows[0]
        name = heading.split(" ")[0]
        probability_text = (row.get("Probability") or "").strip()
        probability_value = None
        if probability_text:
            try:
                probability_value = float(probability_text)
            except ValueError:
                probability_value = None
        if probability_value is None:
            probability_fact = {"state": "unavailable", "reason": "required source field absent"}
        else:
            probability_fact = {
                "value": probability_value,
                "unit": "%",
                "period": "",
                "state": "ready",
                "source_ref": "investment-memo.md",
            }
        scenarios.append(
            {
                "name": name,
                "probability": probability_fact,
                "eps_driver_assumption": row.get("EPS / Driver Assumption", ""),
                "multiple_assumption": row.get("Multiple Assumption", ""),
                "scenario_derived_range": row.get("Scenario-Derived Price Range", ""),
                "validation_trigger": row.get("Validation Trigger", ""),
                "break_condition": row.get("Break Condition", ""),
            }
        )
    return scenarios


def _build_egg_theory(market_data, tdcc_data):
    egg = ((market_data or {}).get("derived") or {}).get("egg_theory_read") or {}
    windows = egg.get("windows") or {}
    history_len = len((tdcc_data or {}).get("history") or [])
    rows = []
    for label in ("1m", "3m", "6m"):
        window = windows.get(label)
        if not window:
            continue
        read_parts = list(window.get("warnings") or [])
        if history_len <= 1:
            read_parts.append("TDCC holder history is snapshot-only (no multi-week trend yet)")
        rows.append(
            {
                "window": label,
                "stage": window.get("stage") or "",
                "signal": window.get("signal") or "",
                "confidence": window.get("confidence") or "",
                "read": "; ".join(read_parts),
            }
        )
    return rows


def _build_open_questions(questions_text, contract):
    issues = validate_ledger(questions_text, contract)
    if issues:
        raise BuildError(f"open-questions.md failed validation: {issues}")
    _, rows = extract_table_under_heading(questions_text, ACTIVE_HEADING)
    return [
        {
            "id": row.get("ID", ""),
            "priority": row.get("Priority", ""),
            "question": row.get("Question", ""),
            "status": row.get("Status", ""),
        }
        for row in rows
    ]


def _build_sources_and_manifest(case_dir, dataset_files):
    sources = []
    manifest = []
    for filename in dataset_files:
        path = case_dir / filename
        if not path.exists():
            continue
        manifest.append({"path": filename, "sha256": hash_file(path)})
        payload = _read_json(path) or {}
        metadata = payload.get("metadata") or {}
        source_urls = metadata.get("source_urls") or {}
        source_tiers = metadata.get("source_tiers") or {}
        for dataset, url in source_urls.items():
            tier = source_tiers.get(dataset, "unknown")
            sources.append({"name": dataset, "tier": tier, "url": url, "restricted": tier != "official"})
    return sources, manifest


def _latest_source_as_of(jsons):
    dates = [
        (payload.get("metadata") or {}).get("source_as_of")
        for payload in jsons
        if payload and (payload.get("metadata") or {}).get("source_as_of")
    ]
    return max(dates) if dates else None


REQUIRED_MARKDOWN_SOURCES = (
    "active-decisions.md",
    "investment-memo.md",
    "open-questions.md",
)


def build_summary(case_dir, distribution="local", as_of=None):
    case_dir = Path(case_dir)
    contract = load_contract()

    gate = gate_stage(case_dir, "research-html-output", contract, date.today())
    if not gate["ready"]:
        raise BuildError(f"research-html-output is not ready: {gate['blocking_reasons']}")

    meta = _read_json(case_dir / "stock-meta.json")
    if meta is None:
        raise BuildError("missing required source: stock-meta.json")

    texts = {}
    for filename in REQUIRED_MARKDOWN_SOURCES:
        text = _read_text(case_dir / filename)
        if text is None:
            raise BuildError(f"missing required source: {filename}")
        texts[filename] = text

    disclaimer_text = _read_text(REPO_ROOT / "DISCLAIMER.md")
    if disclaimer_text is None:
        raise BuildError("missing required source: DISCLAIMER.md")

    active_text = texts["active-decisions.md"]
    memo_text = texts["investment-memo.md"]
    questions_text = texts["open-questions.md"]

    market_data = _read_json(case_dir / "market-data.json")
    tdcc_data = _read_json(case_dir / "tdcc-data.json")

    sources, manifest = _build_sources_and_manifest(case_dir, ["market-data.json", "tdcc-data.json"])
    for filename in ("stock-meta.json",) + REQUIRED_MARKDOWN_SOURCES:
        manifest.append({"path": filename, "sha256": hash_file(case_dir / filename)})
    manifest.sort(key=lambda entry: entry["path"])
    sources.sort(key=lambda entry: entry["name"])

    resolved_as_of = as_of or _latest_source_as_of([market_data, tdcc_data]) or date.today().isoformat()

    return {
        "schema_version": SCHEMA_VERSION,
        "template_version": TEMPLATE_VERSION,
        "case_id": case_dir.name,
        "locale": "zh-Hant-TW",
        "timezone": "Asia/Taipei",
        "as_of": resolved_as_of,
        "distribution": distribution,
        "identity": _build_identity(meta),
        "current_view": _build_current_view(active_text, disclaimer_text),
        "kpis": _build_kpis(active_text),
        "expectation_gaps": _build_expectation_gaps(memo_text),
        "pricing_stage": _build_pricing_stage(memo_text),
        "egg_theory": _build_egg_theory(market_data, tdcc_data),
        "evidence_timeline": _build_evidence_timeline(active_text),
        "kill_criteria": _build_kill_criteria(active_text),
        "scenarios": _build_scenarios(memo_text),
        "watch_items": _build_watch_items(active_text),
        "open_questions": _build_open_questions(questions_text, contract),
        "sources": sources,
        "source_manifest": manifest,
    }


def _atomic_write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_summary(case_dir, check=False, distribution="local"):
    case_dir = Path(case_dir)
    payload = build_summary(case_dir, distribution=distribution)
    issues = validate_summary(payload)
    if issues:
        raise BuildError(f"built payload failed validation: {issues}")

    output_path = case_dir / "research-summary-data.json"
    if check:
        return output_path

    _atomic_write_text(output_path, canonical_json(payload))
    return output_path


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--check", action="store_true", help="Validate only; do not write the payload file.")
    parser.add_argument("--distribution", default="local", choices=("local", "shareable"))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        output_path = write_summary(Path(args.case), check=args.check, distribution=args.distribution)
    except BuildError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.check:
        print(f"research-summary-data.json for {args.case} would be valid (--check, not written)")
    else:
        print(f"research-summary-data.json saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
