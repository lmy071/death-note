"""Markdown 图片语法与本地链接处理。"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from .paths import hyphenate_spaces, strip_notion_id


MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]*>[^)\n]*|(?:[^()\n]|\([^()\n]*\))*)\)")


REFERENCE_LINK_RE = re.compile(
    r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(<[^>\n]*>|[^\s]+)", re.MULTILINE
)


FENCE_OPEN_RE = re.compile(r" {0,3}(`{3,}|~{3,})([^\r\n]*)$")


INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif", ".ico", ".apng"}


IMAGE_PROPERTY_RE = re.compile(r"^[ \t]*(?:图片|图像|images?)[ \t]*[:：][ \t]*", re.IGNORECASE)


def code_spans(markdown: str) -> list[tuple[int, int]]:
    """统一识别围栏、缩进代码及等长反引号代码，供转换和校验共用。"""
    blocks: list[tuple[int, int]] = []
    fence_start: int | None = None
    fence_end: re.Pattern[str] | None = None
    indent_start: int | None = None
    previous_blank = True
    offset = 0
    for line in markdown.splitlines(keepends=True):
        start = offset
        offset += len(line)
        content = line.rstrip("\r\n")
        blank = not content.strip()
        indented = content.startswith(("    ", "\t"))
        if fence_start is not None:
            if fence_end is not None and fence_end.fullmatch(content):
                blocks.append((fence_start, offset))
                fence_start = None
                previous_blank = True
            continue
        if indent_start is not None:
            if blank or indented:
                continue
            blocks.append((indent_start, start))
            indent_start = None
            previous_blank = True
        opening = FENCE_OPEN_RE.fullmatch(content)
        if opening and not (opening[1][0] == "`" and "`" in opening[2]):
            fence_start = start
            marker = re.escape(opening[1][0])
            fence_end = re.compile(r" {0,3}" + marker + "{" + str(len(opening[1])) + r",}[ \t]*")
        elif indented and previous_blank and not blank:
            indent_start = start
        else:
            previous_blank = blank

    if fence_start is not None:
        blocks.append((fence_start, len(markdown)))
    if indent_start is not None:
        blocks.append((indent_start, len(markdown)))

    # 只在代码块之间寻找行内代码，避免跨围栏匹配吞掉正常正文。
    spans = list(blocks)
    offset = 0
    for start, end in [*blocks, (len(markdown), len(markdown))]:
        text = markdown[offset:start]
        position = 0
        while match := INLINE_CODE_RE.search(text, position):
            prefix = text[:match.start()]
            escaped = (len(prefix) - len(prefix.rstrip("\\"))) % 2
            if escaped:
                position = match.start() + len(match[1])
            else:
                spans.append((offset + match.start(), offset + match.end()))
                position = match.end()
        offset = end
    return sorted(spans)


def split_link_target(raw: str) -> tuple[str, str, bool]:
    """分离链接目标、可选标题及尖括号，供改写和校验共用。"""
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        end = raw.index(">")
        return raw[1:end], raw[end + 1 :], True
    title = re.match(r'''^(.*?)(\s+(?:"[^"\n]*"|'[^'\n]*'|\([^()\n]*\)))$''', raw)
    if title:
        return title.group(1), title.group(2), False
    return raw, "", False


def is_image_target(target: str) -> bool:
    """按目标路径扩展名识别图片，忽略查询参数及锚点，不请求远程资源。"""
    if not target or target.startswith(("#", "?")):
        return False
    try:
        parts = urlsplit(target)
    except ValueError:
        return False
    if parts.scheme.lower() not in {"", "http", "https"}:
        return False
    if not parts.scheme and ":" in parts.path:
        return False
    return PurePosixPath(unquote(parts.path)).suffix.lower() in IMAGE_SUFFIXES


def embed_image_links(markdown: str) -> str:
    """将图片链接、图片属性裸地址及独占一行的图片地址转为图片语法。"""
    protected = code_spans(markdown)

    def in_code(position: int) -> bool:
        return any(start <= position < end for start, end in protected)

    edits: list[tuple[int, int, str]] = []
    for match in MARKDOWN_LINK_RE.finditer(markdown):
        if in_code(match.start()) or match.group(0).startswith(("!", "[![")):
            continue
        # 保留转义后的链接示例，不能把字面文本变成图片。
        preceding = markdown[: match.start()]
        if (len(preceding) - len(preceding.rstrip("\\"))) % 2:
            continue
        target, _, _ = split_link_target(match.group(1))
        if is_image_target(target):
            edits.append((match.start(), match.start(), "!"))

    offset = 0
    for line in markdown.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        property_match = IMAGE_PROPERTY_RE.match(content)
        start = property_match.end() if property_match else len(content) - len(content.lstrip())
        raw = content[start:].rstrip()
        target, _, bracketed = split_link_target(raw)
        if (
            not in_code(offset + start)
            and (bracketed or not re.search(r"[\s\[\]]", target))
            and is_image_target(target)
        ):
            edits.append((offset + start, offset + start + len(raw), f"![图片]({raw})"))
        offset += len(line)

    for start, end, replacement in sorted(edits, reverse=True):
        markdown = markdown[:start] + replacement + markdown[end:]
    return markdown


def rewrite_local_links(
    markdown: str, source: Path, paths: dict[Path, Path]
) -> tuple[str, int]:
    """按完整源路径改写目标，保留正文、代码、外链和页面身份。"""
    protected = code_spans(markdown)
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        if any(start <= match.start() < end for start, end in protected):
            return match.group(0)
        target, title, bracketed = split_link_target(match.group(1))
        if not target or target.startswith(("#", "?", "//")) or re.match(
            r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target
        ):
            return match.group(0)
        path_text, *tail = re.split(r"(?=[?#])", target, maxsplit=1)
        decoded = unquote(path_text).replace("\\", "/")
        absolute = decoded.startswith("/")
        original_path = posixpath.normpath(
            decoded.lstrip("/") if absolute else posixpath.join(source.parent.as_posix(), decoded)
        )
        destination = paths.get(Path(original_path))
        if destination is None and source.suffix.lower() == ".csv":
            # Notion CSV 的附件也可能使用从导出根目录起算的路径。
            root_path = Path(posixpath.normpath(decoded.lstrip("/")))
            destination = paths.get(root_path)
            if destination is None:
                # 兼容此前只复制 CSV、已清理文件名的项目；只接受唯一匹配。
                def normalized(path: Path) -> Path:
                    return Path(*(hyphenate_spaces(strip_notion_id(part)) for part in path.parts))

                candidates = {normalized(Path(original_path)), normalized(root_path)}
                matches = {
                    new for old, new in paths.items()
                    if normalized(old) in candidates
                }
                if len(matches) == 1:
                    destination = matches.pop()
        if destination is None:
            return match.group(0)
        new_path = (
            "/" + destination.as_posix() if absolute
            else posixpath.relpath(destination.as_posix(), paths[source].parent.as_posix())
        )
        if new_path == decoded:
            return match.group(0)
        new_target = quote(new_path, safe="/") + "".join(tail)
        if bracketed:
            new_target = f"<{new_target}>"
        changed += 1
        start, end = match.span(1)
        return (
            markdown[match.start() : start]
            + new_target + title
            + markdown[end : match.end()]
        )

    # 两种语法都在原文中定位后逆序改写，避免前一处长度变化影响代码区间。
    matches = list(MARKDOWN_LINK_RE.finditer(markdown))
    matches.extend(REFERENCE_LINK_RE.finditer(markdown))
    updated = markdown
    for match in sorted(matches, key=lambda item: item.start(), reverse=True):
        updated = updated[: match.start()] + replace(match) + updated[match.end() :]
    return updated, changed
