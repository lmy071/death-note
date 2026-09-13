"""Regression coverage for Notion filename normalization and path allocation."""

from pathlib import Path
import tempfile
import unittest

from src.notion_export.errors import ImportFailure
from src.notion_export.paths import (
    first_heading,
    hyphenate_spaces,
    normalize_dotted_filename,
    plan_import_paths,
    strip_notion_id,
)


FIRST_ID = "1" * 32
SECOND_ID = "2" * 32


class FilenameNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def markdown(self, name, content):
        source = self.root / name
        source.write_text(content, encoding="utf-8")
        return source

    def test_strip_notion_id_preserves_extension_and_all_suffix(self):
        cases = {
            f"吃谷 {FIRST_ID}": "吃谷",
            f"吃谷 {FIRST_ID}.md": "吃谷.md",
            f"吃谷 {FIRST_ID}.csv": "吃谷.csv",
            f"吃谷 {FIRST_ID}_all.csv": "吃谷_all.csv",
            f"吃谷 {FIRST_ID}_all": "吃谷_all",
            f"Release 3.5 {'ABCDEF01' * 4}.MD": "Release 3.5.MD",
            f"image {FIRST_ID}.png": "image.png",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(strip_notion_id(source), expected)

    def test_strip_notion_id_leaves_ordinary_and_malformed_names_unchanged(self):
        for name in (
            "普通文件.md",
            "Release 3.5.md",
            "folder with spaces",
            f"page {'1' * 31}.md",
            f"page {'1' * 33}.md",
            f"page {'g' * 32}.md",
            f"page{FIRST_ID}.md",
            f"page {FIRST_ID}_backup.md",
        ):
            with self.subTest(name=name):
                self.assertEqual(strip_notion_id(name), name)

    def test_first_heading_accepts_bom_and_returns_first_level_one_heading(self):
        source = self.root / "page.md"
        source.write_bytes(
            "\ufeffintro\n## Nested\n#  第一标题  \n# Second\n".encode("utf-8")
        )
        self.assertEqual(first_heading(source), "第一标题")

    def test_first_heading_returns_none_without_level_one_heading(self):
        source = self.markdown("page.md", "title\n=====\n## Nested\n#No space\n")
        self.assertIsNone(first_heading(source))

    def test_first_heading_rejects_invalid_utf8_with_import_failure(self):
        source = self.root / "invalid.md"
        source.write_bytes(b"# title\n\xff")
        with self.assertRaisesRegex(ImportFailure, "Markdown 不是 UTF-8 编码"):
            first_heading(source)

    def test_normalize_dotted_filename_restores_matching_title_only(self):
        cases = (
            ("Vue 3 5 35.md", "Vue 3.5.35", "Vue 3.5.35.md"),
            (" value.MD", ".value", ".value.MD"),
            ("v1 2 draft.md", "v1.2 draft", "v1.2 draft.md"),
            ("Original.md", "Other.title", "Original.md"),
            ("Vue 3 5.md", "Vue 3 5", "Vue 3 5.md"),
        )
        for clean_name, heading, expected in cases:
            with self.subTest(clean_name=clean_name, heading=heading):
                source = self.markdown("source.MD", f"# {heading}\n")
                self.assertEqual(normalize_dotted_filename(clean_name, source), expected)

    def test_normalize_dotted_filename_leaves_file_without_heading_unchanged(self):
        source = self.markdown("source.md", "## Vue 3.5\n")
        self.assertEqual(normalize_dotted_filename("Vue 3 5.md", source), "Vue 3 5.md")

    def test_normalize_dotted_filename_does_not_read_non_markdown(self):
        source = self.root / "picture.png"
        source.write_bytes(b"\xff\xfe")
        self.assertEqual(normalize_dotted_filename("picture.png", source), "picture.png")

    def test_hyphenate_spaces_collapses_runs_without_changing_other_characters(self):
        cases = {
            "Vue  3 5": "Vue-3-5",
            " leading  and trailing ": "-leading-and-trailing-",
            "中文 title.md": "中文-title.md",
            "already-hyphenated.md": "already-hyphenated.md",
            "tab\tname\u3000title": "tab\tname\u3000title",
            "": "",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(hyphenate_spaces(source), expected)


class ImportPathPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def file(self, relative, content=""):
        source = self.root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(content, encoding="utf-8")
        return source

    def test_empty_export_maps_its_root(self):
        self.assertEqual(plan_import_paths(self.root), {Path(): Path()})

    def test_plain_paths_and_empty_directories_are_preserved(self):
        self.file("plain.md", "# Plain\n")
        self.file("assets/photo.png", "image")
        (self.root / "empty").mkdir()
        expected = {Path(): Path()}
        expected.update({Path(name): Path(name) for name in (
            "plain.md", "assets", "assets/photo.png", "empty",
        )})
        self.assertEqual(plan_import_paths(self.root), expected)

    def test_duplicate_pages_move_their_own_attachments_as_one_group(self):
        first = f"吃谷 {FIRST_ID}"
        second = f"吃谷 {SECOND_ID}"
        for name in (first, second):
            self.file(f"{name}.md", "# 吃谷\n")
            self.file(f"{name}/图片.png", name)

        planned = plan_import_paths(self.root)

        for source, target in ((first, "吃谷"), (second, "吃谷-2")):
            with self.subTest(source=source):
                self.assertEqual(planned[Path(source + ".md")], Path(target + ".md"))
                self.assertEqual(planned[Path(source)], Path(target))
                self.assertEqual(planned[Path(source) / "图片.png"], Path(target) / "图片.png")
        self.assertEqual(len(planned), 7)

    def test_disambiguation_reserves_natural_numbered_page_names(self):
        first = f"Topic {FIRST_ID}.md"
        second = f"Topic {SECOND_ID}.md"
        for name in (first, second, "Topic-2.md"):
            self.file(name)

        planned = plan_import_paths(self.root)

        self.assertEqual(planned[Path(first)], Path("Topic.md"))
        self.assertEqual(planned[Path(second)], Path("Topic-3.md"))
        self.assertEqual(planned[Path("Topic-2.md")], Path("Topic-2.md"))

    def test_case_insensitive_collisions_do_not_overwrite_pages(self):
        # Different IDs make the source names distinct on Windows as well as POSIX.
        first = f"Topic {FIRST_ID}.md"
        second = f"topic {SECOND_ID}.md"
        self.file(second)
        self.file(first)

        planned = plan_import_paths(self.root)

        self.assertEqual(planned[Path(first)], Path("Topic.md"))
        self.assertEqual(planned[Path(second)], Path("topic-2.md"))
        self.assertEqual(len({str(path).casefold() for path in planned.values()}), len(planned))

    def test_attachment_space_collisions_add_number_before_extension(self):
        self.file("hero  image.png", "first")
        self.file("hero image.png", "second")
        self.file("hero-image-2.png", "natural name")

        planned = plan_import_paths(self.root)

        self.assertEqual(planned[Path("hero  image.png")], Path("hero-image.png"))
        self.assertEqual(planned[Path("hero image.png")], Path("hero-image-3.png"))
        self.assertEqual(planned[Path("hero-image-2.png")], Path("hero-image-2.png"))

    def test_unique_untagged_directory_follows_restored_page_title(self):
        page = f"Vue 3 5 {FIRST_ID}.md"
        self.file(page, "# Vue 3.5\n")
        self.file("Vue 3 5/screen shot.png", "image")

        planned = plan_import_paths(self.root)

        self.assertEqual(planned[Path(page)], Path("Vue-3.5.md"))
        self.assertEqual(planned[Path("Vue 3 5")], Path("Vue-3.5"))
        self.assertEqual(
            planned[Path("Vue 3 5/screen shot.png")], Path("Vue-3.5/screen-shot.png")
        )

    def test_ambiguous_untagged_directory_is_kept_separate(self):
        first = f"Topic {FIRST_ID}.md"
        second = f"Topic {SECOND_ID}.md"
        self.file(first)
        self.file(second)
        self.file("Topic/attachment.png", "unknown owner")

        planned = plan_import_paths(self.root)

        self.assertEqual(planned[Path("Topic")], Path("Topic"))
        self.assertEqual(planned[Path("Topic/attachment.png")], Path("Topic/attachment.png"))
        self.assertEqual(planned[Path(first)], Path("Topic-2.md"))
        self.assertEqual(planned[Path(second)], Path("Topic-3.md"))

    def test_existing_tagged_directory_prevents_association_with_untagged_directory(self):
        page = f"Topic {FIRST_ID}"
        self.file(page + ".md")
        self.file(f"{page}/owned.png", "owned")
        self.file("Topic/unclaimed.png", "unclaimed")

        planned = plan_import_paths(self.root)

        self.assertEqual(planned[Path("Topic")], Path("Topic"))
        self.assertEqual(planned[Path(page)], Path("Topic-2"))
        self.assertEqual(planned[Path(page + ".md")], Path("Topic-2.md"))
        self.assertEqual(planned[Path(page) / "owned.png"], Path("Topic-2/owned.png"))

    def test_nested_page_and_attachment_names_use_their_planned_parent(self):
        parent = f"Parent page {FIRST_ID}"
        child = f"Child page {SECOND_ID}"
        self.file(parent + ".md", "# Parent page\n")
        self.file(f"{parent}/{child}.md", "# Child page\n")
        self.file(f"{parent}/{child}/hero  image.png", "image")

        planned = plan_import_paths(self.root)

        self.assertEqual(planned[Path(parent + ".md")], Path("Parent-page.md"))
        self.assertEqual(
            planned[Path(parent) / (child + ".md")], Path("Parent-page/Child-page.md")
        )
        self.assertEqual(
            planned[Path(parent) / child / "hero  image.png"],
            Path("Parent-page/Child-page/hero-image.png"),
        )

    def test_planning_does_not_rename_or_rewrite_source_files(self):
        source_name = f"Vue 3 5 {FIRST_ID}.md"
        content = "# Vue 3.5\n\nOriginal content.\n"
        source = self.file(source_name, content)
        before = source.read_bytes()

        first = plan_import_paths(self.root)
        second = plan_import_paths(self.root)

        self.assertEqual(first, second)
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse((self.root / "Vue-3.5.md").exists())
        self.assertEqual(list(self.root.iterdir()), [source])


if __name__ == "__main__":
    unittest.main()
