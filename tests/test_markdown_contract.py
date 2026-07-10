import unittest

from scripts.markdown_contract import (
    MarkdownContractError,
    extract_table_under_heading,
    extract_text_under_heading,
    normalize_text,
    parse_pipe_table,
    render_pipe_table,
)


class NormalizeTextTests(unittest.TestCase):
    def test_normalizes_windows_and_mac_newlines_to_unix(self):
        self.assertEqual(normalize_text("a\r\nb\rc\n"), "a\nb\nc\n")

    def test_normalizes_unicode_to_nfc(self):
        decomposed = "é"  # 'e' + combining acute accent
        composed = "é"  # 'é' precomposed
        self.assertEqual(normalize_text(decomposed), composed)


class ParsePipeTableTests(unittest.TestCase):
    def test_parses_headers_and_rows(self):
        block = (
            "| ID | Status |\n"
            "| --- | --- |\n"
            "| A-1 | open |\n"
            "| A-2 | resolved |\n"
        )
        headers, rows = parse_pipe_table(block)

        self.assertEqual(headers, ["ID", "Status"])
        self.assertEqual(rows, [{"ID": "A-1", "Status": "open"}, {"ID": "A-2", "Status": "resolved"}])

    def test_empty_table_with_only_header_and_separator_yields_no_rows(self):
        block = "| ID | Status |\n| --- | --- |\n"
        headers, rows = parse_pipe_table(block)
        self.assertEqual(headers, ["ID", "Status"])
        self.assertEqual(rows, [])

    def test_raises_when_separator_row_missing(self):
        block = "| ID | Status |\n| A-1 | open |\n"
        with self.assertRaises(MarkdownContractError):
            parse_pipe_table(block)

    def test_raises_when_row_has_wrong_cell_count(self):
        block = "| ID | Status |\n| --- | --- |\n| A-1 |\n"
        with self.assertRaises(MarkdownContractError):
            parse_pipe_table(block)

    def test_raises_when_no_table_present(self):
        with self.assertRaises(MarkdownContractError):
            parse_pipe_table("just prose, no table here")


class ExtractTableUnderHeadingTests(unittest.TestCase):
    def test_extracts_the_table_immediately_following_a_heading(self):
        text = (
            "# Doc\n\n"
            "## Active Questions\n\n"
            "| ID | Status |\n"
            "| --- | --- |\n"
            "| A-1 | open |\n\n"
            "## Resolved Questions\n\n"
            "| ID | Resolution |\n"
            "| --- | --- |\n"
        )
        headers, rows = extract_table_under_heading(text, "Active Questions")

        self.assertEqual(headers, ["ID", "Status"])
        self.assertEqual(rows, [{"ID": "A-1", "Status": "open"}])

    def test_does_not_bleed_into_the_next_heading_section(self):
        text = (
            "## Active Questions\n\n"
            "| ID | Status |\n"
            "| --- | --- |\n"
            "| A-1 | open |\n\n"
            "## Resolved Questions\n\n"
            "| ID | Resolution |\n"
            "| --- | --- |\n"
            "| R-1 | done |\n"
        )
        headers, rows = extract_table_under_heading(text, "Resolved Questions")

        self.assertEqual(headers, ["ID", "Resolution"])
        self.assertEqual(rows, [{"ID": "R-1", "Resolution": "done"}])

    def test_raises_when_heading_not_found(self):
        with self.assertRaises(MarkdownContractError):
            extract_table_under_heading("# Doc\n\nno such section", "Active Questions")


class RenderPipeTableTests(unittest.TestCase):
    def test_round_trips_through_parse(self):
        headers = ["ID", "Status"]
        rows = [{"ID": "A-1", "Status": "open"}, {"ID": "A-2", "Status": "resolved"}]

        rendered = render_pipe_table(headers, rows)
        parsed_headers, parsed_rows = parse_pipe_table(rendered)

        self.assertEqual(parsed_headers, headers)
        self.assertEqual(parsed_rows, rows)

    def test_renders_empty_rows_as_header_and_separator_only(self):
        rendered = render_pipe_table(["ID", "Status"], [])
        headers, rows = parse_pipe_table(rendered)
        self.assertEqual(headers, ["ID", "Status"])
        self.assertEqual(rows, [])

    def test_missing_row_key_renders_as_empty_cell(self):
        rendered = render_pipe_table(["ID", "Status"], [{"ID": "A-1"}])
        _, rows = parse_pipe_table(rendered)
        self.assertEqual(rows, [{"ID": "A-1", "Status": ""}])


class ExtractTextUnderHeadingTests(unittest.TestCase):
    def test_extracts_stripped_prose_between_headings(self):
        text = (
            "# Doc\n\n"
            "## Headline\n\n"
            "Company X margins accelerating.\n\n"
            "## Summary\n\n"
            "Two sentence summary here.\n"
        )
        self.assertEqual(extract_text_under_heading(text, "Headline"), "Company X margins accelerating.")
        self.assertEqual(extract_text_under_heading(text, "Summary"), "Two sentence summary here.")

    def test_extracts_to_end_of_document_when_no_following_heading(self):
        text = "## Stance\n\nBase Case Constructive.\n"
        self.assertEqual(extract_text_under_heading(text, "Stance"), "Base Case Constructive.")

    def test_returns_empty_string_for_a_blank_section(self):
        text = "## Headline\n\n## Summary\n\ntext\n"
        self.assertEqual(extract_text_under_heading(text, "Headline"), "")

    def test_raises_when_heading_not_found(self):
        with self.assertRaises(MarkdownContractError):
            extract_text_under_heading("# Doc\n\nno such section", "Headline")


if __name__ == "__main__":
    unittest.main()
