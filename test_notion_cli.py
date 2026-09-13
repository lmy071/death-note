"""Regression tests for the relocated CLI and safe project replacement."""

from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote
from zipfile import ZipFile

from src.notion_export import cli, importer
from src.notion_export.errors import ImportFailure


PROJECT_ROOT = Path(__file__).resolve().parent
ENTRYPOINT = PROJECT_ROOT / "src" / "restore_notion_export.py"


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Include empty directories and exact file bytes in preservation checks."""
    return {
        path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


class NotionCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="notion-cli-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        self.other_cwd = self.base / "other-cwd"
        self.other_cwd.mkdir()
        self.archive = self.project / "export.zip"

        self.write_project("src/tool.py", "# Keep the importer source.\n")
        self.write_project("src/ignored.zip", "Not a root export.\n")
        self.write_project("test_existing.py", "# Keep regression tests.\n")
        self.write_project(".config.json", '{"keep": true}\n')
        self.write_project(".git/config", "fixture Git metadata\n")
        self.write_project("无关页面.md", "# 无关页面\n\n保留正文\n")
        self.write_project("无关页面/附件.txt", "保留附件\n")
        self.write_project("吃谷.md", "# 吃谷\n\n过期正文\n")
        self.write_project("吃谷/旧记录.md", "# 旧记录\n")
        (self.project / "空目录").mkdir()
        self.write_export()

    def write_project(self, relative: str, content: str) -> Path:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_export(self, entries: dict[str, str] | None = None) -> None:
        if entries is None:
            page = "吃谷 " + "a" * 32
            table = page + "/新记录 " + "b" * 32 + ".csv"
            entries = {
                page + ".md": f"# 吃谷\n\n[新记录]({quote(table, safe='/')})\n",
                table: "名称,数量\n知更鸟,002\n",
            }
        with ZipFile(self.archive, "w") as archive:
            for name, content in entries.items():
                archive.writestr(name, content.encode("utf-8"))

    def test_entrypoint_help_works_from_another_working_directory(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(ENTRYPOINT), "--help"],
            cwd=self.other_cwd,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("archive", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_injected_project_root_selects_root_zip_and_dry_run_changes_nothing(self) -> None:
        (self.other_cwd / "wrong.zip").write_bytes(b"Not the requested project.")
        before = snapshot(self.project)
        other_before = snapshot(self.other_cwd)
        output = io.StringIO()

        with contextlib.chdir(self.other_cwd), contextlib.redirect_stdout(output):
            result = cli.main(["--dry-run"], project_root=self.project)

        self.assertEqual(result, 0)
        self.assertIn(str(self.archive.resolve()), output.getvalue())
        self.assertEqual(snapshot(self.project), before)
        self.assertEqual(snapshot(self.other_cwd), other_before)

    def test_entrypoint_default_project_is_parent_of_src(self) -> None:
        # Copy only runtime code to the disposable project, then exercise the real
        # entrypoint without injecting a root or touching this repository's data.
        shutil.copy2(ENTRYPOINT, self.project / "src" / ENTRYPOINT.name)
        shutil.copytree(
            PROJECT_ROOT / "src" / "notion_export",
            self.project / "src" / "notion_export",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        before = snapshot(self.project)
        result = subprocess.run(
            [
                sys.executable, "-B", "-X", "utf8",
                str(self.project / "src" / ENTRYPOINT.name), "--dry-run",
            ],
            cwd=self.other_cwd,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.archive.resolve()), result.stdout)
        self.assertEqual(snapshot(self.project), before)

    def test_full_import_replaces_only_incoming_root_page(self) -> None:
        before = snapshot(self.project)
        with contextlib.redirect_stdout(io.StringIO()):
            result = cli.main([], project_root=self.project)

        self.assertEqual(result, 0)
        after = snapshot(self.project)
        unaffected_before = {
            name: value for name, value in before.items()
            if name not in {"吃谷", "吃谷.md"} and not name.startswith("吃谷/")
        }
        unaffected_after = {
            name: value for name, value in after.items()
            if name not in {"吃谷", "吃谷.md"} and not name.startswith("吃谷/")
        }
        self.assertEqual(unaffected_after, unaffected_before)
        self.assertNotIn("吃谷/旧记录.md", after)
        self.assertNotIn("过期正文", (self.project / "吃谷.md").read_text(encoding="utf-8"))
        self.assertIn(
            "| 知更鸟 | 002 |",
            (self.project / "吃谷" / "新记录.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            quote("吃谷/新记录.md", safe="/"),
            (self.project / "吃谷.md").read_text(encoding="utf-8"),
        )

    def test_src_directory_and_page_collision_abort_before_changing_project(self) -> None:
        for entries in (
            {"src/replaced.py": "# Export must not replace project code.\n"},
            {"src.md": "# src\n"},
        ):
            with self.subTest(export=list(entries)):
                self.write_export(entries)
                before = snapshot(self.project)
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(ImportFailure):
                        cli.main([], project_root=self.project)
                self.assertEqual(snapshot(self.project), before)

    def test_run_reports_import_failure_without_a_traceback(self) -> None:
        self.archive.unlink()
        before = snapshot(self.project)
        output = io.StringIO()
        error = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            result = cli.run([], project_root=self.project)

        self.assertEqual(result, 1)
        self.assertIn("导入失败：", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())
        self.assertEqual(snapshot(self.project), before)

    def test_install_failure_restores_old_page_and_removes_partial_install(self) -> None:
        workspace = self.base / "workspace"
        clean = workspace / "clean"
        clean.mkdir(parents=True)
        (clean / "吃谷.md").write_text("# 吃谷\n\n新正文\n", encoding="utf-8")
        (clean / "吃谷").mkdir()
        (clean / "吃谷" / "新记录.md").write_text("# 新记录\n", encoding="utf-8")
        before = snapshot(self.project)
        original_move = shutil.move
        attempted_installs = 0

        def fail_second_install(source: str, destination: str | Path) -> str:
            nonlocal attempted_installs
            if Path(source).parent == clean:
                attempted_installs += 1
                if attempted_installs == 2:
                    raise OSError("simulated installation failure")
            return original_move(source, destination)

        with patch.object(importer.shutil, "move", side_effect=fail_second_install):
            with self.assertRaisesRegex(OSError, "simulated installation failure"):
                importer.replace_project_contents(
                    self.project, clean, self.archive, workspace
                )

        self.assertEqual(attempted_installs, 2)
        self.assertEqual(snapshot(self.project), before)


if __name__ == "__main__":
    unittest.main()
