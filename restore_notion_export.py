#!/usr/bin/env python3
"""将 Notion 导出 ZIP 全量还原为当前项目的 Markdown 目录。

用法：
    python3 restore_notion_export.py
    python3 restore_notion_export.py /path/to/notion-export.zip
    python3 restore_notion_export.py /path/to/notion-export.zip --dry-run

不传 ZIP 路径时，脚本会在项目根目录查找唯一的 .zip 文件。
导入会保留 .git、其他点号开头的项目配置、本脚本和根目录 ZIP。
全量替换仅作用于本次 ZIP 包含的根页面：例如导入 `前端.md` 与 `前端/`
时，只删除并重建这两个路径，其他根页面保持不变。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote
from zipfile import BadZipFile, ZipFile


NOTION_ID_RE = re.compile(
    r"^(?P<name>.+) (?P<id>[0-9a-f]{32})(?P<tail>_all)?(?P<suffix>\.[^.]*)?$",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
MAX_NESTED_ZIP_DEPTH = 8
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


class ImportFailure(RuntimeError):
    """导入数据不安全或不符合预期时中止操作。"""


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def select_archive(project_root: Path, requested: Path | None) -> Path:
    if requested is not None:
        archive = requested.expanduser().resolve()
        if not archive.is_file():
            raise ImportFailure(f"ZIP 不存在：{archive}")
        if archive.suffix.lower() != ".zip":
            raise ImportFailure(f"输入文件不是 ZIP：{archive}")
        return archive

    archives = sorted(project_root.glob("*.zip"))
    if not archives:
        raise ImportFailure("项目根目录中没有 .zip 文件。")
    if len(archives) > 1:
        names = "\n  ".join(path.name for path in archives)
        raise ImportFailure(
            "项目根目录中有多个 ZIP，请显式指定要导入的文件：\n  " + names
        )
    return archives[0].resolve()


def safe_member_path(name: str) -> Path:
    normalized = name.replace("\\", "/")
    if "\x00" in normalized:
        raise ImportFailure("ZIP 成员名包含空字节。")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ImportFailure(f"ZIP 包含不安全路径：{name}")
    return Path(*pure.parts)


def extract_zip_safely(archive: Path, destination: Path) -> None:
    try:
        with ZipFile(archive) as zip_file:
            infos = zip_file.infolist()
            total_size = sum(info.file_size for info in infos)
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise ImportFailure(
                    f"ZIP 解压后过大：{total_size} bytes，"
                    f"上限为 {MAX_UNCOMPRESSED_BYTES} bytes。"
                )

            for info in infos:
                relative = safe_member_path(info.filename)
                target = destination / relative
                unix_mode = info.external_attr >> 16
                if stat.S_ISLNK(unix_mode):
                    raise ImportFailure(f"ZIP 不允许包含符号链接：{info.filename}")

                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                if target.exists():
                    raise ImportFailure(f"多个压缩包产生了同名文件：{relative}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zip_file.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o644)
    except BadZipFile as exc:
        raise ImportFailure(f"无效 ZIP：{archive}") from exc


def unpack_nested_export(archive: Path, workspace: Path) -> Path:
    """递归展开“外层 ZIP 仅包含 Part-N.zip”的 Notion 导出格式。"""
    current = workspace / "layer-0"
    current.mkdir()
    extract_zip_safely(archive, current)

    for depth in range(1, MAX_NESTED_ZIP_DEPTH + 1):
        macos_metadata = current / "__MACOSX"
        if macos_metadata.exists():
            shutil.rmtree(macos_metadata)

        entries = list(current.iterdir())
        wrapper_zips = [
            entry for entry in entries if entry.is_file() and entry.suffix.lower() == ".zip"
        ]
        if not entries or len(wrapper_zips) != len(entries):
            return current

        next_layer = workspace / f"layer-{depth}"
        next_layer.mkdir()
        for nested_archive in sorted(wrapper_zips):
            extract_zip_safely(nested_archive, next_layer)
        current = next_layer

    raise ImportFailure(f"嵌套 ZIP 超过 {MAX_NESTED_ZIP_DEPTH} 层。")


def strip_notion_id(name: str) -> str:
    match = NOTION_ID_RE.match(name)
    if not match:
        return name
    return (
        match.group("name")
        + (match.group("tail") or "")
        + (match.group("suffix") or "")
    )


def first_heading(markdown: Path) -> str | None:
    try:
        for line in markdown.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except UnicodeDecodeError as exc:
        raise ImportFailure(f"Markdown 不是 UTF-8 编码：{markdown}") from exc
    return None


def normalize_value_filename(clean_name: str, source: Path) -> str:
    """修复 Notion 把标题中的 `.value` 导出为 ` value` 的情况。"""
    if source.suffix.lower() != ".md":
        return clean_name
    path = Path(clean_name)
    heading = first_heading(source)
    if not heading or not path.stem.endswith(" value") or not heading.endswith(".value"):
        return clean_name
    if path.stem[: -len(" value")] != heading[: -len(".value")]:
        return clean_name
    return heading + path.suffix


def create_import_tree(raw_root: Path, clean_root: Path) -> tuple[int, int, int]:
    files = sorted(path for path in raw_root.rglob("*") if path.is_file())
    if not files:
        raise ImportFailure("ZIP 中没有可导入文件。")

    plans: list[tuple[Path, Path]] = []
    replacements: set[tuple[str, str]] = set()
    destinations: dict[str, Path] = {}

    for source in files:
        relative = source.relative_to(raw_root)
        new_parts: list[str] = []
        for index, old_part in enumerate(relative.parts):
            new_part = strip_notion_id(old_part)
            if index == len(relative.parts) - 1:
                new_part = normalize_value_filename(new_part, source)
            if old_part != new_part:
                replacements.add((old_part, new_part))
            new_parts.append(new_part)

        destination_relative = Path(*new_parts)
        collision_key = os.path.normcase(str(destination_relative)).casefold()
        previous = destinations.get(collision_key)
        if previous is not None:
            raise ImportFailure(
                f"移除 Notion ID 后出现同名冲突：{previous} 和 {relative}"
            )
        destinations[collision_key] = relative
        plans.append((source, clean_root / destination_relative))

    encoded_replacements: list[tuple[str, str]] = []
    for old, new in replacements:
        encoded_replacements.append((quote(old, safe=""), quote(new, safe="")))
        encoded_replacements.append((old, new))
    encoded_replacements.sort(key=lambda pair: len(pair[0]), reverse=True)

    changed_markdown = 0
    replaced_links = 0
    for source, destination in plans:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".md":
            try:
                original = source.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ImportFailure(f"Markdown 不是 UTF-8 编码：{source}") from exc
            updated = original
            for old, new in encoded_replacements:
                count = updated.count(old)
                if count:
                    updated = updated.replace(old, new)
                    replaced_links += count
            if updated != original:
                changed_markdown += 1
            destination.write_text(updated, encoding="utf-8")
        else:
            shutil.copyfile(source, destination)
        destination.chmod(0o644)

    return len(files), changed_markdown, replaced_links


def validate_links(root: Path) -> int:
    broken: list[tuple[Path, str]] = []
    checked = 0

    for markdown in root.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        text = FENCED_CODE_RE.sub("", text)
        text = INLINE_CODE_RE.sub("", text)
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw_target = match.group(1).strip()
            if raw_target.startswith("<") and raw_target.endswith(">"):
                raw_target = raw_target[1:-1]
            if not raw_target or raw_target.startswith("#"):
                continue
            if raw_target.startswith("//") or re.match(
                r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw_target
            ):
                continue

            target_text = unquote(raw_target.split("#", 1)[0].split("?", 1)[0])
            if not target_text:
                continue
            checked += 1
            if target_text.startswith("/"):
                resolved = (root / target_text.lstrip("/")).resolve()
            else:
                resolved = (markdown.parent / target_text).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                broken.append((markdown.relative_to(root), raw_target))

    if broken:
        details = "\n".join(f"  {path} -> {target}" for path, target in broken[:20])
        suffix = "" if len(broken) <= 20 else f"\n  ... 共 {len(broken)} 个断链"
        raise ImportFailure("导入内容存在断链：\n" + details + suffix)
    return checked


def validate_no_notion_ids(root: Path) -> None:
    leftovers = [
        path.relative_to(root)
        for path in root.rglob("*")
        if NOTION_ID_RE.match(path.name)
    ]
    if leftovers:
        details = "\n".join(f"  {path}" for path in leftovers[:20])
        raise ImportFailure("仍有路径包含 Notion ID：\n" + details)


def replace_project_contents(
    project_root: Path, clean_root: Path, archive: Path, workspace: Path
) -> int:
    script = Path(__file__).resolve()
    protected_names = {script.name}
    protected_names.update(path.name for path in project_root.glob("*.zip"))
    if archive.parent == project_root:
        protected_names.add(archive.name)

    incoming = list(clean_root.iterdir())
    for entry in incoming:
        if entry.name.startswith(".") or entry.name in protected_names:
            raise ImportFailure(f"导出内容与受保护的项目路径冲突：{entry.name}")

    # 以导入包的顶层名称确定替换范围。根页面通常由
    # `<页面>.md` 和存放子页面/附件的 `<页面>/` 共同组成，因此任意一个
    # 出现在 ZIP 中时，都将这对路径视为同一个全量覆盖单元。
    replacement_names: set[str] = set()
    for entry in incoming:
        replacement_names.add(entry.name)
        if entry.is_dir():
            replacement_names.add(entry.name + ".md")
        elif entry.is_file() and entry.suffix.lower() == ".md":
            replacement_names.add(entry.stem)

    replacement_names.difference_update(protected_names)
    old_entries = [
        project_root / name
        for name in sorted(replacement_names)
        if (project_root / name).exists()
    ]
    backup = workspace / "backup"
    backup.mkdir()
    installed: list[Path] = []

    try:
        # 先将本次根页面的旧内容全部移出，再安装新内容。
        for entry in old_entries:
            shutil.move(str(entry), backup / entry.name)
        for entry in incoming:
            target = project_root / entry.name
            shutil.move(str(entry), target)
            installed.append(target)
    except Exception:
        for target in reversed(installed):
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        for old_entry in backup.iterdir():
            shutil.move(str(old_entry), project_root / old_entry.name)
        raise

    return len(old_entries)


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
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


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ImportFailure as exc:
        print(f"导入失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
