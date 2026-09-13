"""构建转换后的导入目录，并以根页面为单位替换项目内容。"""

from __future__ import annotations

import shutil
from pathlib import Path

from .csv_tables import csv_to_markdown
from .errors import ImportFailure
from .markdown import embed_image_links, rewrite_local_links
from .paths import plan_import_paths


def create_import_tree(raw_root: Path, clean_root: Path) -> tuple[int, int, int]:
    files = sorted(path for path in raw_root.rglob("*") if path.is_file())
    if not files:
        raise ImportFailure("ZIP 中没有可导入文件。")

    paths = plan_import_paths(raw_root)
    for relative, destination in paths.items():
        if (raw_root / relative).is_dir():
            (clean_root / destination).mkdir(parents=True, exist_ok=True)

    changed_markdown = 0
    replaced_links = 0
    for source in files:
        relative = source.relative_to(raw_root)
        destination = clean_root / paths[relative]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".csv":
            updated = csv_to_markdown(source, title=paths[relative].stem)
            updated, count = rewrite_local_links(updated, relative, paths)
            replaced_links += count
            changed_markdown += 1
            destination.write_text(updated, encoding="utf-8")
        elif source.suffix.lower() == ".md":
            try:
                original = source.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ImportFailure(f"Markdown 不是 UTF-8 编码：{source}") from exc
            updated = embed_image_links(original)
            updated, count = rewrite_local_links(updated, relative, paths)
            replaced_links += count
            if updated != original:
                changed_markdown += 1
            destination.write_text(updated, encoding="utf-8")
        else:
            shutil.copyfile(source, destination)
        destination.chmod(0o644)

    return len(files), changed_markdown, replaced_links


def replace_project_contents(
    project_root: Path, clean_root: Path, archive: Path, workspace: Path
) -> int:
    protected_names = {"src", "tests", "restore_notion_export.py"}
    protected_names.update(path.name.casefold() for path in project_root.glob("*.zip"))
    if archive.parent == project_root:
        protected_names.add(archive.name.casefold())

    def is_protected(name: str) -> bool:
        normalized = name.casefold()
        return (
            name.startswith(".")
            or normalized in protected_names
            or (normalized.startswith("test_") and normalized.endswith(".py"))
        )

    incoming = list(clean_root.iterdir())

    # 根页面通常由 `<页面>.md` 和 `<页面>/` 组成，任意一个出现时，
    # 都将这对路径作为同一个全量覆盖单元。
    replacement_names: set[str] = set()
    for entry in incoming:
        replacement_names.add(entry.name)
        if entry.is_dir():
            replacement_names.add(entry.name + ".md")
        elif entry.is_file() and entry.suffix.lower() == ".md":
            replacement_names.add(entry.stem)

    # 校验完整替换范围后才能移动旧文件，避免 src.md 的配套目录
    # 或 test_*.py.md 的配套路径间接触及源码、测试和项目配置。
    for name in sorted(replacement_names):
        if is_protected(name):
            raise ImportFailure(f"导出内容与受保护的项目路径冲突：{name}")

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
