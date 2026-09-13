#!/usr/bin/env python3
"""导入 Notion ZIP：python src/restore_notion_export.py [ZIP] [--dry-run]。"""

if __package__:
    from .notion_export.cli import run
else:
    from notion_export.cli import run


if __name__ == "__main__":
    raise SystemExit(run())
