"""导入结果的本地链接与文件名校验。"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from .errors import ImportFailure
from .markdown import (
    MARKDOWN_LINK_RE,
    REFERENCE_LINK_RE,
    code_spans,
    split_link_target,
)
from .paths import NOTION_ID_RE


def validate_links(root: Path) -> int:
    broken: list[tuple[Path, str]] = []
    checked = 0

    for markdown in root.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for start, end in reversed(code_spans(text)):
            masked = "".join("\n" if char == "\n" else " " for char in text[start:end])
            text = text[:start] + masked + text[end:]
        matches = list(MARKDOWN_LINK_RE.finditer(text))
        matches.extend(REFERENCE_LINK_RE.finditer(text))
        for match in matches:
            raw_target, _, _ = split_link_target(match.group(1))
            if not raw_target or raw_target.startswith(("#", "?")):
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
