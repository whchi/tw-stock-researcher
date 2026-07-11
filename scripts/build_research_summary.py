#!/usr/bin/env python3
"""Deterministic case-files-to-payload builder for research-summary-data.json.

Reads only the fixed set of canonical source files documented in
docs/data-layout.md; never consults an existing research-summary-data.json
or research-summary.html as an input. Section extraction is tolerant:
headings are matched by containment against the shapes in templates/, table
columns are matched by name with common aliases, and a section whose heading
or table is missing renders as empty instead of failing the build. The build
fails only on a missing source file or an invalid final payload.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomic_io import atomic_write_text  # noqa: E402
from markdown_contract import normalize_text  # noqa: E402
from research_summary_contract import SCHEMA_VERSION, TEMPLATE_VERSION, canonical_json, validate_summary  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

DISCLAIMER_SUMMARY = (
    "免責聲明：本文件僅供研究參考，不構成投資建議、買賣推薦或任何形式之邀約。"
)


class BuildError(RuntimeError):
    pass


def hash_file(path):
    path = Path(path)
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path):
    if not path.exists():
        return None
    return normalize_text(path.read_text(encoding="utf-8"))


# --- tolerant markdown extraction -------------------------------------------


def _strip_md(value):
    return value.replace("**", "").strip()


def _sections(text):
    """Split markdown into (heading, body_lines) per `##` section; `#` closes a section."""
    result = []
    heading, body = None, None
    for line in text.split("\n"):
        if line.startswith("## "):
            if heading is not None:
                result.append((heading, body))
            heading, body = line[3:].strip(), []
        elif line.startswith("# "):
            if heading is not None:
                result.append((heading, body))
            heading, body = None, None
        elif heading is not None:
            body.append(line)
    if heading is not None:
        result.append((heading, body))
    return result


def _find_section(text, key):
    """First `##` section whose heading contains key (case-insensitive)."""
    for heading, body in _sections(text):
        if key.lower() in heading.lower():
            return heading, body
    return None, []


def _section_text(text, key):
    _, body = _find_section(text, key)
    return "\n".join(line for line in body if line.strip()).strip()


_TABLE_SEPARATOR_RE = re.compile(r"^[\s|:\-]+$")


def _parse_table(body_lines):
    """First pipe table in a section as (headers, rows-of-dicts); never raises."""
    raw = []
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            raw.append(stripped)
        elif raw:
            break
    if len(raw) < 2:
        return [], []

    def cells(row):
        return [_strip_md(cell) for cell in row.strip("|").split("|")]

    headers = cells(raw[0])
    data = raw[1:]
    if data and _TABLE_SEPARATOR_RE.match(data[0]):
        data = data[1:]
    rows = []
    for line in data:
        values = cells(line)
        rows.append({headers[i]: (values[i] if i < len(values) else "") for i in range(len(headers))})
    return headers, rows


def _table_under(text, key):
    _, body = _find_section(text, key)
    return _parse_table(body)


def _col(row, *names):
    """Value of the first column whose header matches one of names (case-insensitive)."""
    lowered = {header.strip().lower(): value for header, value in row.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()].strip()
    return ""


def _ready_fact(value, source_ref):
    value = (value or "").strip()
    if not value:
        return {"state": "unavailable", "reason": "required source field absent"}
    return {"value": value, "unit": "", "period": "", "state": "ready", "source_ref": source_ref}


def _probability_fact(probability_text):
    probability_text = (probability_text or "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", probability_text)
    if not match:
        return {"state": "unavailable", "reason": "required source field absent"}
    return {
        "value": float(match.group(1)),
        "unit": "%",
        "period": "",
        "state": "ready",
        "source_ref": "investment-memo.md",
    }


# --- payload sections --------------------------------------------------------


def _build_identity(meta):
    return {
        "ticker": meta.get("ticker", ""),
        "company_name": meta.get("company_name", ""),
        "market": meta.get("market", ""),
        "currency": meta.get("currency", ""),
    }


def _build_current_view(active_text, disclaimer_text):
    stance_heading, stance_body = _find_section(active_text, "Stance")
    stance_body_text = "\n".join(line for line in stance_body if line.strip()).strip()
    stance = ""
    if stance_heading is not None:
        _, _, suffix = stance_heading.partition(":")
        stance = suffix.strip() or stance_body_text
    summary = _section_text(active_text, "Summary")
    if not summary and stance and stance != stance_body_text:
        # "## Stance: <立場>" style: the paragraph under the heading is the summary.
        summary = stance_body_text
    return {
        "headline": _section_text(active_text, "Headline"),
        "summary": summary,
        "stance": stance,
        "disclaimer": disclaimer_text,
    }


def _build_kpis(active_text):
    _, rows = _table_under(active_text, "Three Numbers")
    return [
        {
            "label": _col(row, "Number / Signal", "Number", "Signal"),
            "fact": _ready_fact(_col(row, "Current Read", "Current"), "active-decisions.md"),
            "read": _col(row, "Why It Matters"),
        }
        for row in rows
    ]


def _build_evidence_timeline(active_text):
    _, rows = _table_under(active_text, "Evidence Timeline")
    return [
        {
            "evidence": _col(row, "Evidence", "Event"),
            "expected_timing": _col(row, "Expected Timing", "When"),
            "what_confirms": _col(row, "What Confirms", "Key Watch"),
            "what_disconfirms": _col(row, "What Disconfirms"),
            "source": _col(row, "Source"),
        }
        for row in rows
    ]


def _build_kill_criteria(active_text):
    _, rows = _table_under(active_text, "Kill Criteria")
    return [
        {
            "kill_condition": _col(row, "Kill Condition", "Condition"),
            "evidence_needed": _col(row, "Evidence Needed"),
            "source": _col(row, "Source"),
            "tracking_impact": _col(row, "Tracking Impact", "Impact"),
        }
        for row in rows
    ]


def _build_watch_items(active_text):
    _, rows = _table_under(active_text, "Trigger")
    if rows:
        return [
            {"trigger": _col(row, "Trigger"), "why_it_matters": _col(row, "Why It Matters")}
            for row in rows
        ]
    _, body = _find_section(active_text, "Trigger")
    return [
        {"trigger": _strip_md(line.strip()[2:]), "why_it_matters": ""}
        for line in body
        if line.strip().startswith("- ")
    ]


def _build_expectation_gaps(memo_text):
    _, rows = _table_under(memo_text, "Expectation Gap")
    return [
        {
            "market_belief": _col(row, "Market Belief", "Market Believes"),
            "evidence_status": _col(row, "Evidence Status", "Reality"),
            "gap": _col(row, "Gap / Mispricing Risk", "Gap"),
            "verification_source": _col(row, "Verification Source"),
        }
        for row in rows
    ]


def _build_pricing_stage(memo_text):
    _, rows = _table_under(memo_text, "Pricing Stage")
    stage_rows = [
        {
            "stage": _col(row, "Stage"),
            "status": _col(row, "Status"),
            "evidence": _col(row, "Evidence"),
            "transition_trigger": _col(row, "Transition Trigger"),
        }
        for row in rows
    ]
    current = next((row for row in stage_rows if row["status"].strip().lower() == "current"), None)
    if current:
        return {"label": current["stage"], "read": current["evidence"], "rows": stage_rows}
    match = re.search(r"Pricing stage:\**\s*(.+)", memo_text, re.IGNORECASE)
    if match:
        return {"label": _strip_md(match.group(1)), "read": "", "rows": stage_rows}
    return {"label": "Not yet assessed", "read": "", "rows": stage_rows}


_SCENARIO_FIELD_KEYWORDS = (
    ("eps_driver_assumption", ("assumption", "driver", "eps")),
    ("multiple_assumption", ("multiple", "p/b", "p/e")),
    ("scenario_derived_range", ("range",)),
    ("validation_trigger", ("validation",)),
    ("break_condition", ("break", "kill")),
)


def _scenario_from_row(name, row):
    return {
        "name": name,
        "probability": _probability_fact(_col(row, "Probability")),
        "eps_driver_assumption": _col(row, "EPS / Driver Assumption", "Assumptions", "Assumption", "Driver"),
        "multiple_assumption": _col(row, "Multiple Assumption", "Multiple", "P/B", "P/E"),
        "scenario_derived_range": _col(row, "Scenario-Derived Price Range", "Obs. Range", "Range"),
        "validation_trigger": _col(row, "Validation Trigger"),
        "break_condition": _col(row, "Break Condition"),
    }


def _build_scenarios(memo_text):
    scenarios = []
    for key in ("Bull Case", "Base Case", "Bear Case"):
        _, rows = _table_under(memo_text, key)
        if not rows:
            continue
        scenarios.append(_scenario_from_row(key.split(" ")[0], rows[0]))
    if scenarios:
        return scenarios

    headers, rows = _table_under(memo_text, "Scenario")
    if not headers or not rows:
        return []

    if any(header.strip().lower() in ("scenario", "name") for header in headers):
        return [_scenario_from_row(_col(row, "Scenario", "Name"), row) for row in rows]

    # Transposed table: first column holds row labels, remaining headers are
    # scenario names like "Bull (15%)".
    label_key = headers[0]
    columns = []
    for header in headers[1:]:
        match = re.match(r"(.+?)\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)", header)
        columns.append(
            {
                "header": header,
                "name": _strip_md(match.group(1)) if match else _strip_md(header),
                "probability": match.group(2) if match else "",
                "fields": {},
            }
        )
    for row in rows:
        label = row.get(label_key, "").lower()
        field = next(
            (name for name, keywords in _SCENARIO_FIELD_KEYWORDS if any(k in label for k in keywords)),
            None,
        )
        if field is None:
            continue
        for column in columns:
            if field not in column["fields"]:
                column["fields"][field] = row.get(column["header"], "")
    return [
        {
            "name": column["name"],
            "probability": _probability_fact(column["probability"]),
            "eps_driver_assumption": column["fields"].get("eps_driver_assumption", ""),
            "multiple_assumption": column["fields"].get("multiple_assumption", ""),
            "scenario_derived_range": column["fields"].get("scenario_derived_range", ""),
            "validation_trigger": column["fields"].get("validation_trigger", ""),
            "break_condition": column["fields"].get("break_condition", ""),
        }
        for column in columns
    ]


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


def _build_open_questions(questions_text):
    _, rows = _table_under(questions_text, "Active")
    return [
        {
            "id": _col(row, "ID"),
            "priority": _col(row, "Priority"),
            "question": _col(row, "Question"),
            "status": _col(row, "Status"),
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
        manifest.append({"root": "case", "path": filename, "sha256": hash_file(path)})
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
        manifest.append({"root": "case", "path": filename, "sha256": hash_file(case_dir / filename)})
    manifest.append({"root": "repo", "path": "DISCLAIMER.md", "sha256": hash_file(REPO_ROOT / "DISCLAIMER.md")})
    manifest.sort(key=lambda entry: (entry["root"], entry["path"]))
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
        "current_view": _build_current_view(active_text, DISCLAIMER_SUMMARY),
        "kpis": _build_kpis(active_text),
        "expectation_gaps": _build_expectation_gaps(memo_text),
        "pricing_stage": _build_pricing_stage(memo_text),
        "egg_theory": _build_egg_theory(market_data, tdcc_data),
        "evidence_timeline": _build_evidence_timeline(active_text),
        "kill_criteria": _build_kill_criteria(active_text),
        "scenarios": _build_scenarios(memo_text),
        "watch_items": _build_watch_items(active_text),
        "open_questions": _build_open_questions(questions_text),
        "sources": sources,
        "source_manifest": manifest,
    }


def write_summary(case_dir, check=False, distribution="local"):
    case_dir = Path(case_dir)
    payload = build_summary(case_dir, distribution=distribution)
    issues = validate_summary(payload)
    if issues:
        raise BuildError(f"built payload failed validation: {issues}")

    output_path = case_dir / "research-summary-data.json"
    if check:
        return output_path

    atomic_write_text(output_path, canonical_json(payload))
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
