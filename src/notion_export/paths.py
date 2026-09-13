"""Notion 文件名清理、页面分组与导入路径规划。"""

from __future__ import annotations

import re
from pathlib import Path

from .errors import ImportFailure


NOTION_ID_RE = re.compile(
    r"^(?P<name>.+) (?P<id>[0-9a-f]{32})(?P<tail>_all)?(?P<suffix>\.[^.]*)?$",
    re.IGNORECASE,
)


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


def normalize_dotted_filename(clean_name: str, source: Path) -> str:
    """按一级标题还原被 Notion 替换成空格的点号。"""
    if source.suffix.lower() != ".md":
        return clean_name
    path = Path(clean_name)
    heading = first_heading(source)
    if not heading or "." not in heading:
        return clean_name
    # Notion 会把标题中的点号导出为空格，例如：
    # `Vue 3.5.35` -> `Vue 3 5 35`、`.value` -> ` value`。
    # 仅在除点号外完全一致时恢复，避免把任意一级标题强行用作文件名。
    if heading.replace(".", " ") != path.stem:
        return clean_name
    return heading + path.suffix


def hyphenate_spaces(name: str) -> str:
    """将路径名称中的连续空格统一替换为一个连字符。"""
    return re.sub(r" +", "-", name)


def plan_import_paths(raw_root: Path) -> dict[Path, Path]:
    """逐层分配名称；页面、数据库与配套目录作为一组消歧。"""
    paths = {Path(): Path()}

    def visit(directory: Path) -> None:
        entries = sorted(directory.iterdir(), key=lambda entry: (entry.name.casefold(), entry.name))
        groups: dict[tuple[str, str], list[tuple[Path, str]]] = {}
        for entry in entries:
            if entry.is_dir():
                continue
            match = NOTION_ID_RE.match(entry.name)
            if entry.suffix.lower() == ".md":
                key = ("page", entry.stem)
                suffix = entry.suffix
            elif entry.suffix.lower() == ".csv":
                if match:
                    key = ("page", match.group("name") + " " + match.group("id"))
                    suffix = (match.group("tail") or "") + ".md"
                else:
                    key = ("page", entry.stem)
                    suffix = ".md"
            else:
                key = ("file", entry.name)
                suffix = ""
            groups.setdefault(key, []).append((entry, suffix))

        for entry in entries:
            if not entry.is_dir():
                continue
            key = ("page", entry.name)
            if key not in groups and not NOTION_ID_RE.match(entry.name):
                # 部分导出为带 ID 的页面/CSV 配上不带 ID 的目录。
                # 仅在唯一匹配时关联，不能猜测多个同名页面的附件归属。
                candidates = [
                    candidate for candidate in groups
                    if candidate[0] == "page"
                    and strip_notion_id(candidate[1]) == entry.name
                    and not any(item.is_dir() for item, _ in groups[candidate])
                    and not (directory / candidate[1]).is_dir()
                ]
                if len(candidates) == 1:
                    key = candidates[0]
            groups.setdefault(key, []).append((entry, ""))

        bases: dict[tuple[str, str], str] = {}
        for key, members in groups.items():
            base = strip_notion_id(key[1])
            for entry, suffix in members:
                if entry.is_file() and entry.suffix.lower() == ".md":
                    base = Path(normalize_dotted_filename(base + suffix, entry)).stem
                    break
            bases[key] = hyphenate_spaces(base)

        # 同一导出页可能同时包含 Markdown 与 CSV；转换后两者仍须各有文件。
        # 先保留原 Markdown 名，再给组内重名的表格分配后缀，配套目录仍随组移动。
        natural_names = {
            name.casefold()
            for key, members in groups.items()
            for name in [bases[key], *(bases[key] + suffix for _, suffix in members)]
        }
        for key, members in groups.items():
            occupied: set[str] = set()
            allocated: list[tuple[Path, str]] = []
            for entry, suffix in sorted(
                members,
                key=lambda item: (
                    item[0].suffix.lower() == ".csv",
                    item[0].name.casefold(),
                    item[0].name,
                ),
            ):
                candidate_suffix = suffix
                number = 1
                while candidate_suffix.casefold() in occupied or (
                    number > 1
                    and (bases[key] + candidate_suffix).casefold() in natural_names
                ):
                    number += 1
                    stem, separator, extension = suffix.rpartition(".")
                    candidate_suffix = f"{stem}-{number}{separator}{extension}"
                occupied.add(candidate_suffix.casefold())
                allocated.append((entry, candidate_suffix))
            groups[key] = allocated

        # 预留所有自然名称，包括配套目录名，避免自动生成的 -2 抢占原有标题。
        reserved = {
            name.casefold()
            for key, members in groups.items()
            for name in [bases[key], *(bases[key] + suffix for _, suffix in members)]
        }
        used: set[str] = set()
        parent = paths[directory.relative_to(raw_root)]
        for key in sorted(groups, key=lambda item: (item[1].casefold(), item[1], item[0])):
            members = groups[key]
            base = bases[key]
            candidate = base
            number = 1
            while True:
                names = {candidate.casefold()}
                names.update((candidate + suffix).casefold() for _, suffix in members)
                if not names & used and (number == 1 or not names & reserved):
                    break
                number += 1
                if key[0] == "file":
                    filename = Path(base)
                    candidate = f"{filename.stem}-{number}{filename.suffix}"
                else:
                    candidate = f"{base}-{number}"
            used.update(names)
            for entry, suffix in members:
                paths[entry.relative_to(raw_root)] = parent / (candidate + suffix)

        for entry in entries:
            if entry.is_dir():
                visit(entry)

    visit(raw_root)
    return paths
