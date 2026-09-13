"""CSV conversion and import regressions; run with python -m unittest -v."""

from __future__ import annotations

import csv
import html
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from src.notion_export.csv_tables import csv_to_markdown
from src.notion_export.importer import create_import_tree
from src.notion_export.markdown import (
    MARKDOWN_LINK_RE,
    rewrite_local_links,
    split_link_target,
)
from src.notion_export.paths import plan_import_paths
from src.notion_export.validation import validate_links, validate_no_notion_ids


def write_csv(path: Path, rows: list[list[str]], *, bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as output:
        csv.writer(output).writerows(rows)


def table_cells(markdown: str) -> list[list[str]]:
    """Read table cells without treating escaped pipes as column boundaries."""
    rows = []
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        cells = []
        start = 1
        for index in range(1, len(line)):
            if line[index] != "|":
                continue
            backslashes = 0
            previous = index - 1
            while previous >= 0 and line[previous] == "\\":
                backslashes += 1
                previous -= 1
            if backslashes % 2:
                continue
            cells.append(line[start:index].strip())
            start = index + 1
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def plain_cell(cell: str) -> str:
    """Decode either valid Markdown escapes or HTML entities used by cells."""
    cell = re.sub(r"<br\s*/?>", "\n", cell, flags=re.IGNORECASE)
    cell = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])", r"\1", cell)
    return html.unescape(cell)


class CsvToMarkdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="csv-markdown-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def convert(self, rows: list[list[str]], *, bom: bool = False) -> str:
        source = self.root / "记录.csv"
        write_csv(source, rows, bom=bom)
        return csv_to_markdown(source, title="记录")

    def test_text_order_empty_values_bom_and_csv_quoting(self) -> None:
        original = [
            ["名称", "编号", "价格", "备注", "空列"],
            ['知更鸟, "限定"', "00017", "12.50", "第一行\r\n第二行", ""],
            ["第二条", "0", "-3", "", "末列有值"],
            ["", "", "", "", ""],
        ]
        rendered = self.convert(original, bom=True)
        restored = [[plain_cell(cell) for cell in row] for row in table_cells(rendered)]
        expected = [[value.replace("\r\n", "\n") for value in row] for row in original]
        self.assertEqual(restored, expected)
        self.assertNotIn("\ufeff", rendered)
        self.assertIn("<br", rendered.lower())

    def test_markdown_html_pipe_and_backslash_are_literal_text(self) -> None:
        original = [
            ["类别|名称", "备注"],
            ["a|b", r"C:\cards\new|last\\"],
            ["*加粗* _下划线_ `代码`", "<em>原文</em> &copy; &"],
            ["[方括号] # 标记", r"\*字面星号\*"],
        ]
        rendered = self.convert(original)
        self.assertEqual(
            [[plain_cell(cell) for cell in row] for row in table_cells(rendered)],
            original,
        )
        self.assertNotIn("<em>", rendered)
        self.assertNotIn("</em>", rendered)
        self.assertNotIn("`代码`", rendered)
        self.assertNotIn("*加粗*", rendered)

    def test_boundary_whitespace_tabs_and_whitespace_only_cells_survive(self) -> None:
        original = [
            [" 名称 ", "\t备注\t", "空白", "空值"],
            ["谢怜-太子悦神Ver. ", " \t详情\t ", "   ", ""],
            [" 前导空格", "\t\t", " \t ", ""],
            ["多行", " 首行 \r\n\t次行\t", "中间 空格", ""],
        ]
        rendered = self.convert(original)
        restored = [[plain_cell(cell) for cell in row] for row in table_cells(rendered)]
        expected = [[value.replace("\r\n", "\n") for value in row] for row in original]
        self.assertEqual(restored, expected)

    def test_embedded_image_and_bare_image_url_remain_images(self) -> None:
        bare = "https://example.test/cards/bird.PNG?size=100#preview"
        embedded = "![知更鸟](https://example.test/bird.webp)"
        rendered = self.convert([["图片", "已有图片"], [bare, embedded]])
        images = [
            match for match in MARKDOWN_LINK_RE.finditer(rendered)
            if match.group(0).startswith("![")
        ]
        self.assertEqual(len(images), 2)
        targets = {split_link_target(match.group(1))[0] for match in images}
        self.assertEqual(targets, {bare, "https://example.test/bird.webp"})
        self.assertIn(embedded, rendered)

    def test_local_markdown_link_is_available_for_rewriting(self) -> None:
        link = '[条目](<条目 old.md> "详细信息")'
        rendered = self.convert([["名称", "链接"], ["小卡", link]])
        source = Path("记录.csv")
        paths = {
            source: Path("记录.md"),
            Path("条目 old.md"): Path("条目-new.md"),
        }
        rewritten, changed = rewrite_local_links(rendered, source, paths)
        self.assertEqual(changed, 1)
        self.assertIn(f'[条目](<{quote("条目-new.md")}> "详细信息")', rewritten)

    def test_ragged_rows_keep_every_value_and_pad_to_widest_row(self) -> None:
        rendered = self.convert([["名称", "备注"], ["首行"], ["次行", "", "额外数据", "尾列"]])
        self.assertEqual(
            [[plain_cell(cell) for cell in row] for row in table_cells(rendered)],
            [["名称", "备注", "", ""], ["首行", "", "", ""], ["次行", "", "额外数据", "尾列"]],
        )

    def test_empty_csv_has_only_heading(self) -> None:
        source = self.root / "记录.csv"
        source.write_bytes(b"")
        self.assertEqual(csv_to_markdown(source).strip(), "# 记录")

    def test_header_only_csv_still_has_a_table(self) -> None:
        rendered = self.convert([["名称", "数量"]])
        self.assertEqual(table_cells(rendered), [["名称", "数量"]])
        self.assertRegex(rendered, r"\|\s*-{3,}\s*\|\s*-{3,}\s*\|")


class CsvImportTreeTests(unittest.TestCase):
    ID_A = "a" * 32
    ID_B = "b" * 32

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="csv-import-tree-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.clean = self.root / "clean"
        self.raw.mkdir()
        self.clean.mkdir()

    def text_file(self, relative: str | Path, content: str) -> Path:
        path = self.raw / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path.relative_to(self.raw)

    def csv_file(self, relative: str | Path, rows: list[list[str]]) -> Path:
        path = self.raw / relative
        write_csv(path, rows)
        return path.relative_to(self.raw)

    def run_import(self) -> dict[Path, Path]:
        paths = plan_import_paths(self.raw)
        create_import_tree(self.raw, self.clean)
        destinations = [destination.as_posix().casefold() for source, destination in paths.items() if source != Path()]
        self.assertEqual(len(destinations), len(set(destinations)), "Import destinations must be unique")
        self.assertFalse(list(self.clean.rglob("*.csv")))
        self.assertFalse(list(self.clean.rglob("*.CSV")))
        validate_no_notion_ids(self.clean)
        validate_links(self.clean)
        return paths

    def test_csv_without_id_converts_and_inbound_link_changes_extension(self) -> None:
        source = self.csv_file("吃谷/王者谷物_all.csv", [["名称", "数量"], ["小卡", "002"]])
        index = self.text_file("吃谷.md", f"# 吃谷\n\n[表格]({quote(source.as_posix(), safe='/')}#记录)\n")
        paths = self.run_import()
        self.assertEqual(paths[source], Path("吃谷/王者谷物_all.md"))
        content = (self.clean / paths[source]).read_text(encoding="utf-8")
        self.assertEqual(table_cells(content)[1], ["小卡", "002"])
        self.assertIn(
            f"]({quote(paths[source].as_posix(), safe='/')}#记录)",
            (self.clean / paths[index]).read_text(encoding="utf-8"),
        )

    def test_existing_markdown_and_same_name_csv_both_survive(self) -> None:
        page = self.text_file("目录.md", "# 目录\n\n原有页面内容\n")
        table = self.csv_file("目录.csv", [["名称"], ["CSV 独有内容"]])
        paths = self.run_import()
        self.assertNotEqual(paths[page], paths[table])
        self.assertEqual(paths[table].suffix, ".md")
        self.assertIn("原有页面内容", (self.clean / paths[page]).read_text(encoding="utf-8"))
        self.assertIn("CSV 独有内容", (self.clean / paths[table]).read_text(encoding="utf-8"))

    def test_same_notion_id_markdown_csv_and_all_csv_do_not_overwrite(self) -> None:
        stem = f"数据库 {self.ID_A}"
        page = self.text_file(f"{stem}.md", "# 数据库\n\n页面正文\n")
        table = self.csv_file(f"{stem}.csv", [["名称"], ["当前视图"]])
        all_table = self.csv_file(f"{stem}_all.csv", [["名称"], ["完整视图"]])
        paths = self.run_import()
        for source, expected in ((page, "页面正文"), (table, "当前视图"), (all_table, "完整视图")):
            self.assertIn(expected, (self.clean / paths[source]).read_text(encoding="utf-8"))
        self.assertTrue(paths[all_table].stem.endswith("_all"))

    def test_two_same_named_id_databases_keep_their_record_directories(self) -> None:
        sources = []
        for identity, marker in ((self.ID_A, "第一库"), (self.ID_B, "第二库")):
            stem = f"数据库 {identity}"
            record = self.text_file(f"{stem}/条目 {identity}.md", f"# 条目\n\n{marker}\n")
            target = quote(record.as_posix(), safe="/")
            table = self.csv_file(f"{stem}.csv", [["名称", "条目"], [marker, f"[条目]({target})"]])
            sources.append((table, record, marker))
        paths = self.run_import()
        for table, record, marker in sources:
            self.assertEqual(paths[record].parent.name, paths[table].stem)
            self.assertIn(marker, (self.clean / paths[table]).read_text(encoding="utf-8"))
            self.assertIn(marker, (self.clean / paths[record]).read_text(encoding="utf-8"))

    def test_all_csv_uses_database_directory_without_all_suffix(self) -> None:
        stem = f"数据库 {self.ID_A}"
        record = self.text_file(f"{stem}/条目 {self.ID_B}.md", "# 条目\n")
        table = self.csv_file(f"{stem}_all.csv", [["条目"], [f"[条目]({quote(record.as_posix(), safe='/')})"]])
        paths = self.run_import()
        self.assertEqual(paths[table], Path("数据库_all.md"))
        self.assertEqual(paths[record], Path("数据库/条目.md"))

    def test_local_csv_image_target_is_rewritten_with_attachment_path(self) -> None:
        folder = f"数据库 {self.ID_A}"
        image = Path(folder) / "图片 small.png"
        image_path = self.raw / image
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"image fixture")
        table = self.csv_file(f"{folder}.csv", [["图片"], [f"![图片]({quote(image.as_posix(), safe='/')})"]])
        paths = self.run_import()
        rendered = (self.clean / paths[table]).read_text(encoding="utf-8")
        self.assertIn(f"![图片]({quote(paths[image].as_posix(), safe='/')})", rendered)

    def test_case_insensitive_csv_suffix_and_natural_collision_name_survive(self) -> None:
        table = self.csv_file("目录.CSV", [["名称"], ["表格内容"]])
        page = self.text_file("目录.md", "# 目录\n")
        numbered = self.text_file("目录-2.md", "# 目录-2\n")
        paths = self.run_import()
        self.assertEqual(paths[table].suffix, ".md")
        self.assertTrue((self.clean / paths[page]).is_file())
        self.assertEqual(paths[numbered], Path("目录-2.md"))

    def test_bare_local_image_may_be_relative_to_export_root(self) -> None:
        folder = Path("吃谷") / f"数据库 {self.ID_A}"
        image = folder / "图片 small.png"
        image_path = self.raw / image
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"image fixture")
        table = self.csv_file(
            Path("吃谷") / f"数据库 {self.ID_A}_all.csv",
            [["名称", "图片"], ["小卡", image.as_posix()]],
        )
        paths = self.run_import()
        rendered = (self.clean / paths[table]).read_text(encoding="utf-8")
        relative_image = paths[image].relative_to(paths[table].parent).as_posix()
        self.assertIn(f"![图片]({quote(relative_image, safe='/')})", rendered)

    def test_bare_image_stale_spaces_match_previously_cleaned_attachment(self) -> None:
        image = Path("吃谷/曾经-空格/图片-small.png")
        image_path = self.raw / image
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"image fixture")
        table = self.csv_file(
            "吃谷/曾经-空格_all.csv",
            [["名称", "图片"], ["小卡", "吃谷/曾经 空格/图片 small.png"]],
        )
        paths = self.run_import()
        rendered = (self.clean / paths[table]).read_text(encoding="utf-8")
        relative_image = paths[image].relative_to(paths[table].parent).as_posix()
        self.assertIn(f"![图片]({quote(relative_image, safe='/')})", rendered)


if __name__ == "__main__":
    unittest.main()
