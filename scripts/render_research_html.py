#!/usr/bin/env python3
"""Render a research summary HTML file by replacing template placeholders."""

import argparse
import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT_DIR / "templates" / "research-html-summary.html"
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="JSON payload with placeholder values")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE),
        help="HTML template path; defaults to templates/research-html-summary.html",
    )
    return parser.parse_args(argv)


def load_payload(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("HTML payload must be a JSON object")
    return payload


def stringify(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)


def render_html(template_path, output_path, values):
    template_path = Path(template_path)
    output_path = Path(output_path)
    template = template_path.read_text(encoding="utf-8")
    placeholders = sorted(set(PLACEHOLDER_RE.findall(template)))
    missing = [name for name in placeholders if name not in values]

    if missing:
        raise RuntimeError(f"Missing template values: {', '.join(missing)}")

    rendered = template
    for name in placeholders:
        rendered = rendered.replace(f"{{{{{name}}}}}", stringify(values[name]))

    unresolved = sorted(set(PLACEHOLDER_RE.findall(rendered)))
    if unresolved:
        raise RuntimeError(f"Unresolved template values: {', '.join(unresolved)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    render_html(args.template, args.output, load_payload(args.data))
    print(f"Research HTML saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
