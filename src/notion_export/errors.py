"""导入错误。"""

from __future__ import annotations


class ImportFailure(RuntimeError):
    """导入数据不安全或不符合预期时中止操作。"""
