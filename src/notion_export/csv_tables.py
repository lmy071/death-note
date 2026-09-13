"""CSV 数据库到 Markdown 表格的转换。"""

from __future__ import annotations

import csv
import html
import re
from pathlib import Path
from urllib.parse import quote

from .errors import ImportFailure
from .markdown import MARKDOWN_LINK_RE, is_image_target, split_link_target
from .paths import strip_notion_id


def csv_cell_to_markdown(value: str) -> str:
    """保留单元格文本与显式链接，避免管道、换行及 HTML 破坏表格。"""
    value = value.replace("\r\n", "\n").replace("\r", "\n")

    def escape_text(text: str) -> str:
        text = html.escape(text, quote=False)
        # 反引号是 CSV 文本；使用实体避免后续链接扫描把跨单元格文本当成代码。
        text = text.replace("`", "&#96;")
        text = re.sub(r"([\\`*_\[\]|])", r"\\\1", text)
        text = re.sub(
            r"^[ \t]+|[ \t]+$",
            lambda match: "".join(f"&#{ord(char)};" for char in match.group(0)),
            text,
        )
        return text.replace("\n", "<br>")

    def render_line(line: str) -> str:
        # CSV 的图片属性通常是裸 URL；不下载或改动远程地址。
        if not re.search(r"[<>\[\]]", line) and is_image_target(line):
            target = quote(line, safe="/:#?&=%+@~,-._!")
            return f"![图片]({target})"
        pieces: list[str] = []
        offset = 0
        for match in MARKDOWN_LINK_RE.finditer(line):
            pieces.append(escape_text(line[offset:match.start()]))
            raw = match.group(0)
            label_start = 2 if raw.startswith("!") else 1
            label = raw[label_start:raw.index("](")]
            target, title, bracketed = split_link_target(match.group(1))
            prefix = "!" if raw.startswith("!") or is_image_target(target) else ""
            target = target.replace("|", "%7C")
            if bracketed:
                target = f"<{target}>"
            pieces.append(f"{prefix}[{escape_text(label)}]({target}{title.replace('|', '&#124;')})")
            offset = match.end()
        pieces.append(escape_text(line[offset:]))
        return "".join(pieces)

    return "<br>".join(render_line(line) for line in value.split("\n"))


def csv_to_markdown(source: Path, title: str | None = None) -> str:
    """将 UTF-8 CSV 转成表格；不推断数值类型、不丢弃空列或不规则行。"""
    try:
        with source.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream, strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ImportFailure(f"CSV 不是有效的 UTF-8 表格：{source}：{exc}") from exc

    heading = title if title is not None else strip_notion_id(source.name)[:-len(source.suffix)]
    result = [f"# {csv_cell_to_markdown(heading)}", ""]
    width = max((len(row) for row in rows), default=0)
    if not width:
        return "\n".join(result) + "\n"

    def table_row(row: list[str]) -> str:
        cells = row + [""] * (width - len(row))
        return "| " + " | ".join(csv_cell_to_markdown(cell) for cell in cells) + " |"

    result.append(table_row(rows[0]))
    result.append("| " + " | ".join(["---"] * width) + " |")
    result.extend(table_row(row) for row in rows[1:])
    return "\n".join(result) + "\n"
