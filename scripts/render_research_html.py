#!/usr/bin/env python3
"""Render research-summary.html from a validated research-summary-data.json.

Every value inserted into the template is escaped with html.escape(quote=True);
renderer functions build whole table rows/cards/tags from typed payload arrays
instead of scanning already-rendered research text. Template placeholders are
validated against the payload's own field mapping before any string
substitution happens, and the output is written atomically only after
validation passes.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_summary_contract import validate_summary  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT_DIR / "templates" / "research-html-summary.html"
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

FRAGMENT_KEYS = {
    "KPI_CARDS", "EXPECTATION_GAP_ROWS", "PRICING_STAGE_ROWS", "EGG_THEORY_ROWS",
    "EVIDENCE_TIMELINE_ROWS", "KILL_CRITERIA_ROWS", "SCENARIO_CARDS", "WATCH_ITEMS",
    "OPEN_QUESTIONS_ROWS", "SOURCE_QUALITY_ROWS", "SOURCE_MANIFEST_ROWS", "SOURCE_TAGS",
}


class RenderError(RuntimeError):
    pass


def _escape(value):
    return html.escape(str(value), quote=True)


def _fact_display(fact):
    if not isinstance(fact, dict):
        return "", ""
    if fact.get("state") == "unavailable":
        return "unavailable", fact.get("reason", "")
    value = fact.get("value", "")
    unit = fact.get("unit", "")
    display = f"{value}{unit}" if unit else str(value)
    return display, fact.get("period", "")


def render_kpi_cards(kpis):
    cards = []
    for kpi in kpis:
        value_display, _period = _fact_display(kpi.get("fact"))
        cards.append(
            '<div class="kpi">'
            f'<div class="label">{_escape(kpi.get("label", ""))}</div>'
            f'<div class="value">{_escape(value_display)}</div>'
            f'<div class="read">{_escape(kpi.get("read", ""))}</div>'
            "</div>"
        )
    return "\n".join(cards)


def render_expectation_gap_rows(rows):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(row.get('market_belief', ''))}</td>"
        f"<td>{_escape(row.get('evidence_status', ''))}</td>"
        f"<td>{_escape(row.get('gap', ''))}</td>"
        f"<td>{_escape(row.get('verification_source', ''))}</td>"
        "</tr>"
        for row in rows
    )


def render_pricing_stage_rows(rows):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(row.get('stage', ''))}</td>"
        f"<td>{_escape(row.get('status', ''))}</td>"
        f"<td>{_escape(row.get('evidence', ''))}</td>"
        f"<td>{_escape(row.get('transition_trigger', ''))}</td>"
        "</tr>"
        for row in rows
    )


def render_egg_theory_rows(rows):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(row.get('window', ''))}</td>"
        f"<td>{_escape(row.get('stage', ''))}</td>"
        f"<td>{_escape(row.get('signal', ''))}</td>"
        f"<td>{_escape(row.get('confidence', ''))}</td>"
        f"<td>{_escape(row.get('read', ''))}</td>"
        "</tr>"
        for row in rows
    )


def render_evidence_timeline_rows(rows):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(row.get('evidence', ''))}</td>"
        f"<td>{_escape(row.get('expected_timing', ''))}</td>"
        f"<td>{_escape(row.get('what_confirms', ''))}</td>"
        f"<td>{_escape(row.get('what_disconfirms', ''))}</td>"
        f"<td>{_escape(row.get('source', ''))}</td>"
        "</tr>"
        for row in rows
    )


def render_kill_criteria_rows(rows):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(row.get('kill_condition', ''))}</td>"
        f"<td>{_escape(row.get('evidence_needed', ''))}</td>"
        f"<td>{_escape(row.get('source', ''))}</td>"
        f"<td>{_escape(row.get('tracking_impact', ''))}</td>"
        "</tr>"
        for row in rows
    )


def render_scenario_cards(scenarios):
    cards = []
    for scenario in scenarios:
        probability_display, _period = _fact_display(scenario.get("probability"))
        cards.append(
            '<div class="case">'
            f'<strong>{_escape(scenario.get("name", ""))} — {_escape(probability_display)}</strong>'
            f'<p>{_escape(scenario.get("eps_driver_assumption", ""))}</p>'
            f'<p>{_escape(scenario.get("multiple_assumption", ""))}</p>'
            f'<p>{_escape(scenario.get("scenario_derived_range", ""))}</p>'
            f'<p>{_escape(scenario.get("validation_trigger", ""))}</p>'
            f'<p>{_escape(scenario.get("break_condition", ""))}</p>'
            "</div>"
        )
    return "\n".join(cards)


def render_watch_items(items):
    return "\n".join(
        f"<li>{_escape(item.get('trigger', ''))} — {_escape(item.get('why_it_matters', ''))}</li>"
        for item in items
    )


def render_open_questions_rows(questions):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(question.get('id', ''))}</td>"
        f"<td>{_escape(question.get('priority', ''))}</td>"
        f"<td>{_escape(question.get('question', ''))}</td>"
        f"<td>{_escape(question.get('status', ''))}</td>"
        "</tr>"
        for question in questions
    )


def render_source_quality_rows(sources):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(source.get('name', ''))}</td>"
        f"<td>{_escape(source.get('tier', ''))}</td>"
        f"<td>{_escape('restricted' if source.get('restricted') else 'shareable')}</td>"
        "</tr>"
        for source in sources
    )


def render_source_manifest_rows(manifest):
    return "\n".join(
        "<tr>"
        f"<td>{_escape(entry.get('path', ''))}</td>"
        f"<td>{_escape(entry.get('sha256', ''))}</td>"
        "</tr>"
        for entry in manifest
    )


def render_source_tags(sources):
    tags = []
    for source in sources:
        url = source.get("url", "")
        scheme = urlparse(url).scheme
        if scheme not in ("http", "https"):
            raise RenderError(f"source url must be http or https: {url!r}")
        tags.append(
            f'<a class="tag" href="{_escape(url)}" target="_blank" rel="noopener">'
            f'{_escape(source.get("name", ""))}</a>'
        )
    return "\n".join(tags)


def _build_values(payload):
    identity = payload["identity"]
    current_view = payload["current_view"]
    pricing_stage = payload["pricing_stage"]

    return {
        "TITLE": f"{identity['ticker']} {identity['company_name']}",
        "SIDEBAR_TICKER": identity["ticker"],
        "SIDEBAR_TITLE": identity["company_name"],
        "SIDEBAR_DESCRIPTION": current_view["summary"],
        "DISCLAIMER": current_view["disclaimer"],
        "HERO_HEADLINE": current_view["headline"],
        "HERO_SUMMARY": current_view["summary"],
        "STANCE": current_view["stance"],
        "KPI_CARDS": render_kpi_cards(payload["kpis"]),
        "EXPECTATION_GAP_ROWS": render_expectation_gap_rows(payload["expectation_gaps"]),
        "PRICING_STAGE_LABEL": pricing_stage["label"],
        "PRICING_STAGE_READ": pricing_stage["read"],
        "PRICING_STAGE_ROWS": render_pricing_stage_rows(pricing_stage["rows"]),
        "EGG_THEORY_ROWS": render_egg_theory_rows(payload["egg_theory"]),
        "EVIDENCE_TIMELINE_ROWS": render_evidence_timeline_rows(payload["evidence_timeline"]),
        "KILL_CRITERIA_ROWS": render_kill_criteria_rows(payload["kill_criteria"]),
        "SCENARIO_CARDS": render_scenario_cards(payload["scenarios"]),
        "WATCH_ITEMS": render_watch_items(payload["watch_items"]),
        "OPEN_QUESTIONS_ROWS": render_open_questions_rows(payload["open_questions"]),
        "SOURCE_QUALITY_ROWS": render_source_quality_rows(payload["sources"]),
        "SOURCE_MANIFEST_ROWS": render_source_manifest_rows(payload["source_manifest"]),
        "SOURCE_TAGS": render_source_tags(payload["sources"]),
        "SCHEMA_VERSION": payload["schema_version"],
        "TEMPLATE_VERSION": payload["template_version"],
        "AS_OF": payload["as_of"],
        "TIMEZONE": payload["timezone"],
        "CASE_ID": payload["case_id"],
    }


def render_summary(payload, template):
    issues = validate_summary(payload)
    if issues:
        raise RenderError(f"payload failed validation: {issues}")

    placeholders = sorted(set(PLACEHOLDER_RE.findall(template)))
    values = _build_values(payload)

    missing = [name for name in placeholders if name not in values]
    if missing:
        raise RenderError(f"template placeholders have no payload mapping: {missing}")

    rendered = template
    for name in placeholders:
        value = values[name]
        substitution = value if name in FRAGMENT_KEYS else _escape(value)
        rendered = rendered.replace(f"{{{{{name}}}}}", substitution)

    return rendered


def _validate_case_dir(case_dir):
    resolved = Path(case_dir).resolve()
    root = ROOT_DIR.resolve()
    if resolved != root and root not in resolved.parents:
        raise RenderError(f"case dir escapes repository: {resolved}")
    return resolved


def _atomic_write_text(path, text):
    import os
    import tempfile

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


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--check", action="store_true", help="Validate and render only; do not write the HTML file.")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        case_dir = _validate_case_dir(args.case)
    except RenderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload_path = case_dir / "research-summary-data.json"
    if not payload_path.exists():
        print(
            f"Error: {payload_path} does not exist; run build_research_summary.py --case {args.case} first",
            file=sys.stderr,
        )
        return 1

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    template_text = Path(args.template).read_text(encoding="utf-8")

    try:
        rendered = render_summary(payload, template_text)
    except RenderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = case_dir / "research-summary.html"
    if args.check:
        print(f"research-summary.html for {case_dir} would be valid (--check, not written)")
        return 0

    _atomic_write_text(output_path, rendered)
    print(f"Research HTML saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
