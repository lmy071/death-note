"""Notion 导入命令行参数与执行流程。"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from .archive import select_archive, unpack_nested_export
from .errors import ImportFailure
from .importer import create_import_tree, replace_project_contents
from .validation import validate_links, validate_no_notion_ids


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="全量导入 Notion Markdown ZIP，并修复文件名与内部链接。"
    )
    parser.add_argument(
        "archive",
        nargs="?",
        type=Path,
        help="Notion 导出 ZIP；省略时使用项目根目录中唯一的 ZIP。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只解压、转换和校验，不删除或替换项目内容。",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None, project_root: Path | None = None
) -> int:
    args = parse_args(argv)
    project_root = (
        Path(__file__).resolve().parents[2]
        if project_root is None
        else project_root.resolve()
    )
    archive = select_archive(project_root, args.archive)

    with tempfile.TemporaryDirectory(prefix=".notion-import-", dir=project_root) as temp:
        workspace = Path(temp)
        raw_root = unpack_nested_export(archive, workspace)
        clean_root = workspace / "clean"
        clean_root.mkdir()

        file_count, changed_markdown, replaced_links = create_import_tree(
            raw_root, clean_root
        )
        validate_no_notion_ids(clean_root)
        checked_links = validate_links(clean_root)

        print(f"ZIP：{archive}")
        print(f"解压文件：{file_count}")
        print(f"更新 Markdown：{changed_markdown}")
        print(f"替换链接目标：{replaced_links}")
        print(f"校验本地链接：{checked_links}，断链：0")

        if args.dry_run:
            print("干跑完成：未修改项目内容。")
            return 0

        removed_count = replace_project_contents(
            project_root, clean_root, archive, workspace
        )
        print(f"已移除旧的顶层内容：{removed_count} 项")
        print("全量导入完成。")
    return 0


def run(
    argv: Sequence[str] | None = None, project_root: Path | None = None
) -> int:
    """将可预期的导入错误转换为命令行错误消息及退出码。"""
    try:
        return main(argv, project_root)
    except ImportFailure as exc:
        print(f"导入失败：{exc}", file=sys.stderr)
        return 1
