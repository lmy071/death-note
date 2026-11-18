#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图鉴条目 -> 文件名的统一规则（抓取、索引、站点生成脚本共用）。

图片名形如：
    0001-妙蛙种子.png
    0003_1-超级妙蛙花.png
    0003_2-妙蛙花-超极巨化.png
"""
import re

ILLEGAL = '<>:"/\\|?*'


def safe(s):
    s = (s or "").strip()
    for ch in ILLEGAL:
        s = s.replace(ch, "-")
    s = re.sub(r"[\x00-\x1f]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("- ")
    return s


def image_stem(rec):
    """条目 -> 图片文件名主干（不含扩展名）。"""
    parts = [rec.get("id", ""), (rec.get("name") or "").strip()]
    form = (rec.get("form_name") or "").strip()
    if form:
        parts.append(form)
    return safe("-".join(p for p in parts if p))


def image_file(rec, ext=".png"):
    return image_stem(rec) + ext
