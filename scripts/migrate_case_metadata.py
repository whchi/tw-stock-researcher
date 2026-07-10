#!/usr/bin/env python3
"""Read-only migration analysis for existing companies/** cases.

Reports drift between an existing case and the current stock-meta.json,
open-questions.md, and research-summary-data.json contracts. Never writes
to a case; there is intentionally no --apply in this release. A later
change may add per-case apply after the user approves exact targets.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from markdown_contract import normalize_text  # noqa: E402
from open_questions import validate_ledger as validate_question_ledger  # noqa: E402
from research_summary_contract import SCHEMA_VERSION, TEMPLATE_VERSION, validate_summary  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPANIES_DIR = REPO_ROOT / "companies"
TEMPLATE_META_PATH = REPO_ROOT / "templates" / "stock-meta.json"
CONTRACT_PATH = REPO_ROOT / "workflow-contract.json"


def _load_contract():
    with open(CONTRACT_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def _canonical_meta_keys():
    with open(TEMPLATE_META_PATH, encoding="utf-8") as handle:
        template = json.load(handle)
    return set(template.keys()), set(template.get("file_references", {}).keys())


def _analyze_file_references(file_references, case_dir, findings, canonical_ref_keys):
    if not isinstance(file_references, dict):
        findings.append({"check": "file_references_shape", "status": "invalid", "detail": "file_references is not an object"})
        return

    ref_keys = set(file_references.keys())
    missing_ref_keys = sorted(canonical_ref_keys - ref_keys)
    unknown_ref_keys = sorted(ref_keys - canonical_ref_keys)
    if missing_ref_keys:
        findings.append({"check": "file_references_keys", "status": "missing_keys", "detail": missing_ref_keys})
    if unknown_ref_keys:
        findings.append({"check": "file_references_keys", "status": "unknown_keys", "detail": unknown_ref_keys})

    conventions = set()
    dangling = []
    for key, value in sorted(file_references.items()):
        if value is None:
            continue
        if not isinstance(value, str):
            findings.append({"check": "file_references_value", "status": "invalid_type", "detail": key})
            continue
        if value.startswith("companies/"):
            conventions.add("repo_relative")
            resolved = REPO_ROOT / value
        else:
            conventions.add("case_relative")
            resolved = case_dir / value
        if not resolved.exists():
            dangling.append({"key": key, "value": value})

    if len(conventions) > 1:
        findings.append({"check": "file_references_convention", "status": "mixed", "detail": sorted(conventions)})
    if dangling:
        findings.append({"check": "file_references_dangling", "status": "dangling", "detail": dangling})


def _analyze_stock_meta(case_dir, findings):
    meta_path = case_dir / "stock-meta.json"
    if not meta_path.exists():
        findings.append({"check": "stock_meta_presence", "status": "missing", "detail": "stock-meta.json not found"})
        return

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append({"check": "stock_meta_presence", "status": "invalid_json", "detail": str(exc)})
        return

    if not isinstance(meta, dict):
        findings.append({"check": "stock_meta_presence", "status": "invalid_shape", "detail": "top level is not an object"})
        return

    canonical_keys, canonical_ref_keys = _canonical_meta_keys()
    meta_keys = set(meta.keys())
    missing_keys = sorted(canonical_keys - meta_keys)
    unknown_keys = sorted(meta_keys - canonical_keys)
    if missing_keys:
        findings.append({"check": "stock_meta_keys", "status": "missing_keys", "detail": missing_keys})
    if unknown_keys:
        findings.append({"check": "stock_meta_keys", "status": "unknown_keys", "detail": unknown_keys})

    stage_records = meta.get("stage_records")
    if "stage_records" not in meta or not isinstance(stage_records, dict):
        findings.append({"check": "stage_state", "status": "absent", "detail": "no stage_records map (pre-Task-4 case)"})
    elif not stage_records:
        findings.append({"check": "stage_state", "status": "empty", "detail": "stage_records present but empty"})

    _analyze_file_references(meta.get("file_references"), case_dir, findings, canonical_ref_keys)


def _analyze_open_questions(case_dir, contract, findings):
    path = case_dir / "open-questions.md"
    if not path.exists():
        findings.append({"check": "open_questions", "status": "missing", "detail": "open-questions.md not found"})
        return
    text = normalize_text(path.read_text(encoding="utf-8"))
    issues = validate_question_ledger(text, contract)
    if issues:
        findings.append({"check": "open_questions", "status": "legacy_table_shape", "detail": issues})


def _analyze_research_summary(case_dir, findings):
    path = case_dir / "research-summary-data.json"
    if not path.exists():
        return

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append({"check": "research_summary_data", "status": "invalid_json", "detail": str(exc)})
        return

    if not isinstance(payload, dict) or "schema_version" not in payload:
        findings.append({"check": "research_summary_data", "status": "legacy_v0", "detail": "no schema_version field"})
        return

    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("template_version") != TEMPLATE_VERSION:
        findings.append({
            "check": "research_summary_data",
            "status": "version_mismatch",
            "detail": {
                "schema_version": payload.get("schema_version"),
                "template_version": payload.get("template_version"),
            },
        })
        return

    issues = validate_summary(payload)
    if issues:
        findings.append({
            "check": "research_summary_data",
            "status": "invalid_payload",
            "detail": [f"{issue.path}: {issue.message}" for issue in issues],
        })


def analyze_case(case_dir, contract=None):
    case_dir = Path(case_dir)
    contract = contract or _load_contract()
    findings = []
    _analyze_stock_meta(case_dir, findings)
    _analyze_open_questions(case_dir, contract, findings)
    _analyze_research_summary(case_dir, findings)
    return {"case": case_dir.name, "clean": not findings, "findings": findings}


def analyze_all():
    if not COMPANIES_DIR.exists():
        return []
    contract = _load_contract()
    return [
        analyze_case(case_dir, contract=contract)
        for case_dir in sorted(COMPANIES_DIR.iterdir())
        if case_dir.is_dir()
    ]


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--case")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        required=True,
        help="Required in this release: this script never writes and there is no --apply yet.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    reports = analyze_all() if args.all else [analyze_case(Path(args.case))]

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            status = "clean" if report["clean"] else f"{len(report['findings'])} finding(s)"
            print(f"{report['case']}: {status}")
            for finding in report["findings"]:
                print(f"  - {finding['check']}: {finding['status']} -- {finding['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
