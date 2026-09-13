"""Regression coverage for lossless Notion export path normalization."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote, unquote

import restore_notion_export as importer


ID_1 = "00000000000000000000000000000001"
ID_2 = "00000000000000000000000000000002"
ID_3 = "00000000000000000000000000000003"


class ImportTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = tempfile.TemporaryDirectory(prefix="notion-export-test-")
        self.addCleanup(self.workspace.cleanup)
        root = Path(self.workspace.name)
        self.raw = root / "raw"
        self.clean = root / "clean"
        self.raw.mkdir()
        self.clean.mkdir()

    def write(self, relative: str, content: str | bytes) -> None:
        destination = self.raw / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            destination.write_bytes(content)
        else:
            destination.write_text(content, encoding="utf-8")

    def convert(self) -> tuple[int, int, int]:
        result = importer.create_import_tree(self.raw, self.clean)
        importer.validate_no_notion_ids(self.clean)
        importer.validate_links(self.clean)
        return result

    def read(self, relative: str) -> str:
        return (self.clean / relative).read_text(encoding="utf-8")

    def targets(self, relative: str) -> list[str]:
        return [
            unquote(target.strip().removeprefix("<").removesuffix(">"))
            for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", self.read(relative))
        ]

    def test_duplicate_pages_preserve_contents_and_paired_attachments(self) -> None:
        first = f"页面 {ID_1}"
        second = f"页面 {ID_2}"
        self.write(f"{first}.md", f"# 页面\n\nfirst\n\n![图]({quote(first)}/image.png)\n")
        self.write(f"{second}.md", f"# 页面\n\nsecond\n\n![图]({quote(second)}/image.png)\n")
        self.write(f"{first}/image.png", b"first attachment")
        self.write(f"{second}/image.png", b"second attachment")
        self.write("index.md", f"[一]({quote(first)}.md)\n[二]({quote(second)}.md)\n")

        count, _, _ = self.convert()

        self.assertEqual(count, 5)
        self.assertIn("\nfirst\n", self.read("页面.md"))
        self.assertIn("\nsecond\n", self.read("页面-2.md"))
        self.assertEqual((self.clean / "页面/image.png").read_bytes(), b"first attachment")
        self.assertEqual((self.clean / "页面-2/image.png").read_bytes(), b"second attachment")
        self.assertEqual(self.targets("页面.md"), ["页面/image.png"])
        self.assertEqual(self.targets("页面-2.md"), ["页面-2/image.png"])
        self.assertEqual(self.targets("index.md"), ["页面.md", "页面-2.md"])

    def test_existing_numbered_name_is_reserved(self) -> None:
        self.write(f"Note {ID_1}.md", "# Note\n\nfirst\n")
        self.write(f"Note {ID_2}.md", "# Note\n\nsecond\n")
        self.write(f"Note-2 {ID_3}.md", "# Note-2\n\nnatural numbered title\n")

        self.convert()

        self.assertIn("first", self.read("Note.md"))
        self.assertIn("natural numbered title", self.read("Note-2.md"))
        self.assertIn("second", self.read("Note-3.md"))

    def test_id_free_companion_directory_follows_dotted_page_name(self) -> None:
        stem = "Vue 3 5"
        self.write(f"{stem} {ID_1}.md", f"# Vue 3.5\n\n![file]({quote(stem)}/image.png)\n")
        self.write(f"{stem}/image.png", b"companion without ID")

        self.convert()

        self.assertEqual(self.targets("Vue-3.5.md"), ["Vue-3.5/image.png"])
        self.assertEqual((self.clean / "Vue-3.5/image.png").read_bytes(), b"companion without ID")
        self.assertFalse((self.clean / "Vue-3-5").exists())

    def test_csv_and_all_csv_keep_their_page_family_suffix(self) -> None:
        for notion_id, content in [(ID_1, "first"), (ID_2, "second")]:
            stem = f"Table {notion_id}"
            self.write(f"{stem}.csv", f"Name\n{content}\n")
            self.write(f"{stem}_all.csv", f"Name,Details\n{content},all columns\n")
            self.write(f"{stem}/record.md", f"# Record\n\n{content}\n")
        self.write("index.md", f"[all](Table%20{ID_2}_all.csv)\n[record](Table%20{ID_2}/record.md)\n")

        self.convert()

        self.assertIn("first", self.read("Table.csv"))
        self.assertIn("first", self.read("Table_all.csv"))
        self.assertIn("second", self.read("Table-2.csv"))
        self.assertIn("second", self.read("Table-2_all.csv"))
        self.assertIn("second", self.read("Table-2/record.md"))
        self.assertEqual(self.targets("index.md"), ["Table-2_all.csv", "Table-2/record.md"])

    def test_csv_accepts_companion_directory_without_id(self) -> None:
        self.write(f"Data Base {ID_1}.csv", "Name\nrecord\n")
        self.write("Data Base/record.md", "# Record\n")
        self.write("index.md", f"[table](Data%20Base%20{ID_1}.csv)\n[record](Data%20Base/record.md)\n")

        self.convert()

        self.assertEqual(self.targets("index.md"), ["Data-Base.csv", "Data-Base/record.md"])

    def test_nested_duplicate_directories_do_not_merge_disjoint_files(self) -> None:
        first = f"Folder {ID_1}"
        second = f"Folder {ID_2}"
        child = f"Child {ID_3}"
        self.write(f"{first}.md", f"# Folder\n\n[child]({quote(first)}/{quote(child)}.md)\n")
        self.write(f"{second}.md", f"# Folder\n\n[child]({quote(second)}/{quote(child)}.md)\n")
        self.write(f"{first}/{child}.md", f"# Child\n\n![first]({quote(child)}/first.bin)\n")
        self.write(f"{second}/{child}.md", f"# Child\n\n![second]({quote(child)}/second.bin)\n")
        self.write(f"{first}/{child}/first.bin", b"first")
        self.write(f"{second}/{child}/second.bin", b"second")

        self.convert()

        self.assertTrue((self.clean / "Folder/Child/first.bin").is_file())
        self.assertTrue((self.clean / "Folder-2/Child/second.bin").is_file())
        self.assertFalse((self.clean / "Folder/Child/second.bin").exists())
        self.assertEqual(self.targets("Folder.md"), ["Folder/Child.md"])
        self.assertEqual(self.targets("Folder-2.md"), ["Folder-2/Child.md"])

    def test_same_source_basename_uses_parent_specific_mapping(self) -> None:
        repeated = f"Note {ID_2}.md"
        self.write(f"Alpha/Note {ID_1}.md", "# Note\n\nfirst alpha\n")
        self.write(f"Alpha/{repeated}", "# Note\n\nsecond alpha\n")
        self.write(f"Beta/{repeated}", "# Note\n\nonly beta\n")
        self.write("Alpha/index.md", f"[local]({quote(repeated)})\n[other](../Beta/{quote(repeated)})\n")
        self.write("Beta/index.md", f"[local]({quote(repeated)})\n[other](../Alpha/{quote(repeated)})\n")

        self.convert()

        self.assertEqual(self.targets("Alpha/index.md"), ["Note-2.md", "../Beta/Note.md"])
        self.assertEqual(self.targets("Beta/index.md"), ["Note.md", "../Alpha/Note-2.md"])
        self.assertIn("only beta", self.read("Beta/Note.md"))

    def test_case_only_collision_keeps_both_pages(self) -> None:
        self.write(f"Foo {ID_1}.md", "# Foo\n\nuppercase\n")
        self.write(f"foo {ID_2}.md", "# foo\n\nlowercase\n")

        self.convert()

        self.assertIn("uppercase", self.read("Foo.md"))
        self.assertIn("lowercase", self.read("foo-2.md"))
        self.assertEqual(len({path.name.casefold() for path in self.clean.iterdir()}), 2)

    def test_space_and_hyphen_collision_keeps_both_pages(self) -> None:
        self.write(f"A B {ID_1}.md", "# A B\n\nspaced title\n")
        self.write(f"A-B {ID_2}.md", "# A-B\n\nhyphen title\n")

        self.convert()

        self.assertIn("spaced title", self.read("A-B.md"))
        self.assertIn("hyphen title", self.read("A-B-2.md"))

    def test_dotted_heading_restores_only_its_own_page_and_directory(self) -> None:
        stem = f"Vue 3 5 {ID_1}"
        self.write(f"Alpha/{stem}.md", f"# Vue 3.5\n\n![file]({quote(stem)}/image.png)\n")
        self.write(f"Alpha/{stem}/image.png", b"dotted")
        self.write(f"Beta/{stem}.md", f"# Vue 3 5\n\n![file]({quote(stem)}/image.png)\n")
        self.write(f"Beta/{stem}/image.png", b"spaced")
        self.write("index.md", f"[dotted](Alpha/{quote(stem)}.md)\n[spaced](Beta/{quote(stem)}.md)\n")

        self.convert()

        self.assertEqual(self.targets("index.md"), ["Alpha/Vue-3.5.md", "Beta/Vue-3-5.md"])
        self.assertEqual(self.targets("Alpha/Vue-3.5.md"), ["Vue-3.5/image.png"])
        self.assertEqual(self.targets("Beta/Vue-3-5.md"), ["Vue-3-5/image.png"])
        self.assertTrue(self.read("Alpha/Vue-3.5.md").startswith("# Vue 3.5\n"))
        self.assertTrue(self.read("Beta/Vue-3-5.md").startswith("# Vue 3 5\n"))

    def test_local_link_spellings_queries_fragments_and_parent_paths(self) -> None:
        first = f"Note name {ID_1}.md"
        second = f"Note name {ID_2}.md"
        self.write(first, "# Note name\n\nfirst\n")
        self.write(second, "# Note name\n\nsecond\n")
        self.write(
            "Child/index.md",
            f"[encoded](../{quote(second)}?download=1#section)\n"
            f"[raw](../{second})\n"
            f"[angle](<../{second}#heading>)\n"
            f"[root](/{quote(first)}#top)\n",
        )

        self.convert()

        self.assertEqual(
            self.targets("Child/index.md"),
            [
                "../Note-name-2.md?download=1#section",
                "../Note-name-2.md",
                "../Note-name-2.md#heading",
                "/Note-name.md#top",
            ],
        )

    def test_non_link_text_external_links_and_code_are_unchanged(self) -> None:
        stem = f"Note name {ID_1}"
        self.write(f"{stem}.md", "# Note name\n")
        unchanged = (
            f"# {stem}\n\nPlain text: {stem}.md and {quote(stem)}.md\n\n"
            f"[web](https://example.com/{quote(stem)}.md)\n"
            f"[network](//example.com/{quote(stem)}.md)\n"
            f"[mail](mailto:{quote(stem)}@example.com)\n\n"
            f"`[inline]({quote(stem)}.md)`\n\n"
            f"```markdown\n[code]({quote(stem)}.md)\n```\n\n"
            f"~~~markdown\n[code]({quote(stem)}.md)\n~~~\n\n"
        )
        self.write("index.md", unchanged + f"[local]({quote(stem)}.md)\n")

        self.convert()

        self.assertTrue(self.read("index.md").startswith(unchanged))
        self.assertNotIn(ID_1, self.read("index.md")[len(unchanged):])
        self.assertIn("Note-name.md", self.read("index.md")[len(unchanged):])

    def test_reference_definitions_inline_links_and_code_share_correct_mapping(self) -> None:
        first = f"Note name {ID_1}.md"
        second = f"Note name {ID_2}.md"
        self.write(first, "# Note name\n\nfirst\n")
        self.write(second, "# Note name\n\nsecond\n")
        code = (
            "```markdown\n"
            f"[code]: ../{quote(second)} \"literal title\"\n"
            "```\n"
        )
        self.write(
            "Child/index.md",
            f"[inline before](../{quote(first)})\n"
            "[encoded reference][encoded]\n[angle reference][angle]\n\n"
            f"[encoded]: ../{quote(second)}?download=1#section\n"
            f"[inline between](../{quote(second)})\n"
            f"[angle]: <../{second}#heading> \"display title\"\n"
            + code
            + f"[inline after](../{quote(first)})\n",
        )

        self.convert()

        updated = self.read("Child/index.md")
        definitions = {
            label: target
            for label, target in re.findall(r"^\[(encoded|angle)\]: (.+)$", updated, re.MULTILINE)
        }
        self.assertEqual(
            unquote(definitions["encoded"]),
            "../Note-name-2.md?download=1#section",
        )
        self.assertEqual(
            unquote(definitions["angle"]),
            '<../Note-name-2.md#heading> "display title"',
        )
        self.assertEqual(
            self.targets("Child/index.md"),
            ["../Note-name.md", "../Note-name-2.md", "../Note-name.md"],
        )
        self.assertIn(code, updated)
        broken = updated.replace(
            "[encoded]: " + definitions["encoded"], "[encoded]: missing.md", 1
        )
        (self.clean / "Child/index.md").write_text(broken, encoding="utf-8")
        with self.assertRaisesRegex(importer.ImportFailure, r"missing\.md"):
            importer.validate_links(self.clean)

    def test_planning_is_independent_of_source_creation_order(self) -> None:
        self.write(f"Note {ID_2}.md", "# Note\n\nsecond\n")
        self.write(f"Note {ID_1}.md", "# Note\n\nfirst\n")
        self.convert()
        expected = {
            str(path.relative_to(self.clean)): path.read_bytes()
            for path in self.clean.rglob("*")
            if path.is_file()
        }
        second_raw = self.raw.parent / "raw-second"
        second_clean = self.raw.parent / "clean-second"
        second_raw.mkdir()
        second_clean.mkdir()
        for source in sorted(self.raw.iterdir()):
            (second_raw / source.name).write_bytes(source.read_bytes())

        importer.create_import_tree(second_raw, second_clean)

        actual = {
            str(path.relative_to(second_clean)): path.read_bytes()
            for path in second_clean.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, expected)
        self.assertIn(b"first", actual["Note.md"])

    def test_image_links_become_images_without_changing_labels_targets_or_titles(self) -> None:
        image_url = "https://gitee.com/Lmy071/images/raw/main/ChiGuJiLu/1787196021835.png"
        original = (
            "# aven风堇明信片\n\n价格: 5\n"
            f"图片: [{image_url}]({image_url})\n"
            '[另一张](<https://example.com/card.JPEG?size=2#front> "正面")\n'
            "备注: 复数可出，第一张收价6\n数量: 1\n"
        )
        self.write("card.md", original)

        self.convert()

        self.assertEqual(
            self.read("card.md"),
            original.replace(f"[{image_url}]", f"![{image_url}]").replace("[另一张]", "![另一张]"),
        )

    def test_bare_image_properties_and_standalone_addresses_are_embedded(self) -> None:
        urls = [f"https://example.com/{name}.png" for name in ("chinese", "colon", "single", "plural", "alone")]
        prefixes = ["图片: ", "图片：", "iMaGe: ", "IMAGES： ", ""]
        self.write("images.md", "\n".join(prefix + url for prefix, url in zip(prefixes, urls)) + "\n")

        self.convert()

        updated = self.read("images.md")
        self.assertEqual(self.targets("images.md"), urls)
        self.assertEqual(updated.count("![图片]("), len(urls))
        for prefix, line in zip(prefixes, updated.splitlines()):
            self.assertTrue(line.startswith(prefix + "![图片]("), line)

    def test_image_extensions_ignore_case_and_allow_queries_and_fragments(self) -> None:
        urls = [
            f"https://example.com/picture.{extension}?download=1#preview"
            for extension in ("PNG", "JpG", "JPEG", "GiF", "WeBp", "SVG", "BMP", "AVIF", "ICO")
        ]
        self.write("formats.md", "\n".join(f"[format {index}]({url})" for index, url in enumerate(urls)) + "\n")

        self.convert()

        self.assertEqual(self.targets("formats.md"), urls)
        self.assertEqual(
            self.read("formats.md"),
            "\n".join(f"![format {index}]({url})" for index, url in enumerate(urls)) + "\n",
        )

    def test_local_image_properties_are_embedded_before_attachment_paths_are_renamed(self) -> None:
        stem = f"初音 未來 {ID_1}"
        self.write(f"{stem}.md", "# 初音 未來\n\n图片: " + quote(stem + "/front card.JPEG") + "\n")
        self.write(f"{stem}/front card.JPEG", b"front image bytes")
        self.write("index.md", f"[封面]({quote(stem + '/front card.JPEG')}?download=1#front)\n")

        self.convert()

        self.assertIn("图片: ![图片](", self.read("初音-未來.md"))
        self.assertEqual(self.targets("初音-未來.md"), ["初音-未來/front-card.JPEG"])
        self.assertTrue(self.read("index.md").startswith("![封面]("))
        self.assertEqual(self.targets("index.md"), ["初音-未來/front-card.JPEG?download=1#front"])
        self.assertEqual((self.clean / "初音-未來/front-card.JPEG").read_bytes(), b"front image bytes")
        self.assertEqual(importer.validate_links(self.clean), 2)

    def test_existing_images_non_image_links_and_code_are_preserved(self) -> None:
        url = "https://example.com/picture.png"
        original = (
            f'![已经是图片]({url} "原始标题")\n'
            "[普通网页](https://example.com/page)\n"
            "[下载页](https://example.com/download?file=picture.png)\n"
            f"正文中提到 {url}，保持原文。\n"
            f"`[行内代码]({url})`\n"
            f"`图片: {url}`\n"
            f"```markdown\n图片: {url}\n[代码]({url})\n```\n"
            f"~~~markdown\n{url}\n[代码]({url})\n~~~\n"
        )
        self.write("preserved.md", original)

        self.convert()

        self.assertEqual(self.read("preserved.md"), original)

    def test_image_conversion_is_idempotent(self) -> None:
        self.write(
            "images.md",
            "图片: https://example.com/front.png\n"
            "[背面](https://example.com/back.webp)\n"
            "![现有图片](https://example.com/existing.gif)\n",
        )
        self.convert()
        converted = self.read("images.md")
        self.assertEqual(converted.count("!["), 3)
        second_clean = self.raw.parent / "clean-second"
        second_clean.mkdir()

        importer.create_import_tree(self.clean, second_clean)

        self.assertEqual((second_clean / "images.md").read_text(encoding="utf-8"), converted)
        self.assertNotIn("!![", converted)


if __name__ == "__main__":
    unittest.main()
