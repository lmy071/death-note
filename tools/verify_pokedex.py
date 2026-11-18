#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验抓取完整性：基础编号 0001-1025 是否齐全、图片是否有效、字段缺失统计。"""
import argparse
import json
import os
import re
import sys
from collections import Counter

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.dir)

    data_dir = os.path.join(root, "data")
    img_dir = os.path.join(root, "images")
    recs = {}
    for fn in os.listdir(data_dir):
        if fn.endswith(".json"):
            with open(os.path.join(data_dir, fn), encoding="utf-8") as f:
                recs[fn[:-5]] = json.load(f)

    base = [f"{i:04d}" for i in range(1, 1026)]
    missing_base = [b for b in base if b not in recs]
    forms = [k for k in recs if "_" in k]
    print(f"总条目: {len(recs)}  基础编号: {len(base) - len(missing_base)}/1025  形态条目: {len(forms)}")
    if missing_base:
        print(f"缺失基础编号 ({len(missing_base)}): {' '.join(missing_base)}")

    bad_img = []
    for k, r in recs.items():
        name = os.path.basename(r.get("image_file", ""))
        if not name:
            bad_img.append(k + "(no-ref)")
            continue
        p = os.path.join(img_dir, name)
        if not os.path.exists(p):
            bad_img.append(k + "(missing)")
        elif os.path.getsize(p) < 1024:
            bad_img.append(k + "(tiny)")
    print(f"缺图片: {len(bad_img)} {bad_img[:20]}")

    on_disk = set(os.listdir(img_dir))
    referenced = {os.path.basename(r.get("image_file", "")) for r in recs.values()} - {""}
    orphan = sorted(on_disk - referenced)
    print(f"孤儿图片: {len(orphan)} {orphan[:20]}")
    wrong_name = [n for n in referenced if not re.match(r"^\d{4}", n)]
    print(f"命名不合规: {len(wrong_name)} {wrong_name[:20]}")

    empty = Counter()
    for k, r in recs.items():
        for field in ("name", "types", "height", "weight", "category", "gender",
                      "abilities", "dex_entries", "stat_bars", "weaknesses"):
            v = r.get(field)
            if not v:
                empty[field] += 1
    print("空字段统计:", dict(empty))

    noimg_url = sum(1 for r in recs.values() if not r.get("image_url"))
    print("无 image_url:", noimg_url)

    # 检查图片文件是否为合法 PNG
    broken = []
    for k, r in recs.items():
        name = os.path.basename(r.get("image_file", ""))
        p = os.path.join(img_dir, name) if name else ""
        if p and os.path.exists(p):
            with open(p, "rb") as f:
                head = f.read(8)
            if head[:4] != b"\x89PNG":
                broken.append(k)
    print("损坏图片:", len(broken), broken[:20])

if __name__ == "__main__":
    main()
