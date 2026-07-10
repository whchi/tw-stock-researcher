#!/usr/bin/env python3
"""Read-only legacy audit of research-summary-data.json / research-summary.html.

Reports v0 payloads, version mismatches, invalid shapes, and stale source
manifests (a source file that no longer matches the hash recorded when the
summary was built) across companies/. Never writes; rebuilding a legacy case
happens only via build_research_summary.py after the user explicitly
approves it for that case. Never parses old HTML with regex — legacy state
is judged from research-summary-data.json only.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_summary_contract import SCHEMA_VERSION, TEMPLATE_VERSION, validate_summary  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
COMPANIES_DIR = ROOT_DIR / "companies"


def _hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_case(case_dir):
    case_dir = Path(case_dir)
    data_path = case_dir / "research-summary-data.json"
    report = {"case": case_dir.name}

    if not data_path.exists():
        report["status"] = "no_research_summary_data"
        return report

    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report["status"] = "invalid_json"
        report["error"] = str(exc)
        return report

    if not isinstance(payload, dict) or "schema_version" not in payload:
        report["status"] = "legacy_v0"
        return report

    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("template_version") != TEMPLATE_VERSION:
        report["status"] = "version_mismatch"
        report["schema_version"] = payload.get("schema_version")
        report["template_version"] = payload.get("template_version")
        return report

    issues = validate_summary(payload)
    if issues:
        report["status"] = "invalid_payload"
        report["issues"] = [f"{issue.path}: {issue.message}" for issue in issues]
        return report

    stale_entries = []
    for entry in payload.get("source_manifest", []):
        source_path = case_dir / entry["path"]
        if not source_path.exists():
            stale_entries.append(f"{entry['path']}: missing")
            continue
        if _hash_file(source_path) != entry["sha256"]:
            stale_entries.append(f"{entry['path']}: hash drift")

    if stale_entries:
        report["status"] = "stale_manifest"
        report["stale_entries"] = stale_entries
        return report

    report["status"] = "current"
    return report


def audit_all():
    if not COMPANIES_DIR.exists():
        return []
    return [audit_case(case_dir) for case_dir in sorted(COMPANIES_DIR.iterdir()) if case_dir.is_dir()]


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--case")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    reports = audit_all() if args.all else [audit_case(Path(args.case))]

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(f"{report['case']}: {report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
