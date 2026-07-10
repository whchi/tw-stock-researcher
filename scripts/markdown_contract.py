"""Strict fixed-heading/table Markdown parsing shared by the question ledger
and the research-summary HTML builder.

Documents are normalized (Unicode NFC, Unix newlines) before parsing so the
same source bytes always produce the same rows regardless of the editor or
platform that last touched the file.
"""

import re
import unicodedata


class MarkdownContractError(ValueError):
    pass


def normalize_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text)


def _split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


_SEPARATOR_RE = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")


def parse_pipe_table(block):
    lines = [line for line in block.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        raise MarkdownContractError("no markdown pipe table found")

    headers = _split_row(lines[0])
    if not _SEPARATOR_RE.match(lines[1].strip()):
        raise MarkdownContractError(f"missing table separator row after headers: {lines[1]!r}")

    rows = []
    for line in lines[2:]:
        cells = _split_row(line)
        if len(cells) != len(headers):
            raise MarkdownContractError(
                f"row has {len(cells)} cells, expected {len(headers)}: {line!r}"
            )
        rows.append(dict(zip(headers, cells)))
    return headers, rows


def _section_lines(text, heading, level=2):
    marker = "#" * level + " " + heading
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == marker:
            start = i + 1
            break
    if start is None:
        raise MarkdownContractError(f"heading not found: {marker!r}")

    end = len(lines)
    heading_re = re.compile(r"^#{1,%d}\s" % level)
    for i in range(start, len(lines)):
        if heading_re.match(lines[i]):
            end = i
            break

    return lines[start:end]


def extract_table_under_heading(text, heading, level=2):
    block = "\n".join(_section_lines(text, heading, level=level))
    return parse_pipe_table(block)


def extract_text_under_heading(text, heading, level=2):
    lines = [line for line in _section_lines(text, heading, level=level) if line.strip()]
    return "\n".join(lines).strip()


def render_pipe_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines) + "\n"
