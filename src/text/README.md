# Notion 导入回归测试

在项目根目录运行完整测试：

```bash
python -B -m unittest discover -s src/text -t . -v
```

也支持默认测试发现：

```bash
python -B -m unittest discover -v
```

测试仅依赖 Python 标准库。ZIP、Markdown、CSV 和项目替换用例都在临时目录中生成，不需要真实导出包或网络连接。`-B` 避免生成 Python 缓存文件。

| 测试模块 | 回归范围 |
| --- | --- |
| `test_archive.py` | ZIP 选择、内容完整性、重复文件、路径越界、符号链接、大小限制、嵌套多分卷与深度边界 |
| `test_paths.py` | Notion ID 清理、标题点号、编码、名称冲突、页面与附件目录分组 |
| `test_markdown.py` | 图片识别与转换、代码保护、链接目标与标题、引用式链接、URL 编码和 CSV 路径兼容 |
| `test_csv_import.py` | CSV 行列、空值与空白、引号换行、字符转义、图片、数据库重名及附件链接 |
| `test_validation.py` | 本地链接存在性、越界链接、错误汇总、残留 ID、远程链接和代码跳过 |
| `test_importer.py` | 空导出、二进制附件、无效 UTF-8、损坏 CSV、跨单元格代码标记影响链接改写 |
| `test_notion_cli.py` | 从其他工作目录启动、项目根定位、干跑、导入范围、受保护文件、失败回滚和重复导入 |

单独运行一个模块：

```bash
python -B -m unittest src.text.test_archive -v
```

失败用例会报告具体输入和异常；测试不通过时应先排查行为变化，再决定是否需要调整实现或测试。
