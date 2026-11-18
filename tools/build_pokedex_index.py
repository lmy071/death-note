#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据抓取结果生成 README.md 索引与 pokedex.csv 汇总表。

用法:
    python tools/build_pokedex_index.py --dir pokemon-pokedex
"""
import argparse
import csv
import json
import os
import re
import sys


def natural_key(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def load(root):
    records = []
    data_dir = os.path.join(root, "data")
    for fn in os.listdir(data_dir):
        if fn.endswith(".json"):
            with open(os.path.join(data_dir, fn), encoding="utf-8") as f:
                records.append(json.load(f))
    records.sort(key=lambda r: natural_key(r.get("id", "")))
    return records


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.dir)
    records = load(root)

    with open(os.path.join(root, "pokedex.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["图鉴编号", "条目ID", "名称", "样子", "属性", "身高", "体重",
                    "分类", "性别", "特性", "图鉴说明数", "图片", "来源"])
        for r in records:
            w.writerow([
                r.get("dex_no", ""),
                r.get("id", ""),
                r.get("name", ""),
                r.get("form_name", ""),
                " / ".join(r.get("types", [])),
                r.get("height", ""),
                r.get("weight", ""),
                r.get("category", ""),
                r.get("gender", ""),
                " / ".join(a["name"] for a in r.get("abilities", [])),
                len(r.get("dex_entries", [])),
                os.path.basename(r.get("image_file", "")),
                r.get("source", ""),
            ])

    dex_numbers = {r.get("dex_no", "????") for r in records}

    lines = []
    lines.append("# 宝可梦官方图鉴离线存档（简体中文）\n")
    lines.append("数据来源：宝可梦官方网站中文图鉴 <https://www.pokemon.cn/play/pokedex/>"
                 "（页面由 <https://dex.pokemon.cn/play/pokedex/> 提供）。\n")
    lines.append("本目录由脚本自动抓取生成，仅供个人离线查阅；宝可梦相关内容版权归 "
                 "The Pokémon Company / 任天堂 / GAME FREAK 所有。\n")
    lines.append("## 目录结构\n")
    lines.append("| 路径 | 内容 |")
    lines.append("| --- | --- |")
    lines.append("| `index.html` | 离线浏览页：卡片网格 + 名称/编号/属性搜索 + 属性筛选（双击即可打开） |")
    lines.append("| `pages/` | 每个条目一个详情页（含立绘、特性、图鉴说明、能力条、样子、进化） |")
    lines.append("| `data/` | 每个条目一份结构化 JSON（属性、特性、图鉴说明、能力条、样子、进化等） |")
    lines.append("| `markdown/` | 每个条目一份可直接阅读的 Markdown |")
    lines.append("| `images/` | 官网立绘 PNG，文件名形如 `0001-妙蛙种子.png` |")
    lines.append("| `raw_html/` | 原始页面 HTML，便于复查 |")
    lines.append("| `pokedex.csv` | 全部条目的一览表（可用 Excel 打开） |")
    lines.append("| `_meta/` | 抓取日志与形态 ID 探测结果 |")
    lines.append("")
    lines.append("## 统计\n")
    lines.append(f"- 条目总数：{len(records)}（图鉴编号 {len(dex_numbers)} 个，"
                 f"No.{records[0].get('dex_no')} – No.{records[-1].get('dex_no')}）")
    lines.append(f"- 独立「样子」条目：{sum(1 for r in records if '_' in r.get('id', ''))}")
    lines.append(f"- 已下载立绘：{sum(1 for r in records if r.get('image_file'))} 张 PNG")
    lines.append(f"- 图鉴说明段落合计：{sum(len(r.get('dex_entries', [])) for r in records)} 条")
    lines.append(f"- 含进化链的条目：{sum(1 for r in records if r.get('evolutions'))}")
    lines.append("")
    lines.append("## 文件命名\n")
    lines.append("立绘文件名统一为「编号-名称」，形态条目再加样子名，在资源管理器里可直接认图：\n")
    lines.append("| 条目 | 文件名 |")
    lines.append("| --- | --- |")
    lines.append("| No.0001 妙蛙种子 | `0001-妙蛙种子.png` |")
    lines.append("| No.0003_1 超级妙蛙花 | `0003_1-超级妙蛙花.png` |")
    lines.append("| No.0003_2 妙蛙花（超极巨化） | `0003_2-妙蛙花-超极巨化.png` |")
    lines.append("| No.0892_2 武道熊师（一击流／超极巨化） | `0892_2-武道熊师-一击流／超极巨化.png` |")
    lines.append("")
    lines.append("名称中的 `/` 会替换成 `-`（Windows 文件名不允许），所以「伽勒尔的样子/达摩模式」写作")
    lines.append("`0555_3-达摩狒狒-伽勒尔的样子-达摩模式.png`。`data/*.json` 的 `image_file`、")
    lines.append("`markdown/*.md`、`pages/*.html`、`index.html`、`pokedex.csv` 里的图片引用使用同一套文件名。")
    lines.append("")
    lines.append("## 重新抓取\n")
    lines.append("```powershell")
    lines.append("# 1) 抓取全部条目（基础编号 0001-1025 会顺带发现形态条目）")
    lines.append("python tools/scrape_pokedex.py --out pokemon-pokedex --delay 0.3")
    lines.append("# 2) 生成 README.md + pokedex.csv")
    lines.append("python tools/build_pokedex_index.py --dir pokemon-pokedex")
    lines.append("# 3) 生成离线浏览页 index.html + pages/")
    lines.append("python tools/build_pokedex_site.py --dir pokemon-pokedex")
    lines.append("# 4) 校验完整性")
    lines.append("python tools/verify_pokedex.py --dir pokemon-pokedex")
    lines.append("```")
    lines.append("")
    lines.append("## 条目索引\n")
    lines.append("| 编号 | 名称 | 样子 | 属性 | Markdown | 图片 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for r in records:
        md = f"[{r['id']}](markdown/{r['id']}.md)"
        img_name = os.path.basename(r.get("image_file", ""))
        img = f"[PNG](images/{img_name})" if img_name else ""
        lines.append(f"| {r.get('dex_no','')} | {r.get('name','')} | {r.get('form_name','')} "
                     f"| {' / '.join(r.get('types', []))} | {md} | {img} |")
    lines.append("")
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"records={len(records)} dex_numbers={len(dex_numbers)} -> README.md, pokedex.csv")


if __name__ == "__main__":
    main()
