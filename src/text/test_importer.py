"""Import staging failures and binary/content preservation."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from src.notion_export.csv_tables import csv_to_markdown
from src.notion_export.errors import ImportFailure
from src.notion_export.importer import create_import_tree
from src.notion_export.validation import validate_links


class ImportTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="notion-staging-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.clean = self.root / "clean"
        self.raw.mkdir()
        self.clean.mkdir()

    def test_empty_export_is_rejected(self) -> None:
        with self.assertRaisesRegex(ImportFailure, "没有可导入文件"):
            create_import_tree(self.raw, self.clean)

    def test_binary_attachment_is_copied_exactly_and_plain_text_is_preserved(self) -> None:
        content = bytes(range(256)) * 3
        (self.raw / "attachment.bin").write_bytes(content)
        markdown = "# 页面\n\n正文不应改变。\n"
        (self.raw / "页面.md").write_text(markdown, encoding="utf-8")
        count, changed, links = create_import_tree(self.raw, self.clean)
        self.assertEqual((count, changed, links), (2, 0, 0))
        self.assertEqual((self.clean / "attachment.bin").read_bytes(), content)
        self.assertEqual((self.clean / "页面.md").read_text(encoding="utf-8"), markdown)

    def test_invalid_utf8_markdown_is_reported_as_import_failure(self) -> None:
        (self.raw / "invalid.md").write_bytes(b"\xff\xfeinvalid")
        with self.assertRaisesRegex(ImportFailure, "UTF-8"):
            create_import_tree(self.raw, self.clean)

    def test_invalid_utf8_csv_is_reported_as_import_failure(self) -> None:
        (self.raw / "invalid.csv").write_bytes(b"name\n\xff\xfe")
        with self.assertRaisesRegex(ImportFailure, "CSV"):
            create_import_tree(self.raw, self.clean)

    def test_malformed_quoted_csv_is_rejected_without_truncating_records(self) -> None:
        source = self.raw / "invalid.csv"
        source.write_text('名称,备注\n条目,"未闭合的单元格\n', encoding="utf-8")
        with self.assertRaisesRegex(ImportFailure, "CSV"):
            csv_to_markdown(source)

    def test_csv_literal_backticks_do_not_hide_a_local_link_from_rewriting(self) -> None:
        (self.raw / "Page old.md").write_text("# Page old\n", encoding="utf-8")
        with (self.raw / "table.csv").open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerows([
                ["前文", "页面", "后文"],
                ["`literal", "[Page](Page%20old.md)", "literal`"],
            ])
        create_import_tree(self.raw, self.clean)
        rendered = (self.clean / "table.md").read_text(encoding="utf-8")
        self.assertIn(f"[Page]({quote('Page-old.md')})", rendered)
        self.assertEqual(validate_links(self.clean), 1)


if __name__ == "__main__":
    unittest.main()
