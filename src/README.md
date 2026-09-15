# Notion 导入工具

将 Notion 导出的 Markdown ZIP 导入项目，清理文件名、转换 CSV 表格和图片语法，并修复内部链接。

在项目根目录运行：

```bash
python src/restore_notion_export.py
python src/restore_notion_export.py /path/to/notion-export.zip --dry-run
python3 src/restore_notion_export.py /path/to/notion-export.zip
```

省略 ZIP 参数时，自动选择项目根目录中唯一的 ZIP。即使从其他工作目录启动脚本，也会导入脚本所在的项目根目录。相对 ZIP 参数仍相对于当前工作目录解析。

`--dry-run` 只解压、转换和校验。正式导入只替换 ZIP 包含的根页面及其配套目录；`src`、测试脚本、点号开头的配置和根目录 ZIP 受保护。普通 CSV 和 `_all.csv` 分别生成 Markdown 表格；同名文件自动消歧，内部链接随之更新。

| 模块 | 职责 |
| --- | --- |
| `restore_notion_export.py` | 命令行启动入口 |
| `notion_export/cli.py` | 参数解析、项目根目录定位、导入流程调度与错误输出 |
| `notion_export/archive.py` | ZIP 选择、安全解压与嵌套导出展开 |
| `notion_export/paths.py` | Notion ID 清理、文件名规范化与路径冲突处理 |
| `notion_export/markdown.py` | Markdown 链接解析、图片转换与内部链接改写 |
| `notion_export/csv_tables.py` | CSV 解析、表格生成与单元格转义 |
| `notion_export/validation.py` | 本地链接及残留 Notion ID 校验 |
| `notion_export/importer.py` | 构建导入目录、替换项目内容与失败回滚 |
| `notion_export/errors.py` | 导入异常定义 |
| `text/` | 按模块组织的单元回归与临时项目端到端测试 |

运行测试：

```bash
python -B -m unittest discover -s src/text -t . -v
```

测试范围和单模块运行方式见 [回归测试说明](text/README.md)。
