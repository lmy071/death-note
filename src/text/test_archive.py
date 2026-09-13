"""Regression coverage for archive selection, extraction, and nested exports."""

from __future__ import annotations

import io
import os
import stat
import tempfile
import unittest
import warnings
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from src.notion_export import archive
from src.notion_export.errors import ImportFailure


class ArchiveRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="notion-archive-regression-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make_zip(self, name: str, members: dict[str, str | bytes]) -> Path:
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.zip_bytes(members))
        return target

    @staticmethod
    def zip_bytes(members: dict[str, str | bytes]) -> bytes:
        buffer = io.BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_STORED) as zipped:
            for name, content in members.items():
                # ZipInfo normalizes Windows backslashes in its constructor;
                # preserve the original member spelling to exercise importers
                # receiving archives produced by other ZIP implementations.
                member = ZipInfo(name)
                member.filename = name
                member.orig_filename = name
                zipped.writestr(member, content)
        return buffer.getvalue()

    def workspace(self, name: str = "workspace") -> Path:
        result = self.root / name
        result.mkdir()
        return result

    @contextmanager
    def working_directory(self, directory: Path):
        previous = Path.cwd()
        try:
            os.chdir(directory)
            yield
        finally:
            os.chdir(previous)

    def test_selects_only_root_archive_by_default(self) -> None:
        expected = self.make_zip("export.zip", {"page.md": "# 页面"})
        self.make_zip("nested/ignored.zip", {"other.md": "ignored"})
        (self.root / "notes.txt").write_text("notes", encoding="utf-8")

        self.assertEqual(archive.select_archive(self.root, None), expected.resolve())

    def test_default_selection_ignores_directory_with_zip_suffix(self) -> None:
        expected = self.make_zip("export.zip", {"page.md": "page"})
        (self.root / "attachment.zip").mkdir()

        self.assertEqual(archive.select_archive(self.root, None), expected.resolve())

    def test_default_selection_reports_missing_archive(self) -> None:
        with self.assertRaisesRegex(ImportFailure, "没有.*zip"):
            archive.select_archive(self.root, None)

    def test_directory_with_zip_suffix_does_not_count_as_an_archive(self) -> None:
        (self.root / "export.zip").mkdir()

        with self.assertRaisesRegex(ImportFailure, "没有.*zip"):
            archive.select_archive(self.root, None)

    def test_default_selection_lists_ambiguous_archives(self) -> None:
        self.make_zip("second.zip", {})
        self.make_zip("first.zip", {})

        with self.assertRaises(ImportFailure) as caught:
            archive.select_archive(self.root, None)
        self.assertIn("多个 ZIP", str(caught.exception))
        self.assertIn("first.zip", str(caught.exception))
        self.assertIn("second.zip", str(caught.exception))

    def test_explicit_archive_accepts_uppercase_extension_and_resolves_path(self) -> None:
        expected = self.make_zip("downloads/export.ZIP", {"page.md": "page"})
        self.make_zip("other.zip", {})

        self.assertEqual(archive.select_archive(self.root, expected), expected.resolve())

    def test_explicit_relative_archive_is_relative_to_working_directory(self) -> None:
        expected = self.make_zip("downloads/export.zip", {"page.md": "page"})
        project = self.workspace("project")

        with self.working_directory(expected.parent):
            selected = archive.select_archive(project, Path("export.zip"))
        self.assertEqual(selected, expected.resolve())

    def test_explicit_archive_must_exist_and_be_a_file(self) -> None:
        directory = self.workspace("directory.zip")
        for candidate in (self.root / "missing.zip", directory):
            with self.subTest(candidate=candidate.name):
                with self.assertRaisesRegex(ImportFailure, "ZIP 不存在"):
                    archive.select_archive(self.root, candidate)

    def test_explicit_archive_rejects_non_zip_extension(self) -> None:
        candidate = self.root / "export.txt"
        candidate.write_text("not a zip", encoding="utf-8")

        with self.assertRaisesRegex(ImportFailure, "不是 ZIP"):
            archive.select_archive(self.root, candidate)

    def test_safe_member_path_preserves_unicode_spaces_and_nested_paths(self) -> None:
        for member in ("吃谷/图片/知更鸟 小卡.png", "吃谷\\图片\\知更鸟 小卡.png"):
            with self.subTest(member=member):
                self.assertEqual(
                    archive.safe_member_path(member),
                    Path("吃谷") / "图片" / "知更鸟 小卡.png",
                )

    def test_safe_member_path_rejects_traversal_absolute_and_empty_paths(self) -> None:
        # Deliberately never extract these paths: on Windows a drive or root
        # component could otherwise escape the temporary destination.
        unsafe_members = (
            "",
            ".",
            "..",
            "../outside.md",
            "folder/../../outside.md",
            "folder/../outside.md",
            "..\\outside.md",
            "folder\\..\\outside.md",
            "/absolute.md",
            "\\absolute.md",
            "//server/share/outside.md",
            "\\\\server\\share\\outside.md",
            "C:/outside.md",
            "C:\\outside.md",
            "C:outside.md",
            "folder/C:/outside.md",
            "folder/C:outside.md",
            "page.md:alternate-stream",
            "folder/page.md:alternate-stream",
            "\\\\?\\C:\\outside.md",
            "bad\x00name.md",
        )
        for member in unsafe_members:
            with self.subTest(member=repr(member)):
                with self.assertRaises(ImportFailure):
                    archive.safe_member_path(member)

    def test_extracts_files_directories_unicode_and_binary_content(self) -> None:
        binary = bytes(range(256))
        zipped = self.make_zip(
            "export.zip",
            {"empty/": b"", "吃谷/页面.md": "# 知更鸟\n", "吃谷/image.png": binary},
        )
        destination = self.workspace()

        archive.extract_zip_safely(zipped, destination)

        self.assertTrue((destination / "empty").is_dir())
        self.assertEqual((destination / "吃谷/页面.md").read_text(encoding="utf-8"), "# 知更鸟\n")
        self.assertEqual((destination / "吃谷/image.png").read_bytes(), binary)

    def test_extracts_safe_backslash_separated_member_into_subdirectory(self) -> None:
        zipped = self.make_zip("export.zip", {"folder\\page.md": "content"})
        destination = self.workspace()

        archive.extract_zip_safely(zipped, destination)

        self.assertEqual((destination / "folder/page.md").read_text(), "content")

    def test_extracts_archive_at_uncompressed_size_limit(self) -> None:
        zipped = self.make_zip("export.zip", {"one.md": b"abc", "two.md": b"de"})
        destination = self.workspace()

        with patch.object(archive, "MAX_UNCOMPRESSED_BYTES", 5):
            archive.extract_zip_safely(zipped, destination)

        self.assertEqual((destination / "one.md").read_bytes(), b"abc")
        self.assertEqual((destination / "two.md").read_bytes(), b"de")

    def test_rejects_total_uncompressed_size_above_limit_before_writing(self) -> None:
        zipped = self.make_zip("export.zip", {"one.md": b"abc", "two.md": b"def"})
        destination = self.workspace()

        with patch.object(archive, "MAX_UNCOMPRESSED_BYTES", 5):
            with self.assertRaisesRegex(ImportFailure, "解压后过大"):
                archive.extract_zip_safely(zipped, destination)
        self.assertEqual(list(destination.iterdir()), [])

    def test_invalid_zip_is_reported_as_import_failure(self) -> None:
        zipped = self.root / "broken.zip"
        zipped.write_bytes(b"this is not a ZIP archive")

        with self.assertRaisesRegex(ImportFailure, "无效 ZIP"):
            archive.extract_zip_safely(zipped, self.workspace())

    def test_truncated_zip_is_reported_as_import_failure(self) -> None:
        zipped = self.make_zip("truncated.zip", {"page.md": "content"})
        zipped.write_bytes(zipped.read_bytes()[:-12])

        with self.assertRaisesRegex(ImportFailure, "无效 ZIP"):
            archive.extract_zip_safely(zipped, self.workspace())

    def test_corrupt_member_checksum_is_reported_as_import_failure(self) -> None:
        content = b"unique-content-for-checksum-regression"
        zipped = self.make_zip("broken.zip", {"page.md": content})
        data = zipped.read_bytes()
        self.assertEqual(data.count(content), 1)
        zipped.write_bytes(data.replace(content, b"x" + content[1:], 1))

        with self.assertRaisesRegex(ImportFailure, "无效 ZIP"):
            archive.extract_zip_safely(zipped, self.workspace())

    def test_duplicate_members_fail_without_overwriting_first_content(self) -> None:
        zipped = self.root / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(zipped, "w") as output:
                output.writestr("page.md", "first")
                output.writestr("page.md", "second")
        destination = self.workspace()

        with self.assertRaisesRegex(ImportFailure, "同名文件"):
            archive.extract_zip_safely(zipped, destination)
        self.assertEqual((destination / "page.md").read_text(), "first")

    def test_existing_destination_file_is_not_overwritten(self) -> None:
        zipped = self.make_zip("export.zip", {"page.md": "replacement"})
        destination = self.workspace()
        (destination / "page.md").write_text("original", encoding="utf-8")

        with self.assertRaisesRegex(ImportFailure, "同名文件"):
            archive.extract_zip_safely(zipped, destination)
        self.assertEqual((destination / "page.md").read_text(), "original")

    def test_members_aliasing_through_slash_normalization_are_rejected(self) -> None:
        zipped = self.make_zip(
            "duplicate.zip", {"folder/page.md": "first", "folder\\page.md": "second"}
        )
        destination = self.workspace()

        with self.assertRaisesRegex(ImportFailure, "同名文件"):
            archive.extract_zip_safely(zipped, destination)
        self.assertEqual((destination / "folder/page.md").read_text(), "first")

    def test_symlink_member_is_rejected_before_creation(self) -> None:
        zipped = self.root / "symlink.zip"
        member = ZipInfo("shortcut.md")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        with ZipFile(zipped, "w") as output:
            output.writestr(member, "page.md")
        destination = self.workspace()

        with self.assertRaisesRegex(ImportFailure, "符号链接"):
            archive.extract_zip_safely(zipped, destination)
        self.assertEqual(list(destination.iterdir()), [])

    def test_unpack_plain_export_preserves_contents(self) -> None:
        zipped = self.make_zip("export.zip", {"页面.md": "# 内容", "assets/card.png": b"image"})
        workspace = self.workspace()

        result = archive.unpack_nested_export(zipped, workspace)

        self.assertTrue(result.is_relative_to(workspace))
        self.assertEqual((result / "页面.md").read_text(encoding="utf-8"), "# 内容")
        self.assertEqual((result / "assets/card.png").read_bytes(), b"image")

    def test_unpack_empty_export_returns_empty_directory(self) -> None:
        result = archive.unpack_nested_export(self.make_zip("empty.zip", {}), self.workspace())

        self.assertTrue(result.is_dir())
        self.assertEqual(list(result.iterdir()), [])

    def test_unpack_combines_nested_parts_and_shared_directories(self) -> None:
        part_one = self.zip_bytes({"pages/": b"", "pages/one.md": "one"})
        part_two = self.zip_bytes({"pages/": b"", "pages/two.md": "two", "image.png": b"png"})
        combined = self.zip_bytes({"Part-2.zip": part_two, "Part-1.ZIP": part_one})
        zipped = self.make_zip("outer.zip", {"Export.zip": combined})

        result = archive.unpack_nested_export(zipped, self.workspace())

        self.assertEqual((result / "pages/one.md").read_text(), "one")
        self.assertEqual((result / "pages/two.md").read_text(), "two")
        self.assertEqual((result / "image.png").read_bytes(), b"png")
        self.assertEqual(sorted(path.name for path in result.iterdir()), ["image.png", "pages"])

    def test_macos_metadata_does_not_prevent_nested_export_detection(self) -> None:
        nested = self.zip_bytes({"page.md": "page", "__MACOSX/._page.md": "metadata"})
        zipped = self.make_zip(
            "export.zip",
            {"Part-1.zip": nested, "__MACOSX/._Part-1.zip": "metadata"},
        )

        result = archive.unpack_nested_export(zipped, self.workspace())

        self.assertEqual((result / "page.md").read_text(), "page")
        self.assertFalse((result / "__MACOSX").exists())

    def test_mixed_export_keeps_zip_attachment_unexpanded(self) -> None:
        attachment = self.zip_bytes({"private.md": "attachment content"})
        zipped = self.make_zip("export.zip", {"page.md": "page", "attachment.zip": attachment})

        result = archive.unpack_nested_export(zipped, self.workspace())

        self.assertEqual((result / "page.md").read_text(), "page")
        self.assertEqual((result / "attachment.zip").read_bytes(), attachment)
        self.assertFalse((result / "private.md").exists())

    def test_nested_zip_in_content_directory_is_kept_as_attachment(self) -> None:
        attachment = self.zip_bytes({"private.md": "attachment content"})
        zipped = self.make_zip("export.zip", {"assets/attachment.zip": attachment})

        result = archive.unpack_nested_export(zipped, self.workspace())

        self.assertEqual((result / "assets/attachment.zip").read_bytes(), attachment)

    def test_nested_export_at_maximum_depth_is_accepted(self) -> None:
        content = self.zip_bytes({"page.md": "page"})
        content = self.zip_bytes({"Part-1.zip": content})
        zipped = self.make_zip("outer.zip", {"Export.zip": content})

        with patch.object(archive, "MAX_NESTED_ZIP_DEPTH", 2):
            result = archive.unpack_nested_export(zipped, self.workspace())
        self.assertEqual((result / "page.md").read_text(), "page")

    def test_zero_nested_depth_still_accepts_plain_export(self) -> None:
        zipped = self.make_zip("export.zip", {"page.md": "page"})

        with patch.object(archive, "MAX_NESTED_ZIP_DEPTH", 0):
            result = archive.unpack_nested_export(zipped, self.workspace())
        self.assertEqual((result / "page.md").read_text(), "page")

    def test_zero_nested_depth_rejects_wrapped_export(self) -> None:
        zipped = self.make_zip(
            "outer.zip", {"Part-1.zip": self.zip_bytes({"page.md": "page"})}
        )

        with patch.object(archive, "MAX_NESTED_ZIP_DEPTH", 0):
            with self.assertRaisesRegex(ImportFailure, "嵌套 ZIP 超过 0 层"):
                archive.unpack_nested_export(zipped, self.workspace())

    def test_nested_export_beyond_maximum_depth_is_rejected(self) -> None:
        content = self.zip_bytes({"page.md": "page"})
        for index in range(2):
            content = self.zip_bytes({f"Part-{index}.zip": content})
        zipped = self.make_zip("outer.zip", {"Export.zip": content})

        with patch.object(archive, "MAX_NESTED_ZIP_DEPTH", 2):
            with self.assertRaisesRegex(ImportFailure, "嵌套 ZIP 超过 2 层"):
                archive.unpack_nested_export(zipped, self.workspace())

    def test_duplicate_files_across_parts_are_rejected(self) -> None:
        zipped = self.make_zip(
            "export.zip",
            {
                "Part-2.zip": self.zip_bytes({"pages/page.md": "second"}),
                "Part-1.zip": self.zip_bytes({"pages/page.md": "first"}),
            },
        )

        with self.assertRaisesRegex(ImportFailure, "同名文件"):
            archive.unpack_nested_export(zipped, self.workspace())

    def test_corrupt_nested_zip_is_reported_as_import_failure(self) -> None:
        zipped = self.make_zip("export.zip", {"Part-1.zip": b"not a ZIP"})

        with self.assertRaisesRegex(ImportFailure, "无效 ZIP"):
            archive.unpack_nested_export(zipped, self.workspace())


if __name__ == "__main__":
    unittest.main()
