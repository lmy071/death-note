"""Validate local destinations without requesting remote resources."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from src.notion_export.errors import ImportFailure
from src.notion_export.validation import validate_links, validate_no_notion_ids


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="notion-validation-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "export"
        self.root.mkdir()

    def write(self, relative: str, content: str = "") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_inline_image_reference_and_root_links_resolve_with_url_suffixes(self) -> None:
        self.write("条目 one.md", "# 条目\n")
        self.write("assets/图片 one.png")
        page = quote("../条目 one.md", safe="/")
        image = quote("/assets/图片 one.png", safe="/")
        self.write(
            "目录/索引.md",
            f'[条目](<{page}?view=full#标题> "标题")\n'
            f'![图片]({image})\n[参考][item]\n[item]: {page} "标题"\n'
            f'[目录](/assets/)\n',
        )
        self.assertEqual(validate_links(self.root), 4)

    def test_external_anchors_and_code_examples_do_not_require_local_files(self) -> None:
        self.write(
            "index.md",
            "[网络](https://example.test/missing.md)\n[邮件](mailto:test@example.test)\n"
            "[网络](//example.test/missing.md)\n[锚点](#heading)\n[查询](?view=1)\n"
            "`[示例](missing-inline.md)`\n```md\n[示例](missing-fence.md)\n```\n"
            "~~~md\n[图片](missing.png)\n~~~\n[远程][remote]\n"
            "[remote]: https://example.test/remote.md\n",
        )
        self.assertEqual(validate_links(self.root), 0)

    def test_missing_reference_and_image_are_reported_with_source(self) -> None:
        self.write("index.md", "![图片](missing.png)\n[条目][ref]\n[ref]: missing.md\n")
        with self.assertRaises(ImportFailure) as caught:
            validate_links(self.root)
        message = str(caught.exception)
        self.assertIn("index.md", message)
        self.assertIn("missing.png", message)
        self.assertIn("missing.md", message)

    def test_existing_target_outside_export_is_rejected(self) -> None:
        (self.base / "outside.md").write_text("outside", encoding="utf-8")
        self.write("index.md", "[越界](../outside.md)\n")
        with self.assertRaisesRegex(ImportFailure, "outside.md"):
            validate_links(self.root)

    def test_many_broken_links_produce_bounded_error_with_total(self) -> None:
        self.write("index.md", "\n".join(f"[{i}](missing-{i}.md)" for i in range(25)))
        with self.assertRaises(ImportFailure) as caught:
            validate_links(self.root)
        message = str(caught.exception)
        self.assertIn("25", message)
        self.assertIn("missing-0.md", message)
        self.assertNotIn("missing-24.md", message)

    def test_empty_tree_has_no_broken_links_or_remaining_ids(self) -> None:
        self.assertEqual(validate_links(self.root), 0)
        validate_no_notion_ids(self.root)

    def test_remaining_ids_in_directories_and_files_are_reported(self) -> None:
        directory = "数据库 " + "a" * 32
        filename = "表格 " + "b" * 32 + "_all.csv"
        self.write(f"{directory}/{filename}")
        with self.assertRaises(ImportFailure) as caught:
            validate_no_notion_ids(self.root)
        self.assertIn(directory, str(caught.exception))
        self.assertIn(filename, str(caught.exception))

    def test_ids_in_text_or_non_notion_filenames_are_preserved(self) -> None:
        self.write("UUID-a" + "b" * 31 + ".md", "正文 " + "c" * 32)
        self.write("记录_all.md", "# 记录\n")
        validate_no_notion_ids(self.root)

    def test_extended_code_forms_hide_examples_but_leave_live_links_visible(self) -> None:
        self.write("live.md", "# live\n")
        samples = (
            "``[示例](missing.md) `literal` ``\n",
            "````md\n```\n[示例](missing.md)\n````\n",
            "~~~~text\n~~~\n[示例](missing.md)\n~~~~\n",
            "    [示例](missing.md)\n\n",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.write("index.md", sample + "[真实链接](live.md)\n")
                self.assertEqual(validate_links(self.root), 1)

    def test_unclosed_fence_ignores_example_links_through_end_of_file(self) -> None:
        self.write("index.md", "```md\n[示例](missing.md)\n[ref]: absent.md\n")
        self.assertEqual(validate_links(self.root), 0)


if __name__ == "__main__":
    unittest.main()
